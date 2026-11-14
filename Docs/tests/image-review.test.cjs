const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const page=fs.readFileSync(path.join(__dirname,"../image-review/index.html"),"utf8");
const dashboard=fs.readFileSync(path.join(__dirname,"../status/index.html"),"utf8");
const exporter=fs.readFileSync(path.join(__dirname,"../../Tools/export_cardvector_site.py"),"utf8");
test("image review page JavaScript parses and SDK loads first",()=>{
 const scripts=[...page.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(x=>x[1]).filter(Boolean);
 assert.equal(scripts.length,1);
 assert.doesNotThrow(()=>new vm.Script(scripts[0]));
 assert.ok(page.indexOf("supabase-js@2")<page.indexOf("const approvedEmail="));
});
test("image review requires approved account and uses RLS-backed tables",()=>{
 assert.match(page,/db\.auth\.getUser\(\)/);
 assert.match(page,/email_confirmed_at/);
 assert.match(page,/approvedEmail="jhill2487@gmail.com"/);
 for(const name of ["cv_admin_set_coverage","cv_admin_pokewallet_catalog","cv_admin_image_reviews"])assert.ok(page.includes(name));
 assert.match(page,/#private\{display:none\}/);
});
test("only saves private reviews and does not publish to search",()=>{
 for(const word of ["approved","rejected","keep_missing","pending_review"])assert.match(page,new RegExp(word));
 assert.match(page,/public search remains unchanged|No public search change|Public search unchanged/i);
 assert.doesNotMatch(page,/service_role|SUPABASE_SERVICE_ROLE_KEY/);
 assert.doesNotMatch(page,/localStorage\.setItem/);
 assert.match(page,/onConflict:"provider_id"/);
});
test("image URL is restricted to verified R2 archive paths, and CardUploader is reference-only",()=>{
 assert.match(page,/https:\/\/images\.cardvector\.app\/archive\//);
 assert.match(page,/candidateUrl\(path\)/);
 assert.match(page,/carduploader\.com\/dashboard\/card-search\?set_name=Delta\+Reign/);
 assert.match(page,/do not copy images without permission/);
});
test("dashboard links to exported admin image review route",()=>{
 assert.match(dashboard,/href="\/image-review\/"/);
 assert.match(exporter,/"image-review\/index\.html"/);
 assert.match(exporter,/"image-review"/);
});

test("approved images are confirmed against the private catalog before showing success",()=>{
 assert.match(page,/select\("image_status,image_path"\)/);
 assert.match(page,/verified\?\.image_status!=="matched"/);
 assert.match(page,/verified\?\.image_path!==path/);
 assert.match(page,/catalog image did not update/);
});
test("review approvals synchronize to private catalog with exclusive R2 path ownership",()=>{
 const sql=fs.readFileSync(path.join(__dirname,"../../supabase/migrations/20261114011500_sync_approved_catalog_image.sql"),"utf8");
 assert.match(sql,/create unique index if not exists cv_admin_image_reviews_unique_approved_path/i);
 assert.match(sql,/security definer/i);
 assert.match(sql,/set search_path = ''/i);
 assert.match(sql,/set image_status = 'matched'/i);
 assert.match(sql,/image_path = new.candidate_path/i);
 assert.match(sql,/after insert or update of review_status, candidate_path/i);
 assert.doesNotMatch(sql,/update public\.cv_wants|update public\.wanted_cards/i);
});

test("approved artwork renders in original image area without a second preview",()=>{
 assert.match(page,/const savedImage=review\?\.review_status==="approved"\?review\.candidate_path:card\.image_path/);
 assert.match(page,/showCardImage\(visual,path,card\.card_name\+" "\+card\.card_number\)/);
 assert.match(page,/if\(value!=="approved"\)await refresh\(\)/);
});
test("mobile admin can enlarge candidate and approved artwork",()=>{
 assert.match(page,/<dialog id="image-zoom"/);
 assert.match(page,/openImageZoom\(match\.r\.url/);
 assert.match(page,/visual\.onclick=\(\)=>openImageZoom/);
 assert.match(page,/modal\.classList\.toggle\("zoomed"\)/);
 assert.match(page,/\.zoom-area\{max-height:76dvh;overflow:auto/);
});
