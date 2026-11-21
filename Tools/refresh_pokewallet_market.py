"""Refresh cached TCGplayer market prices from existing PokéWallet set pages.

Runs only inside the metadata allocation after the image request target. It
reuses provider set pages (200 at once), never calls paid price endpoints,
and advances a durable set/page cursor for full catalog coverage.
"""
import json
import time
import urllib.parse
from datetime import datetime,timezone

from run_daily_pokewallet_import import Store,PW_URL,api_json,normalize_card
from pokewallet_market_metadata import market_rows
import pokewallet_api_budget as quota

DB="https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/"
JOB="existing_market_refresh"


def records(table,fields,headers,conditions=None):
    query={"select":fields,"limit":"1000",**(conditions or {})}
    rows=api_json(DB+table+"?"+urllib.parse.urlencode(query),headers=headers)
    if not isinstance(rows,list) or len(rows)>=1000:
        raise RuntimeError("Invalid or truncated metadata list")
    return rows


def run(store,pw_key,max_requests=5):
    if max_requests<=0:return {"requests":0,"updated":0}
    languages=records("cv_admin_set_languages",
                      "set_id,set_name,language",store.headers,
                      {"language":"eq.eng"})
    imported=records("cv_admin_pokewallet_catalog",
                     "set_id",store.headers,
                     {"select":"set_id","order":"set_id.asc"})
    # PostgREST caps lists at 1000. Get actual imported sets from a
    # distinct set table instead of fetching thousands of catalog rows.
    sets=sorted((s for s in languages if s["set_id"] in
                {r["set_id"] for r in imported}),key=lambda x:int(x["set_id"]))
    if not sets:return {"requests":0,"updated":0}
    checkpoint=records("cv_admin_pokewallet_market_refresh_state",
                       "job_key,next_set_id,next_page",store.headers,
                       {"job_key":"eq."+JOB})
    state=checkpoint[0] if checkpoint else {"job_key":JOB,"next_set_id":sets[0]["set_id"],"next_page":1}
    lookup={s["set_id"]:i for i,s in enumerate(sets)}
    index=lookup.get(state.get("next_set_id"),0)
    page=max(1,int(state.get("next_page") or 1))
    sent=0
    saved=0
    while sent<max_requests:
        entry=sets[index]
        sid=entry["set_id"]
        # Reserve an atomic shared hourly/daily quota slot before any provider call.
        reservation=quota.reserve(store.headers,"metadata")
        if not reservation["allowed"]:break
        path="/sets/"+urllib.parse.quote(sid,safe="")+"?page="+str(page)+"&limit=200"
        payload=api_json(PW_URL+path,headers={
            "X-API-Key":pw_key,"User-Agent":"CardVector-Market-Metadata-Refresh/1.0"})
        sent+=1
        info=payload.get("set") or {}
        if str(info.get("set_id"))!=sid:
            raise RuntimeError("Provider returned wrong set while refreshing prices")
        items=payload.get("cards")
        total=int(info.get("total_cards") or 0)
        if not isinstance(items,list) or not items or total<=0:
            raise RuntimeError("Incomplete provider price refresh page")
        normalized=[normalize_card(item,{"name":entry["set_name"],"set_id":sid})
                    for item in items]
        prices=market_rows(items,[c for c in normalized if c is not None])
        if prices:
            store.upsert_market(prices)
            saved+=len(prices)
        if page*200>=total:
            index=(index+1)%len(sets)
            page=1
        else:
            page+=1
        store.upsert("cv_admin_pokewallet_market_refresh_state",[{
            "job_key":JOB,"next_set_id":sets[index]["set_id"],"next_page":page,
            "updated_at":datetime.now(timezone.utc).isoformat()}])
        if sent<max_requests:time.sleep(36)
    return {"requests":sent,"market_rows_updated":saved,
            "next_set_id":sets[index]["set_id"],"next_page":page}
