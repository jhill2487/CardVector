"""Cross-workflow PokéWallet API request ledger (server-side, UTC day).

Reservations are atomic in Supabase and are made BEFORE every provider request.
Provider rate-limit headers remain the ultimate authority. An unsuccessful
provider call still consumes a reservation because it may count against quota.
"""
import json
import urllib.parse
from datetime import datetime, timezone, timedelta

DB = "https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/"


def utc_day():
    return datetime.now(timezone.utc).date().isoformat()


def current(headers, day=None):
    from import_pokewallet_set_images import request
    day = day or utc_day()
    url = DB + "cv_admin_pokewallet_api_budget?" + urllib.parse.urlencode({
        "usage_day": "eq." + day,
        "select": "usage_day,image_requests,metadata_requests,image_cap",
    })
    entries = json.loads(request(url, headers))
    return entries[0] if entries else None


def choose_image_cap(headers, image_ready):
    """After a metadata-replenishment day, use all 1,000 for images if ready.

    Keep allocating 1,000-image days while the complete-metadata queue has
    at least 1,000 missing images. Otherwise return to 900+metadata.
    """
    today = utc_day()
    previous = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    last = current(headers, previous)
    today_row = current(headers, today)
    if today_row:
        return int(today_row["image_cap"])
    if image_ready >= 1000 and last and (
        int(last.get("metadata_requests") or 0) > 0 or int(last.get("image_cap") or 0) == 1000
    ):
        return 1000
    return 900


def reserve(headers, kind, image_cap=900, day=None):
    from import_pokewallet_set_images import request
    day = day or utc_day()
    body = {"p_kind": kind, "p_day": day, "p_image_cap": image_cap}
    result = json.loads(request(
        DB + "rpc/cv_reserve_pokewallet_api_request",
        {**headers, "Prefer": "return=representation"},
        method="POST", payload=body
    ))
    if not isinstance(result, dict) or "allowed" not in result:
        raise RuntimeError("Invalid API budget reservation response")
    return result


def metadata_allowance(headers):
    row = current(headers)
    if not row:
        return 0
    if int(row["image_requests"]) < int(row["image_cap"]):
        return 0
    return min(100, max(0,1000-int(row["image_requests"])-int(row["metadata_requests"])))
