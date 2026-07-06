from __future__ import annotations
import csv, json, os, shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

VERSION = "2.2.0"

DEFAULT_LADDER = {
    "0.99": "0.99",
    "1.49": "0.99",
    "1.59": "1.09",
    "1.69": "1.19",
    "1.79": "1.29",
    "1.99": "1.49",
    "2.49": "1.99",
    "2.99": "2.49",
}

DEFAULT_TEMPLATE_INFO = ["#INFO", "Version=1.0.0", "Template= eBay-active-revise-price-quantity-download_US", "", "", "", "", "", "", "", "", ""]
DEFAULT_TEMPLATE_HEADER = [
    "Action", "Category name", "Item number", "Title", "Listing site", "Currency",
    "Start price", "Buy It Now price", "Available quantity", "Relationship", "Relationship details", "Custom label (SKU)"
]

@dataclass
class DetectionResult:
    csv_type: str
    header_index: int
    columns: list[str]
    row_count: int


def find_root() -> Path:
    env = os.environ.get("USERENVIRONMENT")
    if env and Path(env).exists():
        return Path(env)
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".putnam_root").exists():
            return parent
    fallback = Path.home() / "OneDrive" / "PutnamCollectibles"
    return fallback

ROOT = find_root()
OS_ROOT = ROOT / "Putnam_OS"
INVENTORY_ROOT = ROOT / "Putnam_Inventory" / "Pricing_Revisions"
COMPLETED_DIR = INVENTORY_ROOT / "Completed Jobs"
LOG_DIR = INVENTORY_ROOT / "Logs"
TEMPLATE_DIR = ROOT / "Shared" / "Templates" / "eBay" / "Bulk_Revise"
CONFIG_PATH = OS_ROOT / "config" / "pricing_ladder.json"


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def money(value) -> Decimal:
    if value is None:
        raise InvalidOperation("None")
    s = str(value).strip().replace("$", "").replace(",", "")
    if s == "" or s.lower() == "nan":
        raise InvalidOperation("blank")
    if s.startswith("."):
        s = "0" + s
    return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_str(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def display_price(value: Decimal) -> str:
    s = money_str(value)
    if s.startswith("0."):
        return s[1:]  # eBay/CardUploader often uses .99
    return s


def load_ladder() -> dict[str, str]:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        ladder = data.get("price_ladder", data)
    else:
        ladder = DEFAULT_LADDER
    return {money_str(money(k)): money_str(money(v)) for k, v in ladder.items()}


def read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        return list(csv.reader(f, dialect))


def detect_csv(path: Path) -> DetectionResult:
    rows = read_csv_rows(path)
    if not rows:
        raise ValueError("CSV is empty.")
    for i, row in enumerate(rows[:5]):
        cols = [c.strip() for c in row]
        colset = set(cols)
        # CardUploader eBay new-listing export.
        if {"*Title", "*StartPrice"}.issubset(colset) and ("*Action(SiteID=US|Country=US|Currency=USD|Version=1193|CC=UTF-8)" in colset or "*Category" in colset or "*C:Card Name" in colset):
            return DetectionResult("carduploader_new_listing", i, cols, max(0, len(rows)-i-1))
        # eBay active listings export.
        if "Item number" in colset and "Title" in colset and ("Current price" in colset or "Start price" in colset):
            return DetectionResult("ebay_active_listings", i, cols, max(0, len(rows)-i-1))
        # eBay bulk revise template/export.
        if {"Action", "Item number", "Start price"}.issubset(colset):
            return DetectionResult("ebay_bulk_price_template", i, cols, max(0, len(rows)-i-1))
    raise ValueError("CSV type not recognized. Expected CardUploader new-listing export, eBay Active Listings export, or eBay price/quantity template.")


def _idx(header: list[str], name: str, required=True):
    try:
        return header.index(name)
    except ValueError:
        if required:
            raise ValueError(f"Required column missing: {name}")
        return None


def _get(row, index, default=""):
    return row[index].strip() if index is not None and index < len(row) else default


def audit_carduploader_new_listing(source_path: Path) -> dict:
    rows = read_csv_rows(source_path)
    det = detect_csv(source_path)
    if det.csv_type != "carduploader_new_listing":
        raise ValueError("This is not a CardUploader new-listing export.")
    header = rows[det.header_index]
    data = rows[det.header_index+1:]
    title_i = _idx(header, "*Title")
    price_i = _idx(header, "*StartPrice")
    bin_i = _idx(header, "BuyItNowPrice", required=False)
    label_i = _idx(header, "CustomLabel", required=False)
    name_i = _idx(header, "*C:Card Name", required=False)
    set_i = _idx(header, "*C:Set", required=False)
    num_i = _idx(header, "*C:Card Number", required=False)

    ladder = load_ladder()
    out_rows = [list(header)]
    review=[]
    changed=0; invalid=0; raised=0; flagged=0
    old_counter=Counter(); change_counter=Counter()

    for line_no, row in enumerate(data, start=det.header_index+2):
        if not any(str(x).strip() for x in row):
            continue
        row = list(row) + [""]*(len(header)-len(row))
        title = _get(row, title_i)
        sku = _get(row, label_i)
        card_name = _get(row, name_i)
        set_name = _get(row, set_i)
        card_num = _get(row, num_i)
        raw_price = _get(row, price_i)
        status="KEEP"; reason="price accepted"; old_price=""; new_price=""
        try:
            old = money(raw_price)
            old_price = money_str(old)
            old_counter[old_price]+=1
            if old < Decimal("0.99"):
                new = Decimal("0.99")
                status="RAISE_TO_FLOOR"; reason="below Putnam $0.99 minimum floor"; raised+=1
            else:
                key=money_str(old)
                if key in ladder:
                    new = money(ladder[key])
                    if new != old:
                        status="CHANGE"; reason=f"Putnam ladder {key} -> {money_str(new)}"; changed+=1
                    else:
                        new = old
                        status="KEEP"; reason="already at Putnam ladder price"
                else:
                    new = old
                    status="KEEP"; reason="not in ladder; left unchanged"
                if new >= Decimal("20.00"):
                    status = "REVIEW_HIGH_VALUE" if status == "KEEP" else status + "+REVIEW_HIGH_VALUE"
                    reason += "; $20+ review flag"
                    flagged+=1
            new_price = money_str(new)
            if new != old:
                row[price_i] = display_price(new)
                if bin_i is not None and _get(row, bin_i):
                    row[bin_i] = display_price(new)
                change_counter[(money_str(old), money_str(new))]+=1
        except Exception as e:
            status="INVALID_PRICE"; reason=f"invalid/missing price: {e}"; invalid+=1
            new_price=""
        out_rows.append(row)
        review.append({
            "status": status,
            "title": title,
            "card_name": card_name,
            "set": set_name,
            "card_number": card_num,
            "sku": sku,
            "old_price": old_price,
            "new_price": new_price,
            "reason": reason,
            "line_no": line_no,
        })

    job_dir = COMPLETED_DIR / f"New_Listing_Price_Audit_{stamp()}"
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "source_backup").mkdir(exist_ok=True)
    shutil.copy2(source_path, job_dir / "source_backup" / source_path.name)
    revised_csv = job_dir / f"CARDUPLOADER_REVISED_UPLOAD_{stamp()}.csv"
    with revised_csv.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(out_rows)
    review_csv = job_dir / "review_new_listing_prices.csv"
    with review_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["status","title","card_name","set","card_number","sku","old_price","new_price","reason","line_no"])
        w.writeheader(); w.writerows(review)
    report = job_dir / "new_listing_price_audit_report.txt"
    lines = [
        f"Putnam OS Pricing Workspace v{VERSION}",
        "New Listing Price Auditor",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        f"Source: {source_path}",
        f"Listings reviewed: {len(review)}",
        f"Changed by ladder: {changed}",
        f"Raised to $0.99 floor: {raised}",
        f"$20+ review flags: {flagged}",
        f"Invalid/missing prices: {invalid}",
        "",
        "Change summary:",
    ]
    if change_counter:
        for (old,new), count in sorted(change_counter.items(), key=lambda kv: money(kv[0][0])):
            lines.append(f"  ${old} -> ${new}: {count}")
    else:
        lines.append("  No ladder changes.")
    lines += ["", "Input price distribution:"]
    for price,count in sorted(old_counter.items(), key=lambda kv: money(kv[0])):
        lines.append(f"  ${price}: {count}")
    lines += ["", "Outputs:", f"  Revised eBay upload CSV: {revised_csv}", f"  Review CSV: {review_csv}", f"  Report: {report}", "", "Safety: original CSV was not modified."]
    report.write_text("\n".join(lines), encoding="utf-8")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (LOG_DIR / f"new_listing_audit_{stamp()}.log").write_text(f"Source={source_path}\nJob={job_dir}\nReviewed={len(review)}\nChanged={changed}\n", encoding="utf-8")
    return {"job_dir": job_dir, "revised_csv": revised_csv, "review_csv": review_csv, "report": report, "reviewed": len(review), "changed": changed, "raised": raised, "flagged": flagged, "invalid": invalid, "csv_type": det.csv_type}


def _choose_template_rows():
    candidates = sorted(TEMPLATE_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True) if TEMPLATE_DIR.exists() else []
    for p in candidates:
        try:
            rows=read_csv_rows(p)
            det=detect_csv(p)
            if det.csv_type == "ebay_bulk_price_template":
                return rows[0], rows[det.header_index]
        except Exception:
            pass
    return DEFAULT_TEMPLATE_INFO, DEFAULT_TEMPLATE_HEADER


def _build_category(rec):
    name = rec.get("category_name") or "CCG Individual Cards"
    number = rec.get("category_number") or "183454"
    if "(" in name and name.endswith(")"):
        return name
    return f"{name} ({number})"


def audit_existing_listing(source_path: Path) -> dict:
    rows = read_csv_rows(source_path)
    det = detect_csv(source_path)
    if det.csv_type not in {"ebay_active_listings", "ebay_bulk_price_template"}:
        raise ValueError("This is not an eBay active listing/bulk price file.")
    header=[c.strip() for c in rows[det.header_index]]
    data=rows[det.header_index+1:]
    item_i=_idx(header,"Item number")
    title_i=_idx(header,"Title")
    start_i=_idx(header,"Start price", required=False)
    current_i=_idx(header,"Current price", required=False)
    price_i = current_i if current_i is not None else start_i
    qty_i=_idx(header,"Available quantity", required=False)
    currency_i=_idx(header,"Currency", required=False)
    sku_i=_idx(header,"Custom label (SKU)", required=False)
    cat_name_i=_idx(header,"eBay category 1 name", required=False)
    cat_num_i=_idx(header,"eBay category 1 number", required=False)
    ladder=load_ladder()
    review=[]; changed=[]; invalid=[]; old_counter=Counter(); change_counter=Counter()
    for line_no,row in enumerate(data, start=det.header_index+2):
        if not any(str(x).strip() for x in row): continue
        def g(i,d=""): return _get(row,i,d)
        rec={"item_number":g(item_i),"title":g(title_i),"currency":g(currency_i,"USD") or "USD","available_qty":g(qty_i,"1") or "1","sku":g(sku_i),"category_name":g(cat_name_i),"category_number":g(cat_num_i),"line_no":line_no}
        raw=g(price_i)
        try:
            old=money(raw); old_s=money_str(old); old_counter[old_s]+=1
            if old_s in ladder:
                new=money(ladder[old_s])
                status="CHANGE" if new != old else "UNCHANGED"
                reason=f"ladder {old_s} -> {money_str(new)}" if new != old else "ladder leaves unchanged"
            else:
                new=old; status="UNCHANGED"; reason="price not in ladder"
            rec.update({"status":status,"old_price":old_s,"new_price":money_str(new),"change":money_str(new-old),"reason":reason})
            review.append(rec)
            if new != old:
                changed.append(rec); change_counter[(old_s,money_str(new))]+=1
        except Exception as e:
            rec.update({"status":"INVALID_PRICE","old_price":"","new_price":"","change":"","reason":str(e)})
            invalid.append(rec); review.append(rec)
    job_dir=COMPLETED_DIR / f"Existing_Listing_Price_Revision_{stamp()}"; job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir/"source_backup").mkdir(exist_ok=True); shutil.copy2(source_path, job_dir/"source_backup"/source_path.name)
    review_header=["status","item_number","title","old_price","new_price","change","reason","available_qty","currency","category_name","category_number","sku","line_no"]
    review_csv=job_dir/"review_existing_listing_prices.csv"
    with review_csv.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f, fieldnames=review_header, extrasaction="ignore"); w.writeheader(); w.writerows(review)
    upload_csv=job_dir/f"EBAY_UPLOAD_price_revision_{stamp()}.csv"
    info, upload_header = _choose_template_rows()
    with upload_csv.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.writer(f); writer.writerow(info); writer.writerow(upload_header)
        for rec in changed:
            row_map={"Action":"Revise","Category name":_build_category(rec),"Item number":rec["item_number"],"Title":rec["title"],"Listing site":"US","Currency":rec.get("currency") or "USD","Start price":rec["new_price"],"Buy It Now price":"","Available quantity":rec.get("available_qty") or "1","Relationship":"","Relationship details":"","Custom label (SKU)":rec.get("sku") or ""}
            writer.writerow([row_map.get(h,"") for h in upload_header])
    total_reduction=sum((money(r["old_price"])-money(r["new_price"]) for r in changed), Decimal("0"))
    report=job_dir/"existing_listing_price_revision_report.txt"
    lines=[f"Putnam OS Pricing Workspace v{VERSION}","Existing Listing Price Reviser",f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}","",f"Source: {source_path}",f"Rows reviewed: {len(review)}",f"Changed rows: {len(changed)}",f"Invalid rows: {len(invalid)}",f"Total price reduction: ${money_str(total_reduction)}","","Change summary:"]
    for (old,new),count in sorted(change_counter.items(), key=lambda kv: money(kv[0][0])): lines.append(f"  ${old} -> ${new}: {count}")
    lines += ["",f"Upload CSV: {upload_csv}",f"Review CSV: {review_csv}","Safety: original CSV was not modified."]
    report.write_text("\n".join(lines), encoding="utf-8")
    return {"job_dir":job_dir,"upload_csv":upload_csv,"review_csv":review_csv,"report":report,"reviewed":len(review),"changed":len(changed),"invalid":len(invalid),"csv_type":det.csv_type}


def run_auto(source_path: Path) -> dict:
    det=detect_csv(source_path)
    if det.csv_type == "carduploader_new_listing":
        return audit_carduploader_new_listing(source_path)
    return audit_existing_listing(source_path)
