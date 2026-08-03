const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const appSource = fs.readFileSync(path.join(root, "Docs", "app.js"), "utf8");
const start = appSource.indexOf("  function batchLocationLabel");
const end = appSource.indexOf("  function renderBatchReferenceRows", start);

assert(start >= 0, "batchLocationLabel helper not found");
assert(end > start, "renderBatchReferenceRows helper boundary not found");

const helperSource = appSource.slice(start, end);
const helpers = vm.runInNewContext(`(() => {
${helperSource}
return {
  batchHasSlotLocation,
  batchReviewReason,
  groupBatchReferencesByLocation,
  sortedBatchReferences
};
})()`);

const batches = [
  {
    canonical_location_display_code: "ETB-001-A",
    carduploader_batch_id: "later",
    card_count: 12,
    batch_date: "2026-08-03T10:00:00Z"
  },
  {
    canonical_location_display_code: "ETB-001-A",
    carduploader_batch_id: "first",
    card_count: 40,
    batch_date: "2026-08-01T10:00:00Z"
  },
  {
    canonical_location_display_code: "ETB-001-B",
    carduploader_batch_id: "other-slot",
    card_count: 5,
    batch_date: "2026-08-02T10:00:00Z"
  },
  {
    canonical_location_display_code: "ETB-002",
    carduploader_batch_id: "broad-etb",
    card_count: 20
  },
  {
    carduploader_batch_id: "unassigned",
    card_count: 3
  }
];

const groups = helpers.groupBatchReferencesByLocation(batches);
assert.strictEqual(groups.length, 2);

const firstSlot = groups.find((group) => group.location === "ETB-001-A");
assert(firstSlot, "ETB-001-A group should exist");
assert.strictEqual(firstSlot.totalCards, 52);
assert.deepStrictEqual(
  JSON.parse(JSON.stringify(firstSlot.batches.map((batch) => batch.sequence_label))),
  ["ETB-001-A.1", "ETB-001-A.2"]
);
assert.deepStrictEqual(
  JSON.parse(JSON.stringify(firstSlot.batches.map((batch) => batch.carduploader_batch_id))),
  ["first", "later"]
);

const secondSlot = groups.find((group) => group.location === "ETB-001-B");
assert(secondSlot, "ETB-001-B group should exist");
assert.strictEqual(secondSlot.batches[0].sequence_label, "ETB-001-B.1");

assert.strictEqual(helpers.batchHasSlotLocation(batches[3]), false);
assert.strictEqual(helpers.batchReviewReason(batches[3]), "Linked to an ETB, but not a specific A-J slot.");
assert.strictEqual(helpers.batchReviewReason(batches[4]), "No ETB slot is linked yet.");

console.log("operator batch workflow logic tests passed");
