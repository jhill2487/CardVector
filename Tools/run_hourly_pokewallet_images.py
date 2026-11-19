#!/usr/bin/env python3
"""Hourly, quota-aware PokéWallet image ingestion across all complete English catalogs.

Only images consume the precious image-request budget: metadata stays in batched
catalog imports. Approved artwork is never downloaded again. Finish one set before
proceeding to the next, retry incomplete sets on later hours, and automatically
approve fully verified sets without a human reviewer impersonation.
"""
import json
import os
import re
import urllib.parse

import import_pokewallet_set_images as importer
import autoapprove_pokewallet_set as approval
import pokewallet_api_budget as quota

MAX_REQUESTS_PER_RUN = 100
REST_PAGE = 1000


def records(table, fields, headers, *, order="set_id"):
    output = []
    for offset in range(0, 30000, REST_PAGE):
        query = urllib.parse.urlencode({
            "select": fields, "order": order + ".asc",
            "limit": str(REST_PAGE), "offset": str(offset),
        })
        chunk = json.loads(importer.request(importer.DB + table + "?" + query, headers))
        if not isinstance(chunk, list):
            raise RuntimeError("Unexpected catalog response for " + table)
        output.extend(chunk)
        if len(chunk) < REST_PAGE:
            return output
    raise RuntimeError("Catalog pagination limit exceeded")


def slug_for(name):
    """Convert a provider set name to an R2 folder without set-specific mappings."""
    normalized = re.sub(r"^[A-Za-z]{1,6}[0-9]{0,3}:\s*", "", str(name))
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Unsafe or empty set folder name")
    return slug


def eligible_sets(headers):
    languages = {str(x["set_id"]): x for x in
                 records("cv_admin_set_languages",
                         "set_id,language,expected_card_count", headers)}
    cards = records("cv_admin_pokewallet_catalog",
                    "set_id,set_name,provider_id,card_name,card_number,image_status,image_path",
                    headers, order="provider_id")
    reviews = {r["provider_id"]: r for r in
               records("cv_admin_image_reviews",
                       "provider_id,review_status,candidate_path", headers,
                       order="provider_id")}
    grouped = {}
    for c in cards:
        grouped.setdefault(str(c["set_id"]), []).append(c)

    result = []
    for set_id, group in grouped.items():
        info = languages.get(set_id) or {}
        if info.get("language") != "eng":
            continue
        expected = info.get("expected_card_count")
        # Never claim a set complete while its card identities may be missing.
        if expected is None or int(expected) != len(group):
            continue
        if not all(c.get("card_name") and c.get("card_number") for c in group):
            continue
        missing = importer.unprocessed_cards(group, reviews)
        if not missing:
            continue
        if any(not importer.VALID_ID.fullmatch(c["provider_id"]) for c in missing):
            print("Skipping invalid provider identity in set " + set_id, flush=True)
            continue
        partially_staged = sum(1 for c in group
            if (reviews.get(c["provider_id"]) or {}).get("review_status") == "pending_review"
            and str((reviews.get(c["provider_id"]) or {}).get("candidate_path") or "").startswith("pokewallet/"))
        result.append({
            "set_id": set_id, "slug": slug_for(group[0]["set_name"]),
            "count": len(group), "missing": len(missing),
            "partially_staged": partially_staged,
        })
    # Continue any partially staged set first, then finish the smallest remaining
    # whole set efficiently. Optional administrative priority changes ORDER only.
    preferred = os.environ.get("CARDVECTOR_IMAGE_PRIORITY_SET", "")
    result.sort(key=lambda s:(
        0 if preferred and s["set_id"] == preferred else 1,
        0 if s["partially_staged"] else 1,
        s["missing"], -s["count"], int(s["set_id"])))
    return result


def run():
    for key in ("SUPABASE_SERVICE_ROLE_KEY","POKEWALLET_API_KEY",
                "R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET"):
        if not os.getenv(key):
            raise RuntimeError("Missing required image importer secret: " + key)
    headers = importer.db_headers()
    candidates = eligible_sets(headers)
    print(json.dumps({"eligible_sets":len(candidates),
                      "next_set":candidates[0] if candidates else None}), flush=True)
    ready=sum(s["missing"] for s in candidates)
    daily_cap=quota.choose_image_cap(headers,ready)
    today=quota.current(headers)
    remaining_daily=daily_cap-int(today["image_requests"]) if today else daily_cap
    budget=min(MAX_REQUESTS_PER_RUN,max(0,remaining_daily))
    print(json.dumps({"image_ready":ready,"daily_image_cap":daily_cap,
                      "daily_images_reserved":daily_cap-remaining_daily,
                      "hourly_budget":budget}),flush=True)
    if budget==0:
        print("Image allocation reached; remaining requests belong to metadata",flush=True)
        return
    runs = []
    def reserve_image():
        result=quota.reserve(headers,"image",daily_cap)
        return result["allowed"]
    r2 = importer.r2_client()
    for candidate in candidates:
        if budget <= 0:
            break
        importer.SET_ID = candidate["set_id"]
        importer.SET_SLUG = candidate["slug"]
        missing = candidate["missing"]
        while missing > 0 and budget > 0:
            # The reusable importer honors provider hourly/day remaining headers;
            # hourly scheduler does NOT sleep past a reset or waste a free-tier job.
            batch = importer.run(limit=min(100, budget, missing), delay=5.0, before_request=reserve_image)
            attempted = batch["attempted"]
            budget -= attempted
            runs.append({"set_id":candidate["set_id"], "attempted":attempted,
                         "uploaded":batch["counts"]["uploaded"],
                         "remaining":batch["remaining_unstaged"]})
            if batch.get("budget_exhausted"):
                print("Image daily reservation limit reached",flush=True)
                break
            if not batch["remaining_unstaged"]:
                approved, status = approval.approve_set(
                    candidate["set_id"], headers, r2, os.environ["R2_BUCKET"])
                print(json.dumps({"set_id":candidate["set_id"],
                                  "approved":approved,"status":status}), flush=True)
                break
            day = batch.get("quota_remaining_day")
            hour = batch.get("quota_remaining_hour")
            if day is None or hour is None or day <= 0 or hour <= 0:
                print("Pausing imports until next quota window", flush=True)
                print(json.dumps({"runs":runs,"requests_attempted":MAX_REQUESTS_PER_RUN-budget}))
                return
            if attempted == 0 or batch["counts"]["uploaded"] == 0:
                # Failed/unavailable records remain pending for a later retry,
                # rather than repeatedly spending requests on them in one hour.
                break
            missing = batch["remaining_unstaged"]
    print(json.dumps({"runs":runs,"requests_attempted":MAX_REQUESTS_PER_RUN-budget}))


if __name__ == "__main__":
    run()
