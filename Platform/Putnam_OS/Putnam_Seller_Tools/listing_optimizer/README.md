# Putnam Listing Optimizer v1.2

Pre-Export Optimization and Safety Checklist enabled.

## Run

```powershell
python putnam_listing_optimizer_v1_2.py --input "input.csv" --output "output.csv"
```

## Dry Run

```powershell
python putnam_listing_optimizer_v1_2.py --input "input.csv" --output "output.csv" --dry-run
```

The tool prompts for the warehouse location / User SKU, confirms `Buyer Pays Shipping` plus `Free Shipping on 3+ Cards`, applies the v1.2 Decimal pricing ladder, shows a final export summary, and requires `Y` before writing an eBay-ready CSV.

Successful non-dry-run exports append to `logs/export_history.csv`. Canceled exports write no output CSV and do not append export history.

If the User SKU / Custom Label column cannot be identified, the tool prints available columns and stops unless an exact column is configured with `--user-sku-column`.
