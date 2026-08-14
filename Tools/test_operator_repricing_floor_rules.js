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
  defaultRepricingBusinessProfile,
  normalizeRepricingFloorRuleConfig,
  readStoredRepricingFloorRuleConfig,
  writeStoredRepricingFloorRuleConfig,
  normalizeRepricingBusinessProfile,
  readStoredRepricingBusinessProfile,
  writeStoredRepricingBusinessProfile,
  calculateMinimumViablePrice,
  buildRepricingBusinessAnalysis,
  matchedRepricingFloorRule,
  applyRepricingFloorRules,
  summarizeRepricingFloorRules,
  detectRepricingGame,
  repricingGameDisplayLabel,
  repricingGameConfidence,
  detectRepricingPlatform,
  filterRepricingRows
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
assert.strictEqual(api.defaultRepricingFloorRuleConfig.defaultFloor, 1.58);
assert.strictEqual(defaultFloor.recommended_price, 1.82);
assert(defaultFloor.reason_codes.includes("BELOW_DEFAULT_FLOOR"));
assert(defaultFloor.reason_codes.includes("MINIMUM_VIABLE_PRICE_APPLIED"));
assert(defaultFloor.reason_codes.includes("FREE_SHIPPING_ASSUMED"));
assert.strictEqual(defaultFloor.business_analysis.shipping_cost, 0.78);

const customConfig = api.writeStoredRepricingFloorRuleConfig({
  defaultFloor: "1.67",
  pokemonHoloFloor: "2.11",
  pokemonUltraRareFloor: "3.49",
  mtgFoilFloor: "2.24"
});
assert.deepStrictEqual(api.readStoredRepricingFloorRuleConfig(), customConfig);

const [customDefaultFloor] = api.applyRepricingFloorRules([pricedRow()], customConfig);
assert.strictEqual(customDefaultFloor.recommended_price, 1.82);

const customBusiness = api.writeStoredRepricingBusinessProfile({
  ...api.defaultRepricingBusinessProfile,
  acquisitionCost: "0.10",
  ebayStandardEnvelopeOneOz: "0.78",
  minimumProfit: "0.50",
  roundingMode: "ending_0_99"
});
assert.deepStrictEqual(api.readStoredRepricingBusinessProfile(), customBusiness);
assert.strictEqual(api.calculateMinimumViablePrice(customBusiness), 2.99);

const [pokemonHolo] = api.applyRepricingFloorRules([pricedRow({
  title: "Pikachu Reverse Holo Pokemon",
  variant: "Reverse Holo",
  current_price: 1.5
})], customConfig, customBusiness);
assert.strictEqual(pokemonHolo.recommended_price, 2.99);
assert(pokemonHolo.reason_codes.includes("POKEMON_HOLO_FLOOR_APPLIED"));

const [pokemonUltraRare] = api.applyRepricingFloorRules([pricedRow({
  title: "Charizard VMAX Secret Rare Pokemon",
  current_price: 1.99
})], customConfig, customBusiness);
assert.strictEqual(pokemonUltraRare.recommended_price, 3.99);
assert(pokemonUltraRare.reason_codes.includes("POKEMON_ULTRA_RARE_FLOOR_APPLIED"));

const [mtgFoil] = api.applyRepricingFloorRules([pricedRow({
  title: "Counterspell Magic The Gathering",
  variant: "Foil",
  current_price: 1.25
})], customConfig, customBusiness);
assert.strictEqual(mtgFoil.recommended_price, 2.99);
assert(mtgFoil.reason_codes.includes("MTG_FOIL_FLOOR_APPLIED"));

const [aboveFloor] = api.applyRepricingFloorRules([pricedRow({
  title: "Pokemon bulk card",
  current_price: 3
})]);
assert.strictEqual(aboveFloor.recommended_price, 3);
assert(aboveFloor.reason_codes.includes("ABOVE_FLOOR_NO_CHANGE"));
assert.strictEqual(aboveFloor.business_analysis.estimated_net_profit, 1.27);

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
  title: "Forest Basic Land",
  current_price: 1.25,
  raw_row: { platform: "Mana Pool", raw_text: "Forest Mana Pool" }
});
const shortenedPokemon = pricedRow({
  title: "Eevee Gem Pack Volume 2 0110/15 NM Normal",
  current_price: 1.58,
  card_game: "Pokemon English",
  raw_row: { platform: "eBay", tcg: "Pokemon English", raw_text: "Eevee Gem Pack Volume 2 NM eBay" }
});
const shortenedMagic = pricedRow({
  title: "Counter Gain 25c",
  current_price: 1.58,
  card_game: "Magic",
  raw_row: { platform: "eBay", tcg: "Magic", raw_text: "Counter Gain 25c eBay" }
});

assert.strictEqual(api.detectRepricingGame(crossListed), "mtg");
assert.strictEqual(api.detectRepricingGame(manaOnly), "unknown");
assert.strictEqual(api.detectRepricingGame(shortenedPokemon), "pokemon");
assert.strictEqual(api.detectRepricingGame(shortenedMagic), "mtg");
assert.strictEqual(api.repricingGameDisplayLabel(shortenedPokemon), "Pokemon");
assert.strictEqual(api.repricingGameConfidence(shortenedPokemon), "explicit");
assert.strictEqual(api.repricingGameConfidence(manaOnly), "unknown");
assert.strictEqual(api.detectRepricingPlatform(crossListed), "crosslisted");
assert.strictEqual(api.detectRepricingPlatform(ebayOnly), "ebay");
assert.strictEqual(api.detectRepricingPlatform(manaOnly), "manapool");
assert.deepStrictEqual(api.filterRepricingRows([crossListed, ebayOnly, manaOnly], { platform: "crosslisted" }), [crossListed]);
assert.deepStrictEqual(api.filterRepricingRows([crossListed, ebayOnly, manaOnly, shortenedPokemon], { game: "pokemon" }), [ebayOnly, shortenedPokemon]);
assert.deepStrictEqual(api.filterRepricingRows([crossListed, ebayOnly, manaOnly], { priceBucket: "under_2" }).length, 3);
assert.deepStrictEqual(api.filterRepricingRows([crossListed, ebayOnly, manaOnly], { search: "counterspell" }), [crossListed]);

console.log("Operator repricing floor-rule logic passed.");
