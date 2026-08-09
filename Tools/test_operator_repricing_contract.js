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

console.log("Operator batch import price-review contract passed.");
