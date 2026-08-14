const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
const extensionDir = path.join(root, "Tools", "carduploader_chrome_helper");
const manifest = JSON.parse(fs.readFileSync(path.join(extensionDir, "manifest.json"), "utf8"));
const content = fs.readFileSync(path.join(extensionDir, "content.js"), "utf8");
const css = fs.readFileSync(path.join(extensionDir, "panel.css"), "utf8");
const readme = fs.readFileSync(path.join(extensionDir, "README.md"), "utf8");
const app = fs.readFileSync(path.join(root, "Docs", "app.js"), "utf8");

assert.strictEqual(manifest.manifest_version, 3);
assert.strictEqual(manifest.name, "CardVector CardUploader Helper");
assert.strictEqual(manifest.version, "0.3.14");
assert.deepStrictEqual(manifest.permissions, ["storage"]);
assert.deepStrictEqual(manifest.host_permissions, [
  "https://carduploader.com/dashboard/inventory/automatic*",
  "https://cardvector.app/operator/repricing*",
]);
assert.strictEqual(manifest.content_scripts.length, 1);
assert.deepStrictEqual(manifest.content_scripts[0].matches, manifest.host_permissions);
assert.deepStrictEqual(manifest.content_scripts[0].js, ["content.js"]);
assert.deepStrictEqual(manifest.content_scripts[0].css, ["panel.css"]);

[
  "CARDUPLOADER_URL_RE",
  "CARDVECTOR_URL_RE",
  "cardvector.latestCardUploaderAutomaticInventorySnapshot.v1",
  "cardvector.carduploaderAutomaticInventorySnapshot.v1",
  "carduploader_automatic_inventory_page_snapshot",
  "Scan Loaded Rows",
  "Scroll & Scan Page",
  "Scan All Pages",
  "Diagnose Pagination",
  "detectActiveMarketplaceTab",
  "HELPER_VERSION",
  "0.3.14",
  "\"tcg\"",
  "\"game\"",
  "automaticInventoryGameLabel",
  "automaticInventoryGameFromRow",
  "const tcg = automaticInventoryGameFromRow(mapped, cells)",
  "marketplaceTabCandidates",
  "isActiveMarketplaceCandidate",
  "platformHasEbay",
  "platformHasManapool",
  "rowsContainManapoolOnlyEvidence",
  "canScanForEbayPriceReview",
  "scanContextNote",
  "active_marketplace_tab",
  "Scans remain read-only",
  "scanScrollableAutomaticInventoryRows",
  "scanPaginatedAutomaticInventoryRows",
  "safeClickNextPageControl",
  "findNextPageControl",
  "pageInfoFromText",
  "findPageTextNextControl",
  "isMarketplaceTabControl",
  "closestClickableElement",
  "ancestorElements",
  "isLikelyClickableElement",
  "isBlockedPaginationControl",
  "pageTextRect",
  "isNearPageTextNextControl",
  "isCoordinatePaginationCandidate",
  "paginationControlsFromPoint",
  "paginationControlsNearPageText",
  "paginationDiagnosticReport",
  "paginationProbeElements",
  "copyTextToClipboard",
  "pagination Next control",
  "dedupeAutomaticInventoryRows",
  "evidence_text",
  "action_labels",
  "cell_details",
  "Row action menus are not clicked",
  "Send to Page",
  "Open Review",
  "Open CardUploader",
  "Read-only. No prices are edited.",
  "Snapshot sent to CardVector.app",
].forEach((needle) => assert(content.includes(needle), `content.js missing ${needle}`));

assert(content.includes("page\\s+([0-9]+)\\s+of\\s+([0-9]+)"), "content.js must detect Page X of Y pagination text");
assert(content.includes("isMarketplaceTabControl(element)"), "pagination safety must exclude marketplace tabs");
assert(content.includes("controlRect.left >= pageRect.right - 8"), "pagination safety must require the next control beside page text");
assert(content.includes("document.createRange()"), "pagination safety must locate the actual Page X of Y text range");
assert(content.includes("control.querySelector(\"svg, img\")"), "pagination safety must allow icon-only pagination buttons near page text");
assert(content.includes("horizontalDistance <= 180"), "pagination safety must keep next clicks near the page counter");
assert(content.includes("closestClickableElement(element)"), "pagination safety must click the clickable wrapper around icon-only controls");
assert(content.includes("document.elementsFromPoint(x, y)"), "pagination safety must probe the visual area beside the page counter");
assert(content.includes("JSON.stringify(report, null, 2)"), "diagnostic report must be copyable as formatted JSON");
assert(content.includes("!token.includes(\":\")"), "disabled detection must ignore Tailwind disabled: variant classes");

[
  "fetch(",
  "XMLHttpRequest",
  ".submit(",
  "chrome.tabs",
  "chrome.scripting",
  "password",
  "service_role",
  "SUPABASE",
  "supabase",
].forEach((needle) => assert(!content.includes(needle), `content.js contains forbidden marker ${needle}`));

[
  "querySelectorAll(\"table\")",
  "scrollBy",
  "next.click();",
  "chrome.storage.local.set",
  "chrome.storage.local.get",
  "window.localStorage.setItem",
  "CustomEvent(\"cardvector:carduploader-helper-snapshot\"",
].forEach((needle) => assert(content.includes(needle), `content.js missing bridge marker ${needle}`));

[
  ".cardvector-helper-panel",
  ".cardvector-helper-actions",
  ".cardvector-helper-meta",
].forEach((needle) => assert(css.includes(needle), `panel.css missing ${needle}`));

[
  "Read-only helper foundation",
  "Load unpacked",
  "does not edit CardUploader",
  "Scroll & Scan Page",
  "Scan All Pages",
  "does not click row action menus",
  "non-destructive pagination Next control",
  "Page 1 of 6",
  "visible page number to advance",
  "CardVector price review is eBay-only",
  "no longer blocks",
].forEach((needle) => assert(readme.includes(needle), `README missing ${needle}`));

const clickMatches = content.match(/\.click\(/g) || [];
assert.strictEqual(clickMatches.length, 1, "helper should only click the safe pagination Next control");
assert(content.includes("next.click();"), "helper click must remain isolated to safeClickNextPageControl");

[
  "cardvector.carduploaderAutomaticInventorySnapshot.v1",
  "readStoredCardUploaderHelperSnapshot",
  "Load helper snapshot",
  "No helper snapshot found yet",
].forEach((needle) => assert(app.includes(needle), `app.js missing helper integration ${needle}`));

console.log("CardUploader Chrome helper contract passed.");
