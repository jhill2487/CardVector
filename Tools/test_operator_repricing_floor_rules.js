const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
const app = fs.readFileSync(path.join(root, "Docs", "app.js"), "utf8");
const start = app.indexOf("const repricingFloorRuleConfigStorageKey");
const end = app.indexOf("function renderRepricingFilters");

assert(start > -1, "floor rule config not found");
assert(end > start, "floor rule function boundary not found");

const source = app.slice(start, end);
const api = vm.runInNewContext(`(() => {
function parseMoney(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(String(value).replace(/[$,]/g, "").trim());
  return Number.isFinite(number) ? number : null;
}
const localStorage = {
  store: new Map(),
  getItem(key) { return this.store.has(key) ? this.store.get(key) : null; },
  setItem(key, value) { this.store.set(key, String(value)); }
};
const document = { querySelectorAll() { return []; } };
${source}
return {
  defaultRepricingFloorRuleConfig,
  normalizeRepricingFloorRuleConfig,
  readStoredRepricingFloorRuleConfig,
  writeStoredRepricingFloorRuleConfig,
  matchedRepricingFloorRule,
  applyRepricingFloorRules,
  summarizeRepricingFloorRules,
  detectRepricingGame,
  detectRepricingPlatform,
  filterRepricingRows,
  repricingReviewCsv
};
})()`);

function pricedRow(overrides = {}) {
  return {
    title: "Bulk common card",
    condition: "Near Mint",
    variant: "Normal",
    finish: "",
    set_name: "",
    card_number: "",
    marketplace: "carduploader",
    current_price: 1,
    recommended_price: null,
    price_delta: null,
    percent_delta: "",
    quantity: 1,
    confidence: "",
    status: "dry_run",
    review_decision: "manual_review",
    review_priority: "normal",
    reason_codes: ["CARDUPLOADER_AUTOMATIC_INVENTORY_VISIBLE"],
    notes: [],
    raw_row: {},
    ...overrides
  };
}

const [defaultFloor] = api.applyRepricingFloorRules([pricedRow()]);
assert.strictEqual(defaultFloor.recommended_price, 1.48);
assert(defaultFloor.reason_codes.includes("BELOW_DEFAULT_FLOOR"));

const customConfig = api.writeStoredRepricingFloorRuleConfig({
  defaultFloor: "1.67",
  pokemonHoloFloor: "2.11",
  pokemonUltraRareFloor: "3.49",
  mtgFoilFloor: "2.24"
});
assert.deepStrictEqual(api.readStoredRepricingFloorRuleConfig(), customConfig);

const [customDefaultFloor] = api.applyRepricingFloorRules([pricedRow()], customConfig);
assert.strictEqual(customDefaultFloor.recommended_price, 1.67);

const [pokemonHolo] = api.applyRepricingFloorRules([pricedRow({
  title: "Pikachu Reverse Holo Pokemon",
  variant: "Reverse Holo",
  current_price: 1.5
})], customConfig);
assert.strictEqual(pokemonHolo.recommended_price, 2.11);
assert(pokemonHolo.reason_codes.includes("POKEMON_HOLO_FLOOR_APPLIED"));

const [pokemonUltraRare] = api.applyRepricingFloorRules([pricedRow({
  title: "Charizard VMAX Secret Rare Pokemon",
  current_price: 1.99
})], customConfig);
assert.strictEqual(pokemonUltraRare.recommended_price, 3.49);
assert(pokemonUltraRare.reason_codes.includes("POKEMON_ULTRA_RARE_FLOOR_APPLIED"));

const [mtgFoil] = api.applyRepricingFloorRules([pricedRow({
  title: "Counterspell Magic The Gathering",
  variant: "Foil",
  current_price: 1.25
})], customConfig);
assert.strictEqual(mtgFoil.recommended_price, 2.24);
assert(mtgFoil.reason_codes.includes("MTG_FOIL_FLOOR_APPLIED"));

const [aboveFloor] = api.applyRepricingFloorRules([pricedRow({
  title: "Pokemon bulk card",
  current_price: 3
})]);
assert.strictEqual(aboveFloor.recommended_price, null);
assert(aboveFloor.reason_codes.includes("ABOVE_FLOOR_NO_CHANGE"));

const summary = api.summarizeRepricingFloorRules([defaultFloor, pokemonHolo, pokemonUltraRare, mtgFoil, aboveFloor]);
assert.strictEqual(summary.evaluated, 5);
assert.strictEqual(summary.raised, 4);
assert.strictEqual(summary.defaultFloor, 1);
assert.strictEqual(summary.pokemonHolo, 1);
assert.strictEqual(summary.pokemonUltraRare, 1);
assert.strictEqual(summary.mtgFoil, 1);

const crossListed = pricedRow({
  title: "Counterspell Magic The Gathering Foil",
  current_price: 1.5,
  raw_row: { platform: "eBay + Mana Pool", raw_text: "Counterspell eBay Mana Pool" }
});
const ebayOnly = pricedRow({
  title: "Pikachu Pokemon",
  current_price: 1.25,
  raw_row: { platform: "eBay", raw_text: "Pikachu eBay" }
});
const manaOnly = pricedRow({
  title: "Forest Magic",
  current_price: 1.25,
  raw_row: { platform: "Mana Pool", raw_text: "Forest Mana Pool" }
});

assert.strictEqual(api.detectRepricingGame(crossListed), "mtg");
assert.strictEqual(api.detectRepricingPlatform(crossListed), "crosslisted");
assert.strictEqual(api.detectRepricingPlatform(ebayOnly), "ebay");
assert.strictEqual(api.detectRepricingPlatform(manaOnly), "manapool");
assert.deepStrictEqual(api.filterRepricingRows([crossListed, ebayOnly, manaOnly], { platform: "crosslisted" }), [crossListed]);
assert.deepStrictEqual(api.filterRepricingRows([crossListed, ebayOnly, manaOnly], { game: "pokemon" }), [ebayOnly]);
assert.deepStrictEqual(api.filterRepricingRows([crossListed, ebayOnly, manaOnly], { priceBucket: "under_2" }).length, 3);
assert.deepStrictEqual(api.filterRepricingRows([crossListed, ebayOnly, manaOnly], { search: "counterspell" }), [crossListed]);

const csv = api.repricingReviewCsv([crossListed]);
assert(csv.includes("inventory_id,catalog_sku,user_sku,title,game,platform"));
assert(csv.includes("mtg,crosslisted"));

console.log("Operator repricing floor-rule logic passed.");
