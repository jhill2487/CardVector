#!/usr/bin/env python3
"""Publish aggregate CardVector importer progress to admin-only Supabase status.

Requires SUPABASE_SERVICE_ROLE_KEY in the trusted importer environment.
Never use this script in a browser, and never commit the credential.
"""
import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://iqdpfgpkagjxzedfxrvn.supabase.co/rest/v1/cv_admin_job_progress"

def make_record(state, summary=None):
    sets=state.get("sets") or []
    complete=int(state.get("next_set") or 0)
    result={"job_key":"pokewallet-kaggle",
            "status":"import_complete" if state.get("finished") else "importing",
            "sets_total":len(sets),
            "sets_complete":complete,
            "cards_imported":len(state.get("cards") or []),
            "images_matched":None,"images_review":None,"images_missing":None,
            "updated_at":datetime.now(timezone.utc).isoformat()}
    if summary is not None:
        result["images_matched"]=int(summary["matched"])
        result["images_review"]=int(summary["needs_review"])
        result["images_missing"]=int(summary["missing"])
        result["status"]="complete" if state.get("finished") else "reconciling"
    if not 0<=complete<=len(sets):
        raise ValueError("Invalid importer checkpoint")
    return result

def publish(record, key=None, request_fn=urllib.request.urlopen):
    secret=key if key is not None else os.environ.get("SUPABASE_SERVICE_ROLE_KEY","")
    if not secret: raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured in importer environment")
    data=json.dumps(record).encode("utf-8")
    request=urllib.request.Request(URL,data=data,method="POST",headers={
        "apikey":secret,"Authorization":"Bearer "+secret,
        "Content-Type":"application/json","Prefer":"resolution=merge-duplicates,return=minimal"})
    try:
        with request_fn(request,timeout=20) as response:
            if response.status not in (200,201,204):
                raise RuntimeError("Progress publish rejected, HTTP "+str(response.status))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Progress publish failed, HTTP "+str(exc.code)) from None

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--state",required=True,type=Path)
    parser.add_argument("--summary",type=Path)
    args=parser.parse_args()
    state=json.loads(args.state.read_text(encoding="utf-8"))
    summary=json.loads(args.summary.read_text(encoding="utf-8")) if args.summary else None
    publish(make_record(state,summary))
    print("Published secure CardVector import progress.")

if __name__=="__main__":
    main()
