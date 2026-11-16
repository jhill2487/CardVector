#!/usr/bin/env python3
"""Conservative reusable PokéWallet image import into R2 review candidates.

Never approves artwork or edits canonical catalog matches. Each successful upload
is idempotent and offered to the existing administrator image review page.
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

SET_ID="24461"
SET_SLUG="mega-evolution-energies"
DB="https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/"
PW="https://api.pokewallet.io/images/"
VALID_ID=re.compile(r"^pk_[a-f0-9]{40,128}$",re.I)
SAFE_NUMBER=re.compile(r"^(?:\d{1,3}(?:/\d{1,3})?|[RGB]/RGB)$",re.I)

def image_type(data):
    if len(data)<256 or len(data)>1_000_000:
        raise ValueError("Image length out of range")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data)<24:
            raise ValueError("Incomplete PNG")
        width=int.from_bytes(data[16:20],"big")
        height=int.from_bytes(data[20:24],"big")
        if not 100<=width<=2000 or not 100<=height<=3000:
            raise ValueError("PNG dimensions out of range")
        return "png","image/png"
    if data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"):
        return "jpg","image/jpeg"
    if data.startswith(b"RIFF") and data[8:12]==b"WEBP":
        return "webp","image/webp"
    raise ValueError("Unexpected image signature")

def request(url, headers, *, method="GET", payload=None):
    body=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(url,headers=headers,method=method,data=body)
    with urllib.request.urlopen(req,timeout=35) as res:
        return res.read()

def db_headers():
    key=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return {"apikey":key,"Authorization":"Bearer "+key,
            "Content-Type":"application/json","User-Agent":"CardVector-Set-Images/1.0"}

def rows(headers):
    query=urllib.parse.urlencode({"set_id":"eq."+SET_ID,
        "select":"provider_id,card_name,card_number,image_status,image_path",
        "order":"card_number.asc","limit":"1000"})
    cards=json.loads(request(DB+"cv_admin_pokewallet_catalog?"+query,headers))
    # The API orders text numbers lexically (1, 10, 100, ... 2).
    # Sort in Python so small numbered cards and their special printings
    # are imported together, while preserving card identities.
    def key(card):
        label=str(card.get("card_number") or "").strip()
        match=re.fullmatch(r"([A-Za-z]*)([0-9]+)(.*)",label)
        if match:
            return (match.group(1).lower(),int(match.group(2)),match.group(3),
                    str(card.get("card_name") or "").lower(),str(card.get("provider_id") or ""))
        return (label.lower(),float("inf"),"","","")
    return sorted(cards,key=key)

def existing_reviews(headers,cards):
    # Review table holds many sets; the first 500 rows do not represent Delta Reign.
    # Query exactly this set's provider IDs in URL-safe chunks.
    reviews={}
    ids=[card["provider_id"] for card in cards]
    for i in range(0,len(ids),30):
        chunk=ids[i:i+30]
        query=urllib.parse.urlencode({"select":"provider_id,review_status,candidate_path,notes",
            "provider_id":"in.("+",".join(chunk)+")","limit":"100"})
        data=json.loads(request(DB+"cv_admin_image_reviews?"+query,headers))
        for row in data:
            if row.get("provider_id") in chunk:
                reviews[row["provider_id"]]=row
    return reviews

def rejected_legacy_stamp(card,review):
    """A prior archive image was explicitly rejected for a stamped printing.
    Preserve rejection evidence in notes; only an exact PokéWallet upload may
    enter pending review. Never replace an approved or matched record.
    """
    name=str(card.get("card_name") or "").lower()
    path=str((review or {}).get("candidate_path") or "")
    return (bool(re.search(r"(staff|pokemon center exclusive|pokémon center exclusive|stamped)$",name))
            and (review or {}).get("review_status")=="rejected"
            and path.startswith("Pokemon TCG/"))

def unprocessed_cards(cards,reviews):
    return [card for card in cards if
            card["image_status"]!="matched" and not card["image_path"] and
            (card["provider_id"] not in reviews or
             (reviews[card["provider_id"]].get("review_status")=="pending_review" and
              not reviews[card["provider_id"]].get("candidate_path")) or
             rejected_legacy_stamp(card,reviews[card["provider_id"]]))]

def path_for(card,ext):
    pid=card["provider_id"]
    number=card["card_number"]
    if not VALID_ID.fullmatch(pid) or not SAFE_NUMBER.fullmatch(number):
        raise ValueError("Unexpected card identity")
    return "pokewallet/"+SET_SLUG+"/"+number.replace("/","-")+"_"+pid[3:19]+"."+ext

def r2_client():
    import boto3
    from botocore.config import Config
    account=os.environ["R2_ACCOUNT_ID"]
    return boto3.client("s3",endpoint_url="https://"+account+".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",config=Config(signature_version="s3v4",retries={"max_attempts":3}))

def run(limit=1,delay=5.0,provider_id=None):
    if not 1<=limit<=250: raise ValueError("Limit must be between 1 and 250")
    if not 0<=delay<=120: raise ValueError("Invalid delay")
    for key in ("SUPABASE_SERVICE_ROLE_KEY","POKEWALLET_API_KEY",
                "R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET"):
        if not os.getenv(key):
            raise RuntimeError("Missing required secret: "+key)
    headers=db_headers()
    cards=rows(headers)
    if not cards or len(cards)>1000 or any(c["image_status"] not in
        ("pending","missing","needs_review","matched") for c in cards):
        raise RuntimeError("Set catalog missing or unexpectedly changed; no imports made")
    reviews=existing_reviews(headers,cards)
    remaining=unprocessed_cards(cards,reviews)
    if provider_id:
        selected=[c for c in cards if c["provider_id"]==provider_id]
        if len(selected)!=1 or "staff" not in selected[0]["card_name"].lower():
            raise RuntimeError("Selected provider ID is not one staff promo card in this set")
        if selected[0] not in remaining:
            raise RuntimeError("Staff promo already has an image or review decision; preserve existing record")
        remaining=selected
    print("Set "+SET_ID+" image staging: "+str(len(cards)-len(remaining))+
          " existing reviews/matches, "+str(len(remaining))+" not yet staged")
    if not remaining:
        print(json.dumps({"set_id":SET_ID,"attempted":0,"remaining":0,
                          "status":"all catalog records staged or matched; no API requests"}))
        return
    # Validate the bucket/endpoint before any extra PokéWallet image requests.
    # Report only status codes; never print credential values or bucket names.
    bucket=os.environ["R2_BUCKET"]
    if bucket!=bucket.strip() or "/" in bucket or "://" in bucket or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]",bucket):
        raise RuntimeError("R2_BUCKET must be the exact R2 bucket name (no URL, path or whitespace)")
    account=os.environ["R2_ACCOUNT_ID"]
    if account!=account.strip() or not re.fullmatch(r"[a-f0-9]{32}",account,re.I):
        raise RuntimeError("R2_ACCOUNT_ID must be the 32-character Cloudflare account ID")
    client=r2_client()
    try:
        # Object-scoped tokens may lack bucket metadata permissions; test object-list access instead.
        client.list_objects_v2(Bucket=bucket,Prefix="archive/pokewallet/"+SET_SLUG+"/",MaxKeys=1)
        print("R2 object-list preflight succeeded")
    except Exception as exc:
        from botocore.exceptions import ClientError
        if isinstance(exc,ClientError):
            status=exc.response.get("ResponseMetadata",{}).get("HTTPStatusCode","unknown")
            code=exc.response.get("Error",{}).get("Code","unknown")
            raise RuntimeError("R2 object-list preflight failed: HTTP "+str(status)+", code "+str(code)+
                ". Verify exact R2_BUCKET name, R2_ACCOUNT_ID, and R2 S3 API token scope.") from None
        # Expose TLS failure category without logging the endpoint/account or credentials.
        from botocore.exceptions import SSLError, EndpointConnectionError, ConnectTimeoutError
        if isinstance(exc,SSLError):
            detail=str(exc).lower()
            if "certificate_verify_failed" in detail or "certificate verify failed" in detail:
                reason="certificate verification failed"
            elif "hostname" in detail or "certificate" in detail:
                reason="TLS hostname or certificate mismatch"
            elif "eof" in detail or "handshake" in detail:
                reason="TLS handshake terminated"
            elif "wrong version number" in detail:
                reason="invalid TLS protocol response"
            else:
                reason="TLS connection failure"
            raise RuntimeError("R2 object-list preflight SSL failure: "+reason+
                ". Verify the R2_ACCOUNT_ID is the account owning the bucket and the S3 endpoint is correct.") from None
        if isinstance(exc,(EndpointConnectionError,ConnectTimeoutError)):
            raise RuntimeError("R2 object-list preflight failed to connect to the S3 endpoint") from None
        raise RuntimeError("R2 object-list preflight encountered "+type(exc).__name__) from None
    counts={"available":0,"unavailable":0,"rate_limited":0,
            "skipped":0,"uploaded":0,"errors":0}
    attempts=0
    quota_remaining=None
    quota_hourly=None
    quota_guard=20  # Leave room for concurrent catalog activity.
    hourly_waits=0
    probe_after_wait=False
    for card in remaining:
        if attempts>=limit: break
        if attempts>0:
            if quota_remaining is None or quota_hourly is None or quota_remaining<=quota_guard:
                print("Stopping before next request: daily quota headroom not verified or below safety margin",flush=True)
                break
            if quota_hourly<=quota_guard and not probe_after_wait:
                if os.getenv("CARDVECTOR_WAIT_HOURLY_RESET")=="1" and hourly_waits<2:
                    hourly_waits+=1
                    print("Hourly quota headroom low; pausing inside the same batch before one quota-checked probe",flush=True)
                    time.sleep(3700)
                    probe_after_wait=True
                else:
                    print("Stopping before next request: hourly quota headroom below safety margin",flush=True)
                    break
        probe_after_wait=False
        pid=card["provider_id"]
        if not VALID_ID.fullmatch(pid):
            counts["errors"]+=1
            continue
        attempts+=1
        if attempts>1 and delay:time.sleep(delay)
        req=urllib.request.Request(PW+urllib.parse.quote(pid,safe="")+"?size=low",
            headers={"X-API-Key":os.environ["POKEWALLET_API_KEY"],
                     "User-Agent":"CardVector-Set-Images/1.0"})
        try:
            with urllib.request.urlopen(req,timeout=25) as response:
                # These headers track all API calls, unlike the catalog's daily card count.
                day=response.headers.get("X-RateLimit-Remaining-Day")
                hour=response.headers.get("X-RateLimit-Remaining-Hour")
                quota_remaining=int(day) if day is not None and day.isdecimal() else None
                quota_hourly=int(hour) if hour is not None and hour.isdecimal() else None
                data=response.read(1_000_001)
            ext,mime=image_type(data)
            counts["available"]+=1
        except urllib.error.HTTPError as exc:
            day=exc.headers.get("X-RateLimit-Remaining-Day") if exc.headers else None
            hour=exc.headers.get("X-RateLimit-Remaining-Hour") if exc.headers else None
            quota_remaining=int(day) if day is not None and day.isdecimal() else None
            quota_hourly=int(hour) if hour is not None and hour.isdecimal() else None
            if exc.code==429:
                counts["rate_limited"]+=1
                break
            if exc.code in (404,410):
                counts["unavailable"]+=1
                continue
            counts["errors"]+=1
            print("Image HTTP error for card "+card["card_number"]+": "+str(exc.code))
            continue
        except (urllib.error.URLError,TimeoutError,ValueError) as exc:
            counts["errors"]+=1
            print("Image invalid/unavailable for card "+card["card_number"]+": "+str(type(exc).__name__))
            continue
        path=path_for(card,ext)
        object_key="archive/"+path
        # Do not overwrite anything already in R2, including other source images.
        try:
            client.head_object(Bucket=os.environ["R2_BUCKET"],Key=object_key)
        except Exception as exc:
            from botocore.exceptions import ClientError
            if not isinstance(exc,ClientError) or exc.response.get("ResponseMetadata",{}).get("HTTPStatusCode")!=404:
                raise
            client.put_object(Bucket=os.environ["R2_BUCKET"],Key=object_key,
                Body=data,ContentType=mime,CacheControl="public, max-age=86400",
                Metadata={"source":"pokewallet","set-id":SET_ID})
        # Preserve all prior decisions. Only repair an existing pending review
        # with no image, or insert a new pending review if none exists.
        review={"provider_id":pid,"candidate_path":path,
            "review_status":"pending_review",
            "notes":"PokéWallet exact-printing image candidate. Inspect stamp and card identity before approval."}
        try:
            old_review=reviews.get(pid)
            if old_review:
                legacy=rejected_legacy_stamp(card,old_review)
                if not legacy and (old_review.get("review_status")!="pending_review" or old_review.get("candidate_path")):
                    raise RuntimeError("Review changed since preflight; refusing overwrite")
                original=old_review.get("candidate_path")
                query=urllib.parse.urlencode({"provider_id":"eq."+pid,
                    "review_status":"eq.rejected" if legacy else "eq.pending_review",
                    "candidate_path":"eq."+original if legacy else "is.null",
                    "select":"provider_id,candidate_path,review_status"})
                update={"candidate_path":path}
                if legacy:
                    note=(str(old_review.get("notes") or "")+" | Previous rejected R2 image: "+original+"; replacement is PokéWallet exact printing awaiting verification.")[:2000]
                    update.update({"review_status":"pending_review","notes":note})
                updated=json.loads(request(DB+"cv_admin_image_reviews?"+query,
                    {**headers,"Prefer":"return=representation"},
                    method="PATCH",payload=update))
                if len(updated)!=1 or updated[0].get("candidate_path")!=path:
                    raise RuntimeError("Pending image review changed concurrently; no overwrite")
            else:
                query=urllib.parse.urlencode({"on_conflict":"provider_id",
                    "select":"provider_id,candidate_path"})
                inserted=json.loads(request(DB+"cv_admin_image_reviews?"+query,
                    {**headers,"Prefer":"resolution=ignore-duplicates,return=representation"},
                    method="POST",payload=[review]))
                if len(inserted)!=1 or inserted[0].get("candidate_path")!=path:
                    raise RuntimeError("Image review created concurrently; no overwrite")
        except urllib.error.HTTPError as exc:
            counts["errors"]+=1
            print("R2 uploaded, candidate review insert failed for card "+card["card_number"]+
                  " (HTTP "+str(exc.code)+")")
            continue
        counts["uploaded"]+=1
        reviews[pid]=review
        print("Candidate ready for review: "+card["card_name"]+" "+card["card_number"])
        if quota_remaining is None or quota_hourly is None:
            print("Stopping: PokéWallet did not provide both quota headers; cannot verify safe headroom")
            break
        print("PokéWallet quota remaining: day="+str(quota_remaining)+", hour="+str(quota_hourly))
        if min(quota_remaining,quota_hourly)<=quota_guard:
            print("Stopping: PokéWallet request headroom is at or below safety margin")
            break
    still_unstaged=unprocessed_cards(cards,reviews)
    print(json.dumps({"set_id":SET_ID,"attempted":attempts,
        "remaining_unstaged":len(still_unstaged),
        "next_card_number":still_unstaged[0]["card_number"] if still_unstaged else None,
        "counts":counts,"writes":"R2 candidate images and pending reviews; no approvals"},sort_keys=True))
    if counts["rate_limited"]:
        print("Stopped because PokéWallet returned HTTP 429")
    if counts["errors"]:
        raise RuntimeError("One or more image imports failed; see prior safe error summaries")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--set-id",required=True,help="Verified PokéWallet catalog set ID")
    parser.add_argument("--slug",required=True,help="Canonical short R2 folder slug")
    parser.add_argument("--limit",type=int,default=1)
    parser.add_argument("--delay",type=float,default=5.0)
    parser.add_argument("--provider-id",default=None,help="Optional exact Staff promo ID for a single-image pilot")
    args=parser.parse_args()
    if not re.fullmatch(r"[0-9]{2,8}",args.set_id) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",args.slug):
        parser.error("Set ID and slug must be safe, explicit values")
    SET_ID=args.set_id
    SET_SLUG=args.slug
    if args.provider_id and not VALID_ID.fullmatch(args.provider_id):
        parser.error("Invalid provider ID")
    run(args.limit,args.delay,args.provider_id)
