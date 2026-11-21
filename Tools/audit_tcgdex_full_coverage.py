#!/usr/bin/env python3
"""Read-only complete TCGdex English image coverage audit, independent of CardVector."""
import urllib.request,urllib.error,json,collections,datetime,time
BASE="https://api.tcgdex.net/v2/en"
def get(path):
    last=None
    for attempt in range(5):
        try:
            req=urllib.request.Request(BASE+path,headers={"User-Agent":"CardVector-TCGdex-Audit/1.0","Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=45) as response:
                return json.load(response)
        except (urllib.error.URLError,TimeoutError) as e:
            last=e
            print("Retry "+path+" attempt="+str(attempt+1)+" reason="+str(e)[:90],flush=True)
            time.sleep(min(12,2**attempt))
    raise RuntimeError("TCGdex unavailable for "+path+": "+str(last))
sets=get("/sets")
cards=[]
page=1
size=300
while page<=150:
    part=get("/cards?pagination:page="+str(page)+"&pagination:itemsPerPage="+str(size))
    if not isinstance(part,list):raise RuntimeError("Expected list from card page")
    if not part:break
    cards.extend(part)
    if len(part)<size:break
    page+=1
else:
    raise RuntimeError("Pagination guard reached; dataset potentially incomplete")
print("Fetched pages="+str(page)+" cards="+str(len(cards)),flush=True)
pocket=set()
try:
    series=get("/series/tcgp")
    pocket={str(s.get("id")) for s in series.get("sets",[])}
except Exception as e:
    print("WARNING: Pocket set discovery unavailable: "+str(e),flush=True)
assert isinstance(cards,list) and len(cards)>1000,(type(cards),len(cards))
assert isinstance(sets,list) and len(sets)>100,(type(sets),len(sets))
set_ids=sorted([s["id"] for s in sets if isinstance(s,dict) and isinstance(s.get("id"),str)],key=len,reverse=True)
set_names={s["id"]:s.get("name",s["id"]) for s in sets}
groups=collections.defaultdict(list)
unknown=[]
for c in cards:
    cardid=str(c.get("id",""))
    sid=next((sid for sid in set_ids if cardid.startswith(sid+"-")),None)
    if sid is None:unknown.append(cardid);sid="<unknown>"
    groups[sid].append(c)
rows=[]
for sid,cs in groups.items():
    with_image=sum(bool(c.get("image")) for c in cs)
    rows.append({"set_id":sid,"set_name":set_names.get(sid,sid),"cards":len(cs),"with_image":with_image,"missing_image":len(cs)-with_image,"is_pocket":sid in pocket})
physical=[c for sid,cs in groups.items() if sid not in pocket for c in cs]
image_count=sum(bool(c.get("image")) for c in physical)
missing=sum(not bool(c.get("image")) for c in physical)
report={
    "audit_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source":"https://api.tcgdex.net/v2/en/cards",
    "set_source":"https://api.tcgdex.net/v2/en/sets",
    "scope":"English Pokémon TCG, excluding TCG Pocket in physical totals",
    "all_english_cards_including_pocket":len(cards),
    "all_english_with_image":sum(bool(c.get("image")) for c in cards),
    "all_english_missing_image":sum(not bool(c.get("image")) for c in cards),
    "english_sets_including_pocket":len(sets),
    "physical_sets_represented":len([r for r in rows if not r["is_pocket"]]),
    "physical_cards":len(physical),
    "physical_cards_with_image":image_count,
    "physical_cards_missing_image":missing,
    "physical_image_coverage_percent":round(100*image_count/len(physical),2),
    "pocket_sets_identified":len(pocket),
    "unmatched_set_id_count":len(unknown),
    "first_unmatched_ids":unknown[:15],
    "sets_entirely_without_images":sorted([r for r in rows if not r["is_pocket"] and r["with_image"]==0],key=lambda x:-x["cards"]),
    "sets_with_biggest_gaps":sorted([r for r in rows if not r["is_pocket"] and r["missing_image"]>0],key=lambda x:-x["missing_image"])[:35]
}
print("TCGDEX_AUDIT_JSON_START",flush=True)
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
print("TCGDEX_AUDIT_JSON_END",flush=True)
