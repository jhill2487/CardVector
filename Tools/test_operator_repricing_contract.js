const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
const docs = path.join(root, "Docs");
const app = fs.readFileSync(path.join(docs, "app.js"), "utf8");
const css = fs.readFileSync(path.join(docs, "style.css"), "utf8");
const exporter = fs.readFileSync(path.join(root, "Tools", "export_cardvector_site.py"), "utf8");

[
  'href="/operator/repricing"',
  "Automatic Inventory Price Review",
  "renderOperatorRepricingReview",
  "Open CardUploader Automatic Inventory",
  "carduploader.com/dashboard/inventory/automatic",
  "Review CardUploader automatic inventory prices through the Chrome helper before changing values that sync live to eBay",
  "Live apply remains disabled until apply behavior and approval guardrails are built",
  "CardUploader remains inventory truth",
  "Safe Review Workflow",
  "PC Helper Connection",
  "Check helper status",
  "Load helper snapshot",
  "No snapshot yet",
  "Install the private Chrome helper",
  "id=\"repricing-helper-status\"",
  "id=\"repricing-request-snapshot\"",
  "readStoredCardUploaderHelperSnapshot",
  "cardvector.carduploaderAutomaticInventorySnapshot.v1",
  "Price Review Candidates",
  "Floor Rule Recommendations",
  "Business pricing profile",
  "Include free shipping, supplies, fees, and profit",
  "Minimum viable",
  "Profit",
  "Target",
  "defaultRepricingFloorRuleConfig",
  "defaultRepricingBusinessProfile",
  "ebayStandardEnvelopeOneOz: 0.78",
  "repricingFloorRuleConfigStorageKey",
  "cardvector.repricingFloorRules.v1",
  "repricingFilterConfigStorageKey",
  "cardvector.repricingFilters.v1",
  "repricingBusinessProfileStorageKey",
  "cardvector.repricingBusinessProfile.v1",
  "readStoredRepricingFloorRuleConfig",
  "writeStoredRepricingFloorRuleConfig",
  "readStoredRepricingBusinessProfile",
  "writeStoredRepricingBusinessProfile",
  "calculateMinimumViablePrice",
  "buildRepricingBusinessAnalysis",
  "readStoredRepricingFilterConfig",
  "writeStoredRepricingFilterConfig",
  "data-repricing-floor",
  "raw.evidence_text",
  "raw.action_labels",
  "raw.cell_details",
  "Save floor rules",
  "Reset defaults",
  "Reapply to snapshot",
  "applyRepricingFloorRules",
  "summarizeRepricingFloorRules",
  "renderRepricingFloorRuleSummary",
  "focusCandidates",
  "scrollIntoView",
  "state.filters = writeStoredRepricingFilterConfig({ ...state.filters, status: floorSummary.raised ? \"increase\" : \"all\" })",
  "BELOW_DEFAULT_FLOOR",
  "POKEMON_HOLO_FLOOR_APPLIED",
  "POKEMON_ULTRA_RARE_FLOOR_APPLIED",
  "MTG_FOIL_FLOOR_APPLIED",
  "MINIMUM_VIABLE_PRICE_APPLIED",
  "FREE_SHIPPING_ASSUMED",
  "MANUAL_RECOMMENDATION_OVERRIDE",
  "Prepare approved price updates",
  "Review filters",
  "data-repricing-filter-field",
  "eBay + Mana Pool",
  "Under $2",
  "detectRepricingPlatform",
  "data-repricing-recommend",
  "updateRepricingRecommendation",
  "reviewedRepricingExport",
  "live_apply_permitted: false",
].forEach((needle) => assert(app.includes(needle), `app.js missing ${needle}`));

[
  '"repricing"',
  '"price-review"',
].forEach((needle) => assert(exporter.includes(needle), `export route missing ${needle}`));

[
  ".repricing-summary",
  ".repricing-command-bar",
  ".repricing-command-actions",
  ".repricing-scan-panel",
  ".repricing-live-steps",
  ".repricing-safeguard-list",
  ".repricing-instructions",
  ".repricing-helper-card",
  ".repricing-floor-card",
  ".repricing-floor-grid",
  ".repricing-floor-actions",
  ".repricing-filter-panel",
  ".repricing-filter-grid",
  ".repricing-filter-header",
  ".repricing-business-card",
  ".repricing-business-grid",
].forEach((needle) => assert(css.includes(needle), `style.css missing ${needle}`));

const repricingSource = app.slice(
  app.indexOf("async function renderOperatorRepricingReview"),
  app.indexOf("async function renderOperatorListingReconciliationView")
);

[
  "No CardUploader ID",
  "No SKU",
  "NO_NOTES",
  "Set recommended",
  "<span>Recommended</span>",
  "<span>Min viable</span>",
  "<span>Est. profit</span>",
].forEach((needle) => assert(!repricingSource.includes(needle), `repricing page should not show verbose row marker ${needle}`));

[
  "revise_listing",
  "publish_listing",
  "end_listing",
  "sync_to_tcgplayer",
  ".from(",
  ".upsert(",
  ".insert(",
  ".update(",
  ".delete(",
].forEach((needle) => assert(!repricingSource.includes(needle), `repricing page contains live-write marker ${needle}`));

[
  "fetch(",
  "XMLHttpRequest",
  ".submit(",
].forEach((needle) => assert(!app.slice(app.indexOf("function cardUploaderAutomaticInventoryScannerScript"), app.indexOf("function looksLikeCardUploaderAutomaticInventoryUrl")).includes(needle), `scanner script contains unsafe marker ${needle}`));

[
  "Batch Import Price Review",
  "CardUploader Batch Scanner",
  "Scan CardUploader batch",
  "Review batch prices",
  "carduploader_batch_page_snapshot",
  "Copy scanner script",
  "Load captured JSON",
  "Do not paste the scanner script itself here",
  "carduploader-batch-snapshot",
  "repricing-plan-file",
  "Import Repricing Plan",
  "Choose repricing plan JSON or CSV",
  "Export reviewed plan",
  "Approve all safe",
  "Live CardUploader Repricing",
  "Open CardUploader Inventory",
  "Scan visible rows read-only",
  "Automatic Inventory Snapshot",
  "repricing-scan-results-title",
  "renderCardUploaderAutomaticInventoryRows(state.snapshot)",
].forEach((needle) => assert(!repricingSource.includes(needle), `repricing page still contains import workflow marker ${needle}`));

assert(
  /id="repricing-apply-live"[^>]*disabled/.test(repricingSource),
  "price preparation button must remain disabled"
);

assert(
  /id="repricing-request-snapshot"[^>]*disabled/.test(repricingSource),
  "helper snapshot button must remain conditionally disabled until a snapshot exists"
);

assert(
  !/id="repricing-helper-status"[^>]*disabled/.test(repricingSource),
  "helper status button must be active"
);

console.log("Operator Chrome-helper price-review contract passed.");
