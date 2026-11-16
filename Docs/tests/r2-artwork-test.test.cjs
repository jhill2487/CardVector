const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const source=fs.readFileSync(__dirname+"/../r2-artwork-test.js","utf8");
const window={};vm.runInNewContext(source,{window});
const api=window.CardVectorR2ArtworkTest;
const row=(number,path,name="")=>({number,filename:path.split("/").pop(),path:"archive/"+path,setSlug:path.split("/").slice(-2,-1)[0],name});
const cards=[
 {provider_id:"a",card_name:"Venusaur ex",card_number:"001/142"},
 {provider_id:"b",card_name:"Venusaur ex Poke Ball Pattern",card_number:"001/142"},
 {provider_id:"c",card_name:"Ledyba",card_number:"002/142"},
 {provider_id:"d",card_name:"Ledian",card_number:"003/142"}
];
const mapping={folder:"stellar-crown",code:"sv7",denominator:"142"};
test("one standard image resolves multiple variant records without changing identities",()=>{
 const plan=api.plan([row("001","stellar-crown/sv7_en_001_std.jpg"),row("002","stellar-crown/sv7_en_002_std.jpg"),row("003","stellar-crown/sv7_en_003_std.jpg")],cards,"SV07: Stellar Crown",mapping);
 assert.equal(plan.matched.length,4);
 assert.equal(plan.missing.length,0);
 assert.equal(plan.matched[0].row.path,plan.matched[1].row.path);
 assert.notEqual(plan.matched[0].card.provider_id,plan.matched[1].card.provider_id);
});
test("does not match images across set folders",()=>{
 const plan=api.plan([row("001","other-set/sv7_en_001_std.jpg")],cards,"SV07: Stellar Crown",mapping);
 assert.equal(plan.matched.length,0);
});
test("detects conflicting filenames rather than guessing",()=>{
 const plan=api.plan([row("001","stellar-crown/sv7_en_001_std.jpg"),row("001","stellar-crown/sv7_en_001_std.png")],[cards[0]],"Stellar Crown",mapping);
 assert.equal(plan.ambiguous.length,1);
});
test("detects missing artwork",()=>{
 const plan=api.plan([row("001","stellar-crown/sv7_en_001_std.jpg")],cards,"SV07: Stellar Crown",mapping);
 assert.equal(plan.missing.length,2);
});
test("detects folder automatically when unique",()=>{
 const p=api.plan([row("001","stellar-crown/sv7_en_001_std.jpg")],[cards[0]],"SV07: Stellar Crown",null);
 assert.equal(p.choice.folder,"stellar-crown");
});
