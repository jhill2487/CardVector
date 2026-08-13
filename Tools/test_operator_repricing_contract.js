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
  "Review CardUploader automatic inventory prices through the workstation helper before changing values that sync live to eBay",
  "Live apply remains disabled until the persistent PC helper and approval guardrails are built",
  "CardUploader remains inventory truth",
  "Safe Review Workflow",
  "PC Helper Connection",
  "Check helper status",
  "Request inventory snapshot",
  "Not connected yet",
  "The manual scanner has been retired from the primary workflow",
  "No helper snapshot loaded yet",
  "id=\"repricing-helper-status\"",
  "id=\"repricing-request-snapshot\"",
  "Price Review Candidates",
  "Download approved prices",
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
].forEach((needle) => assert(css.includes(needle), `style.css missing ${needle}`));

const repricingSource = app.slice(
  app.indexOf("async function renderOperatorRepricingReview"),
  app.indexOf("async function renderOperatorListingReconciliationView")
);

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
].forEach((needle) => assert(!repricingSource.includes(needle), `repricing page still contains import workflow marker ${needle}`));

assert(
  /id="repricing-apply-live"[^>]*disabled/.test(repricingSource),
  "price preparation button must remain disabled"
);

assert(
  /id="repricing-request-snapshot"[^>]*disabled/.test(repricingSource),
  "helper snapshot button must remain disabled until helper exists"
);

assert(
  !/id="repricing-helper-status"[^>]*disabled/.test(repricingSource),
  "helper status button must be active"
);

console.log("Operator PC-helper price-review contract passed.");
