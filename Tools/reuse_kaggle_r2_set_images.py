#!/usr/bin/env python3
"""Reuse indexed R2 Kaggle images by exact set/collector number, without API calls.

Stage only unambiguous catalog identities in administrator image review.
Special printings and duplicate collector numbers are intentionally excluded.
Generic matcher: pass an English provider set ID and verified R2 folder slug.
"""
import collections
import csv
import io
import json
import os
import re
import urllib.parse
import urllib.request

import import_pokewallet_set_images as images

INDEX="https://images.cardvector.app/archive/card-image-index.csv"


def norm(s):
    return re.sub(r"[^a-z0-9]+","",str(s or "").lower())


def number(s):
    n=str(s or "").lower().strip().split("/")[0]
    n=re.sub(r"^(?:svp|sv)[-_]?","",n)
    return str(int(n)) if n.isdigit() else n


def image_number_name(fname):
    stem=re.sub(r"\.[^.]+$","",fname)
    # en_US-Promo_SV-SV001-sprigatito and en_US-Promo_SV-004-mimikyu_ex
    legacy=re.match(r"en_US-[^-]+-((?:[a-z]{1,4})?\d{1,3})-(.+)$",stem,re.I)
    if legacy:
        return number(legacy.group(1)),legacy.group(2)
    # svbsp_en_005.jpg; disallow hyphenated revision suffix, e.g. 150-1
    numbered=re.fullmatch(r"[a-z0-9-]+_en_([0-9]{1,3})(?:_(?:std|holo|rev))?",stem,re.I)
    if numbered:
        return number(numbered.group(1)),""
    return None,None


def db_rows(table,select,filter_q):
    base=images.DB+table+"?"+urllib.parse.urlencode({"select":select,**filter_q,"limit":1000})
    data=json.loads(images.request(base,images.db_headers()))
    if not isinstance(data,list) or len(data)>=1000:
        raise RuntimeError("Unexpected or truncated Supabase catalog")
    return data


def candidates(set_id,folder):
    with urllib.request.urlopen(urllib.request.Request(
        INDEX,headers={"User-Agent":"CardVector-R2-Existing-Artwork/1.0"}),timeout=40) as response:
        entries=list(csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"))))
    catalog=db_rows("cv_admin_pokewallet_catalog",
                    "provider_id,set_id,set_name,card_name,card_number,image_status,image_path",
                    {"set_id":"eq."+set_id})
    info=db_rows("cv_admin_set_languages",
                 "set_id,language,expected_card_count",{"set_id":"eq."+set_id})
    if len(info)!=1 or info[0]["language"]!="eng" or len(catalog)!=info[0]["expected_card_count"]:
        raise RuntimeError("Metadata not complete or not English; refusing R2 matches")
    reviewed=set()
    for start in range(0,len(catalog),20):
        ids=[c["provider_id"] for c in catalog[start:start+20]]
        reviews=db_rows("cv_admin_image_reviews","provider_id,review_status,candidate_path",
                        {"provider_id":"in.("+",".join(ids)+")"})
        reviewed.update(r["provider_id"] for r in reviews)
    by_number=collections.defaultdict(list)
    for c in catalog:
        by_number[number(c["card_number"])].append(c)
    indexed=collections.defaultdict(list)
    for row in entries:
        path=str(row.get("RelativePath") or "").replace("\\","/")
        if not path.endswith(tuple([".jpg",".jpeg",".png",".webp"])) or ".." in path:
            continue
        if path.split("/")[-2]!=folder:
            continue
        num,embedded_name=image_number_name(path.rsplit("/",1)[-1])
        if num:
            indexed[num].append((path,embedded_name))
    matched=[]
    ambiguous=collections.Counter()
    for num,cs in by_number.items():
        paths=indexed.get(num,[])
        if len(cs)!=1:
            ambiguous["duplicate_catalog_printings"]+=len(cs)
            continue
        c=cs[0]
        if c["provider_id"] in reviewed or c["image_status"]=="matched" or c.get("image_path"):
            ambiguous["already_staged_or_matched"]+=1
            continue
        if len(paths)!=1:
            ambiguous["multiple_or_missing_images"]+=1
            continue
        path,filename_name=paths[0]
        # Explicit staff/alternate printings cannot safely share a base image.
        if re.search(r"\b(staff|prerelease|pokemon.center|stamped|cosmos|alternate|winner)\b",c["card_name"],re.I):
            ambiguous["special_printing"]+=1
            continue
        if filename_name and norm(filename_name)!=norm(c["card_name"]):
            ambiguous["filename_name_conflict"]+=1
            continue
        matched.append((c,path))
    return matched,ambiguous,len(catalog),len(entries),sum(len(v) for v in indexed.values())


def main():
    set_id=os.getenv("CARDVECTOR_TARGET_SET_ID","22872")
    folder=os.getenv("CARDVECTOR_R2_SET_FOLDER","scarlet-violet-promos")
    if not re.fullmatch(r"\d{2,8}",set_id) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",folder):
        raise RuntimeError("Unsafe set identifier or folder")
    matched,ambiguous,total,index_len,folder_count=candidates(set_id,folder)
    print(json.dumps({"set_id":set_id,"imported_catalog_cards":total,
                      "index_rows":index_len,"folder_images":folder_count,
                      "safe_unique_candidates":len(matched),
                      "excluded":ambiguous,
                      "sample":[{"number":c["card_number"],"name":c["card_name"],"path":p} for c,p in matched[:6]]},
                     sort_keys=True,default=dict),flush=True)
    if os.getenv("CARDVECTOR_STAGE_R2")!="1":
        return
    r2=images.r2_client()
    staged=0
    for c,path in matched:
        # Confirm actual original R2 object exists before staging a reference.
        try:
            r2.head_object(Bucket=os.environ["R2_BUCKET"],Key="archive/"+path)
        except Exception:
            print("Skipped R2 object unavailable for collector number "+c["card_number"],flush=True)
            continue
        review={"provider_id":c["provider_id"],"candidate_path":path,
                "review_status":"pending_review",
                "notes":"Existing Kaggle R2 image; exact unique English set/number and matching name where encoded. Pending administrator visual approval; do not infer stamp/finish."}
        query=urllib.parse.urlencode({"on_conflict":"provider_id",
                                     "select":"provider_id,candidate_path"})
        inserted=json.loads(images.request(images.DB+"cv_admin_image_reviews?"+query,
                     {**images.db_headers(),"Prefer":"resolution=ignore-duplicates,return=representation"},
                     method="POST",payload=[review]))
        if len(inserted)==1 and inserted[0]["candidate_path"]==path:
            staged+=1
    print(json.dumps({"set_id":set_id,"staged_for_admin_review":staged,
                      "pokewallet_requests_used":0}),flush=True)


if __name__=="__main__":
    main()
