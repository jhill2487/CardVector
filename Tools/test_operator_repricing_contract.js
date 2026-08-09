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
  "Batch Import Price Review",
  "renderOperatorRepricingReview",
  "Open CardUploader Batches",
  "carduploader.com/dashboard/history",
  "Review starting prices before a CardUploader batch is added to automatic inventory",
  "Automatic inventory is treated as post-approval live state",
  "CardUploader remains inventory truth",
  "Pre-Live Workflow",
  "CardUploader Batch Scanner",
  "id=\"repricing-copy-scanner\"",
  "id=\"repricing-load-snapshot\"",
  "id=\"carduploader-batch-snapshot\"",
  "cardUploaderBatchScannerScript",
  "parseCardUploaderBatchSnapshot",
  "carduploader_batch_page_snapshot",
  "Scanned Batch Rows",
  "Prepare approved prices",
  "Bulk preparation remains capped",
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
  ".click(",
  "fetch(",
  "XMLHttpRequest",
  ".submit(",
].forEach((needle) => assert(!app.slice(app.indexOf("function cardUploaderBatchScannerScript"), app.indexOf("function looksLikeCardUploaderBatchUrl")).includes(needle), `scanner script contains unsafe marker ${needle}`));

[
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
  !/id="repricing-copy-scanner"[^>]*disabled/.test(repricingSource),
  "batch scanner button must be active"
);

assert(
  !/id="repricing-load-snapshot"[^>]*disabled/.test(repricingSource),
  "batch snapshot review button must be active"
);

console.log("Operator batch import price-review contract passed.");
