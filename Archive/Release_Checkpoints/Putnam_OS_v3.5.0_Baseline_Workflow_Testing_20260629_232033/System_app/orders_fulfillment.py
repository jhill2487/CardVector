from __future__ import annotations

import csv
import html
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


def _bootstrap_repo_import_path() -> None:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents]:
        if (
            (candidate / ".putnam_root").exists()
            or ((candidate / "AGENTS.md").exists() and (candidate / "Docs" / "AGENTS.md").exists())
        ):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return


_bootstrap_repo_import_path()

from Platform.putnam_paths import DATA_EXPORTS_DIR


PICK_LIST_ROOT = DATA_EXPORTS_DIR / "Pick_Lists"


@dataclass
class OrderLine:
    title: str
    quantity: str
    sku: str = ""
    location: str = ""


@dataclass
class Order:
    order_number: str
    buyer_name: str = ""
    shipping_service: str = ""
    shipping_paid_indicator: str = ""
    order_total: str = ""
    lines: list[OrderLine] = field(default_factory=list)


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with source.open(newline="", encoding=encoding) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    with source.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def find_column(fieldnames: Iterable[str], aliases: Iterable[str], contains: Iterable[str] = ()) -> str | None:
    fields = list(fieldnames)
    normalized = {_norm(name): name for name in fields}
    for alias in aliases:
        found = normalized.get(_norm(alias))
        if found:
            return found
    contains_norm = [_norm(part) for part in contains]
    if contains_norm:
        for name in fields:
            normalized_name = _norm(name)
            if all(part in normalized_name for part in contains_norm):
                return name
    return None


def detect_order_columns(fieldnames: Iterable[str]) -> dict[str, str | None]:
    fields = list(fieldnames)
    return {
        "order_number": find_column(
            fields,
            ["Order Number", "Order ID", "Order Id", "Sales Record Number", "Sales Record", "Record Number"],
            contains=["order"],
        ),
        "buyer_name": find_column(
            fields,
            ["Buyer Name", "Buyer Full Name", "Buyer Username", "Buyer", "Ship To Name", "Ship To"],
            contains=["buyer"],
        ),
        "title": find_column(fields, ["Item Title", "Title", "Item name", "Item"], contains=["title"]),
        "quantity": find_column(fields, ["Quantity", "Qty", "Quantity Purchased", "Quantity sold"], contains=["quantity"]),
        "sku": find_column(
            fields,
            ["Custom Label", "Custom label (SKU)", "Custom SKU", "User SKU", "SKU", "Seller SKU"],
        ),
        "location": find_column(fields, ["Inventory Location", "Location", "Warehouse Location", "Bin Location"]),
        "shipping_service": find_column(
            fields,
            ["Shipping Service", "Shipping service selected", "Shipping Service Selected", "Ship Service"],
            contains=["shipping", "service"],
        ),
        "shipping_paid": find_column(
            fields,
            [
                "Shipping and Handling",
                "Shipping cost",
                "Shipping Cost",
                "Shipping paid by buyer",
                "Postage and handling",
                "Postage",
            ],
            contains=["shipping", "cost"],
        ),
        "order_total": find_column(fields, ["Order Total", "Total", "Total Price", "Total paid", "Amount Paid"]),
    }


def _clean(value: object) -> str:
    return str(value or "").strip()


def _first_present(row: dict[str, str], *columns: str | None) -> str:
    for column in columns:
        if column and _clean(row.get(column)):
            return _clean(row.get(column))
    return ""


def shipping_paid_indicator(value: str) -> str:
    raw = _clean(value)
    if not raw:
        return ""
    normalized = raw.replace("$", "").replace(",", "").strip().lower()
    if normalized in {"0", "0.0", "0.00", "free"}:
        return "Free shipping / $0.00"
    try:
        amount = float(normalized)
        if amount <= 0:
            return "Free shipping / $0.00"
        return f"Buyer paid shipping / ${amount:.2f}"
    except ValueError:
        if "free" in normalized or "seller" in normalized:
            return raw
        return raw


def parse_orders(rows: list[dict[str, str]]) -> tuple[list[Order], dict[str, str | None]]:
    if not rows:
        raise ValueError("Orders CSV has no rows.")
    columns = detect_order_columns(rows[0].keys())
    if not columns["order_number"]:
        raise ValueError("Could not find an order number column in the eBay orders CSV.")
    if not columns["title"]:
        raise ValueError("Could not find an item title column in the eBay orders CSV.")

    grouped: dict[str, Order] = {}
    order_sequence: list[str] = []
    for row in rows:
        order_number = _first_present(row, columns["order_number"]) or "UNKNOWN_ORDER"
        if order_number not in grouped:
            grouped[order_number] = Order(
                order_number=order_number,
                buyer_name=_first_present(row, columns["buyer_name"]),
                shipping_service=_first_present(row, columns["shipping_service"]),
                shipping_paid_indicator=shipping_paid_indicator(_first_present(row, columns["shipping_paid"])),
                order_total=_first_present(row, columns["order_total"]),
            )
            order_sequence.append(order_number)
        order = grouped[order_number]
        order.lines.append(
            OrderLine(
                title=_first_present(row, columns["title"]),
                quantity=_first_present(row, columns["quantity"]) or "1",
                sku=_first_present(row, columns["sku"]),
                location=_first_present(row, columns["location"], columns["sku"]),
            )
        )
    return [grouped[key] for key in order_sequence], columns


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or "order"


def render_pick_slip_txt(order: Order) -> str:
    lines = [
        "Putnam OS Orders v1 - Pick Slip",
        "=" * 36,
        f"Order number: {order.order_number}",
        f"Buyer: {order.buyer_name or '(not available)'}",
        f"Shipping service: {order.shipping_service or '(not available)'}",
        f"Shipping paid/free: {order.shipping_paid_indicator or '(not available)'}",
        f"Order total: {order.order_total or '(not available)'}",
        "",
        "Items:",
    ]
    for index, line in enumerate(order.lines, 1):
        lines.extend(
            [
                f"{index}. {line.title}",
                f"   Quantity: {line.quantity}",
                f"   SKU/custom label: {line.sku or '(blank)'}",
                f"   Location: {line.location or '(blank)'}",
            ]
        )
    return "\n".join(lines) + "\n"


def render_pick_slip_html(order: Order) -> str:
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(line.title)}</td>"
        f"<td>{html.escape(line.quantity)}</td>"
        f"<td>{html.escape(line.sku or '')}</td>"
        f"<td>{html.escape(line.location or '')}</td>"
        "</tr>"
        for line in order.lines
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Pick Slip {html.escape(order.order_number)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
    h1 {{ font-size: 22px; margin-bottom: 4px; }}
    .meta {{ margin: 10px 0 18px; line-height: 1.5; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #999; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #eee; }}
    @media print {{ body {{ margin: 12px; }} }}
  </style>
</head>
<body>
  <h1>Putnam OS Orders v1 - Pick Slip</h1>
  <div class="meta">
    <strong>Order number:</strong> {html.escape(order.order_number)}<br>
    <strong>Buyer:</strong> {html.escape(order.buyer_name or '(not available)')}<br>
    <strong>Shipping service:</strong> {html.escape(order.shipping_service or '(not available)')}<br>
    <strong>Shipping paid/free:</strong> {html.escape(order.shipping_paid_indicator or '(not available)')}<br>
    <strong>Order total:</strong> {html.escape(order.order_total or '(not available)')}
  </div>
  <table>
    <thead>
      <tr><th>Item title</th><th>Quantity</th><th>SKU/custom label</th><th>Location</th></tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
"""


def write_summary_csv(path: Path, orders: list[Order]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "order_number",
                "buyer_name",
                "line_count",
                "item_quantity_total",
                "shipping_service",
                "shipping_paid_indicator",
                "order_total",
            ],
        )
        writer.writeheader()
        for order in orders:
            quantity_total = 0
            for line in order.lines:
                try:
                    quantity_total += int(float(line.quantity))
                except ValueError:
                    quantity_total += 1
            writer.writerow(
                {
                    "order_number": order.order_number,
                    "buyer_name": order.buyer_name,
                    "line_count": len(order.lines),
                    "item_quantity_total": quantity_total,
                    "shipping_service": order.shipping_service,
                    "shipping_paid_indicator": order.shipping_paid_indicator,
                    "order_total": order.order_total,
                }
            )


def generate_pick_slips(input_csv: str | Path, output_root: Path = PICK_LIST_ROOT) -> dict[str, object]:
    rows = read_csv_rows(input_csv)
    orders, columns = parse_orders(rows)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)

    txt_files: list[str] = []
    html_files: list[str] = []
    for order in orders:
        base_name = safe_filename(order.order_number)
        txt_path = output_dir / f"{base_name}_pick_slip.txt"
        html_path = output_dir / f"{base_name}_pick_slip.html"
        txt_path.write_text(render_pick_slip_txt(order), encoding="utf-8")
        html_path.write_text(render_pick_slip_html(order), encoding="utf-8")
        txt_files.append(str(txt_path))
        html_files.append(str(html_path))

    summary_csv = output_dir / "pick_list_summary.csv"
    write_summary_csv(summary_csv, orders)
    return {
        "input_csv": str(input_csv),
        "output_dir": str(output_dir),
        "order_count": len(orders),
        "line_count": sum(len(order.lines) for order in orders),
        "txt_files": txt_files,
        "html_files": html_files,
        "summary_csv": str(summary_csv),
        "columns": columns,
    }
