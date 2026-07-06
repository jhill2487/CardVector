
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from statistics import median

VERSION = "2.4.1"

def find_root() -> Path:
    env = os.environ.get("USERENVIRONMENT")
    if env and Path(env).exists():
        return Path(env)
    fallback = Path.home() / "OneDrive" / "PutnamCollectibles"
    if fallback.exists():
        return fallback
    raise SystemExit("Could not find Putnam root. Set USERENVIRONMENT first.")

ROOT = find_root()
OUT_ROOT = ROOT / "Putnam_Inventory" / "Pricing_Revisions" / "Completed Jobs"
CACHE_ROOT = ROOT / "Putnam_Inventory" / "Pricing_Revisions" / "Market Cache"
CONFIG_PATH = ROOT / "Putnam_Platform" / "engines" / "Market_Intelligence" / "config" / "market_validation_rules.json"

DEFAULT_RULES = {
    "floor_price": 0.99,
    "opportunity_multiplier": 2.0,
    "min_accepted_comps": 3,
    "reject_terms": [
        "world championship", "worlds", "championship deck", "deck",
        "proxy", "proxies", "custom", "metal", "gold foil", "fan art",
        "pack", "booster", "wrapper", "empty pack", "sealed", "blister",
        "lot", "binder", "complete set", "master set", "playset", "4x", "x4",
        "psa", "bgs", "cgc", "sgc", "ace", "tag", "graded", "slab",
        "jumbo", "oversized", "reprint"
    ]
}

def money(v):
    try:
        return Decimal(str(v).replace("$","").replace(",","").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()

def norm_token(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()

def load_rules():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    return DEFAULT_RULES

def read_csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample=f.read(4096); f.seek(0)
        try:
            dialect=csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect=csv.excel
        return list(csv.DictReader(f, dialect=dialect))

def first_existing(row, names):
    for n in names:
        if n in row and str(row[n]).strip():
            return str(row[n]).strip()
    return ""

def build_query(row):
    card_name = first_existing(row, ["*C:Card Name", "Card Name", "card_name", "name"])
    card_set = first_existing(row, ["*C:Set", "Set", "set_name", "set"])
    card_number = first_existing(row, ["*C:Card Number", "Card Number", "card_number", "number"])
    title = first_existing(row, ["*Title", "Title", "title"])
    parts = [card_name, card_set, card_number]
    q = " ".join(p for p in parts if p)
    if not q:
        q = title
    return q.strip(), card_name, card_set, card_number, title

def cache_name(query: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", query.strip())[:120]
    return CACHE_ROOT / f"{safe}.json"

def fetch_sales(query: str):
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    cp = cache_name(query)
    if cp.exists():
        try:
            data=json.loads(cp.read_text(encoding="utf-8"))
            return data, "cache"
        except Exception:
            pass
    url = "https://carduploader.com/backend/sales/search?q=" + urllib.parse.quote_plus(query)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 PutnamOS/2.4.1",
        "Accept": "application/json,text/plain,*/*"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw=resp.read().decode("utf-8")
        data=json.loads(raw)
    cp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    time.sleep(0.35)
    return data, "live"

def is_rejected_by_term(title: str, rules):
    lt = clean_text(title)
    for term in rules.get("reject_terms", []):
        if term.lower() in lt:
            return True, f"reject term: {term}"
    return False, ""

def comparable_score(title: str, card_name: str, card_set: str, card_number: str):
    t = norm_token(title)
    score = 0
    reasons=[]
    if card_name:
        name_tokens = [x for x in norm_token(card_name).split() if len(x) > 1]
        if name_tokens and all(tok in t for tok in name_tokens):
            score += 40
            reasons.append("name_match")
        elif name_tokens and any(tok in t for tok in name_tokens):
            score += 20
            reasons.append("partial_name")
    if card_set:
        set_tokens = [x for x in norm_token(card_set).split() if len(x) > 2]
        if set_tokens and all(tok in t for tok in set_tokens):
            score += 30
            reasons.append("set_match")
        elif set_tokens and any(tok in t for tok in set_tokens):
            score += 15
            reasons.append("partial_set")
    if card_number:
        # Match raw, normalized, and common no-leading-zero variant.
        cn = str(card_number).strip()
        cands = {cn.lower(), cn.replace(" ", "").lower()}
        m = re.match(r"0*([0-9]+)\s*/\s*0*([0-9]+)", cn)
        if m:
            cands.add(f"{int(m.group(1))}/{int(m.group(2))}")
            cands.add(f"{m.group(1)}/{m.group(2)}")
        low = title.lower().replace(" ", "")
        if any(c.replace(" ","") in low for c in cands if c):
            score += 30
            reasons.append("number_match")
    return score, "|".join(reasons)

def analyze_result(item, card_name, card_set, card_number, rules):
    title = item.get("title","")
    reject, reason = is_rejected_by_term(title, rules)
    if reject:
        return False, 0, reason
    score, reasons = comparable_score(title, card_name, card_set, card_number)
    # Need at least name+number OR name+set for current prototype.
    if score >= 65:
        return True, score, reasons
    return False, score, f"low comparable score {score}: {reasons}"

def average_last_n(values, n=3):
    vals = values[:n]
    if not vals:
        return None
    return sum(vals, Decimal("0.00")) / Decimal(len(vals))

def write_dict_csv(path, rows, headers):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def run(csv_path: Path):
    rules = load_rules()
    rows = read_csv_rows(csv_path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job = OUT_ROOT / f"Market_Validation_{stamp}"
    job.mkdir(parents=True, exist_ok=True)

    summary_rows=[]
    rejected_rows=[]
    accepted_rows=[]
    opps=0

    for idx, row in enumerate(rows, start=1):
        query, card_name, card_set, card_number, title = build_query(row)
        current_price = money(first_existing(row, ["*StartPrice", "StartPrice", "BuyItNowPrice", "Price", "price"])) or Decimal("0.99")
        try:
            data, source = fetch_sales(query)
            results = data.get("results", [])
            provider_count = data.get("count", len(results))
        except Exception as e:
            summary_rows.append({
                "status":"MARKET_LOOKUP_ERROR","title":title,"card_name":card_name,"set":card_set,"card_number":card_number,
                "current_price":str(current_price),"query":query,"error":str(e),"row":idx
            })
            continue

        accepted_prices=[]
        for item in results:
            ok, score, reason = analyze_result(item, card_name, card_set, card_number, rules)
            rec = {
                "source_row": idx,
                "query": query,
                "input_title": title,
                "result_title": item.get("title",""),
                "price": item.get("price",""),
                "saleType": item.get("saleType",""),
                "source": item.get("source",""),
                "date": item.get("date",""),
                "url": item.get("url",""),
                "score": score,
                "reason": reason
            }
            if ok:
                p=money(item.get("price"))
                if p is not None:
                    accepted_prices.append(p)
                    accepted_rows.append(rec)
            else:
                rejected_rows.append(rec)

        last_sale = accepted_prices[0] if accepted_prices else None
        last3 = average_last_n(accepted_prices, 3)
        med = median(accepted_prices) if accepted_prices else None
        floor = money(rules.get("floor_price", 0.99)) or Decimal("0.99")
        mult = Decimal(str(rules.get("opportunity_multiplier", 2.0)))
        min_comps = int(rules.get("min_accepted_comps", 3))
        status = "NO_MARKET_OPPORTUNITY"
        reason = "No accepted comparable sales or below threshold."
        suggested = current_price

        if last3 is not None and len(accepted_prices) >= min_comps and last3 >= (floor * mult):
            status = "MARKET_OPPORTUNITY_REVIEW"
            reason = f"Accepted last 3 avg ${last3.quantize(Decimal('0.01'))} is >= {mult}x floor; {len(accepted_prices)} accepted comps."
            opps += 1
            # Conservative suggested price: nearest .49/.99 below last3, capped under last3.
            raw = last3 - Decimal("0.50")
            if raw < floor:
                raw = floor
            # Simple psychological rounding.
            dollars = int(raw)
            cents99 = Decimal(dollars) + Decimal("0.99")
            cents49 = Decimal(dollars) + Decimal("0.49")
            suggested = cents99 if cents99 <= raw else cents49
            if suggested < floor:
                suggested = floor

        summary_rows.append({
            "status": status,
            "title": title,
            "card_name": card_name,
            "set": card_set,
            "card_number": card_number,
            "current_price": str(current_price),
            "suggested_price": str(suggested.quantize(Decimal("0.01")) if isinstance(suggested, Decimal) else suggested),
            "provider_result_count": provider_count,
            "accepted_comps": len(accepted_prices),
            "rejected_results": len(results) - len(accepted_prices),
            "last_sale": str(last_sale) if last_sale is not None else "",
            "last3_avg": str(last3.quantize(Decimal("0.01"))) if last3 is not None else "",
            "median_accepted": str(Decimal(str(med)).quantize(Decimal("0.01"))) if med is not None else "",
            "query": query,
            "provider_source": source,
            "reason": reason,
            "row": idx
        })

    summary_headers=["status","title","card_name","set","card_number","current_price","suggested_price","provider_result_count","accepted_comps","rejected_results","last_sale","last3_avg","median_accepted","query","provider_source","reason","row","error"]
    result_headers=["source_row","query","input_title","result_title","price","saleType","source","date","url","score","reason"]
    write_dict_csv(job/"market_validation_summary.csv", summary_rows, summary_headers)
    write_dict_csv(job/"accepted_comparables.csv", accepted_rows, result_headers)
    write_dict_csv(job/"rejected_comparables.csv", rejected_rows, result_headers)
    report = [
        f"Putnam OS v{VERSION} - Comparable Validation Engine",
        f"Generated: {datetime.now()}",
        f"Source: {csv_path}",
        "",
        f"Rows in CSV: {len(rows)}",
        f"Rows analyzed: {len(summary_rows)}",
        f"Market opportunities flagged: {opps}",
        "",
        "Validation notes:",
        "- Market statistics are calculated only from accepted comparable sales.",
        "- World Championship, deck, graded, lot, pack, proxy, and other non-comparable terms are rejected.",
        "- This version does not automatically reprice.",
        "",
        "Output files:",
        f"- {job/'market_validation_summary.csv'}",
        f"- {job/'accepted_comparables.csv'}",
        f"- {job/'rejected_comparables.csv'}",
    ]
    (job/"market_validation_report.txt").write_text("\n".join(report), encoding="utf-8")
    return job

def main():
    print(f"Putnam Market Validation Prototype v{VERSION}")
    print("Paste or drag a CardUploader eBay CSV path, then press Enter.")
    p=input("CSV path: ").strip().strip('"')
    if not p:
        raise SystemExit("No input file.")
    job=run(Path(p))
    print("")
    print("Complete.")
    print(job)
    try:
        os.startfile(str(job))
    except Exception:
        pass

if __name__ == "__main__":
    main()
