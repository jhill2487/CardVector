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

test("pending catalog entries can be reviewed and set menu distinguishes pending from missing",()=>{
 assert.match(page,/<option value="pending">Pending images<\/option>/);
 assert.match(page,/\["pending","missing","needs_review","matched"\]\.includes\(filter\)/);
 assert.match(page,/s\.imported_cards-s\.matched_cards-s\.unmatched_cards-s\.review_cards/);
});
test("unmapped sets require a selected indexed R2 folder for first approval",()=>{
 assert.match(page,/id="r2-folder"/);
 assert.match(page,/configureFolder\(setId\)/);
 assert.match(page,/mapping=currentFolderFor\(card\.set_id\)/);
 assert.match(page,/temporaryFolder\?\.setId===String\(setId\)/);
 assert.match(page,/found\.some\(x=>x\.r\.path\.replace/);
});

test("missing index rows can display an explicitly unverified same-set numbered suggestion",()=>{
 assert.match(page,/function seriesCandidatesFor\(card,mapping\)/);
 assert.match(page,/if\(mapping\.temporary\|\|!folderAllowedForSet/);
 assert.match(page,/identity\.startsWith\(String\(card\.set_id\)/);
 assert.match(page,/return indexed\.length\?indexed:seriesCandidatesFor\(card,mapping\)/);
 assert.match(page,/Filename inferred from a prior approval/);
 assert.match(page,/if\(match\.inferred\)thumb\.onerror/);
});

test("verified ME01 R2 series supplies previews when CSV has no records",()=>{
 const mapping=fs.readFileSync(path.join(__dirname,"../r2-set-mappings.js"),"utf8");
 assert.match(mapping,/"24380": Object\.freeze/);
 assert.match(mapping,/pathPrefix:"Pokemon TCG\/Pokemon TCG\/mega-evolution\/"/);
 assert.match(mapping,/code:"me1"/);
 assert.match(page,/function mappedSeriesCandidate\(card,mapping\)/);
 assert.match(page,/if\(mapped\)return \[mapped\]/);
 assert.match(page,/mapping\.pathPrefix\+mapping\.code\+"_en_"/);
});
test("unindexed bulk matching verifies existence before accepting files",()=>{
 assert.match(page,/if\(!candidates\.length&&mapping\?\.pathPrefix\)/);
 assert.match(page,/img\.onload=\(\)=>finish\(true\)/);
 assert.match(page,/img\.onerror=\(\)=>finish\(false\)/);
 assert.match(page,/Nothing saved yet/);
 assert.match(page,/await Promise\.all\(Array\.from/);
});

test("same-set same-number printings can reuse artwork without merging finish identity",()=>{
 assert.match(page,/function claimedByDifferentSet\(path,setId,cardNumber\)/);
 assert.match(page,/ownerSet!==String\(setId\)\|\|\(cardNumber!=null&&ownerNumber!==String\(cardNumber\)\)/);
 assert.match(page,/select\("provider_id,set_id,card_number"\)/);
 assert.match(page,/async function shareApprovedArtwork\(\)/);
 assert.match(page,/const paths=anchors\.get\(card\.card_number\)/);
 assert.match(page,/if\(!paths\|\|paths\.size!==1\)return \[\]/);
 assert.match(page,/if\(decisions\.has\(card\.provider_id\)\)return \[\]/);
 assert.match(page,/individual printing\/finish retained/);
 assert.match(page,/id="match-shared"/);
});
test("migration rejects sharing across collector number and set",()=>{
 const migrations=fs.readdirSync(path.join(__dirname,"../../supabase/migrations"));
 const migration=migrations.find(name=>name.includes("allow_same_card_shared_artwork"));
 assert.ok(migration);
 const sql=fs.readFileSync(path.join(__dirname,"../../supabase/migrations",migration),"utf8");
 assert.match(sql,/sibling\.set_id is distinct from target_set/);
 assert.match(sql,/sibling\.card_number is distinct from target_number/);
 assert.match(sql,/pg_advisory_xact_lock/);
 assert.match(sql,/drop index if exists public\.cv_admin_image_reviews_unique_approved_path/);
});

test("first pass matches only unique base artwork and defers pattern printings",()=>{
 assert.match(page,/function isFinishPrinting\(card\)/);
 assert.match(page,/Poke Ball Pattern\| Master Ball Pattern\| Energy Symbol Pattern/);
 assert.match(page,/function baseArtworkCards\(cards\)/);
 assert.match(page,/const baseCards=baseArtworkCards\(cards\)/);
 assert.match(page,/for\(const c of baseCards\)/);
 assert.match(page,/const proposed=baseCards\.filter/);
 assert.match(page,/First pass: match base artwork/);
 assert.match(page,/Pattern variants remain unapproved until the second pass/);
});
test("Black Bolt mapping uses exact verified set ID and standard image prefix",()=>{
 const mapping=fs.readFileSync(path.join(__dirname,"../r2-set-mappings.js"),"utf8");
 assert.match(mapping,/"24325": Object\.freeze/);
 assert.match(mapping,/pathPrefix:"Pokemon TCG\/Pokemon TCG\/black-bolt\/"/);
 assert.match(mapping,/code:"zsv10-5"/);
 assert.match(mapping,/denominator:"086"/);
});

test("first-pass matching shows mobile progress and bounds failed R2 checks",()=>{
 assert.match(page,/id="match-progress"/);
 assert.match(page,/role="status" aria-live="polite"/);
 assert.match(page,/button\.textContent="Checking set…"/);
 assert.match(page,/setTimeout\(\(\)=>finish\(false\),7000\)/);
 assert.match(page,/Math\.min\(12,proposed\.length\)/);
 assert.match(page,/No approvals saved yet/);
 assert.match(page,/button\.textContent=originalLabel/);
});
