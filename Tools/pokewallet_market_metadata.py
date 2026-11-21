"""Normalize PokéWallet set-page TCGplayer price and product references.

All prices are per exact provider printing and per finish, not per name/number.
The originating API page is fetched by backend jobs, never by public search.
"""
import re
from urllib.parse import urlparse

PRODUCT_RE=re.compile(r"^https://(?:www\.)?tcgplayer\.com/product/\d+(?:[/?#].*)?$",re.I)
ALLOWED_PRICE_KEYS=("sub_type_name","market_price","low_price","mid_price","high_price","updated_at")


def market_row(item):
    if not isinstance(item,dict):
        return None
    info=item.get("card_info") or {}
    if not isinstance(info,dict) or info.get("product_type")=="sealed":
        return None
    identity=str(item.get("id") or "")
    if not re.fullmatch(r"pk_[a-f0-9]{40,128}",identity,re.I):
        return None
    tcg=item.get("tcgplayer")
    if not isinstance(tcg,dict):
        tcg={}
    url=tcg.get("url")
    if not isinstance(url,str) or not PRODUCT_RE.fullmatch(url):
        url=None
    prices=[]
    for row in tcg.get("prices") or []:
        if not isinstance(row,dict):
            continue
        sub=str(row.get("sub_type_name") or "").strip()
        value=row.get("market_price")
        if not sub or len(sub)>80 or isinstance(value,bool):
            continue
        try:
            market=float(value)
        except (ValueError,TypeError,OverflowError):
            continue
        if market<=0 or market>10000000:
            continue
        item_price={key:row[key] for key in ALLOWED_PRICE_KEYS
                    if key in row and row[key] is not None}
        item_price["sub_type_name"]=sub
        item_price["market_price"]=market
        prices.append(item_price)
    rarity=info.get("rarity")
    if not isinstance(rarity,str) or len(rarity)>90:
        rarity=None
    return {"provider_id":identity,"tcgplayer_url":url,
            "tcgplayer_prices":prices,"rarity":rarity}


def market_rows(raw_items,accepted):
    allowed={str(card.get("id") or "") for card in accepted}
    return [row for item in raw_items if (row:=market_row(item)) is not None
            and row["provider_id"] in allowed]
