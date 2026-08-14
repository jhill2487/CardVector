const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
const app = fs.readFileSync(path.join(root, "Docs", "app.js"), "utf8");
const start = app.indexOf("function automaticInventoryHeaderKey");
const end = app.indexOf("function parseCardUploaderAutomaticInventorySnapshot");

assert(start > -1, "automatic inventory header helper not found");
assert(end > start, "automatic inventory parser boundary not found");

const source = app.slice(start, end);
const api = vm.runInNewContext(`(() => {
${source}
return {
  automaticInventoryHeaderKey,
  looksLikeAutomaticInventoryHeaders,
  mappedAutomaticInventoryCells,
  automaticInventoryGameLabel,
  automaticInventoryGameFromRow
};
})()`);

const headers = ["Card", "Status", "Platform", "User SKU", "Catalog SKU", "Condition", "Variant", "TCG", "Price", "Market", "Qty"];
assert.strictEqual(api.looksLikeAutomaticInventoryHeaders(headers), true);

const pokemonCells = ["Eevee Gem Pack Volume 2 0110/15", "Listed", "eBay", "ETB-006-A", "CS-POKE-123", "NM", "Normal", "Pokemon English", "$1.58", "$0.31", "1"];
const mtgCells = ["Counter Gain 25c", "Listed", "eBay + Mana Pool", "ETB-010-B", "CS-MTG-456", "NM", "Normal", "Magic", "$1.58", "$0.21", "1"];
const manaPoolPlatformCells = ["Forest Basic Land", "Listed", "Mana Pool", "ETB-010-C", "CS-UNK-789", "NM", "Normal", "", "$1.58", "$0.01", "1"];

assert.strictEqual(api.automaticInventoryGameFromRow(api.mappedAutomaticInventoryCells(headers, pokemonCells), pokemonCells), "Pokemon");
assert.strictEqual(api.automaticInventoryGameFromRow(api.mappedAutomaticInventoryCells(headers, mtgCells), mtgCells), "Magic");
assert.strictEqual(api.automaticInventoryGameFromRow(api.mappedAutomaticInventoryCells(headers, manaPoolPlatformCells), manaPoolPlatformCells), "");

const shiftedHeaders = ["Card", "Status", "Platform", "User SKU", "Catalog SKU", "Condition", "Variant", "Price", "Market", "Qty"];
const shiftedPokemonCells = ["Eevee Gem Pack Volume 2 0110/15", "Listed", "eBay", "ETB-006-A", "CS-POKE-123", "NM", "Normal", "Pokemon English", "$1.58", "$0.31", "1"];
const shiftedMtgCells = ["Counter Gain 25c", "Listed", "eBay + Mana Pool", "ETB-010-B", "CS-MTG-456", "NM", "Normal", "Magic", "$1.58", "$0.21", "1"];

assert.strictEqual(api.automaticInventoryGameFromRow(api.mappedAutomaticInventoryCells(shiftedHeaders, shiftedPokemonCells), shiftedPokemonCells), "Pokemon");
assert.strictEqual(api.automaticInventoryGameFromRow(api.mappedAutomaticInventoryCells(shiftedHeaders, shiftedMtgCells), shiftedMtgCells), "Magic");

console.log("Automatic inventory game detection passed.");
