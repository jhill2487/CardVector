from __future__ import annotations
import csv, json, os, shutil
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

VERSION = "2.0.0"

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

DEFAULT_INFO = ["#INFO", "Version=1.0.0", "Template= eBay-active-revise-price-quantity-download_US", "", "", "", "", "", "", "", "", ""]
DEFAULT_HEADER = [
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
    raise RuntimeError("Could not locate PutnamCollectibles root. Set USERENVIRONMENT or create .putnam_root.")


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def money(value) -> Decimal:
    if value is None:
        raise InvalidOperation("None")
    s = str(value).strip().replace("$", "").replace(",", "")
    if not s:
        raise InvalidOperation("blank")
    return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_str(v: Decimal) -> str:
    return f"{v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def load_ladder(config_path: Path | None = None) -> dict[str, str]:
    if config_path and config_path.exists():
        raw = config_path.read_text(encoding="utf-8-sig")
        data = json.loads(raw)
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


def detect_file(rows: list[list[str]]):
    if not rows:
        return None, None
    h0 = [c.strip() for c in rows[0]]
    if "Item number" in h0 and ("Current price" in h0 or "Start price" in h0):
        return "active_listings", 0
    for i, row in enumerate(rows[:8]):
        h = [c.strip() for c in row]
        if "Action" in h and "Item number" in h and "Start price" in h:
            return "bulk_template", i
    return None, None


def col(header: list[str], name: str, required=True):
    try:
        return header.index(name)
    except ValueError:
        if required:
            raise ValueError(f"Required column missing: {name}")
        return None


def normalize_active(rows, header_index):
    header = [c.strip() for c in rows[header_index]]
    data = rows[header_index + 1:]
    cols = {
        "item": col(header, "Item number"),
        "title": col(header, "Title"),
        "sku": col(header, "Custom label (SKU)", False),
        "qty": col(header, "Available quantity", False),
        "currency": col(header, "Currency", False),
        "start": col(header, "Start price", False),
        "current": col(header, "Current price", False),
        "cat_name": col(header, "eBay category 1 name", False),
        "cat_num": col(header, "eBay category 1 number", False),
    }
    out = []
    for line_no, row in enumerate(data, header_index + 2):
        if not any(str(x).strip() for x in row):
            continue
        def get(k, default=""):
            i = cols.get(k)
            return row[i].strip() if i is not None and i < len(row) else default
        out.append({
            "line_no": line_no,
            "item_number": get("item"),
            "title": get("title"),
            "sku": get("sku"),
            "available_qty": get("qty", "1") or "1",
            "currency": get("currency", "USD") or "USD",
            "old_price_raw": get("current") or get("start"),
            "category_name": get("cat_name") or "CCG Individual Cards",
            "category_number": get("cat_num") or "183454",
        })
    return out


def normalize_bulk(rows, header_index):
    header = [c.strip() for c in rows[header_index]]
    data = rows[header_index + 1:]
    cols = {
        "item": col(header, "Item number"),
        "title": col(header, "Title"),
        "sku": col(header, "Custom label (SKU)", False),
        "qty": col(header, "Available quantity", False),
        "currency": col(header, "Currency", False),
        "start": col(header, "Start price"),
        "cat": col(header, "Category name", False),
    }
    out = []
    for line_no, row in enumerate(data, header_index + 2):
        if not any(str(x).strip() for x in row):
            continue
        def get(k, default=""):
            i = cols.get(k)
            return row[i].strip() if i is not None and i < len(row) else default
        cat = get("cat") or "CCG Individual Cards (183454)"
        num = "183454"
        name = cat
        if cat.endswith(")") and "(" in cat:
            name = cat.rsplit("(", 1)[0].strip()
            num = cat.rsplit("(", 1)[1].rstrip(")")
        out.append({
            "line_no": line_no,
            "item_number": get("item"),
            "title": get("title"),
            "sku": get("sku"),
            "available_qty": get("qty", "1") or "1",
            "currency": get("currency", "USD") or "USD",
            "old_price_raw": get("start"),
            "category_name": name,
            "category_number": num,
        })
    return out


def apply_ladder(records, ladder):
    processed, invalid = [], []
    for rec in records:
        try:
            old = money(rec["old_price_raw"])
            key = money_str(old)
        except Exception as e:
            r = dict(rec)
            r.update({"status": "INVALID_PRICE", "old_price": "", "new_price": "", "change": "", "reason": str(e)})
            invalid.append(r)
            continue
        if key in ladder:
            new = money(ladder[key])
            status = "CHANGE" if new != old else "UNCHANGED"
            reason = f"ladder {key} -> {money_str(new)}" if status == "CHANGE" else "ladder leaves price unchanged"
        else:
            new = old
            status = "UNCHANGED"
            reason = "price not in ladder"
        r = dict(rec)
        r.update({"status": status, "old_price": money_str(old), "new_price": money_str(new), "change": money_str(new - old), "reason": reason})
        processed.append(r)
    return processed, invalid


def category_string(r):
    name = r.get("category_name") or "CCG Individual Cards"
    num = r.get("category_number") or "183454"
    if name.endswith(")") and "(" in name:
        return name
    return f"{name} ({num})"


def choose_template(root: Path):
    template_dir = root / "Shared" / "Templates" / "eBay" / "Bulk_Revise"
    if template_dir.exists():
        for p in sorted(template_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                rows = read_csv_rows(p)
                typ, hi = detect_file(rows)
                if typ == "bulk_template":
                    return rows[0], [c.strip() for c in rows[hi]]
            except Exception:
                pass
    return DEFAULT_INFO, DEFAULT_HEADER


def write_review(path: Path, rows):
    header = ["status", "item_number", "title", "old_price", "new_price", "change", "reason", "available_qty", "currency", "category_name", "category_number", "sku", "line_no"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def write_upload(path: Path, rows, root: Path, use_old=False):
    info, header = choose_template(root)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(info)
        w.writerow(header)
        for r in rows:
            price = r["old_price"] if use_old else r["new_price"]
            m = {
                "Action": "Revise",
                "Category name": category_string(r),
                "Item number": r["item_number"],
                "Title": r["title"],
                "Listing site": "US",
                "Currency": r.get("currency") or "USD",
                "Start price": price,
                "Buy It Now price": "",
                "Available quantity": r.get("available_qty") or "1",
                "Relationship": "",
                "Relationship details": "",
                "Custom label (SKU)": r.get("sku") or "",
            }
            w.writerow([m.get(h, "") for h in header])


def summarize(records, invalid, ladder):
    changed = [r for r in records if r["status"] == "CHANGE"]
    unchanged = [r for r in records if r["status"] == "UNCHANGED"]
    old_counter = Counter(r["old_price"] for r in records if r.get("old_price"))
    change_counter = Counter((r["old_price"], r["new_price"]) for r in changed)
    reduction = sum((money(r["old_price"]) - money(r["new_price"]) for r in changed), Decimal("0.00"))
    return {
        "valid_rows": len(records),
        "changed_rows": len(changed),
        "unchanged_rows": len(unchanged),
        "invalid_rows": len(invalid),
        "total_reduction": money_str(reduction),
        "price_distribution": dict(sorted(old_counter.items(), key=lambda kv: money(kv[0]))),
        "change_summary": {f"{a}->{b}": c for (a,b), c in sorted(change_counter.items(), key=lambda kv: money(kv[0][0]))},
        "ladder": ladder,
    }


def preview_file(source_path: str | Path, root: Path | None = None, config_path: Path | None = None):
    source_path = Path(source_path)
    root = root or find_root()
    rows = read_csv_rows(source_path)
    ftype, hidx = detect_file(rows)
    if not ftype:
        raise ValueError("This does not appear to be an eBay Active Listings CSV or eBay Price/Quantity template.")
    records = normalize_active(rows, hidx) if ftype == "active_listings" else normalize_bulk(rows, hidx)
    ladder = load_ladder(config_path)
    processed, invalid = apply_ladder(records, ladder)
    summary = summarize(processed, invalid, ladder)
    summary["file_type"] = ftype
    summary["source_file"] = str(source_path)
    summary["total_rows"] = len(records) + len(invalid)
    return summary, processed, invalid


def run_revision(source_path: str | Path, root: Path | None = None, config_path: Path | None = None, output_base: Path | None = None):
    root = root or find_root()
    source_path = Path(source_path)
    summary, processed, invalid = preview_file(source_path, root, config_path)
    changed = [r for r in processed if r["status"] == "CHANGE"]
    stamp = ts()
    output_base = output_base or (root / "Putnam_OS" / "Completed Jobs")
    job_dir = output_base / f"Price_Revision_{stamp}"
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "source_backup").mkdir(exist_ok=True)
    shutil.copy2(source_path, job_dir / "source_backup" / source_path.name)

    review_csv = job_dir / f"review_all_rows_{stamp}.csv"
    changed_csv = job_dir / f"changed_only_{stamp}.csv"
    upload_csv = job_dir / f"EBAY_UPLOAD_price_revision_{stamp}.csv"
    rollback_csv = job_dir / f"ROLLBACK_old_prices_{stamp}.csv"
    report_txt = job_dir / f"price_revision_report_{stamp}.txt"
    invalid_csv = job_dir / f"invalid_rows_{stamp}.csv"

    write_review(review_csv, processed + invalid)
    write_review(changed_csv, changed)
    if invalid:
        write_review(invalid_csv, invalid)
    write_upload(upload_csv, changed, root, use_old=False)
    write_upload(rollback_csv, changed, root, use_old=True)

    lines = [
        "Putnam OS v2.0.0 - Bulk Price Engine",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Source file: {source_path}",
        f"Detected type: {summary['file_type']}",
        f"Listings read: {summary['total_rows']}",
        f"Changed rows: {summary['changed_rows']}",
        f"Unchanged rows: {summary['unchanged_rows']}",
        f"Invalid rows: {summary['invalid_rows']}",
        f"Total listed price reduction if uploaded: ${summary['total_reduction']}",
        "",
        "Change summary:",
    ]
    for k, c in summary["change_summary"].items():
        lines.append(f"  ${k.replace('->', ' -> $')}: {c}")
    lines += ["", "Output files:", f"  Review CSV: {review_csv}", f"  Changed-only CSV: {changed_csv}", f"  Upload candidate: {upload_csv}", f"  Rollback CSV: {rollback_csv}"]
    if invalid:
        lines.append(f"  Invalid rows CSV: {invalid_csv}")
    lines += ["", "Safety:", "  Original CSV was not modified.", "  Review output before uploading to eBay.", "  Upload candidate contains changed rows only."]
    report_txt.write_text("\n".join(lines), encoding="utf-8")

    log_dir = root / "Putnam_OS" / "System" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"pricing_{stamp}.log").write_text(f"Source={source_path}\nJob={job_dir}\nChanged={summary['changed_rows']}\n", encoding="utf-8")

    summary["job_dir"] = str(job_dir)
    summary["upload_csv"] = str(upload_csv)
    summary["review_csv"] = str(review_csv)
    summary["changed_csv"] = str(changed_csv)
    summary["rollback_csv"] = str(rollback_csv)
    summary["report_txt"] = str(report_txt)
    return summary
