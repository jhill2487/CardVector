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
  "Repricing Review",
  "renderOperatorRepricingReview",
  "repricingReviewStorageKey",
  "cardvector.repricingPlan.v1",
  "parseRepricingPlanFile",
  "parseRepricingPlanJson",
  "parseRepricingPlanCsv",
  "canApproveRepricingRow",
  "reviewedRepricingExport",
  "Export reviewed plan",
  "Approve all safe",
  "Apply approved changes",
  "Open sold search",
  "This page does not sign in to CardUploader, revise eBay listings, update TCGplayer, or change live inventory.",
  "live_apply_permitted: false",
].forEach((needle) => assert(app.includes(needle), `app.js missing ${needle}`));

[
  '"repricing"',
  '"price-review"',
].forEach((needle) => assert(exporter.includes(needle), `export route missing ${needle}`));

[
  ".repricing-summary",
  ".repricing-command-bar",
  ".repricing-filter",
  ".repricing-row",
  ".repricing-chip",
  ".repricing-price-stack",
  ".repricing-actions",
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

assert(
  /id="repricing-apply-live"[^>]*disabled/.test(repricingSource),
  "live apply button must remain disabled"
);

console.log("Operator repricing approval contract passed.");
