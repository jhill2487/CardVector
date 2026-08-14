# CardVector CardUploader Chrome Helper

Private unpacked Chrome extension for the CardUploader automatic-inventory
repricing workflow.

## Status

Read-only helper foundation. It does not edit CardUploader, save prices, sync
eBay, publish listings, or make network requests.

## What It Does

- Runs on `https://carduploader.com/dashboard/inventory/automatic`.
- Adds a small CardVector helper panel.
- Scans loaded automatic-inventory table rows.
- Can scroll the current Automatic Inventory page and rescan loaded rows.
- Can scan paginated Automatic Inventory pages by clicking only the safe
  pagination Next control, including icon-only controls beside text such as
  `Page 1 of 6`.
- Captures richer read-only row evidence, including row links, image alt text,
  cell attributes, and visible row action labels.
- Saves the latest snapshot in Chrome extension storage.
- Runs on `https://cardvector.app/operator/repricing`.
- Bridges the latest snapshot into CardVector.app local page storage for review.

## Install Locally

1. Open Chrome on the workstation.
2. Go to `chrome://extensions`.
3. Turn on **Developer mode**.
4. Choose **Load unpacked**.
5. Select this folder:

   `Tools/carduploader_chrome_helper`

## Use

1. Open CardUploader Automatic Inventory in the same Chrome profile.
2. Click **Scan Loaded Rows**, **Scroll & Scan Page**, or **Scan All Pages** in the CardVector helper panel.
3. Open `https://cardvector.app/operator/repricing`.
4. Click **Send to Page** in the helper panel if needed.
5. Click **Check helper status**, then **Load helper snapshot** in CardVector.app.

## Safety

This extension is intentionally read-only. Live price application requires a
separate approved implementation after CardUploader save behavior is
characterized and tested.

The helper does not click row action menus. Options such as Mark Listed, Mark
Not Listed, Mark Sold, View Batch, and Manage Platforms are treated only as
evidence when they are already visible on the page. The only click automation in
version 0.3.3 is the non-destructive pagination Next control used by **Scan All
Pages**. The helper waits for the visible page number to advance before scanning
the next page.

For now, CardVector price review is eBay-only. If the helper can tell the
Manapool tab is active, scan buttons are disabled and no price-review snapshot is
created. Version 0.3.3 also recognizes CardUploader's visual eBay tab selection
when the page does not expose a formal selected-tab attribute.
