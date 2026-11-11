#!/usr/bin/env python3
"""Daily automatic PokéWallet card-printing import (750 per scheduled run).

GitHub Actions supplies POKEWALLET_API_KEY and SUPABASE_SERVICE_ROLE_KEY.
Private catalog and progress live in Supabase, not in GitHub artifacts.
All writes are idempotent and the cursor is saved after each successful page.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from import_pokewallet_catalog import order_sets_newest_first, normalize_card
from pokewallet_set_language import set_language

SUPABASE_URL="https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/"
PW_URL="https://api.pokewallet.io"
JOB="pokewallet-kaggle"
DAILY_CAP=750
PAGE_SIZE=100
REQUEST_CAP=40
INTERVAL_SECONDS=45

def api_json(url, method="GET", body=None, headers=None):
    data=json.dumps(body).encode("utf-8") if body is not None else None
    request=urllib.request.Request(url,data=data,method=method,headers=headers or {})
    try:
        with urllib.request.urlopen(request,timeout=35) as response:
            body=response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        # Never emit request headers or API keys.
        raise RuntimeError("API request failed: HTTP "+str(error.code)) from None

class Store:
    def __init__(self,key):
        if not key: raise ValueError("Missing Supabase server credential")
        self.headers={"apikey":key,"Authorization":"Bearer "+key,
                      "Content-Type":"application/json"}
    def get(self):
        data=api_json(SUPABASE_URL+"cv_admin_pokewallet_import_state?job_key=eq."+JOB+"&select=state",
                      headers=self.headers)
        return data[0]["state"] if data else None
    def upsert(self,table,rows):
        if not rows:return
        headers={**self.headers,"Prefer":"resolution=merge-duplicates,return=minimal"}
        api_json(SUPABASE_URL+table,method="POST",body=rows,headers=headers)
    def save(self,state):
        self.upsert("cv_admin_pokewallet_import_state",[{"job_key":JOB,"state":state,
                                        "updated_at":datetime.now(timezone.utc).isoformat()}])
    def publish(self,state):
        totals=state.get("image_counts",{})
        row={"job_key":JOB,
             "status":"import_complete" if state.get("finished") else "importing",
             "sets_total":len(state.get("sets") or []),
             "sets_complete":int(state.get("next_set",0)),
             "cards_imported":int(state.get("cards_imported",0)),
             "images_matched":int(totals.get("matched",0)),
             "images_review":int(totals.get("needs_review",0)),
             "images_missing":int(totals.get("missing",0)),
             "updated_at":datetime.now(timezone.utc).isoformat()}
        self.upsert("cv_admin_job_progress",[row])

def make_state():
    return {"version":2,"sets":[],"next_set":0,"next_page":1,"next_offset":0,
            "cards_imported":0,"daily_date":"","daily_imported":0,"image_counts":{"matched":0,"needs_review":0,"missing":0},
            "finished":False}

def normalize_sets(data):
    sets=data.get("data")
    if not isinstance(sets,list) or not sets:
        raise RuntimeError("Unexpected PokéWallet set directory")
    entries=[]
    for i,row in enumerate(sets):
        if not isinstance(row,dict) or not re.fullmatch(r"\d+",str(row.get("set_id",""))):
            continue
        if not row.get("name"):continue
        entries.append({"set_id":str(row["set_id"]),"name":str(row["name"]),
                        "release_date":str(row.get("release_date") or ""),
                        "source_position":i})
    if not entries:raise RuntimeError("No valid set identifiers")
    return order_sets_newest_first(entries)

def step(state,fetch,write,cap=DAILY_CAP,max_requests=REQUEST_CAP,day=None):
    """Import at most cap physical card records, preserving a mid-page cursor.

    fetch(path)->decoded PokéWallet JSON; write(state, cards)->transaction-like
    durable commit: upsert records before checkpoint. Replayed pages are safe
    because each provider ID is a primary key in Supabase.
    """
    if state.get("finished"):return {"today":0,"requests":0,"finished":True}
    day=day or datetime.now(timezone.utc).date().isoformat()
    if state.get("daily_date")!=day:
        state["daily_date"]=day
        state["daily_imported"]=0
    allowance=max(0,min(cap,DAILY_CAP-int(state.get("daily_imported",0))))
    if not allowance:
        return {"today":0,"requests":0,"daily_limit_reached":True,"finished":False}
    requests=0
    today=0
    if not state["sets"]:
        if requests>=max_requests:return {"today":today,"requests":requests,"finished":False}
        state["sets"]=normalize_sets(fetch("/sets"))
        requests+=1
        write(state,[])
    while today<allowance and requests<max_requests and state["next_set"]<len(state["sets"]):
        current=state["sets"][state["next_set"]]
        if set_language(current)!="eng":
            state["next_set"]+=1
            state["next_page"]=1
            state["next_offset"]=0
            write(state,[])
            continue
        path="/sets/"+urllib.parse.quote(current["set_id"],safe="")+"?page="+str(state["next_page"])+"&limit="+str(PAGE_SIZE)
        payload=fetch(path)
        requests+=1
        items=payload.get("cards")
        metadata=payload.get("set")
        if not isinstance(items,list) or not isinstance(metadata,dict):
            raise RuntimeError("Unexpected PokéWallet card page")
        if str(metadata.get("set_id"))!=current["set_id"]:
            raise RuntimeError("PokéWallet set identity changed")
        total=int(metadata.get("total_cards") or 0)
        if not items and (state["next_page"]-1)*PAGE_SIZE<total:
            raise RuntimeError("Unexpected empty PokéWallet page")
        offset=int(state.get("next_offset",0))
        if offset>len(items):raise RuntimeError("Resume offset exceeds page length")
        rows=[]
        while offset<len(items) and today<allowance:
            item=items[offset]
            offset+=1
            card=normalize_card(item,current)
            if card and card["id"]:
                rows.append(card)
                today+=1
        if offset<len(items):
            state["next_offset"]=offset
        elif state["next_page"]*PAGE_SIZE<total or len(items)==PAGE_SIZE and not total:
            state["next_page"]+=1
            state["next_offset"]=0
        else:
            state["next_set"]+=1
            state["next_page"]=1
            state["next_offset"]=0
        catalog_rows=[]
        for card in rows:
            info=card["card_info"]
            catalog_rows.append({
                "provider_id":card["id"],"set_id":info["set_id"],
                "set_name":info["set_name"],"card_name":info["name"],
                "card_number":info["card_number"],"variants":info["variants"],
                "image_status":"pending","image_path":None})
        state["cards_imported"]+=len(rows)
        state["daily_imported"]+=len(rows)
        write(state,catalog_rows)
    state["finished"]=state["next_set"]>=len(state["sets"]) and bool(state["sets"])
    write(state,[])
    return {"today":today,"requests":requests,"sets_complete":state["next_set"],
            "sets_total":len(state["sets"]),"cards_imported":state["cards_imported"],"daily_imported":state["daily_imported"],
            "finished":state["finished"]}

def main():
    pw_key=os.environ.get("POKEWALLET_API_KEY","")
    db_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY","")
    if not pw_key or not db_key:
        raise SystemExit("Required GitHub Actions secrets are not configured")
    store=Store(db_key)
    state=store.get() or make_state()
    if state.get("version")!=2:
        raise SystemExit("Unsupported importer checkpoint version")
    last=[0.]
    count=[0]
    def fetch(path):
        if count[0]>0:
            remaining=INTERVAL_SECONDS-(time.monotonic()-last[0])
            if remaining>0:time.sleep(remaining)
        data=api_json(PW_URL+path,headers={"X-API-Key":pw_key,
                       "User-Agent":"CardVector-Daily-Importer/1.0"})
        last[0]=time.monotonic()
        count[0]+=1
        return data
    def write(checkpoint,rows):
        store.upsert("cv_admin_pokewallet_catalog",rows)
        store.save(checkpoint)
        store.publish(checkpoint)
    # Provider IDs are retained for authorized image retrieval separately; no Kaggle image matching.
    # Scope all provider sets before requesting more card pages. The
    # existing provider cursor is kept; Japanese records already imported
    # remain archived, but they are not displayed in English-only coverage.
    store.upsert("cv_admin_set_languages",[
        {"set_id":row["set_id"],"set_name":row["name"],
         "language":set_language(row)}
        for row in state.get("sets",[])
    ])
    summary=step(state,fetch,write)
    summary["language_scope"]="English confirmed; unknown and Japanese deferred"
    print(json.dumps(summary,sort_keys=True))
if __name__=="__main__":
    main()
