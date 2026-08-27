const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
const docs = path.join(root, "Docs");
const app = fs.readFileSync(path.join(docs, "app.js"), "utf8");
const html = fs.readFileSync(path.join(docs, "index.html"), "utf8");
const css = fs.readFileSync(path.join(docs, "style.css"), "utf8");
const exporter = fs.readFileSync(path.join(root, "Tools", "export_cardvector_site.py"), "utf8");
const inventory = JSON.parse(fs.readFileSync(path.join(docs, "content", "shop", "direct-inventory.json"), "utf8"));

[
  'href="/shop/"',
  'href="/cart/"',
  "Shop Direct",
  "CardVector Cart",
].forEach((needle) => assert(html.includes(needle), `index.html missing ${needle}`));

[
  "directStoreInventoryUrl",
  "loadDirectStoreCatalog",
  "normalizeDirectStoreItem",
  "directStoreCartSummary",
  "setDirectStoreCartQuantity",
  "createDirectStoreReservation",
  "checkout_ready_for_payment_integration",
  "payment_status: \"not_configured\"",
  "marketplace_release_status: \"not_configured\"",
  "Adding to cart does not reserve inventory",
  "Checkout re-checks current availability",
  "route === \"shop\"",
  "route === \"cart\"",
  "cardvector.directStoreCart.v1",
  "cardvector.directStoreReservations.v1",
].forEach((needle) => assert(app.includes(needle), `app.js missing ${needle}`));

[
  "stripe.confirmPayment",
  "paypal.Buttons",
  "capture_payment",
  "end_listing",
  "revise_listing",
  "withdraw_offer",
  "sync_to_ebay",
].forEach((needle) => assert(!app.includes(needle), `direct storefront should not contain live action marker ${needle}`));

[
  ".direct-store-shell",
  ".direct-store-layout",
  ".direct-store-item",
  ".direct-cart-panel",
  ".direct-checkout-form",
].forEach((needle) => assert(css.includes(needle), `style.css missing ${needle}`));

[
  '"shop"',
  '"cart"',
  "render_shop_static_page",
  "render_cart_static_page",
  "content/shop/direct-inventory.json",
  'SITE_URL}/shop/',
].forEach((needle) => assert(exporter.includes(needle), `exporter missing ${needle}`));

assert.strictEqual(inventory.schema_version, "1.0");
assert.strictEqual(inventory.checkout_mode, "reservation_pilot");
assert.strictEqual(inventory.currency, "USD");
assert.deepStrictEqual(inventory.items, []);

console.log("Direct storefront cart contract passed.");
