#!/usr/bin/env python3
"""Resolve TCGdex image gaps from PokéWallet set pages, then cache exact images.

Pilot: Shining Fates Shiny Vault (122 records absent from TCGdex artwork).
Unlike the old gap filler, does not require set cards to be imported into the
CardVector catalog. Respects shared atomic daily/hourly quotas.
"""
import collections,json,os,re,time,urllib.request,urllib.parse,urllib.error
import fill_tcgdex_gaps_pokewallet as old
import import_pokewallet_set_images as images
import pokewallet_api_budget as quota
from run_hourly_pokewallet_images import records

TARGET_TCGDEX_SET=os.getenv("TCGDEX_GAP_SET","swsh4.5sv")
TARGET_PROVIDER_SET=os.getenv("POKEWALLET_GAP_SET","2781")
SPECIAL=old.SPECIAL
MAX_IMAGES=15

def fetch_set(headers,target_id):
    if not re.fullmatch(r"\d{2,8}",target_id):raise RuntimeError("Invalid provider set ID")
    reservation=json.loads(images.request(
        images.DB+"rpc/cv_reserve_pokewallet_priority_metadata_request",
        {**headers,"Prefer":"return=representation"},method="POST",payload={}))
    if not reservation.get("allowed"):
        raise RuntimeError("Shared hourly/daily metadata quota is exhausted; no API call made")
    req=urllib.request.Request("https://api.pokewallet.io/sets/"+target_id+"?page=1&limit=200",
       headers={"X-API-Key":os.environ["POKEWALLET_API_KEY"],
                "User-Agent":"CardVector-TCGdex-Gapfill/1.0"})
    with urllib.request.urlopen(req,timeout=40) as response:
        payload=json.load(response)
    info=payload.get("set") or {}
    rows=payload.get("cards")
    if str(info.get("set_id"))!=target_id or not isinstance(rows,list):
        raise RuntimeError("Invalid provider set response")
    total=int(info.get("total_cards") or len(rows))
    if total!=len(rows) or total>200:
        raise RuntimeError("Pilot requires a complete single-page set; refused partial metadata")
    return rows

def exact_pairs(missing,provider):
    by_number=collections.defaultdict(list)
    for entry in provider:
        info=entry.get("card_info") if isinstance(entry,dict) else None
        if not isinstance(info,dict) or info.get("product_type")=="sealed":continue
        pid=str(entry.get("id") or "")
        if not images.VALID_ID.fullmatch(pid):continue
        by_number[old.number(info.get("card_number"))].append((pid,info))
    unique=collections.Counter(old.number(c["number"]) for c in missing)
    result=[]
    reasons=collections.Counter()
    for card in missing:
        number=old.number(card["number"])
        candidates=by_number[number]
        if not old.SAFE_CARD_ID.fullmatch(card["id"]):
            reasons["invalid_tcgdex_id"]+=1;continue
        if unique[number]!=1 or len(candidates)!=1:
            reasons["ambiguous_number"]+=1;continue
        pid,info=candidates[0]
        provider_names={old.norm(info.get("name")),old.norm(info.get("clean_name"))}
        if SPECIAL.search(card["name"]) or any(SPECIAL.search(str(n or "")) for n in (info.get("name"),info.get("clean_name"))):
            reasons["special_printing"]+=1;continue
        if old.norm(card["name"]) not in provider_names:
            reasons["name_mismatch"]+=1;continue
        result.append((card,pid))
    return result,reasons

def run(limit=MAX_IMAGES):
    if not 0<=limit<=30:raise ValueError("Invalid image batch size")
    headers=images.db_headers()
    missing=[c for c in old.tcgdex_missing_cards() if c["set_id"]==TARGET_TCGDEX_SET]
    if not missing:raise RuntimeError("No missing image cards found in requested TCGdex set")
    known={c["tcgdex_id"]:c for c in records("cv_admin_tcgdex_pokewallet_images",
            "tcgdex_id,provider_id,image_status",headers,order="tcgdex_id")}
    known_set=records("cv_admin_tcgdex_gap_scanned_sets",
            "tcgdex_set_id,pokewallet_set_id,mapped_cards",headers,order="tcgdex_set_id")
    scanned=any(c["tcgdex_set_id"]==TARGET_TCGDEX_SET for c in known_set)
    pairs=[]
    if not scanned:
        # Verify set IDs against publicly stored PokéWallet English set directory.
        langs=records("cv_admin_set_languages",
                     "set_id,set_name,language,expected_card_count",headers)
        found=[x for x in langs if x["set_id"]==TARGET_PROVIDER_SET and x["language"]=="eng"]
        if len(found)!=1 or int(found[0]["expected_card_count"])!=len(missing):
            raise RuntimeError("PokéWallet target set not verified, or not one-to-one with TCGdex set")
        provider=fetch_set(headers,TARGET_PROVIDER_SET)
        pairs,excluded=exact_pairs(missing,provider)
        if not pairs:
            print(json.dumps({"set":TARGET_TCGDEX_SET,"candidate_count":0,
                "excluded":dict(excluded),"status":"no safe matches; not cached"}),flush=True)
            return
        for c,pid in pairs:
            if c["id"] in known:continue
            old.write_cache(headers,c,{"provider_id":pid,"set_id":TARGET_PROVIDER_SET},
                            None,"identified")
            known[c["id"]]={"tcgdex_id":c["id"],"provider_id":pid,"image_status":"identified"}
        params=urllib.parse.urlencode({"on_conflict":"tcgdex_set_id","select":"tcgdex_set_id"})
        rows=[{"tcgdex_set_id":TARGET_TCGDEX_SET,
               "pokewallet_set_id":TARGET_PROVIDER_SET,"mapped_cards":len(pairs)}]
        ok=json.loads(images.request(images.DB+"cv_admin_tcgdex_gap_scanned_sets?"+params,
            {**headers,"Prefer":"resolution=ignore-duplicates,return=representation"},
            method="POST",payload=rows))
        if len(ok)!=1:raise RuntimeError("Could not record completed set metadata scan")
        print(json.dumps({"set":TARGET_TCGDEX_SET,"tcgdex_missing":len(missing),
                "exact_matches":len(pairs),"excluded":dict(excluded)}),flush=True)
    todo=[(c,known[c["id"]]["provider_id"]) for c in missing
          if c["id"] in known and known[c["id"]]["image_status"]=="identified"]
    if limit==0:return
    for key in ("R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET"):
        if not os.environ.get(key):raise RuntimeError("Missing R2 credential: "+key)
    client=images.r2_client()
    success=0
    unavailable=0
    attempts=0
    for card,pid in todo:
        if attempts>=limit:break
        r=quota.reserve(headers,"image",quota.choose_image_cap(headers,len(todo)))
        if not r.get("allowed"):
            print("Image quota exhausted; stopped",flush=True);break
        attempts+=1
        request=urllib.request.Request(images.PW+urllib.parse.quote(pid,safe="")+"?size=low",
            headers={"X-API-Key":os.environ["POKEWALLET_API_KEY"],
                     "User-Agent":"CardVector-TCGdex-Gapfill/1.0"})
        try:
            with urllib.request.urlopen(request,timeout=35) as response:
                body=response.read(1_000_001)
                day=response.headers.get("X-RateLimit-Remaining-Day")
                hour=response.headers.get("X-RateLimit-Remaining-Hour")
            ext,mime=images.image_type(body)
        except urllib.error.HTTPError as exc:
            if exc.code in (404,410):
                update_status(headers,card["id"],None,"not_available")
                unavailable+=1;continue
            print("Provider image error "+str(exc.code),flush=True)
            break
        except (ValueError,urllib.error.URLError,TimeoutError) as exc:
            print("Image fetch failed: "+type(exc).__name__,flush=True)
            break
        path="pokewallet/tcgdex-gaps/"+card["id"].lower()+"."+ext
        client.put_object(Bucket=os.environ["R2_BUCKET"],Key="archive/"+path,
                          Body=body,ContentType=mime,
                          CacheControl="public, max-age=86400",
                          Metadata={"source":"pokewallet","set-id":TARGET_PROVIDER_SET})
        update_status(headers,card["id"],path,"available")
        success+=1
        if not hour or not day or not hour.isdecimal() or not day.isdecimal() or int(hour)<1 or int(day)<1:
            break
        time.sleep(4)
    print(json.dumps({"set":TARGET_TCGDEX_SET,"attempted":attempts,
        "new_images":success,"provider_unavailable":unavailable,
        "remaining_unprocessed":len(todo)-attempts}),flush=True)

def update_status(headers,tcg_id,path,status):
    query=urllib.parse.urlencode({"tcgdex_id":"eq."+tcg_id,
      "image_status":"eq.identified","select":"tcgdex_id"})
    changed=json.loads(images.request(images.DB+"cv_admin_tcgdex_pokewallet_images?"+query,
      {**headers,"Prefer":"return=representation"},method="PATCH",
      payload={"image_path":path,"image_status":status}))
    if len(changed)!=1:raise RuntimeError("Image gap cache changed during download")

if __name__=="__main__":
    run()
