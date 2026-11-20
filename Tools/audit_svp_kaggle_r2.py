#!/usr/bin/env python3
"""Audit read-only Kaggle R2 index for English Scarlet & Violet (SVP) promos.

Do not infer that any image is correct solely from a similar number; report
set-folder evidence and unique numeric candidates for administrator review.
"""
import collections
import csv
import io
import json
import re
import urllib.request
import urllib.parse

SOURCE="https://images.cardvector.app/archive/card-image-index.csv"

def main():
    req=urllib.request.Request(SOURCE,headers={"User-Agent":"CardVector-R2-SVP-Audit/1.0"})
    with urllib.request.urlopen(req,timeout=40) as res:
        text=res.read().decode("utf-8-sig")
    rows=list(csv.DictReader(io.StringIO(text)))
    paths=[str(row.get("RelativePath") or "").replace("\\","/") for row in rows]
    selected=[p for p in paths if re.search(r"(?:^|/)(?:sv[-_]?p|svp|sv-black-star-promos|scarlet[-_ ]violet[-_ ]promos|scarlet-and-violet-promos)(?:[/-]|$)",p,re.I)]
    folders=collections.Counter("/".join(p.split("/")[:-1]) for p in selected)
    filenames=[p.rsplit("/",1)[-1] for p in selected]
    cards=collections.defaultdict(list)
    for p in selected:
        fname=p.rsplit("/",1)[-1]
        patterns=(
            r"[_-](SVP[_-]?\d{1,3})[_-]",
            r"[_-](SVP[_-]?\d{1,3})(?:\.|$)",
            r"[_-]en[_-](\d{1,3})[_-](?:std|holo|rev)",
            r"[-_](\d{1,3})(?:\.|$)",
        )
        matches=[re.search(pat,fname,re.I) for pat in patterns]
        found=next((m.group(1) for m in matches if m),None)
        if found:
            number=re.sub(r"(?i)^svp[_-]?","",found)
            cards[int(number)].append(p)
    print(json.dumps({
        "index_rows":len(rows),"candidate_paths":len(selected),
        "candidate_folders":folders.most_common(30),
        "unique_number_candidates":len(cards),
        "unique_paths_per_number":sum(len(v)==1 for v in cards.values()),
        "ambiguous_numbers":sum(len(v)>1 for v in cards.values()),
        "sample_candidate_paths":selected[:25],
        "number_samples":dict(list((k,v) for k,v in sorted(cards.items()))[:12]),
    },indent=2))
if __name__=="__main__":
    main()
