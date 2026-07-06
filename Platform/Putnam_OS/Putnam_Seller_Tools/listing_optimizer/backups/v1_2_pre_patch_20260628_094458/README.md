# Putnam Listing Optimizer v1.1

Pre-Export Safety Checklist enabled.

## Run

```powershell
python putnam_listing_optimizer_v1_1.py --input "input.csv" --output "output.csv"
```

## Dry Run

```powershell
python putnam_listing_optimizer_v1_1.py --input "input.csv" --output "output.csv" --dry-run
```

The tool prompts for the warehouse location / User SKU, writes that value to the detected User SKU / Custom Label column, checks shipping policy values, shows a final checklist, and requires `EXPORT` before writing an eBay-ready CSV.

If the User SKU / Custom Label column cannot be identified, the tool prints available columns and stops unless an exact column is configured with `--user-sku-column`.
