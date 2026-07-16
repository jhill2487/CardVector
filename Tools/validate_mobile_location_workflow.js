"use strict";

const assert = require("node:assert/strict");
const mobile = require("../Docs/app.js");

assert.equal(mobile.normalizeEtbId("etb-002"), "ETB-002");
assert.equal(mobile.normalizeLocationCode("g"), "G");
assert.equal(mobile.canonicalLocationId("ETB-002", "G"), "ETB-002-G");

assert.equal(mobile.nextAvailableLocationCode([]), "A");
assert.equal(mobile.nextAvailableLocationCode([{ location_code: "A" }]), "B");
assert.equal(mobile.nextAvailableLocationCode([{ location_code: "A" }, { location_code: "C" }]), "B");
assert.equal(mobile.nextAvailableLocationCode(Array.from("ABCDEFGHIJ")), "");

assert.throws(() => mobile.normalizeEtbId("ETB-2"));
assert.throws(() => mobile.normalizeLocationCode("K"));

console.log("Mobile location workflow validation passed.");
