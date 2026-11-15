#!/usr/bin/env python3
"""Conservative PokéWallet Delta Reign image import into R2 review candidates.

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

SET_ID="24831"
DB="https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/"
PW="https://api.pokewallet.io/images/"
VALID_ID=re.compile(r"^pk_[a-f0-9]{40,128}$",re.I)
SAFE_NUMBER=re.compile(r"^\d{1,3}(?:/\d{1,3})?$")

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
            "Content-Type":"application/json","User-Agent":"CardVector-Delta-Images/1.0"}

def rows(headers):
    query=urllib.parse.urlencode({"set_id":"eq."+SET_ID,
        "select":"provider_id,card_name,card_number,image_status,image_path",
        "order":"card_number.asc","limit":"500"})
    return json.loads(request(DB+"cv_admin_pokewallet_catalog?"+query,headers))

def existing_review(provider_id,headers):
    query=urllib.parse.urlencode({"provider_id":"eq."+provider_id,
        "select":"review_status,candidate_path","limit":"1"})
    return json.loads(request(DB+"cv_admin_image_reviews?"+query,headers))

def path_for(card,ext):
    pid=card["provider_id"]
    number=card["card_number"]
    if not VALID_ID.fullmatch(pid) or not SAFE_NUMBER.fullmatch(number):
        raise ValueError("Unexpected card identity")
    return "pokewallet/delta-reign/"+number.replace("/","-")+"_"+pid[3:19]+"."+ext

def r2_client():
    import boto3
    from botocore.config import Config
    account=os.environ["R2_ACCOUNT_ID"]
    return boto3.client("s3",endpoint_url="https://"+account+".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",config=Config(signature_version="s3v4",retries={"max_attempts":3}))

def run(limit=1,delay=5.0):
    if not 1<=limit<=141: raise ValueError("Limit must be between 1 and 141")
    if not 0<=delay<=120: raise ValueError("Invalid delay")
    for key in ("SUPABASE_SERVICE_ROLE_KEY","POKEWALLET_API_KEY",
                "R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET"):
        if not os.getenv(key):
            raise RuntimeError("Missing required secret: "+key)
    headers=db_headers()
    cards=rows(headers)
    if len(cards)!=141 or any(c["image_status"] not in
        ("pending","missing","needs_review","matched") for c in cards):
        raise RuntimeError("Delta Reign catalog incomplete or unexpectedly changed; no imports made")
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
        client.head_bucket(Bucket=bucket)
        print("R2 bucket preflight succeeded")
    except Exception as exc:
        from botocore.exceptions import ClientError
        if isinstance(exc,ClientError):
            status=exc.response.get("ResponseMetadata",{}).get("HTTPStatusCode","unknown")
            code=exc.response.get("Error",{}).get("Code","unknown")
            raise RuntimeError("R2 bucket preflight failed: HTTP "+str(status)+", code "+str(code)+
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
            raise RuntimeError("R2 bucket preflight SSL failure: "+reason+
                ". Verify the R2_ACCOUNT_ID is the account owning the bucket and the S3 endpoint is correct.") from None
        if isinstance(exc,(EndpointConnectionError,ConnectTimeoutError)):
            raise RuntimeError("R2 bucket preflight failed to connect to the S3 endpoint") from None
        raise RuntimeError("R2 bucket preflight encountered "+type(exc).__name__) from None
    counts={"available":0,"unavailable":0,"rate_limited":0,
            "skipped":0,"uploaded":0,"errors":0}
    attempts=0
    for card in cards:
        if attempts>=limit: break
        if card["image_status"]=="matched" or card["image_path"]:
            counts["skipped"]+=1
            continue
        if existing_review(card["provider_id"],headers):
            counts["skipped"]+=1
            continue
        pid=card["provider_id"]
        if not VALID_ID.fullmatch(pid):
            counts["errors"]+=1
            continue
        attempts+=1
        if attempts>1 and delay:time.sleep(delay)
        req=urllib.request.Request(PW+urllib.parse.quote(pid,safe="")+"?size=low",
            headers={"X-API-Key":os.environ["POKEWALLET_API_KEY"],
                     "User-Agent":"CardVector-Delta-Images/1.0"})
        try:
            with urllib.request.urlopen(req,timeout=25) as response:
                data=response.read(1_000_001)
            ext,mime=image_type(data)
            counts["available"]+=1
        except urllib.error.HTTPError as exc:
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
        # Save for manual review only. Conflict-ignore will not overwrite an approval.
        review={"provider_id":pid,"candidate_path":path,
            "review_status":"pending_review",
            "notes":"PokéWallet base artwork candidate. Printing, provider permissions and image identity require administrator verification."}
        try:
            request(DB+"cv_admin_image_reviews?on_conflict=provider_id",
                {**headers,"Prefer":"resolution=ignore-duplicates,return=minimal"},
                method="POST",payload=[review])
        except urllib.error.HTTPError as exc:
            counts["errors"]+=1
            print("R2 uploaded, candidate review insert failed for card "+card["card_number"]+
                  " (HTTP "+str(exc.code)+")")
            continue
        counts["uploaded"]+=1
        print("Candidate ready for review: "+card["card_name"]+" "+card["card_number"])
    print(json.dumps({"set_id":SET_ID,"attempted":attempts,
        "counts":counts,"writes":"R2 candidate images and pending reviews; no approvals"},sort_keys=True))
    if counts["rate_limited"]:
        print("Stopped because PokéWallet returned HTTP 429")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--limit",type=int,default=1)
    parser.add_argument("--delay",type=float,default=5.0)
    args=parser.parse_args()
    run(args.limit,args.delay)
