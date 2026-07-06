# Putnam Seller Audit v1.1

Local quality-control reports for eBay Active Listings Report CSVs.

## Purpose

Putnam Seller Audit scans the newest eBay Active Listings Report CSV and creates read-only audit reports for:

- Shipping policy/free-shipping risk
- User SKU / warehouse label quality
- Title length and duplicate-title issues
- Pricing review thresholds
- Batch location coverage using the rule `User SKU = Batch Location`

The tool never modifies the source CSV. It only writes reports.

## Save Location

```text
%USERPROFILE%\OneDrive\PutnamCollectibles\Putnam_Seller_Tools\seller_audit\
```

## Input Folder

```text
%USERPROFILE%\OneDrive\PutnamCollectibles\eBay Store Items\
```

## Output Folder

```text
%USERPROFILE%\OneDrive\PutnamCollectibles\Putnam_Seller_Tools\seller_audit\reports\
```

## Run Command

From the seller audit folder:

```powershell
python putnam_seller_audit_v1_0.py
```

From the Putnam Collectibles root:

```powershell
python Putnam_Seller_Tools\seller_audit\putnam_seller_audit_v1_0.py
```

## Example Commands

```powershell
python putnam_seller_audit_v1_0.py
```

```powershell
python putnam_seller_audit_v1_0.py --input "%USERPROFILE%\OneDrive\PutnamCollectibles\eBay Store Items\eBay-all-active-listings-report.csv"
```

```powershell
python putnam_seller_audit_v1_0.py --open-report
```

Optional custom folders:

```powershell
python putnam_seller_audit_v1_0.py --folder "%USERPROFILE%\OneDrive\PutnamCollectibles\eBay Store Items" --output "%USERPROFILE%\OneDrive\PutnamCollectibles\Putnam_Seller_Tools\seller_audit\reports"
```

## Reports

- `free_shipping_listings.csv`
- `shipping_policy_summary.csv`
- `missing_or_invalid_user_sku.csv`
- `title_audit.csv`
- `duplicate_titles.csv`
- `pricing_audit.csv`
- `location_audit.csv`
- `location_registry_summary.csv`
- `putnam_seller_audit_summary.txt`

## SKU Repair Planner v1.1.2

Builds a safe local plan for repairing missing or invalid User SKU / Custom Label
values from the latest seller audit reports.

It does not revise eBay directly.

User SKU / Custom Label is treated as the physical storage location, not a
unique card identifier. Multiple listings can intentionally share the same ETB
location, such as `ETB-04-A`.

Run:

```powershell
python putnam_sku_repair_planner_v1_1.py
```

Non-interactive example:

```powershell
python putnam_sku_repair_planner_v1_1.py --location-prefix ETB-01-A
```

Game/category repair examples:

```powershell
python putnam_sku_repair_planner_v1_1.py --game Magic --location-prefix ETB-04-A
```

```powershell
python putnam_sku_repair_planner_v1_1.py --game "One Piece" --location-prefix ETB-05-A
```

If `--location-prefix` is omitted, the tool suggests the next available batch
location from the shared registry:

```powershell
python putnam_sku_repair_planner_v1_1.py --game Magic
```

To record the chosen location in the registry after writing a safe repair plan:

```powershell
python putnam_sku_repair_planner_v1_1.py --game Magic --location-prefix ETB-04-A --record-location
```

Outputs:

- `sku_repair_plan.csv`
- `sku_repair_summary.txt`
- `ebay_bulk_revise_sku_repair.csv`

When `--game` is used without `--output`, reports are written to a filtered
subfolder such as `reports\sku_repair_magic` or `reports\sku_repair_one_piece`.

The bulk revise CSV contains only rows marked safe for repair. `CS-*` and other
possible card-specific/non-location identifiers are preserved for manual review
and excluded from the bulk revise CSV. Duplicate titles and shared proposed ETB
locations are allowed because the SKU is a physical location, not a unique card
ID.

Shared location registry:

```text
%USERPROFILE%\OneDrive\PutnamCollectibles\Putnam_OS\System\config\location_registry.json
```
