# CardUploader Web Repricing Safeguards

## Status

Implemented as a non-destructive safety contract. Browser automation and live
CardUploader edits are not implemented in this step.

## Intended Workflow

1. Operator opens `https://carduploader.com/dashboard/inventory/automatic`.
2. CardVector reads visible CardUploader rows from the browser.
3. Marketplace Intelligence creates price recommendations.
4. CardVector builds approved-or-blocked CardUploader price-update plans.
5. CardVector maps approved plans back to visible CardUploader rows.
6. A safety gate validates the current page, save behavior, visible row identity,
   current price, row selector, row count, and explicit live-sync confirmation.
7. Only a later browser-assisted apply tool may type approved prices.

## Safety Requirements

- CardUploader remains inventory truth.
- CardVector must not edit CardUploader unless the operator explicitly approves
  the affected rows.
- The browser must be on the CardUploader automatic inventory page.
- Save behavior must be known before live apply.
- Autosave pages are blocked by default.
- The visible CardUploader current price must match the plan current price.
- The visible row must expose a stable price-input selector.
- Bulk apply is capped by policy.
- Live-sync impact must be explicitly acknowledged.
- Blocked or unapproved rows must never be applied.

## Implemented Contract

`Platform/cardvector/integrations/carduploader/web_repricing.py` defines:

- `CardUploaderWebInventoryRow`
- `CardUploaderWebPageSnapshot`
- `CardUploaderWebSafetyPolicy`
- `CardUploaderWebPriceEdit`
- `carduploader_inventory_snapshot_script(...)`
- `normalize_carduploader_web_snapshot(...)`
- `build_web_price_edits(...)`
- `require_web_apply_ready(...)`

The contract creates browser edit intents only. It performs no browser control,
network request, CardUploader write, eBay write, or TCGplayer write.

## Read-Only Page Scanner

The scanner script reads the CardUploader automatic-inventory page table without
clicking controls, typing values, submitting forms, or making network requests.
It normalizes visible table rows into `CardUploaderWebPageSnapshot` so plans can
be matched against the exact CardUploader row data visible to the operator.

The current CardUploader automatic inventory page exposes price values in the
table and a `Set price` control, but not stable visible price inputs until edit
mode is characterized. Because of that, table snapshots remain blocked from live
apply by default with `price_input_selector_missing` and unknown save-mode
guards.

## Live Apply Remains Future Work

Before enabling live edits, the browser automation layer must prove:

- How CardUploader saves price changes: manual save, row save, or autosave.
- Which DOM selectors identify rows and price inputs reliably.
- How validation errors are displayed.
- How to stop before submitting changes when safeguards fail.
- How to log every proposed and applied edit.

## Validation

Covered by:

- `Platform/cardvector/integrations/carduploader/test_web_repricing.py`
- `Platform/cardvector/integrations/carduploader/test_price_updates.py`
