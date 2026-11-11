const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const html=fs.readFileSync(path.join(__dirname,"../status/index.html"),"utf8");
test("dashboard inline JavaScript parses",()=>{
 const blocks=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(Boolean);
 assert.equal(blocks.length,1);
 assert.doesNotThrow(()=>new vm.Script(blocks[0]));
});
test("admin check gates development dashboard",()=>{
 assert.match(html,/getUser\(\)/);
 assert.match(html,/adminEmail="jhill2487@gmail.com"/);
 assert.match(html,/email_confirmed_at/);
 assert.doesNotMatch(html,/owners\.has/);
 assert.match(html,/id="private"/);
 assert.match(html,/#private\{display:none\}/);
});
test("deployment status refresh and separate source and Pages status remain",()=>{
 for(const key of ["source-badge","pages-badge","source-sha","pages-sha","refresh","checked"]){
   assert.ok(html.includes('id="'+key+'"'),key);
 }
 assert.match(html,/CardVector-site\/actions\/runs/);
 assert.match(html,/CardVector\/actions\/runs/);
});
test("importer progress stays unknown without verified checkpoint",()=>{
 assert.match(html,/No executed batch or verified importer checkpoint/);
 assert.match(html,/id="import-sets">—/);
 assert.match(html,/id="import-matched">—/);
 assert.doesNotMatch(html,/id="import-sets">0/);
});

test("admin login runs on status page without redirecting to collector dashboard",()=>{
 assert.match(html,/id="admin-login"/);
 assert.match(html,/id="admin-email"/);
 assert.match(html,/id="admin-password"/);
 assert.match(html,/client\.auth\.signInWithPassword/);
 assert.match(html,/await verifyAdministrator\(\)/);
 assert.doesNotMatch(html,/href="\/account\/\?next=status"/);
 const account=fs.readFileSync(path.join(__dirname,"../account/app.js"),"utf8");
 assert.match(account,/destinations\[next\] \|\| "\/dashboard\/"/);
});

test("Supabase SDK loads synchronously before inline administrator bootstrap",()=>{
 const sdk=html.indexOf('<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>');
 const admin=html.indexOf('const adminEmail=');
 assert.ok(sdk>=0,"missing synchronous SDK script");
 assert.ok(admin>sdk,"admin code must follow loaded SDK");
 assert.doesNotMatch(html,/<script src="https:\/\/cdn.jsdelivr.net\/npm\/@supabase\/supabase-js@2" defer>/);
});
