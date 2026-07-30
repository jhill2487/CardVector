# CardVector OS

CardVector OS is the operating workspace for Putnam Collectibles inventory,
pricing, SKU/location logic, work sessions, and eBay-ready CSV workflows.

## CardVector Platform v1.3.0

v1.3.0 makes CardVector OS a minimal workflow conductor.

Production navigation:

- Home
- Capture
- Processing
- Marketplace
- Orders
- Settings

Home is limited to Pending Work and Active Listings.
Processing combines CardUploader CSV intake, pricing review, and eBay export
handoff while retaining the exact capture-folder context. Pricing work runs in
the background and progress is hidden while idle.

CardVector coordinates Capture -> CardUploader -> Processing -> eBay. It does
not replace recognition, managed marketplace inventory, or fulfillment systems.

## CardVector Platform v1.2.2

v1.2.2 applied CardVector UI Foundation v1 to the production shell, shared
controls, status indicators, and tables.

## CardVector Platform v1.2.1

v1.2.1 adds the shared OBS WebSocket connection manager used by CardVector
Capture Studio status checks and screenshot capture.

## CardVector Platform v1.2.0

v1.2.0 adds CardVector Capture Studio v2.1 Automated OBS Capture.

Production rhythm:

```text
Place card
CardVector detects stable image
Front is captured automatically
Flip card
CardVector detects stable image
Back is captured automatically
Repeat
```

Manual capture remains available at all times with the `Capture` button.

Auto Capture settings are stored at:

```text
Platform/Putnam_OS/System/config/auto_capture_settings.json
```

Default settings:

```json
{
  "auto_capture_enabled": false,
  "stability_delay_seconds": 1.0,
  "duplicate_lockout_seconds": 2.0,
  "frame_poll_interval_ms": 200,
  "sensitivity": "Medium"
}
```

Auto Capture compares live OBS screenshots, waits for image stability, prevents
same-frame duplicate captures, and writes images into the existing Capture
Studio session structure.

## CardVector Platform v1.1.1

v1.1.1 is a production UI regression-fix release:

- Capture button label is now `Capture`.
- Capture preview rail loads actual front/back JPEG thumbnails when readable.
- Import owns CardUploader CSV intake.
- Pricing & Decisions no longer duplicates the Import CSV drop zone or Fast Path
  section.
- Inventory Label Center logs generation results to
  `Data/Logs/label_generation_log.txt` and keeps the app open on success or
  failure.

## CardVector Platform v1.1.0

This release focuses on production workflow cleanup:

- CardVector Capture Studio v2 now presents one operator capture action:
  `Capture Next Card`.
- OBS connection management is passive. The app checks connection health and
  only shows `Retry` when OBS is not connected.
- Recent capture pairs are displayed in a permanently docked right preview rail.
- Inventory Label Center v1 exposes QR/PDF location label generation from the
  Inventory tab.

Capture Studio remains image acquisition only. CardUploader remains the card
recognition source.

## CardVector Capture Studio v2

Open:

```text
Capture
```

Production workflow:

```text
Start Capture Session
Capture Next Card
Capture Next Card
Finish Session
```

`Capture Next Card` automatically alternates front/back internally. Operators do
not choose front or back in the production UI.

The current session panel shows:

- session name
- capture folder
- cards captured
- current card
- current pair status
- passive OBS connection state

The right preview rail shows recent pairs with front/back thumbnails, pair
number, timestamp, and pair status. Clicking a thumbnail opens a larger preview.

## Inventory Label Center v1

Open:

```text
Inventory -> Label Center
```

Select:

```text
ETB Labels
```

Then choose:

```text
Generate Labels
```

Initial production support focuses on ETB/location labels. Future templates are
reserved for long boxes, binder spines, shelves, and card show cases.

## CardVector OS Inventory Label Generator v1

The ETB QR label generator creates printable PDF labels for storage locations.

Script:

```text
Platform/Putnam_OS/System/tools/generate_etb_qr_labels.py
```

Install dependencies:

```powershell
py -m pip install "qrcode[pil]" reportlab
```

Run against the existing location registries:

```powershell
py Platform\Putnam_OS\System\tools\generate_etb_qr_labels.py
```

Run against a fallback CSV:

```powershell
py Platform\Putnam_OS\System\tools\generate_etb_qr_labels.py --csv Platform\Putnam_OS\System\tools\sample_etb_locations.csv
```

Output PDFs are written to:

```text
Data/Exports/Labels/
```

QR identity:

```text
https://cardvector.app/etb/<etb_id>
https://cardvector.app/location/<etb_id>/<location_code>
```

## Inventory Audit Mode v1.0

Inventory Audit Mode lives inside the existing Putnam OS application:

```text
Inventory -> Inventory Audit
```

It is not a standalone app.

Purpose:

- Physically verify active inventory.
- Assign trusted Batch Locations.
- Preserve audit progress for resume.
- Optionally attach internal verification images.
- Generate a safe eBay bulk revise CSV later.

Core rule:

```text
User SKU / Custom Label = Batch Location
```

Examples:

```text
ETB-01-A
ETB-01-B
ETB-04-A
```

The Batch Location answers:

```text
Where is this card stored?
```

The eBay Item ID and Title identify the listing/card.

## Inventory Audit Workflow

1. Open Putnam OS.
2. Go to `Inventory`.
3. Choose an inventory source CSV.
4. Select game/category.
5. Select or override the suggested Batch Location.
6. Load the audit queue.
7. Physically verify each card.
8. Use one of the audit actions:

```text
Confirm
Already Correct
Missing Card
Needs Review
Skip
Previous
Next
```

9. Generate reports.

## Supported Sources

Inventory Audit is source-agnostic internally. Normalized fields are:

```text
item_id
title
game
category
quantity
user_sku
source_file
source_type
```

v1.0 primary source:

```text
Latest eBay Active Listings Report
```

Future sources can include Putnam OS exports, CardUploader exports, and manual
inventory CSVs without changing the audit workflow.

## Capture Studio Integration

Inventory Audit can optionally attach internal verification images.

This is not OCR.
This is not scanning.
This is not CardUploader recognition.

If enabled, Putnam OS can launch Capture Studio. Confirmed audit cards attach
the latest Capture Studio JPEG into:

```text
Putnam_OS\System\data\inventory_audit\audit_images\
```

These images are internal evidence only and should never be uploaded to eBay.

### OBS WebSocket Config

Capture Studio reads OBS connection settings from:

```text
Platform/Putnam_OS/System/config/obs_config.json
```

Exact keys:

```json
{
  "obs": {
    "host": "127.0.0.1",
    "port": 4455,
    "password": ""
  }
}
```

The OBS password can be entered once in Putnam OS under `Settings -> OBS
WebSocket`. `PUTNAM_OBS_PASSWORD` overrides the saved password when present.

## eBay Business Policy Config

Putnam OS reads eBay policy names from:

```text
Platform/Putnam_OS/System/config/ebay_business_policies.json
```

Exact keys:

```json
{
  "ebay_business_policies": {
    "shipping_policy": "BuyerPaid Ship - EBay Standard Envelope",
    "payment_policy": "",
    "return_policy": ""
  }
}
```

These values can be edited in Putnam OS under `Settings -> eBay Business
Policies`. eBay CSV export stops before writing a file if any required policy
name is blank.

## Launch Modes

Development launch with console output:

```text
Platform/Putnam_OS/Run Putnam OS.bat
```

Production launch without a visible console:

```text
Platform/Putnam_OS/Run Putnam OS Production.vbs
```

## Audit Storage

Persistent audit files are stored under:

```text
Putnam_OS\System\data\inventory_audit\
```

Important files:

```text
current_inventory_audit.json
inventory_audit_history.csv
audit_images\
reports\
```

Progress is saved after each audit action, so the operator can resume later.

## Reports

Generated reports:

```text
inventory_location_audit.csv
inventory_location_summary.txt
ebay_bulk_revise_location_confirmed.csv
```

Safety:

- eBay is never modified directly.
- Source CSVs are never modified.
- Only `confirmed` rows appear in the eBay bulk revise CSV.
- Missing, needs-review, skipped, and already-correct rows are excluded from the bulk revise CSV.
- `CS-*` values remain preserved unless the operator confirms a location through audit.

## Batch Size Guidance

Target batch size:

```text
100 cards
```

Healthy range:

```text
75-125 cards
```

Putnam OS warns below 50 or above 125, but does not block the operator.
