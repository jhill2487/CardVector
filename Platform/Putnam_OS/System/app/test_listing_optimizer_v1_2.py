from __future__ import annotations

import csv
from pathlib import Path

from putnam_os import (
    EXPORT_HISTORY_LOG,
    ExportCancelled,
    audit_new_listing,
    read_csv,
)


HEADER = [
    "*Title",
    "*StartPrice",
    "*C:Card Name",
    "*C:Set",
    "*C:Card Number",
    "*CustomLabel",
    "User SKU",
    "Inventory Location",
    "*ShippingProfileName",
    "Promotion Profile",
]

CASES = [
    ("price 0.50", "0.50", "0.99", "TRUE"),
    ("price 1.49", "1.49", "0.99", "TRUE"),
    ("price 1.50", "1.50", "0.99", "TRUE"),
    ("price 1.51", "1.51", "1.49", "FALSE"),
    ("price 2.99", "2.99", "1.49", "FALSE"),
    ("price 3.00", "3.00", "2.99", "FALSE"),
    ("price 4.99", "4.99", "2.99", "FALSE"),
    ("price 5.00", "5.00", "5.00", "FALSE"),
]


def log_row_count() -> int:
    if not EXPORT_HISTORY_LOG.exists():
        return 0
    with EXPORT_HISTORY_LOG.open("r", encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def write_sample(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        for idx, (title, price, _expected, _sweetener) in enumerate(CASES, 1):
            writer.writerow(
                {
                    "*Title": title,
                    "*StartPrice": price,
                    "*C:Card Name": f"Card {idx}",
                    "*C:Set": "Test Set",
                    "*C:Card Number": str(idx),
                    "*CustomLabel": f"CARD-SKU-{idx}",
                    "User SKU": "",
                    "Inventory Location": "",
                    "*ShippingProfileName": "Old Policy",
                    "Promotion Profile": "",
                }
            )


def expect_cancel(sample: Path, callback) -> None:
    before = log_row_count()
    try:
        audit_new_listing(sample, use_market=False, batch_location="ETB-01-A", confirm_callback=callback)
    except ExportCancelled:
        pass
    else:
        raise AssertionError("Expected export cancellation.")
    after = log_row_count()
    assert after == before, "Canceled export appended export history."


def main() -> int:
    artifact_dir = Path(__file__).resolve().parent / "test_artifacts" / "listing_optimizer_v1_2"
    sample = artifact_dir / "sample_acceptance.csv"
    write_sample(sample)

    expect_cancel(sample, lambda phase, _message: False)
    expect_cancel(sample, lambda phase, _message: phase == "shipping")

    before_success = log_row_count()
    job, rows, changes, opp, summary = audit_new_listing(
        sample,
        use_market=False,
        batch_location="ETB-01-A",
        confirm_callback=lambda _phase, _message: True,
    )

    exported = read_csv(job / "ebay_upload_ready.csv")
    review = read_csv(job / "optimization_review.csv")

    assert rows == len(CASES)
    assert changes == 7
    assert opp == 0
    assert list(exported[0].keys()) == HEADER, "eBay CSV column structure changed."
    assert [row["*StartPrice"] for row in exported] == [case[2] for case in CASES]
    assert [row["cart_sweetener"] for row in review] == [case[3] for case in CASES]
    assert summary["cart_sweetener_count"] == 3
    assert summary["average_final_price"] == "2.12"
    assert summary["min_final_price"] == "0.99"
    assert summary["max_final_price"] == "5.00"
    assert all(row["User SKU"] == "ETB-01-A" for row in exported)
    assert all(row["Inventory Location"] == "ETB-01-A" for row in exported)
    assert all(row["*ShippingProfileName"] == "Buyer Pays Shipping" for row in exported)
    assert all(row["Promotion Profile"] == "Free Shipping on 3+ Cards" for row in exported)
    assert log_row_count() == before_success + 1, "Successful export did not append exactly one history row."

    print("Listing Optimizer v1.2 acceptance test passed.")
    print(f"Job folder: {job}")
    print(f"Export history: {EXPORT_HISTORY_LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
