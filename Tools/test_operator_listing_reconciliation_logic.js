const fs = require("fs");
const path = require("path");
const assert = require("assert");

const app = fs.readFileSync(path.join(__dirname, "..", "Docs", "app.js"), "utf8");

function sourceBetween(startNeedle, endNeedle) {
  const start = app.indexOf(startNeedle);
  const end = app.indexOf(endNeedle, start);
  assert(start >= 0, `Missing source start ${startNeedle}`);
  assert(end > start, `Missing source end ${endNeedle}`);
  return app.slice(start, end);
}

function functionSource(name) {
  const start = app.indexOf(`function ${name}(`);
  assert(start >= 0, `Missing function ${name}`);
  let parenDepth = 0;
  let brace = -1;
  for (let index = start; index < app.length; index += 1) {
    if (app[index] === "(") parenDepth += 1;
    if (app[index] === ")") parenDepth -= 1;
    if (parenDepth === 0 && app[index] === "{") {
      brace = index;
      break;
    }
  }
  assert(brace >= 0, `Missing function body for ${name}`);
  let depth = 0;
  for (let index = brace; index < app.length; index += 1) {
    if (app[index] === "{") depth += 1;
    if (app[index] === "}") depth -= 1;
    if (depth === 0) return app.slice(start, index + 1);
  }
  throw new Error(`Unterminated function ${name}`);
}

const build = new Function(`
  ${sourceBetween("const ebayListingColumns", "function normalizeCsvColumn")}
  function escapeHtml(value) { return String(value || ""); }
  function compactStatusLabel(value) { return String(value || ""); }
  ${functionSource("normalizeSku")}
  ${functionSource("normalizeCsvColumn")}
  ${functionSource("csvCell")}
  ${functionSource("parseCsvRows")}
  ${functionSource("columnMapping")}
  ${functionSource("parseMoney")}
  ${functionSource("parseWholeNumber")}
  ${functionSource("normalizeSnapshotIdentityPart")}
  ${functionSource("listingLocationHint")}
  ${functionSource("baseLocationHint")}
  ${functionSource("reasonBucket")}
  ${functionSource("syntheticMarketplaceListingId")}
  ${functionSource("syntheticInventorySnapshotId")}
  ${functionSource("inventoryQuantitySnapshotPayload")}
  ${functionSource("inventorySnapshotConflictKey")}
  ${functionSource("dedupeInventorySnapshotRows")}
  ${functionSource("summarizeListingRows")}
  ${functionSource("summarizeInventoryRows")}
  ${functionSource("parseMarketplaceListingsCsv")}
  ${functionSource("parseEbayListingsCsv")}
  ${functionSource("parseCardUploaderInventoryCsv")}
  ${functionSource("listingReferenceLocation")}
  ${functionSource("reconcileListingSnapshots")}
  ${functionSource("buildMarketplaceAllocationLedger")}
  return { reconcileListingSnapshots, parseMarketplaceListingsCsv, parseEbayListingsCsv, parseCardUploaderInventoryCsv, inventoryQuantitySnapshotPayload, dedupeInventorySnapshotRows, buildMarketplaceAllocationLedger };
`);
const {
  reconcileListingSnapshots: reconcile,
  parseMarketplaceListingsCsv,
  parseEbayListingsCsv,
  parseCardUploaderInventoryCsv,
  inventoryQuantitySnapshotPayload,
  dedupeInventorySnapshotRows,
  buildMarketplaceAllocationLedger,
} = build();

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

const ebayCsv = [
  "Item number,Custom label (SKU),Title,Current price,Available quantity",
  "123,ETB-001-A.1,Pikachu,$1.99,1",
].join("\n");
const parsedEbay = parseEbayListingsCsv(ebayCsv, { name: "ebay.csv", sha256: "abc" });
assert.strictEqual(parsedEbay.marketplace, "ebay");
assert.strictEqual(parsedEbay.errors.length, 0);
assert.strictEqual(parsedEbay.records[0].marketplace_listing_id, "123");
assert.strictEqual(parsedEbay.records[0].quantity_available, 1);

const tcgCsv = [
  "Product Name,SKU,Condition,Price,Quantity",
  "Pikachu,ETB-001-A.1,Near Mint,1.99,1",
].join("\n");
const parsedTcg = parseMarketplaceListingsCsv(tcgCsv, { name: "tcg.csv", sha256: "def" }, "tcgplayer");
assert.strictEqual(parsedTcg.marketplace, "tcgplayer");
assert.strictEqual(parsedTcg.errors.length, 0);
assert.strictEqual(parsedTcg.records[0].listing_id_is_synthetic, true);
assert.ok(parsedTcg.records[0].marketplace_listing_id.startsWith("tcgplayer:snapshot:"));
assert.ok(parsedTcg.records[0].reason_codes.includes("SYNTHETIC_MARKETPLACE_ID"));

const cardUploaderCsv = [
  "Title,User SKU,Condition,Qty,Status",
  "Pikachu,ETB-001-A.1,Near Mint,1,Listed",
].join("\n");
const parsedInventory = parseCardUploaderInventoryCsv(cardUploaderCsv, { name: "inventory.csv", sha256: "ghi" });
assert.strictEqual(parsedInventory.type, "inventory");
assert.strictEqual(parsedInventory.errors.length, 0);
assert.strictEqual(parsedInventory.records[0].external_inventory_provider, "carduploader");
assert.ok(parsedInventory.records[0].external_inventory_id.startsWith("carduploader:snapshot:"));
assert.strictEqual(parsedInventory.records[0].available_quantity, 1);
assert.strictEqual(parsedInventory.summary.totalQuantity, 1);

const duplicateProductSkuCsv = [
  "Title,User SKU,Catalog SKU,Condition,Qty",
  "Pikachu,ETB-001-A.1,12345,Near Mint,1",
  "Pikachu,ETB-001-A.2,12345,Near Mint,1",
].join("\n");
const parsedDuplicateProductSku = parseCardUploaderInventoryCsv(duplicateProductSkuCsv, { name: "inventory.csv", sha256: "same-file" });
assert.strictEqual(parsedDuplicateProductSku.errors.length, 0);
assert.notStrictEqual(
  parsedDuplicateProductSku.records[0].external_inventory_id,
  parsedDuplicateProductSku.records[1].external_inventory_id,
  "Catalog SKU must not collapse separate CardUploader inventory rows"
);

const duplicateRows = [
  inventoryQuantitySnapshotPayload(
    {
      ...parsedInventory.records[0],
      external_inventory_id: "stable-carduploader-row-1",
      condition: "Near Mint",
    },
    { id: "user-1" },
    "batch-1"
  ),
  inventoryQuantitySnapshotPayload(
    {
      ...parsedInventory.records[0],
      external_inventory_id: "stable-carduploader-row-1",
      condition: "Near Mint",
      row_number: 2,
      raw_row: { duplicate: "same identity" },
    },
    { id: "user-1" },
    "batch-1"
  ),
];
const dedupedInventory = dedupeInventorySnapshotRows(duplicateRows);
assert.strictEqual(dedupedInventory.rows.length, 1);
assert.strictEqual(dedupedInventory.duplicateCount, 1);
assert.strictEqual(dedupedInventory.rows[0].duplicate_source_rows.length, 1);

const allocation = buildMarketplaceAllocationLedger(
  [
    { marketplace: "ebay", sku: "ETB-001-A.1", quantity_available: 1 },
    { marketplace: "tcgplayer", sku: "etb-001-a.1", quantity_available: 1 },
    { marketplace: "ebay", sku: "ETB-002-B.1", quantity_available: 1 },
  ],
  [
    { sku: "ETB-001-A.1", inventory_title: "Pikachu", available_quantity: 1 },
    { sku: "ETB-002-B.1", inventory_title: "Charmander", available_quantity: 3 },
  ],
);
assert.strictEqual(allocation[0].sku, "ETB-001-A.1");
assert.strictEqual(allocation[0].allocation_status, "oversell_risk");
assert.ok(allocation[0].reason_codes.includes("LISTED_QUANTITY_EXCEEDS_AVAILABLE"));
assert.strictEqual(allocation.find((row) => row.sku === "ETB-002-B.1").allocation_status, "safe_capacity");

const missingInventory = buildMarketplaceAllocationLedger(
  [{ marketplace: "tcgplayer", sku: "NO-SNAPSHOT", quantity_available: 2 }],
  [],
);
assert.strictEqual(missingInventory[0].allocation_status, "needs_inventory_snapshot");

console.log("Operator listing reconciliation logic passed.");
