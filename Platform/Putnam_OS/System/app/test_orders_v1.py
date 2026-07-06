from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from orders_fulfillment import generate_pick_slips, parse_orders, read_csv_rows


def build_sample(path: Path) -> None:
    fields = [
        "Order Number",
        "Buyer Username",
        "Item Title",
        "Quantity",
        "Custom Label",
        "Shipping Service",
        "Shipping and Handling",
        "Order Total",
    ]
    rows = [
        {
            "Order Number": "ORDER-1001",
            "Buyer Username": "buyer_a",
            "Item Title": "Pikachu 025/165 Pokemon",
            "Quantity": "1",
            "Custom Label": "ETB-01-A",
            "Shipping Service": "eBay Standard Envelope",
            "Shipping and Handling": "0.00",
            "Order Total": "1.49",
        },
        {
            "Order Number": "ORDER-1001",
            "Buyer Username": "buyer_a",
            "Item Title": "Charmander 004/165 Pokemon",
            "Quantity": "2",
            "Custom Label": "ETB-01-A",
            "Shipping Service": "eBay Standard Envelope",
            "Shipping and Handling": "0.00",
            "Order Total": "1.49",
        },
        {
            "Order Number": "ORDER-1002",
            "Buyer Username": "buyer_b",
            "Item Title": "Luffy OP01-001 One Piece",
            "Quantity": "1",
            "Custom Label": "ETB-05-A",
            "Shipping Service": "USPS Ground Advantage",
            "Shipping and Handling": "4.25",
            "Order Total": "9.99",
        },
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_orders_group_and_pick_slips(tmp_path: Path) -> None:
    source = tmp_path / "orders.csv"
    build_sample(source)
    rows = read_csv_rows(source)
    orders, columns = parse_orders(rows)
    assert columns["order_number"] == "Order Number"
    assert len(orders) == 2
    assert len(orders[0].lines) == 2
    assert orders[0].shipping_paid_indicator == "Free shipping / $0.00"
    assert orders[1].shipping_paid_indicator == "Buyer paid shipping / $4.25"

    result = generate_pick_slips(source, tmp_path / "Pick_Lists")
    output_dir = Path(result["output_dir"])
    assert result["order_count"] == 2
    assert result["line_count"] == 3
    assert (output_dir / "ORDER-1001_pick_slip.txt").exists()
    assert (output_dir / "ORDER-1001_pick_slip.html").exists()
    assert (output_dir / "pick_list_summary.csv").exists()


if __name__ == "__main__":
    root = Path(tempfile.mkdtemp(prefix="putnam_orders_test_"))
    test_orders_group_and_pick_slips(root)
    print(f"Orders v1 smoke test passed: {root}")
