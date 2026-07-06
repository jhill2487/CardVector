from __future__ import annotations

import csv
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


def decimal_money(value, default: Decimal | None = None) -> Decimal | None:
    raw = str(value or "").replace("$", "").replace(",", "").strip()
    if not raw:
        return default
    try:
        return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return default


def money_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def normalize_column_name(value: str) -> str:
    return "".join(ch for ch in str(value or "").lower().strip() if ch.isalnum())


def find_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    by_norm = {normalize_column_name(name): name for name in fieldnames}
    for candidate in candidates:
        found = by_norm.get(normalize_column_name(candidate))
        if found:
            return found
    return None


def normalize_title(value: str) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def safe_filename(value: str, fallback: str = "marketplace_intelligence") -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "").strip())
    return safe.strip("._") or fallback


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    for encoding in ["utf-8-sig", "utf-8", "cp1252"]:
        try:
            with Path(path).open("r", encoding=encoding, newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel
                return list(csv.DictReader(f, dialect=dialect))
        except UnicodeDecodeError:
            continue
    with Path(path).open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path

