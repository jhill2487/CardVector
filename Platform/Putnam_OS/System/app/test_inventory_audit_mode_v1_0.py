from __future__ import annotations

import csv
import shutil
from pathlib import Path

from putnam_os import (
    apply_inventory_audit_action,
    create_inventory_audit_session,
    generate_inventory_audit_reports,
    load_inventory_audit_session,
    read_csv,
)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    root = Path(__file__).resolve().parent / "test_artifacts" / "inventory_audit_v1_0"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    source = root / "sample_ebay_active_listings.csv"
    write_rows(
        source,
        [
            {
                "Item number": "1001",
                "Title": "Pikachu 025/165 Pokemon Near Mint",
                "Custom label (SKU)": "",
                "Available quantity": "1",
                "Current price": "1.49",
                "eBay category 1 name": "CCG Individual Cards",
            },
            {
                "Item number": "1002",
                "Title": "Charmander 004/165 Pokemon Near Mint",
                "Custom label (SKU)": "",
                "Available quantity": "1",
                "Current price": "0.99",
                "eBay category 1 name": "CCG Individual Cards",
            },
            {
                "Item number": "1003",
                "Title": "Squirtle 007/165 Pokemon Near Mint",
                "Custom label (SKU)": "CS-KEEP",
                "Available quantity": "1",
                "Current price": "2.99",
                "eBay category 1 name": "CCG Individual Cards",
            },
            {
                "Item number": "1004",
                "Title": "Bulbasaur 001/165 Pokemon Near Mint",
                "Custom label (SKU)": "ETB-01-B",
                "Available quantity": "1",
                "Current price": "1.49",
                "eBay category 1 name": "CCG Individual Cards",
            },
        ],
    )

    capture_source = root / "capture_source.jpg"
    capture_source.write_bytes(b"fake jpeg bytes for internal audit evidence")

    session = create_inventory_audit_session(source, "Pokemon", "ETB-01-B", capture_enabled=True, audit_root=root)
    assert session["source_type"] == "ebay_active_listings"
    assert len(session["records"]) == 4
    assert session["records"][0]["item_id"] == "1001"

    session = apply_inventory_audit_action(session, "confirm", "physically verified", audit_root=root, capture_source=capture_source)
    assert session["records"][0]["confirmed_location"] == "ETB-01-B"
    assert Path(session["records"][0]["capture_image_path"]).exists()

    session = apply_inventory_audit_action(session, "missing", "not in box", audit_root=root)
    session = apply_inventory_audit_action(session, "needs_review", "CS value preserved", audit_root=root)
    session = apply_inventory_audit_action(session, "already_correct", "already located", audit_root=root)

    resumed = load_inventory_audit_session(root)
    assert resumed is not None
    assert resumed["records"][0]["audit_status"] == "confirmed"
    assert resumed["records"][1]["audit_status"] == "missing"
    assert resumed["records"][2]["audit_status"] == "needs_review"
    assert resumed["records"][3]["audit_status"] == "already_correct"

    reports = generate_inventory_audit_reports(resumed, audit_root=root)
    assert reports["audit_csv"].exists()
    assert reports["summary_txt"].exists()
    assert reports["bulk_csv"].exists()

    bulk_rows = read_csv(reports["bulk_csv"])
    assert len(bulk_rows) == 1
    assert bulk_rows[0]["ItemID"] == "1001"
    assert bulk_rows[0]["CustomLabel"] == "ETB-01-B"

    audit_rows = read_csv(reports["audit_csv"])
    statuses = {row["item_id"]: row["audit_status"] for row in audit_rows}
    assert statuses["1002"] == "missing"
    assert statuses["1003"] == "needs_review"
    assert statuses["1004"] == "already_correct"

    print("Inventory Audit Mode v1.0 acceptance test passed.")
    print(f"Reports: {reports['summary_txt'].parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
