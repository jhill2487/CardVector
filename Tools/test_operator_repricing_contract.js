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
  "Live CardUploader Repricing",
  "renderOperatorRepricingReview",
  "Open CardUploader Inventory",
  "carduploader.com/dashboard/inventory/automatic",
  "Scan visible rows read-only",
  "CardVector.app cannot read another website tab directly",
  "CardUploader remains inventory truth",
  "Apply approved changes",
  "Bulk apply remains capped",
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
].forEach((needle) => assert(!repricingSource.includes(needle), `repricing page still contains import workflow marker ${needle}`));

assert(
  /id="repricing-apply-live"[^>]*disabled/.test(repricingSource),
  "live apply button must remain disabled"
);

console.log("Operator live repricing contract passed.");
