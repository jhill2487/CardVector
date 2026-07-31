const fs = require("fs");
const path = require("path");
const assert = require("assert");

const app = fs.readFileSync(path.join(__dirname, "..", "Docs", "app.js"), "utf8");

function functionSource(name) {
  const start = app.indexOf(`function ${name}(`);
  assert(start >= 0, `Missing function ${name}`);
  const brace = app.indexOf("{", start);
  let depth = 0;
  for (let index = brace; index < app.length; index += 1) {
    if (app[index] === "{") depth += 1;
    if (app[index] === "}") depth -= 1;
    if (depth === 0) return app.slice(start, index + 1);
  }
  throw new Error(`Unterminated function ${name}`);
}

const build = new Function(`
  ${functionSource("normalizeSku")}
  ${functionSource("listingLocationHint")}
  ${functionSource("baseLocationHint")}
  ${functionSource("listingReferenceLocation")}
  ${functionSource("reconcileListingSnapshots")}
  return reconcileListingSnapshots;
`);
const reconcile = build();

const listings = [
  { marketplace_listing_id: "1", sku: "ETB-001-A.1", listing_title: "Matched" },
  { marketplace_listing_id: "2", sku: "solo-1", listing_title: "eBay only" },
  { marketplace_listing_id: "3", sku: "dup", listing_title: "Duplicate one" },
  { marketplace_listing_id: "4", sku: "DUP", listing_title: "Duplicate two" },
  { marketplace_listing_id: "5", sku: "", listing_title: "Missing SKU" },
  { marketplace_listing_id: "6", sku: "ETB-999-A.1", listing_title: "Unknown location" },
];
const references = [
  { carduploader_batch_id: "batch-1", location_display_code: "ETB-001-A" },
  { carduploader_batch_id: "batch-2", location_display_code: "ETB-002-B" },
];
const buckets = reconcile(listings, references);

assert.strictEqual(buckets.matched.length, 1);
assert.strictEqual(buckets.ebay_only.length, 1);
assert.strictEqual(buckets.duplicate_sku.length, 2);
assert.strictEqual(buckets.missing_sku.length, 1);
assert.strictEqual(buckets.needs_manual_review.length, 1);
assert.strictEqual(buckets.missing_from_ebay.length, 1);
assert.strictEqual(buckets.matched[0].matched_batch_references[0].carduploader_batch_id, "batch-1");
assert.strictEqual(buckets.missing_from_ebay[0].carduploader_batch_id, "batch-2");

console.log("Operator listing reconciliation logic passed.");
