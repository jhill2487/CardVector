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
 assert.match(page,/if\(mapping\.pathPrefix&&mapping\.code\)/);
 assert.match(page,/img\.onload=\(\)=>finish\(true\)/);
 assert.match(page,/img\.onerror=\(\)=>finish\(false\)/);
 assert.match(page,/Nothing saved yet/);
 assert.match(page,/await Promise\.all\(Array\.from/);
});

test("same-set same-number printings can reuse artwork without merging finish identity",()=>{
 assert.match(page,/function claimedByDifferentSet\(path,setId,cardNumber\)/);
 assert.match(page,/ownerSet!==String\(setId\)\|\|\(cardNumber!=null&&ownerNumber!==String\(cardNumber\)\)/);
 assert.match(page,/lookupByProviderIds\("cv_admin_pokewallet_catalog","provider_id,set_id,card_number"/);
 assert.match(page,/async function shareApprovedArtwork\(\)/);
 assert.match(page,/const paths=anchors\.get\(card\.card_number\)/);
 assert.match(page,/if\(!paths\|\|paths\.size!==1\)return \[\]/);
 assert.match(page,/if\(decisions\.has\(card\.provider_id\)\|\|requiresDistinctImage\(card\)\)return \[\]/);
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
 assert.match(page,/for\(const card of baseCards\)/);
 assert.match(page,/const baseCards=baseArtworkCards\(cards\)/);
 assert.match(page,/First pass: match base artwork/);
 assert.match(page,/Finish variants are not included/);
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
 assert.match(page,/setTimeout\(\(\)=>finish\(false\),10000\)/);
 assert.match(page,/Math\.min\(12,candidates\.length\)/);
 assert.match(page,/Nothing saved yet/);
 assert.match(page,/button\.textContent=originalLabel/);
});

test("bulk artwork run offers one confirmation and reports exceptions without touching finish variants",()=>{
 assert.match(page,/id="match-exceptions"/);
 assert.match(page,/id="match-exceptions-list"/);
 assert.match(page,/const report=\(items\)=>/);
 assert.match(page,/reviewed\.has\(card\.provider_id\)/);
 assert.match(page,/claimedByDifferentSet\(path,setId,card\.card_number\)/);
 assert.match(page,/imageExists\(item\.url\)/);
 assert.match(page,/Approve "\+ok\.length\+" verified base artwork matches/);
 assert.match(page,/Finish variants remain separate/);
 assert.match(page,/No new base images to match/);
});

test("large imported sets query review decisions in safe chunks",()=>{
 assert.match(page,/async function lookupByProviderIds\(table,columns,ids\)/);
 assert.match(page,/i\+=35/);
 assert.match(page,/ids\.slice\(i,i\+35\)/);
 assert.match(page,/lookupByProviderIds\("cv_admin_image_reviews"/);
 assert.match(page,/lookupByProviderIds\("cv_admin_pokewallet_catalog"/);
 assert.match(page,/id="build-version">Review build 165/);
 assert.doesNotMatch(page,/\.in\("provider_id",cards\.map/);
});

test("Ascended Heroes verified indexed path uses complete set identity",()=>{
 const mapping=fs.readFileSync(path.join(__dirname,"../r2-set-mappings.js"),"utf8");
 assert.match(mapping,/"24541": Object\.freeze/);
 assert.match(mapping,/folder:"ascended-heroes"/);
 assert.match(mapping,/code:"me2-5"/);
 assert.match(mapping,/denominator:"217"/);
 assert.match(mapping,/pathPrefix:"ascended-heroes\/ascended-heroes\/"/);
 assert.match(page,/r2-set-mappings\.js\?v=20261113e-white-flare/);
});
test("Dusk Ball finishes remain distinct during Ascended Heroes base first pass",()=>{
 assert.match(page,/Quick Ball\| Dusk Ball\| Team Rocket/);
 assert.match(page,/function baseArtworkCards\(cards\)/);
 assert.match(page,/const baseCards=baseArtworkCards\(cards\)/);
 assert.match(page,/async function shareApprovedArtwork\(\)/);
});

test("White Flare verified R2 series activates full-set bulk artwork matcher",()=>{
 const mapping=fs.readFileSync(path.join(__dirname,"../r2-set-mappings.js"),"utf8");
 assert.match(mapping,/"24326": Object\.freeze/);
 assert.match(mapping,/set:"SV: White Flare"/);
 assert.match(mapping,/folder:"white-flare"/);
 assert.match(mapping,/code:"rsv10-5"/);
 assert.match(mapping,/denominator:"086"/);
 assert.match(mapping,/pathPrefix:"Pokemon TCG\/Pokemon TCG\/white-flare\/"/);
 assert.match(page,/const mapping=verifiedFolderFor\(setId\)/);
 assert.match(page,/if\(mapping\.pathPrefix&&mapping\.code\)/);
 assert.match(page,/const baseCards=baseArtworkCards\(cards\)/);
});

test("bulk matching learns numbered art from approved base card in ANY set",()=>{
 assert.match(page,/function approvedArtworkSeries\(cards,reviews,folder\)/);
 assert.match(page,/review\.review_status!=="approved"/);
 assert.match(page,/isFinishPrinting\(card\)/);
 assert.match(page,/Number\(match\[2\]\)!==Number\(number\)/);
 assert.match(page,/found\.size===1/);
 assert.match(page,/const learned=approvedArtworkSeries\(cards,reviews,mapping\?\.folder\|\|""\)/);
 assert.match(page,/path=indexedAnchor\.folder\+indexedAnchor\.prefix/);
 assert.match(page,/if\(learned\.ambiguous&&!mapping\?\.pathPrefix\)/);
 assert.match(page,/if\(!mapping\.pathPrefix&&!indexedAnchor&&!mapping\.code\)/);
});
test("approved artwork series is set-safe, resists conflicts and preserves correct folder",()=>{
 const vm=require("node:vm");
 const html=page;
 const block=html.slice(html.indexOf("function approvedArtworkSeries("),html.indexOf("// First-pass artwork approval",html.indexOf("function approvedArtworkSeries(")));
 const ctx={};
 vm.runInNewContext("const isFinishPrinting=card=>/(?: Poke Ball Pattern| Master Ball Pattern)$/i.test(card.card_name||'');"+block+"this.get=approvedArtworkSeries;",ctx);
 const cards=[{provider_id:"p1",card_name:"Ethan's Pinsir",card_number:"001/182"},
 {provider_id:"p2",card_name:"Yanma",card_number:"002/182"},
 {provider_id:"p3",card_name:"Yanma Master Ball Pattern",card_number:"002/182"}];
 const r=[{provider_id:"p1",review_status:"approved",candidate_path:"Pokemon TCG/Pokemon TCG/destined-rivals/sv10_en_001_std.jpg"}];
 const match=ctx.get(cards,r,"destined-rivals");
 assert.equal(match.ambiguous,false);
 assert.equal(match.series.prefix,"sv10_en_");
 assert.equal(match.series.folder,"Pokemon TCG/Pokemon TCG/destined-rivals/");
 assert.equal(match.series.pad,3);
 assert.equal(match.series.folder+match.series.prefix+"002"+match.series.suffix,"Pokemon TCG/Pokemon TCG/destined-rivals/sv10_en_002_std.jpg");
 assert.equal(ctx.get(cards,r,"other-set").series,null);
 const wrong=[{...r[0],candidate_path:"Pokemon TCG/Pokemon TCG/destined-rivals/sv10_en_004_std.jpg"}];
 assert.equal(ctx.get(cards,wrong,"destined-rivals").series,null);
 const variant=[{provider_id:"p3",review_status:"approved",candidate_path:"Pokemon TCG/Pokemon TCG/destined-rivals/sv10_en_002_std.jpg"}];
 assert.equal(ctx.get(cards,variant,"destined-rivals").series,null);
 const mixed=[...r,{provider_id:"p2",review_status:"approved",candidate_path:"Pokemon TCG/Pokemon TCG/destined-rivals/other_en_002_std.jpg"}];
 assert.equal(ctx.get(cards,mixed,"destined-rivals").ambiguous,true);
});

test("image review selector only shows unresolved imported sets",()=>{
 assert.match(page,/function hasUnresolvedImages\(s\)/);
 assert.match(page,/return missing>0\|\|review>0\|\|Math\.max\(0,imported-matched-missing-review\)>0/);
 assert.match(page,/sets=\(data\|\|\[\]\)\.filter\(hasUnresolvedImages\)/);
 assert.match(page,/if\(!sets\.length\).*All imported sets have their images matched/);
 assert.match(page,/async function reloadReviewSets\(\)/);
 assert.match(page,/await reloadReviewSets\(\)/);
 assert.match(page,/reloadReviewSets\(\)\.catch/);
});
test("resolved set filtering includes missing and review states and handles new pending cards",()=>{
 const vm=require("node:vm");
 const code=page.slice(page.indexOf("function hasUnresolvedImages("),page.indexOf("async function getSets()",page.indexOf("function hasUnresolvedImages(")));
 const ctx={};vm.runInNewContext(code+"this.check=hasUnresolvedImages;",ctx);
 const check=ctx.check;
 assert.equal(check({imported_cards:325,matched_cards:325,unmatched_cards:0,review_cards:0}),false);
 assert.equal(check({imported_cards:325,matched_cards:324,unmatched_cards:0,review_cards:0}),true);
 assert.equal(check({imported_cards:325,matched_cards:324,unmatched_cards:1,review_cards:0}),true);
 assert.equal(check({imported_cards:325,matched_cards:324,unmatched_cards:0,review_cards:1}),true);
 assert.equal(check({imported_cards:326,matched_cards:325,unmatched_cards:0,review_cards:0}),true);
 assert.equal(check({imported_cards:0,matched_cards:0,unmatched_cards:0,review_cards:0}),false);
});

test("stamped promos cannot inherit standard artwork through either batch operation",()=>{
 const vm=require("node:vm");
 const from=page.indexOf("function requiresDistinctImage(");
 const to=page.indexOf("// Use one approved image",from);
 assert.ok(from>0&&to>from);
 const context={};
 vm.runInNewContext(page.slice(from,to)+"this.requiresDistinctImage=requiresDistinctImage;",context);
 const distinct=context.requiresDistinctImage;
 for(const name of ["Ceruledge Prerelease Staff","Meganium 001 Staff","Charcadet 022 Pokemon Center Exclusive","Riolu 010 Pokemon Center Exclusive","Miraidon 082 Pitch Black Stamped","Pikachu 093 Winner","Paradise Resort 092 World Championships 2026 Staff"]){
  assert.equal(distinct({card_name:name}),true,name);
 }
 for(const name of ["Ceruledge Prerelease","Charcadet","Cottonee Cosmos Holo","Pikachu Poke Ball Pattern","Team Rocket's Pikachu"]){
  assert.equal(distinct({card_name:name}),false,name);
 }
 assert.match(page,/if\(decisions\.has\(card\.provider_id\)\|\|requiresDistinctImage\(card\)\)return \[\]/);
 assert.match(page,/return requiresDistinctImage\(card\)\|\|/);
 assert.match(page,/function baseArtworkCards\(cards\)/);
 assert.match(page,/const baseCards=baseArtworkCards\(cards\)/);
});

test("R2 artwork candidate discovery automatically excludes standard images for visible stamped variants",()=>{
 const vm=require("node:vm");
 const begin=page.indexOf("function requiredStampToken("),end=page.indexOf("function candidatesFor(card)",begin);
 assert.ok(begin>0&&end>begin);
 const ctx={};vm.runInNewContext(page.slice(begin,end)+"this.classify=requiredStampToken;this.accept=candidateMatchesPrinting;",ctx);
 const accept=ctx.accept, mk=(name,path)=>accept({card_name:name},{path,filename:path.split("/").pop()});
 assert.equal(mk("Meganium 001 Staff","mega-evolution-promos/mebsp_en_001_std.jpg"),false);
 assert.equal(mk("Meganium 001 Staff","mega-evolution-promos/mebsp_en_001_staff.jpg"),true);
 assert.equal(mk("Riolu 010 Pokemon Center Exclusive","mega-evolution-promos/mebsp_en_010_std.jpg"),false);
 assert.equal(mk("Riolu 010 Pokemon Center Exclusive","mega-evolution-promos/riolu_010_pokemon-center.jpg"),true);
 assert.equal(mk("Pikachu 093 Winner","mega-evolution-promos/mebsp_en_093_std.jpg"),false);
 assert.equal(mk("Pikachu 093 Winner","mega-evolution-promos/pikachu_093_winner.jpg"),true);
 assert.equal(mk("Miraidon 082 Pitch Black Stamped","mega-evolution-promos/mebsp_en_082_std.jpg"),false);
 assert.equal(mk("Miraidon 082 Pitch Black Stamped","mega-evolution-promos/miraidon_082_stamped.jpg"),true);
 assert.equal(mk("Ceruledge Prerelease","mega-evolution-promos/mebsp_en_014_std.jpg"),true);
 assert.match(page,/if\(!candidateMatchesPrinting\(card,row\)\)return null/);
 assert.match(page,/if\(requiresDistinctImage\(card\)\)return indexed/);
 assert.match(page,/Source acquisition required; do not substitute the unstamped artwork/);
});
