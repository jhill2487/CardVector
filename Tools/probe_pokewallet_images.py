#!/usr/bin/env python3
"""Read-only, printing-specific PokéWallet image availability probe.

Identifies whether a provider has an image for exact print IDs. Does not
download/store image files, change database rows, or imply stamp verification.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

DB_URL="https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/"
API_URL="https://api.pokewallet.io"
VALID_ID=re.compile(r"^(?:pk_)?[a-f0-9]{32,128}$")
USER_AGENT="CardVector-Image-Source-Availability/1.0"


def select_records(rows, names, max_records):
    """Take only explicitly requested unresolved records (conservative default)."""
    targets={x.strip().casefold() for x in names.split(";") if x.strip()}
    if not targets:
        raise ValueError("Specify test card names to prevent unbounded API requests")
    if max_records<1 or max_records>5:
        raise ValueError("Limit must be from 1 to 5")
    results=[]
    for row in rows:
        if (str(row.get("card_name","")).casefold() not in targets
                or row.get("image_status") not in ("pending","missing")):
            continue
        pid=str(row.get("provider_id",""))
        if not VALID_ID.fullmatch(pid):
            continue
        results.append(row)
    return sorted(results,key=lambda row:row["card_name"])[:max_records]


def probe_image(provider_id, key, opener=urllib.request.urlopen):
    """Read only a small JPEG/WebP signature, never image content to disk."""
    if not VALID_ID.fullmatch(provider_id):
        raise ValueError("Invalid provider ID")
    req=urllib.request.Request(
        API_URL+"/images/"+urllib.parse.quote(provider_id,safe="")+"?size=low",
        headers={"X-API-Key":key,"User-Agent":USER_AGENT},
        method="GET",
    )
    try:
        with opener(req,timeout=25) as response:
            content_type=response.headers.get("Content-Type","").lower().split(";")[0].strip()
            signature=response.read(16)
            valid=(content_type=="image/jpeg" and signature.startswith(b"\xff\xd8\xff")) or (
                content_type=="image/webp" and signature[:4]==b"RIFF" and signature[8:12]==b"WEBP")
            return "available_unverified" if response.status==200 and valid else "invalid_image_response"
    except urllib.error.HTTPError as error:
        if error.code in (404,410):return "not_available"
        if error.code==429:return "rate_limited"
        return "provider_http_"+str(error.code)
    except (urllib.error.URLError,TimeoutError):
        return "network_error"


def query_rows(set_id,key,opener=urllib.request.urlopen):
    if not re.fullmatch(r"\d{1,10}",set_id):
        raise ValueError("Invalid set ID")
    params=urllib.parse.urlencode({"set_id":"eq."+set_id,
        "select":"provider_id,set_id,card_name,card_number,image_status",
        "limit":"1000"})
    req=urllib.request.Request(DB_URL+"cv_admin_pokewallet_catalog?"+params,
        headers={"apikey":key,"Authorization":"Bearer "+key,
                 "User-Agent":USER_AGENT})
    with opener(req,timeout=25) as response:
        return json.load(response)


def main():
    pw_key=os.environ.get("POKEWALLET_API_KEY")
    db_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not pw_key or not db_key:
        raise SystemExit("Missing server-side image-probe credentials")
    set_id=os.environ.get("CARDVECTOR_DISCOVERY_SET_ID","24451")
    names=os.environ.get("CARDVECTOR_DISCOVERY_NAMES",
        "Meganium 001 Staff;Riolu 010 Pokemon Center Exclusive")
    maximum=int(os.environ.get("CARDVECTOR_DISCOVERY_LIMIT","2"))
    records=select_records(query_rows(set_id,db_key),names,maximum)
    output=[]
    for row in records:
        status=probe_image(row["provider_id"],pw_key)
        output.append({"set_id":row["set_id"],"card_name":row["card_name"],
            "card_number":row["card_number"],"status":status,
            "note":"Provider binary exists; printing stamp and usage rights not verified" if status=="available_unverified"
                else "No image approval or catalog change"})
        if status=="rate_limited":break
    print(json.dumps({"probe":"read_only","checked":len(output),
        "results":output,"writes":0},sort_keys=True))
    if len(records)==0:raise SystemExit("No matching unresolved records available")

if __name__=="__main__":
    main()
