# Putnam OS Module: Bulk Price Reviser

Version: v1.1.0

## Purpose

Reprice current active eBay listings after the move from free shipping to buyer-paid shipping.

This tool is intentionally narrow. It does not optimize titles, item specifics, or inventory locations.
It applies the approved Putnam pricing ladder and creates review/output files.

## Current Pricing Ladder

- 1.49 -> 0.99
- 1.59 -> 1.09
- 1.69 -> 1.19
- 1.79 -> 1.29
- 1.99 -> 1.49
- 2.49 -> 1.99
- 2.99 -> 2.49

Higher prices are left unchanged.

## How to Use

1. Put your eBay active listings export CSV in:

   Putnam_OS/modules/Bulk_Price_Reviser/input

2. Double-click:

   run_bulk_price_reviser.bat

3. Review the files in:

   Putnam_OS/modules/Bulk_Price_Reviser/output

4. Only upload the eBay upload candidate after reviewing it.

## Output Files

- price_revision_review_TIMESTAMP.csv
- price_revision_changed_only_TIMESTAMP.csv
- eBay_price_revision_UPLOAD_CANDIDATE_TIMESTAMP.csv
- price_revision_report_TIMESTAMP.txt

## Safety

- Original input CSV is copied to archive before processing.
- The tool does not modify the original CSV.
- The eBay upload candidate only includes changed listings.
