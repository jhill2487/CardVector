#!/usr/bin/env python3
"""Fill missing English physical TCGdex artwork using exact PokéWallet images.

Independent of CardVector's imported set coverage audit: inspect every missing
TCGdex card, then resolve only unique exact set/number/name matches already in
our PokéWallet catalog. Never guess stamps or editions. Atomic shared quota
reservations precede each PokéWallet image request. Results are cached in R2
and Supabase, not exposed from the provider API to browsers.

Can be safely run hourly: cached positive/negative results are never re-fetched.
"""
import collections
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import import_pokewallet_set_images as images
import pokewallet_api_budget as quota
from run_hourly_pokewallet_images import records

BASE="https://api.tcgdex.net/v2/en"
MAX_PER_HOUR=15
SPECIAL=re.compile(r"\b(staff|prerelease|pokemon center|stamped|winner|cosmos|league|alternate|1st edition|first edition|championship|holofoil stamp)\b",re.I)
SAFE_CARD_ID=re.compile(r"^[a-z0-9.-]{1,40}-[a-z0-9.-]{1,20}$",re.I)


def tcgdex(path):
    err=None
    for attempt in range(3):
        try:
            request=urllib.request.Request(BASE+path,headers={
                "User-Agent":"CardVector-TCGdex-Pokewallet-Gapfill/1.0"})
            with urllib.request.urlopen(request,timeout=45) as response:
                return json.load(response)
        except (urllib.error.URLError,TimeoutError) as exc:
            err=exc
            if attempt<2:time.sleep(2**attempt)
    raise RuntimeError("TCGdex catalog unavailable: "+str(type(err).__name__))


def tcgdex_missing_cards():
    sets=tcgdex("/sets")
    if not isinstance(sets,list) or len(sets)<100:
        raise RuntimeError("TCGdex set directory incomplete")
    set_names={r["id"]:r["name"] for r in sets
               if isinstance(r,dict) and r.get("id") and r.get("name")}
    ids=sorted(set_names,key=len,reverse=True)
    pocket=tcgdex("/series/tcgp")
    pocket_ids={str(r["id"]) for r in pocket.get("sets",[]) if r.get("id")}
    cards=[]
    for page in range(1,151):
        part=tcgdex("/cards?pagination:page="+str(page)+"&pagination:itemsPerPage=300")
        if not isinstance(part,list):
            raise RuntimeError("TCGdex did not return a card list")
        cards.extend(part)
        if len(part)<300:break
    else:raise RuntimeError("TCGdex card pagination incomplete")
    if len(cards)<20000:raise RuntimeError("TCGdex card directory unexpectedly small")
    missing=[]
    for entry in cards:
        if entry.get("image") or not entry.get("id") or not entry.get("name"):
            continue
        card_id=str(entry["id"])
        sid=next((s for s in ids if card_id.startswith(s+"-")),None)
        if not sid or sid in pocket_ids:
            continue
        missing.append({"id":card_id,"set_id":sid,
            "set_name":set_names[sid],"number":card_id[len(sid)+1:],
            "name":entry["name"]})
    return missing


def norm(s):
    value=re.sub(r"^[A-Za-z]{1,8}[0-9]{0,3}:\s*","",str(s or ""))
    return re.sub(r"[^a-z0-9]+"," ",value.lower()).strip()


def number(s):
    raw=str(s or "").split("/")[0].strip().lower()
    return raw.lstrip("0") or "0" if raw.isdecimal() else raw


def eligible(missing,catalog,existing):
    grouped=collections.defaultdict(list)
    tcgnums=collections.Counter()
    for card in catalog:
        grouped[(norm(card["set_name"]),number(card["card_number"]))].append(card)
    for card in missing:
        tcgnums[(norm(card["set_name"]),number(card["number"]))]+=1
    resolved=[]
    counters=collections.Counter()
    for c in missing:
        if not SAFE_CARD_ID.fullmatch(c["id"]):
            counters["unsafe_id"]+=1;continue
        if c["id"] in existing:
            counters["cached"]+=1;continue
        if SPECIAL.search(c["name"]):
            counters["special_printing"]+=1;continue
        group=grouped.get((norm(c["set_name"]),number(c["number"])),[])
        if len(group)!=1 or tcgnums[(norm(c["set_name"]),number(c["number"]))]!=1:
            counters["missing_or_ambiguous_identity"]+=1;continue
        item=group[0]
        if SPECIAL.search(item["card_name"]) or norm(item["card_name"])!=norm(c["name"]):
            counters["name_or_printing_conflict"]+=1;continue
        if not images.VALID_ID.fullmatch(item["provider_id"]):
            counters["invalid_provider_id"]+=1;continue
        resolved.append((c,item))
    return resolved,counters


def write_cache(headers,tcg,card,path,status):
    item={"tcgdex_id":tcg["id"],"provider_id":card["provider_id"],
          "source_set_id":card["set_id"],"image_path":path,
          "image_status":status}
    # Insert-only. Never overwrite existing verified mappings.
    query=urllib.parse.urlencode({"on_conflict":"tcgdex_id",
                                 "select":"tcgdex_id"})
    result=json.loads(images.request(
        images.DB+"cv_admin_tcgdex_pokewallet_images?"+query,
        {**headers,"Prefer":"resolution=ignore-duplicates,return=representation"},
        method="POST",payload=[item]))
    if not isinstance(result,list) or len(result)!=1:
        raise RuntimeError("TCGdex image cache changed concurrently")


def run(max_images=MAX_PER_HOUR,dry_run=False):
    if not 0<=max_images<=30:
        raise RuntimeError("Unsafe per-run image request limit")
    headers=images.db_headers()
    missing=tcgdex_missing_cards()
    catalog=records("cv_admin_pokewallet_catalog",
                    "provider_id,set_id,set_name,card_name,card_number,image_status,image_path",
                    headers,order="provider_id")
    languages={r["set_id"]:r["language"] for r in
        records("cv_admin_set_languages","set_id,language",headers)}
    catalog=[r for r in catalog if languages.get(r["set_id"])=="eng"]
    cached=records("cv_admin_tcgdex_pokewallet_images",
                   "tcgdex_id,provider_id,image_status",headers,order="tcgdex_id")
    eligible_cards,excluded=eligible(missing,catalog,{r["tcgdex_id"] for r in cached})
    summary={"tcgdex_missing_image_records":len(missing),
             "english_pokewallet_cards_imported":len(catalog),
             "unique_exact_candidates":len(eligible_cards),
             "already_processed":len(cached),
             "excluded":dict(excluded)}
    print(json.dumps(summary,sort_keys=True),flush=True)
    if dry_run or max_images==0:
        print(json.dumps({"dry_run":True,
                          "examples":[{"tcgdex_id":t["id"],"pokewallet_set_id":c["set_id"]}
                                      for t,c in eligible_cards[:15]]}),flush=True)
        return summary
    for secret in ("POKEWALLET_API_KEY","R2_ACCOUNT_ID","R2_ACCESS_KEY_ID",
                   "R2_SECRET_ACCESS_KEY","R2_BUCKET"):
        if not os.environ.get(secret):
            raise RuntimeError("Missing private image credential: "+secret)
    r2=images.r2_client()
    count=0
    uploaded=0
    unavailable=0
    budget_errors=0
    for tcg,card in eligible_cards:
        if count>=max_images:break
        reservation=quota.reserve(headers,"image",quota.choose_image_cap(headers,len(eligible_cards)))
        if not reservation["allowed"]:
            print("Shared PokéWallet image budget reached; safely stopping",flush=True)
            break
        count+=1
        pid=card["provider_id"]
        req=urllib.request.Request(images.PW+urllib.parse.quote(pid,safe="")+"?size=low",
            headers={"X-API-Key":os.environ["POKEWALLET_API_KEY"],
                "User-Agent":"CardVector-TCGdex-Pokewallet-Gapfill/1.0"})
        try:
            with urllib.request.urlopen(req,timeout=35) as response:
                remaining_hour=response.headers.get("X-RateLimit-Remaining-Hour")
                remaining_day=response.headers.get("X-RateLimit-Remaining-Day")
                data=response.read(1_000_001)
            ext,mime=images.image_type(data)
        except urllib.error.HTTPError as exc:
            if exc.code in (404,410):
                write_cache(headers,tcg,card,None,"not_available")
                unavailable+=1
                continue
            if exc.code==429:
                budget_errors+=1
                print("PokéWallet returned rate-limit 429; stopping",flush=True)
                break
            print("PokéWallet image temporary error HTTP "+str(exc.code),flush=True)
            break
        except (ValueError,urllib.error.URLError,TimeoutError) as exc:
            print("Image format/network error: "+type(exc).__name__,flush=True)
            break
        key=re.sub(r"[^a-z0-9.-]+","-",tcg["id"].lower()).strip("-")
        path="pokewallet/tcgdex-gaps/"+key+"."+ext
        r2.put_object(Bucket=os.environ["R2_BUCKET"],Key="archive/"+path,
            Body=data,ContentType=mime,CacheControl="public, max-age=86400",
            Metadata={"source":"pokewallet","set-id":str(card["set_id"])})
        write_cache(headers,tcg,card,path,"available")
        uploaded+=1
        if uploaded<=5:
            print("Gap image uploaded for TCGdex card "+tcg["id"],flush=True)
        if remaining_hour is None or remaining_day is None:
            print("Rate limit headers missing; stopping safely",flush=True)
            break
        if remaining_hour.isdecimal() and int(remaining_hour)<1:break
        if remaining_day.isdecimal() and int(remaining_day)<1:break
        time.sleep(4)
    summary.update({"provider_requests":count,"new_images":uploaded,
        "provider_missing_images":unavailable,"rate_limited":budget_errors})
    print(json.dumps(summary,sort_keys=True),flush=True)
    return summary


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--limit",type=int,default=MAX_PER_HOUR)
    args=parser.parse_args()
    run(args.limit,args.dry_run)
