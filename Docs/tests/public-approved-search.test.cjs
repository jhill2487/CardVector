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
 assert.match(source,/cv_public_catalog_sets/);
 assert.match(source,/cv_public_catalog_search/);
 assert.match(source,/approvedCards\(query,field,chosenSet\)/);
 assert.match(source,/p_set_id:providerSetId/);
 assert.match(source,/if\(chosenSet\.startsWith\(PW_SET_PREFIX\)\)/);
 assert.match(source,/removeDuplicateUnverifiedCards\(verified,validExternal\)/);
 assert.match(source,/approvedImageUrl\(row\.image_path\)/);
 assert.match(source,/_cvArtworkApproved:!!image/);
 assert.match(source,/attachExactFallbackArtwork\(deduplicateIdenticalPrintings\(approved\),historical\)/);
 assert.match(source,/attachExactFallbackArtwork\(deduplicateIdenticalPrintings\(approved\|\|\[\]\),validExternal\)/);
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
 assert.doesNotMatch(page,/id="wanted-build"|Search build:/);
 assert.match(page,/search-savefix-20261110\.js\?v=20261123batch1/);
});

test("compact search presents pricing without presenting import diagnostics",()=>{
 assert.match(source,/marketLine\(card\)/);
 assert.match(source,/marketPrices:Array\.isArray\(row\.tcgplayer_prices\)/);
 assert.match(source,/appendTcgplayerMarket\(details,card\)/);
 assert.match(source,/View exact product on TCGplayer/);
 assert.match(source,/Price updated /);
 assert.match(source,/noopener noreferrer/);
 assert.match(source,/validatedTcgplayerUrl/);
 assert.doesNotMatch(page,/More card games are coming later/);
});

test("all imported card identities remain searchable without approved artwork",()=>{
 assert.match(source,/cv_public_catalog_search/);
 assert.match(source,/if\(card\._cvArtworkApproved&&card\.image\)/);
 assert.match(source,/return noArtwork\(\)/);
 assert.match(source,/externalArtForSet\(setId,searchController\.signal\)/);
 assert.match(source,/await Promise\.all\(\[catalogSetsReady,setNamesReady\]\)/);
});
test("artwork fallback refuses duplicate-number and special stamp mismatches",()=>{
 const start=source.indexOf("  function comparableSetName(");
 const end=source.indexOf("  async function search(query)",start);
 assert.ok(start>=0&&end>start);
 const setNames=new Map([["svp","Scarlet & Violet Black Star Promos"]]);
 const approvedSetNames=new Map([["pw:22872","SV: Scarlet & Violet Promo Cards"]]);
 const ctx={PW_SET_PREFIX:"pw:",setNames,approvedSetNames,
  setNamesReady:Promise.resolve(),
  setIdFor:c=>c.set?.id||String(c.id).split("-")[0],
  isPhysicalCard:()=>true,fetch:async()=>({ok:true,json:async()=>({cards:[]})})};
 vm.runInNewContext(source.slice(start,end)+
  "\nthis.testFallback=attachExactFallbackArtwork;this.testDedupe=removeDuplicateUnverifiedCards;this.isSpecial=isSpecialPrinting;",ctx);
 const pk=(id,name,num)=>({
   id:"pw:"+id,_cvProviderId:id,_cvApproved:true,_cvArtworkApproved:false,
   name,localId:num,set:{id:"pw:22872",name:"SV: Scarlet & Violet Promo Cards"},image:null
 });
 const external={id:"svp-27",name:"Pikachu",localId:"27",set:{id:"svp",name:"Scarlet & Violet Black Star Promos"},image:"https://example.test/pikachu"};
 const regular=pk("pk_regular","Pikachu","027");
 ctx.testFallback([regular],[external]);
 assert.equal(regular._cvArtworkCard,external);
 assert.equal(ctx.testDedupe([regular],[external]).length,0);
 // Two matching providers show only one card tile; genuinely distinct printings remain.
 const unrelated={...external,id:"svp-28",localId:"028"};
 assert.equal(ctx.testDedupe([regular],[external,unrelated]).length,1);
 const special={...external,id:"svp-27-staff",name:"Pikachu Staff"};
 assert.equal(ctx.testDedupe([regular],[special]).length,1);

 const duplicate=pk("pk_duplicate","Pikachu 027 Prerelease Staff","027");
 ctx.testFallback([regular,duplicate],[external]);
 assert.equal(duplicate._cvArtworkCard,undefined);
 const other=pk("pk_special","Pikachu Pokémon Center","028");
 const similar={...external,id:"svp-28",localId:"028",name:"Pikachu Pokémon Center"};
 ctx.testFallback([other],[similar]);
 assert.equal(other._cvArtworkCard,undefined);
 const wrong={...external,id:"sv1-27",set:{id:"sv1",name:"Scarlet & Violet Base Set"}};
 const plain=pk("pk_plain","Pikachu","027");
 ctx.testFallback([plain],[wrong]);
 assert.equal(plain._cvArtworkCard,undefined);
});

test("market reference stays inline and never claims verified NM pricing",()=>{
 assert.match(page,/id="inline-market-guide"/);
 assert.match(source,/function showInlinePricing\(card\)/);
 assert.match(source,/function tcgdexPriceRows\(details\)/);
 assert.match(source,/Not a verified NM-only price/);
 assert.match(source,/Use "\+marketUSD\.format\(price\)/);
 assert.match(source,/appendTcgplayerSearchLink\(text/);
});

test("duplicate PokéWallet product IDs do not duplicate the same exact printing",()=>{
 const start=source.indexOf("  function deduplicateIdenticalPrintings(");
 const end=source.indexOf("  const catalogSetsReady=",start);
 assert.ok(start>=0&&end>start);
 const ctx={};
 vm.runInNewContext(source.slice(start,end)+";this.dedupe=deduplicateIdenticalPrintings;",ctx);
 const card=(id,name,variants=["Holofoil"])=>({
   id:"pw:"+id,_cvProviderId:id,_cvArtworkApproved:false,
   name,localId:"063/086",set:{id:"pw:24325"},variants,
 });
 const items=[
   card("pk_a","Klinklang Master Ball Pattern"),
   card("pk_b","Klinklang Master Ball Pattern"),
   card("pk_c","Klinklang Poke Ball Pattern"),
   card("pk_d","Klinklang"),
   card("pk_e","Klinklang",["Reverse Holofoil"])
 ];
 const merged=ctx.dedupe(items);
 assert.equal(merged.length,4);
 assert.equal(merged.filter(c=>c.name==="Klinklang Master Ball Pattern").length,1);
 assert.equal(merged.filter(c=>c.name==="Klinklang Poke Ball Pattern").length,1);
 assert.equal(merged.filter(c=>c.name==="Klinklang").length,2);
});

test("set-filtered bulk wanted requests preserve every card's exact identity and finish",()=>{
 assert.match(page,/id="batch-panel"/);
 assert.match(page,/id="batch-items"/);
 assert.match(page,/id="batch-submit"/);
 assert.match(page,/id="batch-hint"/);
 assert.match(source,/function batchIsActive\(\)\{return Boolean\(setFilter\.value\);\}/);
 assert.match(source,/function batchSelectCard\(card,checked\)/);
 assert.match(source,/function submitBatch\(\)/);
 assert.match(source,/finishKeys\.includes\(finish\)/);
 assert.match(source,/source:isApprovedCard\(card\)\?"pokewallet":"tcgdex"/);
 assert.match(source,/card_id:isApprovedCard\(card\)\?card\._cvProviderId:card\.id/);
 assert.match(source,/accepted_finishes:\[finish\]/);
 assert.match(source,/insert\(requests\.map\(request=>\(\{\.\.\.request,user_id:user\.id\}\)\)\)/);
 assert.match(source,/batchCards\.clear\(\)/);
 assert.match(source,/batchCards\.size>=99/);
});
