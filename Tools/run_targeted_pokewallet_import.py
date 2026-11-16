#!/usr/bin/env python3
"""One-set manual PokéWallet import, preserving the daily importer's cursor.

This is intentionally a one-shot, explicitly selected English set. It imports
at most the remaining daily allowance and never carries unused budget to
another set. Existing catalog records are not overwritten. Does not match
or approve any images.
"""
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from run_daily_pokewallet_import import (
    Store, api_json, normalize_card, PW_URL, MANUAL_TOPUP_CAP,
    MANUAL_DAILY_CEILING, PAGE_SIZE, INTERVAL_SECONDS, provider_language
)

def build_catalog_rows(pages,set_info):
    rows=[]
    ids=set()
    for items in pages:
        for item in items:
            card=normalize_card(item,set_info)
            if card is None:
                # A set page may include promotional products or incomplete
                # entries. Never import them as cards; the exact expected
                # unique card count below is still mandatory.
                continue
            if not card.get("id"):
                raise RuntimeError("Target card has no provider identity")
            if card["id"] in ids:
                raise RuntimeError("Duplicate provider ID in targeted set")
            ids.add(card["id"])
            info=card["card_info"]
            if str(info["set_id"])!=str(set_info["set_id"]):
                raise RuntimeError("Target card belongs to another set")
            rows.append({"provider_id":card["id"],"set_id":info["set_id"],
                "set_name":info["set_name"],"card_name":info["name"],
                "card_number":info["card_number"],"variants":info["variants"],
                "image_status":"pending","image_path":None})
    return rows

def run_targeted(state,store,fetch,now=None,set_id="23353",expected=245):
    day=now or datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    if not set_id.isdecimal() or expected>MANUAL_TOPUP_CAP or expected<1:
        raise RuntimeError("Unsafe targeted set configuration")
    already=int(state.get("daily_imported",0)) if state.get("daily_date")==day else 0
    if MANUAL_DAILY_CEILING-already<expected:
        raise RuntimeError("Not enough daily allowance to finish one set; no import started")
    match=next((x for x in state.get("sets",[]) if x.get("set_id")==set_id),None)
    if not match or provider_language(match)!="eng" or match.get("card_count")!=expected:
        raise RuntimeError("Target set is not an exact English set of the expected size")
    # Stop rather than overwrite even one already reviewed/matched catalog row.
    existing=api_json(
        "https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/cv_admin_pokewallet_catalog?"
        +urllib.parse.urlencode({"set_id":"eq."+set_id,"select":"provider_id","limit":"1"}),
        headers=store.headers)
    if existing:
        raise RuntimeError("Target set has existing catalog rows: refusing to overwrite any review")
    pages=[]
    page=1
    total=None
    while True:
        if page>4:raise RuntimeError("Target exceeded bounded page limit")
        if page>1:time.sleep(INTERVAL_SECONDS)
        response=fetch("/sets/"+set_id+"?page="+str(page)+"&limit="+str(PAGE_SIZE))
        meta=response.get("set") or {}
        if str(meta.get("set_id"))!=set_id or (
            meta.get("language") and provider_language({"language":meta["language"]})!="eng"):
            raise RuntimeError("PokéWallet target set identity or language mismatch")
        if total is None:total=int(meta.get("total_cards") or 0)
        # PokéWallet total_cards includes sealed products. The catalog importer
        # excludes sealed items: verify total against card_count + sealed_count.
        bound=expected+int(match.get("sealed_count") or 0)
        if total<expected or total>bound:
            raise RuntimeError(f"Provider total {total} outside safe range {expected}–{bound}")
        items=response.get("cards")
        if not isinstance(items,list) or not items:raise RuntimeError("Missing target page")
        pages.append(items)
        if sum(map(len,pages))>=total:break
        page+=1
    if sum(map(len,pages))!=total:
        raise RuntimeError("Target provider pages were incomplete or exceeded declared total")
    rows=build_catalog_rows(pages,match)
    if len(rows)!=expected:
        categories={}
        examples=[]
        for items in pages:
            for item in items:
                info=item.get("card_info") if isinstance(item,dict) else None
                if not isinstance(info,dict): info={}
                card=normalize_card(item,match)
                if card: continue
                kind=str(info.get("product_type") or "<missing type>")
                has_name=bool(info.get("clean_name") or info.get("name"))
                has_number=bool(info.get("card_number"))
                key=f"{kind}: name={has_name}, number={has_number}"
                categories[key]=categories.get(key,0)+1
                if kind!="sealed" and len(examples)<30:
                    examples.append({"type":kind,"name":str(info.get("clean_name") or info.get("name") or "")[:85],
                                     "number":str(info.get("card_number") or "")[:30]})
        print(json.dumps({"set_id":set_id,"provider_total":total,"expected_cards":expected,
                          "normalized_cards":len(rows),"excluded_by_type":categories,
                          "excluded_examples":examples},sort_keys=True),flush=True)
        raise RuntimeError("Normalized set was incomplete; no catalog writes")
    # All source validation completes before writes. Cursor fields stay intact.
    for i in range(0,len(rows),40):
        store.upsert("cv_admin_pokewallet_catalog",rows[i:i+40])
    state["daily_date"]=day
    state["daily_imported"]=already+len(rows)
    state["cards_imported"]=int(state.get("cards_imported",0))+len(rows)
    store.save(state)
    store.publish(state)
    return {"mode":"targeted_manual","set_id":set_id,"set_name":match["name"],
        "imported":len(rows),"expected":expected,"daily_imported":state["daily_imported"],
        "regular_cursor_unchanged":True,"image_approvals":0}

def main():
    pw=os.environ.get("POKEWALLET_API_KEY","")
    key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY","")
    if not pw or not key:raise SystemExit("Required private importer credentials unavailable")
    store=Store(key)
    state=store.get()
    if not state or state.get("version")!=2:
        raise SystemExit("Existing importer checkpoint missing or unexpected")
    def fetch(path):
        return api_json(PW_URL+path,headers={
            "X-API-Key":pw,"User-Agent":"CardVector-Targeted-Importer/1.0"})
    target_id=os.environ.get("CARDVECTOR_TARGET_SET_ID","23353")
    target_count=int(os.environ.get("CARDVECTOR_TARGET_CARD_COUNT","245"))
    result=run_targeted(state,store,fetch,set_id=target_id,expected=target_count)
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
