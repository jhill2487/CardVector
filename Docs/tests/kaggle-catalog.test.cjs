/* Run with: node --test Docs/tests/kaggle-catalog.test.cjs */
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.resolve(__dirname,"../kaggle-catalog.js"),"utf8");
const csv = [
  '"RelativePath","FileName","Folder","SizeKB"',
  '"Pokemon TCG\\Pokemon TCG\\xy-trainer-kit-pikachu-libre\\en_US-TK9A-014-pikachu_libre.jpg","en_US-TK9A-014-pikachu_libre.jpg","xy-trainer-kit-pikachu-libre","80"',
  '"Pokemon TCG\\Pokemon TCG\\xy-trainer-kit-pikachu-libre\\en_US-TK9A-030-pikachu_libre.jpg","en_US-TK9A-030-pikachu_libre.jpg","xy-trainer-kit-pikachu-libre","81"',
  '"Pokemon TCG\\Pokemon TCG\\151\\sv3-5_en_001_std.jpg","sv3-5_en_001_std.jpg","151","75"',
  '"Pokemon TCG\\Pokemon TCG\\base-set\\en_US-BS-001-alakazam.jpg","en_US-BS-001-alakazam.jpg","base-set","72"'
].join("\r\n");
let calls=0;
const window={};
vm.runInNewContext(source,{window,fetch:async()=>{calls++;return {ok:true,text:async()=>csv};},URL,encodeURIComponent});
const api=window.CardVectorKaggleCatalog;
test("parses quoted CSV and maps real legacy filename patterns",()=>{
  const lines=api.parseCSV(csv);
  assert.equal(lines.length,5);
  const first=api.fromRow(lines[1]);
  assert.equal(first.number,"014");
  assert.equal(first.name,"pikachu libre");
  assert.match(first.url,/archive\/Pokemon%20TCG\/Pokemon%20TCG\/xy-trainer-kit-pikachu-libre/);
  assert.equal(first.finishVerified,false);
});
test("keeps the Pikachu Libre printings distinct and does not assert finish",async()=>{
  const found=await api.search("pikachu libre");
  assert.deepEqual(Array.from(found,card=>card.number),["014","030"]);
  assert.ok(found.every(card=>card.finishVerified===false));
});
test("does not guess a name from a numeric-only modern filename",()=>{
  const modern=api.fromRow(api.parseCSV(csv)[3]);
  assert.equal(modern.name,"");assert.equal(modern.number,"001");
});
test("supports set search and caches the shared R2 index",async()=>{
  assert.equal((await api.search("base set","set")).length,1);
  assert.equal(calls,1);
});
test("rejects path traversal",()=>{
  assert.equal(api.fromRow(["../secret.jpg"]),null);
});
