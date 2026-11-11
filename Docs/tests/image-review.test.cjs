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
 assert.match(page,/No live search changes/);
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
