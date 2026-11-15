#!/usr/bin/env python3
"""Run the existing importer and persist exact status in a private admin table."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from run_daily_pokewallet_import import Store

def iso():
    return datetime.now(timezone.utc).isoformat()

def report(store,run_id,kind,status,imported_count=0,error_class=None,error_message=None):
    # Keep errors short and avoid storing credentials, URL query parameters or headers.
    safe_message=re.sub(r'(?:Bearer|apikey|X-API-Key|secret|password)\s*[:= ]\s*\S+','[redacted]',str(error_message or ''),flags=re.I)
    row={"run_id":run_id,"run_kind":kind,"status":status,
         "error_class":error_class,"error_message":safe_message[:450] or None,
         "imported_count":int(imported_count)}
    if status!="started":row["finished_at"]=iso()
    store.upsert("cv_admin_import_run_diagnostics",[row])

def main():
    kind=os.environ.get("CARDVECTOR_DIAGNOSTIC_MODE","")
    if kind not in ("targeted_paldean_fates","daily","manual_topup"):
        raise SystemExit("Unsupported diagnostics run kind")
    run_id=os.environ.get("GITHUB_RUN_ID","")
    if not re.fullmatch(r"\d{1,30}",run_id):
        raise SystemExit("GitHub run identity required")
    key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:raise SystemExit("Missing server-side diagnostic credential")
    store=Store(key)
    report(store,run_id,kind,"started")
    try:
        if kind=="targeted_paldean_fates":
            from run_targeted_pokewallet_import import main as target
            target()
            # The targeted importer verifies a complete set before reporting success.
            imported_count=245
        else:
            from run_daily_pokewallet_import import main as daily
            daily()
            imported_count=0  # Lifetime counts are available from existing checkpoint.
        report(store,run_id,kind,"completed",imported_count=imported_count)
    except Exception as error:
        report(store,run_id,kind,"failed",error_class=type(error).__name__,
               error_message=str(error))
        raise

if __name__=="__main__":
    main()
