#!/usr/bin/env python3
"""Auto-approve complete sets of exact-identity PokéWallet images after R2 verification.

Universal for all sets. Existing admin-approved artwork remains unchanged.
A single incomplete, invalid or ambiguous card blocks approval for that set.
"""
import argparse
import json
import os
import re
import urllib.parse
import urllib.request

import import_pokewallet_set_images as importer

DB = importer.DB
REVIEW = "cv_admin_image_reviews"
CATALOG = "cv_admin_pokewallet_catalog"
SAFE_SET = re.compile(r"^[0-9]{2,8}$")
SAFE_PATH = re.compile(r"^pokewallet/([a-z0-9]+(?:-[a-z0-9]+)*)/([0-9]{1,3}(?:-[0-9]{1,3})?|[RGB]-RGB)_([a-f0-9]{16})\.(jpg|jpeg|png|webp)$", re.I)


def get(url, headers):
    return json.loads(importer.request(url, headers))


def discover_sets(headers):
    """Find set IDs with pending PokéWallet uploads, paginating all records."""
    pending = []
    for offset in range(0, 20000, 1000):
        q = urllib.parse.urlencode({
            "select": "provider_id",
            "review_status": "eq.pending_review",
            "candidate_path": "like.pokewallet/*",
            "order": "provider_id.asc",
            "limit": "1000",
            "offset": str(offset),
        })
        part = get(DB + REVIEW + "?" + q, headers)
        pending.extend(part)
        if len(part) < 1000:
            break
    if not pending:
        return []
    found = set()
    ids = [row["provider_id"] for row in pending]
    for i in range(0, len(ids), 30):
        q = urllib.parse.urlencode({
            "select": "provider_id,set_id",
            "provider_id": "in.(" + ",".join(ids[i:i+30]) + ")",
            "limit": "100",
        })
        for card in get(DB + CATALOG + "?" + q, headers):
            if SAFE_SET.fullmatch(str(card["set_id"])):
                found.add(str(card["set_id"]))
    return sorted(found, key=int)


def verify_candidate(card, review, r2, bucket, set_id):
    path = str(review.get("candidate_path") or "")
    match = SAFE_PATH.fullmatch(path)
    if not match:
        raise ValueError("Candidate path is not an exact PokéWallet upload")
    slug, _, fingerprint, ext = match.groups()
    if not importer.VALID_ID.fullmatch(card["provider_id"]):
        raise ValueError("Unexpected card provider ID")
    if fingerprint.lower() != card["provider_id"][3:19].lower():
        raise ValueError("Provider ID fingerprint mismatch")
    importer.SET_SLUG = slug
    if importer.path_for(card, ext.lower()).lower() != path.lower():
        raise ValueError("Collector number or provider identity mismatch")
    obj = r2.head_object(Bucket=bucket, Key="archive/" + path)
    metadata = {k.lower():v for k,v in (obj.get("Metadata") or {}).items()}
    if metadata.get("source") != "pokewallet" or metadata.get("set-id") != set_id:
        raise ValueError("Object provenance or set ID mismatch")
    if not 256 <= obj.get("ContentLength", 0) <= 1_000_000:
        raise ValueError("R2 object size invalid")
    if obj.get("ContentType", "").lower() not in ("image/jpeg","image/png","image/webp"):
        raise ValueError("R2 object MIME type invalid")
    return path


def approve_set(set_id, headers, r2, bucket):
    if not SAFE_SET.fullmatch(set_id):
        raise ValueError("Unsafe set ID")
    importer.SET_ID = set_id
    cards = importer.rows(headers)
    if not cards or len(cards) > 1000:
        raise ValueError("Missing or unexpectedly large catalog set")
    reviews = importer.existing_reviews(headers, cards)
    pending = []
    for card in cards:
        pid = card["provider_id"]
        if not card.get("card_name") or not card.get("card_number") or not importer.VALID_ID.fullmatch(pid):
            print("Set " + set_id + ": incomplete card metadata; no approvals")
            return (0, "blocked")
        review = reviews.get(pid)
        if not review or not review.get("candidate_path"):
            print("Set " + set_id + ": missing image for card " + card["card_number"] + "; no approvals")
            return (0, "incomplete")
        if review["review_status"] == "approved":
            # Prior administrator approvals are trusted, even if from R2 archives.
            continue
        if review["review_status"] != "pending_review":
            print("Set " + set_id + ": non-pending review for " + card["card_number"] + "; no approvals")
            return (0, "blocked")
        pending.append((card, review))
    if not pending:
        return (0, "already-approved")
    # Preflight ALL pending uploads before approving ANY in this set.
    try:
        for card, review in pending:
            verify_candidate(card, review, r2, bucket, set_id)
    except Exception as exc:
        print("Set " + set_id + ": image preflight failed (" + type(exc).__name__ + "); no approvals")
        return (0, "blocked")
    approved = 0
    for card, review in pending:
        pid, path = card["provider_id"], review["candidate_path"]
        query = urllib.parse.urlencode({
            "provider_id": "eq." + pid,
            "review_status": "eq.pending_review",
            "candidate_path": "eq." + path,
            "select": "provider_id,review_status",
        })
        note = ("Automatically approved: exact PokéWallet provider-ID upload, matching collector number, "
                "R2 source/set provenance, size and MIME checked; complete set preflight passed.")
        result = importer.request(DB + REVIEW + "?" + query,
            {**headers, "Prefer": "return=representation"},
            method="PATCH", payload={"review_status":"approved", "approval_method":"pokewallet_auto", "notes":note})
        updated = json.loads(result)
        if len(updated) != 1 or updated[0].get("review_status") != "approved":
            raise RuntimeError("Review changed during auto-approval; stopped without overwriting")
        approved += 1
    # The existing SQL trigger synchronizes each newly approved image to the catalog.
    refreshed = importer.existing_reviews(headers, cards)
    if any(refreshed.get(c["provider_id"], {}).get("review_status") != "approved" for c in cards):
        raise RuntimeError("Approval verification failed for set " + set_id)
    print(json.dumps({"set_id":set_id, "catalog_cards":len(cards), "auto_approved":approved, "status":"approved", "audit_method":"pokewallet_auto"}))
    return (approved, "approved")


def main():
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--set-id")
    target.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.set_id and not SAFE_SET.fullmatch(args.set_id):
        parser.error("Invalid set ID")
    for name in ("SUPABASE_SERVICE_ROLE_KEY","R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET"):
        if not os.environ.get(name):
            raise RuntimeError("Missing required secret: " + name)
    headers = importer.db_headers()
    sets = discover_sets(headers) if args.all else [args.set_id]
    r2 = importer.r2_client()
    bucket = os.environ["R2_BUCKET"]
    results = {}
    for set_id in sets:
        approved, status = approve_set(set_id, headers, r2, bucket)
        results[set_id] = {"approved":approved, "status":status}
    print(json.dumps({"sets_checked":len(sets),"results":results},sort_keys=True))


if __name__ == "__main__":
    main()
