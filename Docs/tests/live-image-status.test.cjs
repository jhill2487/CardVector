const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const page=fs.readFileSync(path.join(__dirname,"../status/index.html"),"utf8");
const importer=fs.readFileSync(path.join(__dirname,"../../Tools/run_daily_pokewallet_import.py"),"utf8");
test("live image counts are fetched on each admin dashboard refresh",()=>{
 assert.match(page,/cv_admin_image_status_summary/);
 assert.match(page,/getImportProgress\(\),getLiveImageCounts\(\),getSetCoverage\(\)/);
 assert.match(page,/matched_cards,review_cards,missing_cards,pending_cards/);
 assert.match(page,/import-matched/);
 assert.match(page,/import-review/);
});
test("importer no longer republishes stale image counts",()=>{
 const start=importer.indexOf("    def publish(self,state):");
 const end=importer.indexOf("\ndef make_state()",start);
 const method=importer.slice(start,end);
 assert.doesNotMatch(method,/images_matched|images_review|images_missing|image_counts/);
 assert.match(method,/cards_imported/);
});
