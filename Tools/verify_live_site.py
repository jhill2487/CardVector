"""Verify that cardvector.app serves the intended deployment, not a stale page."""
import json
import sys
import time
import urllib.request

base = "https://cardvector.app"
expected = sys.argv[1]
last = ""
for attempt in range(18):
    try:
        def fetch(path):
            request = urllib.request.Request(base + path, headers={"Cache-Control":"no-cache","User-Agent":"CardVector-Release-Check/1.0"})
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.read().decode("utf-8")
        manifest = json.loads(fetch("/deployment-manifest.json?verify=" + expected))
        home = fetch("/?verify=" + expected)
        account = fetch("/account/?verify=" + expected)
        partners = fetch("/partners/?verify=" + expected)
        if manifest.get("source_commit") != expected:
            raise ValueError("Live manifest does not match the release commit")
        if 'The right card.' not in home or 'href="/partners/"' not in home or 'href="/account/"' not in home:
            raise ValueError("Live homepage is missing expected sections")
        if "Misprint" not in partners or "Whatnot" not in partners:
            raise ValueError("Live resources page incomplete")
        if 'id="auth-form"' not in account:
            raise ValueError("Live account page is missing registration form")
        print("LIVE DEPLOYMENT VERIFIED: " + expected)
        sys.exit(0)
    except Exception as exc:
        last = str(exc)
        print(f"Live check {attempt + 1}/18 not ready: {last}",flush=True)
        if attempt < 17:
            time.sleep(10)
raise SystemExit("Live site has NOT published this commit: " + last)
