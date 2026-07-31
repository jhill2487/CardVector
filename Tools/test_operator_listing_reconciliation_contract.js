const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
const docs = path.join(root, "Docs");
const app = fs.readFileSync(path.join(docs, "app.js"), "utf8");
const css = fs.readFileSync(path.join(docs, "style.css"), "utf8");
const exporter = fs.readFileSync(path.join(root, "Tools", "export_cardvector_site.py"), "utf8");
const migration = fs.readFileSync(
  path.join(root, "supabase", "migrations", "20260730233000_ebay_listing_reconciliation.sql"),
  "utf8"
);

[
  'href="/operator/listings"',
  "renderOperatorListingReconciliation",
  "parseEbayListingsCsv",
  "cardvector_marketplace_listing_snapshots",
  "cardvector_inventory_listing_matches",
  "cardvector_ebay_listing_reconciliation_v",
  "cardvector_carduploader_batch_events",
  "reconcileListingSnapshots",
  "missing_from_ebay",
  "needs_manual_review",
  "Card-level absence cannot be inferred from batch metadata.",
  "CardUploader remains inventory truth; eBay remains live listing truth.",
  "This page does not revise, end, publish, or otherwise change live eBay listings.",
  '"owner_user_id,marketplace,marketplace_listing_id"',
].forEach((needle) => assert(app.includes(needle), `app.js missing ${needle}`));

[
  '"listings"',
  '"listing-reconciliation"',
].forEach((needle) => assert(exporter.includes(needle), `export route missing ${needle}`));

[
  ".listing-file-drop",
  ".listing-reconciliation-row",
  ".listing-summary",
  ".listing-bucket-summary",
  ".listing-buckets",
].forEach((needle) => assert(css.includes(needle), `style.css missing ${needle}`));

[
  "create table if not exists public.cardvector_marketplace_listing_snapshots",
  "create table if not exists public.cardvector_inventory_listing_matches",
  "create or replace view public.cardvector_ebay_listing_reconciliation_v",
  "alter table public.cardvector_marketplace_listing_snapshots enable row level security",
  "alter table public.cardvector_inventory_listing_matches enable row level security",
  "revoke all on table public.cardvector_marketplace_listing_snapshots from anon",
  "revoke all on table public.cardvector_inventory_listing_matches from anon",
  "notify pgrst, 'reload schema'",
].forEach((needle) => assert(migration.includes(needle), `migration missing ${needle}`));

const listingSource = app.slice(
  app.indexOf("const ebayListingColumns"),
  app.indexOf("function renderOperatorRegistryView")
);
[
  "revise_listing",
  "publish_listing",
  "end_listing",
  ".delete(",
].forEach((needle) => assert(!listingSource.includes(needle), `listing workflow contains live-write marker ${needle}`));

console.log("Operator listing reconciliation contract passed.");
