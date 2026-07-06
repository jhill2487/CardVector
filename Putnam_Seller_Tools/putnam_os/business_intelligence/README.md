# Putnam OS - Business Intelligence & Action Queue v0.1

## Purpose

This module reads existing Putnam OS, seller audit, CardUploader, and eBay CSV outputs and turns them into a lightweight business snapshot plus an action queue.

It answers:

```text
What should I work on next to improve profit per envelope, inventory velocity, and cash flow?
```

This is an analysis module only. It does not replace CardUploader, eBay, or the inventory system. It does not modify input files.

## Save Location

```text
%USERPROFILE%\OneDrive\PutnamCollectibles\Putnam_Seller_Tools\putnam_os\business_intelligence\
```

## Input Folders

The script checks the requested legacy folders and current reorganized Putnam OS folders when available:

```text
%USERPROFILE%\OneDrive\PutnamCollectibles\eBay Store Items\
%USERPROFILE%\OneDrive\PutnamCollectibles\Business\eBay_Store_Items\
%USERPROFILE%\OneDrive\PutnamCollectibles\Putnam_Seller_Tools\seller_audit\reports\
%USERPROFILE%\OneDrive\PutnamCollectibles\Platform\Putnam_OS\Putnam_Seller_Tools\seller_audit\reports\
%USERPROFILE%\OneDrive\PutnamCollectibles\Putnam_Seller_Tools\listing_optimizer\
%USERPROFILE%\OneDrive\PutnamCollectibles\Platform\Putnam_OS\Putnam_Seller_Tools\listing_optimizer\
%USERPROFILE%\OneDrive\PutnamCollectibles\Platform\Putnam_OS\Completed Jobs\
%USERPROFILE%\OneDrive\PutnamCollectibles\Data\Exports\
%USERPROFILE%\OneDrive\PutnamCollectibles\Data\Imports\CardUploader_Inventory\
%USERPROFILE%\OneDrive\PutnamCollectibles\Data\Logs\
```

## Required Input Reports

The module works best when these exist:

- `putnam_seller_audit_summary.txt`
- `missing_or_invalid_user_sku.csv`
- `pricing_audit.csv`
- `title_audit.csv`
- `duplicate_titles.csv`
- `free_shipping_listings.csv`
- `export_history.csv`
- latest `ebay_upload_ready*.csv`

If files are missing, the script continues and lists missing metrics in the summary.

## Output Reports

Reports are written to:

```text
%USERPROFILE%\OneDrive\PutnamCollectibles\Putnam_Seller_Tools\putnam_os\business_intelligence\reports\
```

Generated files:

- `business_intelligence_summary.txt`
- `action_queue.csv`
- `action_queue_summary.txt`
- `kpi_snapshot.csv`

## Run Command

From the repository root:

```powershell
python Putnam_Seller_Tools\putnam_os\business_intelligence\business_intelligence_v0_1.py
```

Or:

```powershell
py Putnam_Seller_Tools\putnam_os\business_intelligence\business_intelligence_v0_1.py
```

To open the action queue summary after completion:

```powershell
python Putnam_Seller_Tools\putnam_os\business_intelligence\business_intelligence_v0_1.py --open-report
```

## Example Workflow

1. Export or refresh eBay/CardUploader reports.
2. Run seller audit and listing optimizer as usual.
3. Run this BI module.
4. Open `action_queue_summary.txt`.
5. Work the top action first.
6. Re-run after a cleanup, pricing, or listing session.

## Version

Business Intelligence & Action Queue v0.1
