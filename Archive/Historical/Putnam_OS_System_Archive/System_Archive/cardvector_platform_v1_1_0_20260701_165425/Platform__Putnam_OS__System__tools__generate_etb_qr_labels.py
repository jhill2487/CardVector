from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable


SCRIPT_VERSION = "CardVector OS Inventory Label Generator v1"
QR_PREFIX = "CVLOC:"
DEFAULT_CAPACITY = "100"
SAMPLE_CSV_NAME = "sample_etb_locations.csv"


@dataclass
class LocationLabel:
    location_id: str
    label: str = ""
    capacity: str = ""
    category: str = ""

    @property
    def qr_value(self) -> str:
        return f"{QR_PREFIX}{self.location_id}"


def resolve_project_root() -> Path:
    candidates: list[Path] = []
    for env_name in ("USERENVIRONMENT", "PUTNAM_ROOT"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        candidates.append(Path(user_profile) / "OneDrive" / "PutnamCollectibles")
    candidates.extend([Path.cwd(), Path(__file__).resolve()])
    for start in candidates:
        try:
            resolved = start.expanduser().resolve()
        except OSError:
            continue
        search = [resolved] if resolved.is_dir() else [resolved.parent]
        search.extend(search[0].parents)
        for candidate in search:
            if (candidate / "AGENTS.md").exists() and (candidate / "Platform").exists():
                return candidate
    raise RuntimeError("Could not locate PutnamCollectibles project root.")


def unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def clean_text(value: object) -> str:
    return str(value or "").strip()


def normalize_location(value: object) -> str:
    return clean_text(value).upper()


def read_fallback_csv(path: Path) -> list[LocationLabel]:
    rows: list[LocationLabel] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            location_id = normalize_location(row.get("location_id"))
            if not location_id:
                continue
            rows.append(
                LocationLabel(
                    location_id=location_id,
                    label=clean_text(row.get("label")),
                    capacity=clean_text(row.get("capacity")),
                    category=clean_text(row.get("category")),
                )
            )
    return rows


def read_etb_capacity_registry(root: Path) -> list[LocationLabel]:
    path = root / "Data" / "Config" / "etb_location_registry.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    default_capacity = clean_text(data.get("default_capacity")) or DEFAULT_CAPACITY
    rows: list[LocationLabel] = []
    for item in data.get("locations", []):
        location_id = normalize_location(item.get("location_code"))
        if not location_id:
            continue
        rows.append(
            LocationLabel(
                location_id=location_id,
                label=clean_text(item.get("status")),
                capacity=clean_text(item.get("estimated_capacity")) or default_capacity,
                category="ETB Storage",
            )
        )
    return rows


def read_batch_location_registry(root: Path) -> list[LocationLabel]:
    path = root / "Platform" / "Putnam_OS" / "System" / "config" / "location_registry.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rows: list[LocationLabel] = []
    for _game, item in data.get("games", {}).items():
        category = clean_text(item.get("display_name"))
        seen = []
        for location in item.get("used_locations", []):
            normalized = normalize_location(location)
            if normalized:
                seen.append(normalized)
        current = normalize_location(item.get("current_location"))
        if current:
            seen.append(current)
        for location_id in dict.fromkeys(seen):
            rows.append(
                LocationLabel(
                    location_id=location_id,
                    label=f"{category} Singles" if category else "",
                    capacity=DEFAULT_CAPACITY,
                    category=category,
                )
            )
    return rows


def merge_locations(*groups: Iterable[LocationLabel]) -> list[LocationLabel]:
    merged: dict[str, LocationLabel] = {}
    for group in groups:
        for row in group:
            location_id = normalize_location(row.location_id)
            if not location_id:
                continue
            existing = merged.get(location_id)
            if not existing:
                merged[location_id] = LocationLabel(
                    location_id=location_id,
                    label=row.label,
                    capacity=row.capacity,
                    category=row.category,
                )
                continue
            # Prefer richer category/label data from the batch registry while
            # preserving capacity from the ETB capacity registry.
            if row.label:
                existing.label = row.label
            if row.category:
                existing.category = row.category
            if row.capacity and not existing.capacity:
                existing.capacity = row.capacity
    return sorted(merged.values(), key=lambda item: item.location_id)


def load_locations(root: Path, csv_path: Path | None = None) -> list[LocationLabel]:
    if csv_path:
        return read_fallback_csv(csv_path)
    locations = merge_locations(read_etb_capacity_registry(root), read_batch_location_registry(root))
    if locations:
        return locations
    sample = Path(__file__).resolve().with_name(SAMPLE_CSV_NAME)
    if sample.exists():
        return read_fallback_csv(sample)
    return []


def make_qr_image(qr_value: str):
    try:
        import qrcode
        from reportlab.lib.utils import ImageReader
    except ImportError as exc:
        raise SystemExit(
            "Missing label dependencies. Install with:\n"
            'py -m pip install "qrcode[pil]" reportlab'
        ) from exc
    image = qrcode.make(qr_value)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def draw_label(canvas, row: LocationLabel, x: float, y: float, width: float, height: float) -> None:
    from reportlab.lib import colors

    padding = 12
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(1.2)
    canvas.rect(x, y, width, height)

    qr_size = min(height - (padding * 2), 112)
    qr_x = x + width - qr_size - padding
    qr_y = y + (height - qr_size) / 2
    canvas.drawImage(make_qr_image(row.qr_value), qr_x, qr_y, qr_size, qr_size, preserveAspectRatio=True)

    text_x = x + padding
    text_right = qr_x - padding
    canvas.setFillColor(colors.black)
    canvas.setFont("Helvetica-Bold", 28)
    canvas.drawString(text_x, y + height - 42, row.location_id)

    line_y = y + height - 68
    canvas.setFont("Helvetica", 11)
    if row.category:
        canvas.drawString(text_x, line_y, row.category[:38])
        line_y -= 16
    if row.label and row.label != row.category:
        canvas.drawString(text_x, line_y, row.label[:38])
        line_y -= 16
    if row.capacity:
        canvas.drawString(text_x, line_y, f"Capacity: {row.capacity}")

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.darkgray)
    canvas.drawString(text_x, y + padding, row.qr_value)
    canvas.line(text_right, y + padding, text_right, y + height - padding)


def write_pdf(labels: list[LocationLabel], output_path: Path) -> Path:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise SystemExit(
            "Missing label dependencies. Install with:\n"
            'py -m pip install "qrcode[pil]" reportlab'
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path = unique_output_path(output_path)
    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    page_width, page_height = letter
    margin_x = 27
    margin_y = 27
    gap_x = 18
    gap_y = 14
    columns = 2
    rows_per_page = 5
    label_width = (page_width - (2 * margin_x) - gap_x) / columns
    label_height = (page_height - (2 * margin_y) - ((rows_per_page - 1) * gap_y)) / rows_per_page

    for index, row in enumerate(labels):
        page_index = index % (columns * rows_per_page)
        if index and page_index == 0:
            pdf.showPage()
        col = page_index % columns
        row_index = page_index // columns
        x = margin_x + (col * (label_width + gap_x))
        y = page_height - margin_y - label_height - (row_index * (label_height + gap_y))
        draw_label(pdf, row, x, y, label_width, label_height)
    pdf.save()
    return output_path


def write_sample_csv(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path
    rows = [
        {"location_id": "ETB-02-A", "label": "Pokemon Singles", "capacity": "100", "category": "Pokemon"},
        {"location_id": "ETB-04-A", "label": "Magic Singles", "capacity": "100", "category": "Magic / MTG"},
        {"location_id": "ETB-05-B", "label": "One Piece Singles", "capacity": "100", "category": "One Piece"},
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["location_id", "label", "capacity", "category"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=SCRIPT_VERSION)
    parser.add_argument("--csv", help="Optional fallback CSV with columns: location_id,label,capacity,category.")
    parser.add_argument("--output", help="Optional output PDF path or folder. Defaults to Data/Exports/Labels.")
    parser.add_argument("--sample-template", action="store_true", help="Create the sample fallback CSV template and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = resolve_project_root()
    sample_path = Path(__file__).resolve().with_name(SAMPLE_CSV_NAME)
    write_sample_csv(sample_path)
    if args.sample_template:
        print(f"Sample fallback CSV: {sample_path}")
        return 0

    csv_path = Path(args.csv).expanduser() if args.csv else None
    labels = load_locations(root, csv_path)
    if not labels:
        raise SystemExit("No locations found in registry or fallback CSV.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_arg = Path(args.output).expanduser() if args.output else root / "Data" / "Exports" / "Labels"
    output_path = output_arg if output_arg.suffix.lower() == ".pdf" else output_arg / f"cardvector_etb_qr_labels_{timestamp}.pdf"
    pdf_path = write_pdf(labels, output_path)
    print(SCRIPT_VERSION)
    print(f"Project root: {root}")
    print(f"Labels generated: {len(labels)}")
    print(f"PDF: {pdf_path}")
    print(f"QR format: {QR_PREFIX}<location_id>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
