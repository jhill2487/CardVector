const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
const extensionDir = path.join(root, "Tools", "carduploader_chrome_helper");
const manifest = JSON.parse(fs.readFileSync(path.join(extensionDir, "manifest.json"), "utf8"));
const content = fs.readFileSync(path.join(extensionDir, "content.js"), "utf8");
const css = fs.readFileSync(path.join(extensionDir, "panel.css"), "utf8");
const readme = fs.readFileSync(path.join(extensionDir, "README.md"), "utf8");
const app = fs.readFileSync(path.join(root, "Docs", "app.js"), "utf8");

assert.strictEqual(manifest.manifest_version, 3);
assert.strictEqual(manifest.name, "CardVector CardUploader Helper");
assert.deepStrictEqual(manifest.permissions, ["storage"]);
assert.deepStrictEqual(manifest.host_permissions, [
  "https://carduploader.com/dashboard/inventory/automatic*",
  "https://cardvector.app/operator/repricing*",
]);
assert.strictEqual(manifest.content_scripts.length, 1);
assert.deepStrictEqual(manifest.content_scripts[0].matches, manifest.host_permissions);
assert.deepStrictEqual(manifest.content_scripts[0].js, ["content.js"]);
assert.deepStrictEqual(manifest.content_scripts[0].css, ["panel.css"]);

[
  "CARDUPLOADER_URL_RE",
  "CARDVECTOR_URL_RE",
  "cardvector.latestCardUploaderAutomaticInventorySnapshot.v1",
  "cardvector.carduploaderAutomaticInventorySnapshot.v1",
  "carduploader_automatic_inventory_page_snapshot",
  "Scan Visible Rows",
  "Send to Page",
  "Open Review",
  "Open CardUploader",
  "Read-only. No prices are edited.",
  "Snapshot sent to CardVector.app",
].forEach((needle) => assert(content.includes(needle), `content.js missing ${needle}`));

[
  "fetch(",
  "XMLHttpRequest",
  ".submit(",
  "chrome.tabs",
  "chrome.scripting",
  "password",
  "service_role",
  "SUPABASE",
  "supabase",
].forEach((needle) => assert(!content.includes(needle), `content.js contains forbidden marker ${needle}`));

[
  "querySelectorAll(\"table\")",
  "chrome.storage.local.set",
  "chrome.storage.local.get",
  "window.localStorage.setItem",
  "CustomEvent(\"cardvector:carduploader-helper-snapshot\"",
].forEach((needle) => assert(content.includes(needle), `content.js missing bridge marker ${needle}`));

[
  ".cardvector-helper-panel",
  ".cardvector-helper-actions",
  ".cardvector-helper-meta",
].forEach((needle) => assert(css.includes(needle), `panel.css missing ${needle}`));

[
  "Read-only helper foundation",
  "Load unpacked",
  "does not edit CardUploader",
].forEach((needle) => assert(readme.includes(needle), `README missing ${needle}`));

[
  "cardvector.carduploaderAutomaticInventorySnapshot.v1",
  "readStoredCardUploaderHelperSnapshot",
  "Load helper snapshot",
  "No helper snapshot found yet",
].forEach((needle) => assert(app.includes(needle), `app.js missing helper integration ${needle}`));

console.log("CardUploader Chrome helper contract passed.");
