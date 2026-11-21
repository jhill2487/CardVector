#!/usr/bin/env python3
"""One-time priority English set import, bypassing image-first metadata window.

Honors atomic shared hourly and daily PokéWallet request caps. Does not modify
the normal card importer cursor or overwrite previously reviewed catalog rows.
Stages as many images as remaining hourly quota permits; the regular hourly
importer then continues this set from the administrator priority queue.
"""
import json
import os
import time
import urllib.parse
import urllib.error

from run_daily_pokewallet_import import Store, api_json, PW_URL, provider_language, normalize_card
from run_targeted_pokewallet_import import build_catalog_rows
from pokewallet_market_metadata import market_rows
import pokewallet_api_budget as budget
import import_pokewallet_set_images as images
import autoapprove_pokewallet_set as approval

SET_ID=os.environ.get("CARDVECTOR_TARGET_SET_ID","22872")
EXPECTED=int(os.environ.get("CARDVECTOR_TARGET_CARD_COUNT","278"))
SLUG=os.environ.get("CARDVECTOR_TARGET_SLUG","scarlet-violet-promo-cards")
PAGE_SIZE=100
MAX_IMAGE_ATTEMPTS=100


def reserve_priority_metadata(store):
    result=api_json(
        "https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/rpc/cv_reserve_pokewallet_priority_metadata_request",
        method="POST", body={}, headers=store.headers)
    if not isinstance(result,dict) or not result.get("allowed"):
        raise RuntimeError("Hourly or daily PokéWallet metadata request budget exhausted")
    return result


def run():
    if not SET_ID.isdecimal() or not 1<=EXPECTED<=1000:
        raise RuntimeError("Unsafe targeted set identity or card count")
    keys=("POKEWALLET_API_KEY","SUPABASE_SERVICE_ROLE_KEY",
          "R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET")
    for key in keys:
        if not os.getenv(key):
            raise RuntimeError("Missing required import credential: "+key)
    store=Store(os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    data=api_json(
        store_url("cv_admin_set_languages",
                  {"set_id":"eq."+SET_ID,
                   "select":"set_id,set_name,language,expected_card_count","limit":"1"}),
        headers=store.headers)
    if len(data)!=1 or data[0]["language"]!="eng" or data[0]["expected_card_count"]!=EXPECTED:
        raise RuntimeError("Target must be an English set with verified provider card count")
    info={**data[0],"name":data[0]["set_name"]}
    existing=api_json(store_url("cv_admin_pokewallet_catalog",
                      {"set_id":"eq."+SET_ID,"select":"provider_id","limit":"1000"}),
                      headers=store.headers)
    if existing and len(existing)!=EXPECTED:
        raise RuntimeError("Partial set already imported; refusing unsafe merge")

    if not existing:
        pages=[]
        total=None
        page=1
        last=0.0
        while page<=12:
            if last:
                wait=4-(time.monotonic()-last)
                if wait>0:time.sleep(wait)
            reserve_priority_metadata(store)
            payload=api_json(
                PW_URL+"/sets/"+SET_ID+"?page="+str(page)+"&limit="+str(PAGE_SIZE),
                headers={"X-API-Key":os.environ["POKEWALLET_API_KEY"],
                         "User-Agent":"CardVector-Priority-Import/1.0"})
            last=time.monotonic()
            meta=payload.get("set") or {}
            if str(meta.get("set_id"))!=SET_ID or (
                meta.get("language") and provider_language({"language":meta["language"]})!="eng"):
                raise RuntimeError("Wrong target set or language")
            items=payload.get("cards")
            if not isinstance(items,list) or not items:
                raise RuntimeError("Empty metadata page from provider")
            if total is None:
                total=int(meta.get("total_cards") or 0)
                if total<EXPECTED or total>EXPECTED+50:
                    raise RuntimeError("Unexpected provider metadata count")
            pages.append(items)
            if sum(len(chunk) for chunk in pages)>=total:break
            page+=1
        if sum(len(chunk) for chunk in pages)!=total:
            raise RuntimeError("Incomplete provider metadata pages; nothing written")
        rows=build_catalog_rows(pages,info)
        if len(rows)!=EXPECTED:
            raise RuntimeError("Expected "+str(EXPECTED)+" physical cards, normalized "+str(len(rows))+"; nothing written")
        # One API response includes per-printing TCGplayer prices and links.
        raw_items=[item for page_items in pages for item in page_items]
        normalized=[normalize_card(item,info) for item in raw_items]
        pricing=market_rows(raw_items,[item for item in normalized if item is not None])
        for start in range(0,len(rows),40):
            store.insert_new_cards(rows[start:start+40])
        for start in range(0,len(pricing),40):
            store.upsert_market(pricing[start:start+40])
        print(json.dumps({"set_id":SET_ID,"metadata_imported":len(rows),
                          "provider_requests":len(pages),
                          "regular_importer_cursor":"unchanged"}),flush=True)
    else:
        print(json.dumps({"set_id":SET_ID,"metadata_already_imported":len(existing)}),flush=True)

    # Stage only the selected set with remaining hourly quota; do not wait
    # past hourly reset. Continue tomorrow through the permanent hourly queue.
    images.SET_ID=SET_ID
    images.SET_SLUG=SLUG
    def reserve_image():
        return bool(budget.reserve(store.headers,"image",900)["allowed"])
    results=images.run(limit=MAX_IMAGE_ATTEMPTS,delay=5,
                       before_request=reserve_image)
    if results.get("remaining_unstaged")==0:
        client=images.r2_client()
        count,status=approval.approve_set(SET_ID,store.headers,client,os.environ["R2_BUCKET"])
        print(json.dumps({"auto_approved":count,"approval_status":status}),flush=True)
    print(json.dumps({"set_id":SET_ID,"image_requests_attempted":results["attempted"],
        "images_staged":results["counts"]["uploaded"],
        "images_remaining":results["remaining_unstaged"],
        "status":"hourly importer retains priority until set completes"}),flush=True)


def store_url(table,query):
    return "https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/"+table+"?"+urllib.parse.urlencode(query)


if __name__=="__main__":
    run()
