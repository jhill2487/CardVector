const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");

const source=fs.readFileSync(path.join(__dirname,"../wanted/search-savefix-20261110.js"),"utf8");
const page=fs.readFileSync(path.join(__dirname,"../wanted/index.html"),"utf8");

test("public search JavaScript parses",()=>{
 assert.doesNotThrow(()=>new vm.Script(source));
});
test("public search uses approved provider printing IDs before historical fallback",()=>{
 assert.match(source,/cv_public_approved_card_sets/);
 assert.match(source,/cv_public_approved_card_search/);
 assert.match(source,/approvedCards\(query,field,chosenSet\)/);
 assert.match(source,/p_set_id:chosenSet\?chosenSet\.slice/);
 assert.match(source,/if\(chosenSet\.startsWith\(PW_SET_PREFIX\)\)/);
 assert.match(source,/removeDuplicateUnverifiedCards\(verified,validExternal\)/);
 assert.match(source,/approvedImageUrl\(row\.image_path\)/);
 assert.match(source,/isApprovedCard\(card\)/);
});
test("verified PokéWallet cards remain selectable and can become wanted requests",()=>{
 assert.match(source,/source:"pokewallet",card_id:card\._cvProviderId/);
 assert.match(source,/source: selectedCard\.source\|\|"tcgdex"/);
 assert.match(source,/approvedFinishKeys\(card\)/);
 assert.match(source,/populateFinishOptions\(finishKeys\)/);
 assert.match(source,/cv_wanted_requests/);
});
test("unverified artwork is excluded from the public card source",()=>{
 assert.doesNotMatch(source,/from\("cv_admin_image_reviews"\)/);
 assert.doesNotMatch(source,/from\("cv_admin_pokewallet_catalog"\)/);
 assert.doesNotMatch(source,/POKEWALLET_API_KEY/);
 assert.match(page,/verified-cardvector-20261119/);
 assert.match(page,/search-savefix-20261110\.js\?v=20261119approved1/);
});
