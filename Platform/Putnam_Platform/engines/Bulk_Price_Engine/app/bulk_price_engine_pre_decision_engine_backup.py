
from __future__ import annotations

import csv
import json
import os
import shutil
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

VERSION = "1.0.0"

DEFAULT_LADDER = {
    "0.99": "0.99",
    "1.49": "0.99",
    "1.59": "1.09",
    "1.69": "1.19",
    "1.79": "1.29",
    "1.99": "1.49",
    "2.49": "1.99",
    "2.99": "2.49"
}

DEFAULT_TEMPLATE_INFO = ["#INFO", "Version=1.0.0", "Template= eBay-active-revise-price-quantity-download_US", "", "", "", "", "", "", "", "", ""]
DEFAULT_TEMPLATE_HEADER = [
    "Action", "Category name", "Item number", "Title", "Listing site", "Currency",
    "Start price", "Buy It Now price", "Available quantity", "Relationship", "Relationship details", "Custom label (SKU)"
]


def find_root() -> Path:
    env = os.environ.get("USERENVIRONMENT")
    if env and Path(env).exists():
        return Path(env)
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".putnam_root").exists():
            return parent
    fallback = Path.home() / "OneDrive" / "PutnamCollectibles"
    if fallback.exists():
        return fallback
    raise SystemExit("Could not locate PutnamCollectibles root. Set USERENVIRONMENT first.")


ROOT = find_root()
ENGINE_DIR = Path(__file__).resolve().parent
INVENTORY_DIR = ROOT / "Putnam_Inventory" / "Pricing_Revisions"
INCOMING_DIR = INVENTORY_DIR / "Incoming Files"
COMPLETED_DIR = INVENTORY_DIR / "Completed Jobs"
LOG_DIR = INVENTORY_DIR / "Logs"
TEMPLATE_DIR = ROOT / "Shared" / "Templates" / "eBay" / "Bulk_Revise"
CONFIG_PATH = ENGINE_DIR / "config" / "pricing_ladder.json"


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def money(value) -> Decimal:
    if value is None:
        raise InvalidOperation("None")
    s = str(value).strip().replace("$", "").replace(",", "")
    if s == "":
        raise InvalidOperation("blank")
    return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_str(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def load_ladder() -> dict[str, str]:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        ladder = data.get("price_ladder", data)
    else:
        ladder = DEFAULT_LADDER
    return {money_str(money(k)): money_str(money(v)) for k, v in ladder.items()}


def sniff_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(f, dialect))
    return rows


def detect_file(rows):
    if not rows:
        return None, None
    header0 = [c.strip() for c in rows[0]]
    # eBay Active Listings export
    if "Item number" in header0 and ("Current price" in header0 or "Start price" in header0):
        return "active_listings", 0
    # eBay Bulk Price/Qty template usually has #INFO row and header on row 2.
    for idx, row in enumerate(rows[:5]):
        h = [c.strip() for c in row]
        if "Action" in h and "Item number" in h and "Start price" in h:
            return "bulk_template", idx
    return None, None


def idx(header, name, required=True):
    try:
        return header.index(name)
    except ValueError:
        if required:
            raise ValueError(f"Required column missing: {name}")
        return None


def normalize_active_rows(rows, header_index):
    header = [c.strip() for c in rows[header_index]]
    data = rows[header_index + 1:]
    cols = {
        "item": idx(header, "Item number"),
        "title": idx(header, "Title"),
        "currency": idx(header, "Currency", required=False),
        "start_price": idx(header, "Start price", required=False),
        "current_price": idx(header, "Current price", required=False),
        "available_qty": idx(header, "Available quantity", required=False),
        "category_name": idx(header, "eBay category 1 name", required=False),
        "category_number": idx(header, "eBay category 1 number", required=False),
        "sku": idx(header, "Custom label (SKU)", required=False),
    }
    records = []
    for line_no, row in enumerate(data, start=header_index+2):
        if not any(str(x).strip() for x in row):
            continue
        def get(col, default=""):
            i = cols.get(col)
            return row[i].strip() if i is not None and i < len(row) else default
        price_raw = get("current_price") or get("start_price")
        records.append({
            "line_no": line_no,
            "item_number": get("item"),
            "title": get("title"),
            "currency": get("currency", "USD") or "USD",
            "old_price_raw": price_raw,
            "available_qty": get("available_qty", "1") or "1",
            "category_name": get("category_name"),
            "category_number": get("category_number"),
            "sku": get("sku"),
            "source_type": "active_listings",
        })
    return records


def normalize_bulk_rows(rows, header_index):
    header = [c.strip() for c in rows[header_index]]
    data = rows[header_index + 1:]
    cols = {
        "action": idx(header, "Action", required=False),
        "category_name": idx(header, "Category name", required=False),
        "item": idx(header, "Item number"),
        "title": idx(header, "Title"),
        "site": idx(header, "Listing site", required=False),
        "currency": idx(header, "Currency", required=False),
        "start_price": idx(header, "Start price"),
        "available_qty": idx(header, "Available quantity", required=False),
        "sku": idx(header, "Custom label (SKU)", required=False),
    }
    records=[]
    for line_no, row in enumerate(data, start=header_index+2):
        if not any(str(x).strip() for x in row):
            continue
        def get(col, default=""):
            i=cols.get(col)
            return row[i].strip() if i is not None and i < len(row) else default
        cat = get("category_name")
        cat_name, cat_num = cat, ""
        # eBay format may be: CCG Individual Cards (183454)
        if cat.endswith(")") and "(" in cat:
            cat_num = cat.rsplit("(",1)[1].rstrip(")")
        records.append({
            "line_no": line_no,
            "item_number": get("item"),
            "title": get("title"),
            "currency": get("currency", "USD") or "USD",
            "old_price_raw": get("start_price"),
            "available_qty": get("available_qty", "1") or "1",
            "category_name": cat_name,
            "category_number": cat_num,
            "sku": get("sku"),
            "source_type": "bulk_template",
        })
    return records


def build_category(record):
    name = record.get("category_name") or "CCG Individual Cards"
    number = record.get("category_number") or "183454"
    if "(" in name and name.endswith(")"):
        return name
    return f"{name} ({number})"


def choose_template_rows():
    # Prefer canonical template if user has saved it.
    candidates = sorted(TEMPLATE_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True) if TEMPLATE_DIR.exists() else []
    for path in candidates:
        try:
            rows = sniff_csv(path)
            ftype, hidx = detect_file(rows)
            if ftype == "bulk_template":
                return rows[0], rows[hidx]
        except Exception:
            continue
    return DEFAULT_TEMPLATE_INFO, DEFAULT_TEMPLATE_HEADER


def apply_ladder(records, ladder):
    processed=[]
    invalid=[]
    for rec in records:
        try:
            old = money(rec["old_price_raw"])
        except Exception as e:
            rec2 = dict(rec)
            rec2.update({"status":"INVALID_PRICE", "old_price":"", "new_price":"", "change":"", "reason": str(e)})
            invalid.append(rec2)
            continue
        key=money_str(old)
        if key in ladder:
            new=money(ladder[key])
            changed = (new != old)
            status = "CHANGE" if changed else "UNCHANGED"
            reason = f"ladder {key} -> {money_str(new)}" if changed else "ladder leaves price unchanged"
        else:
            new=old
            changed=False
            status="UNCHANGED"
            reason="price not in ladder"
        rec2=dict(rec)
        rec2.update({
            "old_price": money_str(old),
            "new_price": money_str(new),
            "change": money_str(new-old),
            "status": status,
            "reason": reason,
        })
        processed.append(rec2)
    return processed, invalid


def write_csv(path, rows, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_upload_csv(path, changed):
    info, header = choose_template_rows()
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer=csv.writer(f)
        writer.writerow(info)
        writer.writerow(header)
        for rec in changed:
            row_map={
                "Action":"Revise",
                "Category name": build_category(rec),
                "Item number": rec["item_number"],
                "Title": rec["title"],
                "Listing site":"US",
                "Currency":rec.get("currency") or "USD",
                "Start price":rec["new_price"],
                "Buy It Now price":"",
                "Available quantity":rec.get("available_qty") or "1",
                "Relationship":"",
                "Relationship details":"",
                "Custom label (SKU)":rec.get("sku") or "",
            }
            writer.writerow([row_map.get(h, "") for h in header])


def write_report(path, source_file, file_type, records, invalid, ladder, output_files):
    changed=[r for r in records if r["status"]=="CHANGE"]
    unchanged=[r for r in records if r["status"]=="UNCHANGED"]
    old_counter=Counter(r["old_price"] for r in records if r.get("old_price"))
    change_counter=Counter((r["old_price"], r["new_price"]) for r in changed)
    total_reduction=sum((money(r["old_price"])-money(r["new_price"]) for r in changed), Decimal("0.00"))
    lines=[]
    lines.append("Putnam Bulk Price Engine v1.0.0")
    lines.append("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("")
    lines.append(f"Source file: {source_file}")
    lines.append(f"Detected type: {file_type}")
    lines.append("")
    lines.append(f"Listings read: {len(records)+len(invalid)}")
    lines.append(f"Valid price rows: {len(records)}")
    lines.append(f"Changed rows: {len(changed)}")
    lines.append(f"Unchanged rows: {len(unchanged)}")
    lines.append(f"Invalid price rows: {len(invalid)}")
    lines.append(f"Total listed price reduction if uploaded: ${money_str(total_reduction)}")
    lines.append("")
    lines.append("Pricing ladder:")
    for k in sorted(ladder, key=lambda x: money(x)):
        lines.append(f"  ${k} -> ${ladder[k]}")
    lines.append("")
    lines.append("Change summary:")
    for (old,new), count in sorted(change_counter.items(), key=lambda kv: money(kv[0][0])):
        lines.append(f"  ${old} -> ${new}: {count}")
    lines.append("")
    lines.append("Current price distribution:")
    for price,count in sorted(old_counter.items(), key=lambda kv: money(kv[0])):
        lines.append(f"  ${price}: {count}")
    lines.append("")
    lines.append("Output files:")
    for label, p in output_files.items():
        lines.append(f"  {label}: {p}")
    lines.append("")
    lines.append("Safety notes:")
    lines.append("  - Original CSV was not modified.")
    lines.append("  - Review the review CSV and report before uploading anything to eBay.")
    lines.append("  - The upload candidate contains changed rows only.")
    path.write_text("\n".join(lines), encoding="utf-8")


def run(source_path: Path) -> Path:
    if not source_path.exists():
        raise SystemExit(f"Input file does not exist: {source_path}")
    rows=sniff_csv(source_path)
    ftype,hidx=detect_file(rows)
    if not ftype:
        raise SystemExit("This does not appear to be an eBay Active Listings CSV or eBay price/quantity template.")
    records = normalize_active_rows(rows, hidx) if ftype=="active_listings" else normalize_bulk_rows(rows, hidx)
    ladder=load_ladder()
    processed, invalid=apply_ladder(records, ladder)
    changed=[r for r in processed if r["status"]=="CHANGE"]
    stamp=now_stamp()
    job_dir=COMPLETED_DIR / f"Price_Revision_{stamp}"
    job_dir.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    archive_dir=job_dir / "source_backup"
    archive_dir.mkdir(exist_ok=True)
    shutil.copy2(source_path, archive_dir / source_path.name)
    review_header=["status","item_number","title","old_price","new_price","change","reason","available_qty","currency","category_name","category_number","sku","line_no"]
    review_csv=job_dir / f"review_all_rows_{stamp}.csv"
    changed_csv=job_dir / f"changed_only_{stamp}.csv"
    invalid_csv=job_dir / f"invalid_rows_{stamp}.csv"
    upload_csv=job_dir / f"EBAY_UPLOAD_price_revision_{stamp}.csv"
    rollback_csv=job_dir / f"ROLLBACK_old_prices_{stamp}.csv"
    report_txt=job_dir / f"price_revision_report_{stamp}.txt"
    write_csv(review_csv, processed+invalid, review_header)
    write_csv(changed_csv, changed, review_header)
    if invalid:
        write_csv(invalid_csv, invalid, review_header)
    write_upload_csv(upload_csv, changed)
    # Rollback CSV uses old prices for changed rows.
    rollback_records=[]
    for r in changed:
        rb=dict(r)
        rb["new_price"] = r["old_price"]
        rollback_records.append(rb)
    write_upload_csv(rollback_csv, rollback_records)
    outputs={
        "review_csv": review_csv,
        "changed_only_csv": changed_csv,
        "upload_candidate_csv": upload_csv,
        "rollback_csv": rollback_csv,
        "report_txt": report_txt,
    }
    if invalid:
        outputs["invalid_rows_csv"] = invalid_csv
    write_report(report_txt, source_path, ftype, processed, invalid, ladder, outputs)
    log_path=LOG_DIR / f"bulk_price_engine_{stamp}.log"
    log_path.write_text(f"Ran Putnam Bulk Price Engine v{VERSION}\nSource: {source_path}\nJob: {job_dir}\nChanged: {len(changed)}\n", encoding="utf-8")
    return job_dir


def main():
    print("Putnam Bulk Price Engine v1.0.0")
    print("Root:", ROOT)
    print("")
    import argparse
    parser=argparse.ArgumentParser(description="Generate eBay bulk price revision files from an active listings CSV.")
    parser.add_argument("input", nargs="?", help="Path to eBay active listings CSV or price/quantity template.")
    args=parser.parse_args()
    src=args.input
    if not src:
        print("Paste the path to your eBay Active Listings CSV, then press Enter.")
        print("Tip: You can drag the CSV into this window to paste its path.")
        src=input("CSV path: ").strip().strip('"')
    source_path=Path(src)
    job_dir=run(source_path)
    print("")
    print("Price revision job complete.")
    print("Output folder:")
    print(job_dir)
    print("")
    try:
        os.startfile(str(job_dir))
    except Exception:
        pass


if __name__ == "__main__":
    main()

