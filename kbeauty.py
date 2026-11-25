#!/usr/bin/env python3
"""
K-beauty price comparison for Albanian stores.

    python kbeauty.py                 fetch all stores, match, build the site/ folder
    python kbeauty.py --offline       rebuild from data/raw/*.json (no network)
    python kbeauty.py --stores kfarma,beautene

Outputs:
    data/raw/<store>.json   raw API responses (so you can rebuild offline)
    data/products.json      normalized + matched products
    data/matches.csv        every match with its score, for manual review
    site/                   the static multi-page website (see site_build.py)
"""
import argparse
import csv
import html
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

# ---------------------------------------------------------------- config

STORES = [
    {"id": "kfarma", "name": "KFarma", "platform": "shopify",
     "base": "https://kfarma.al", "vendor_is_brand": True},
    {"id": "beautene", "name": "Beautene", "platform": "woocommerce",
     "base": "https://beautene.al"},
    {"id": "koral", "name": "Koral Secrets", "platform": "shopify",
     "base": "https://koralsecrets.al", "vendor_is_brand": False},
    {"id": "glowyskin", "name": "Glowy Skin", "platform": "shopify",
     "base": "https://glowyskinshop.com", "vendor_is_brand": False},
]
# Which store's title to show for a matched product (cleanest naming first).
TITLE_PRIORITY = ["kfarma", "beautene", "koral", "glowyskin"]

# Brands to detect in titles for stores that don't store the brand separately.
# KFarma vendors and Beautene brands are added automatically on every run.
EXTRA_BRANDS = [
    "Dr. Sante", "Centellian24", "Sungboon Editor", "Aromatica", "Beauty of Joseon",
    "COSRX", "Anua", "Round Lab", "Torriden", "Medicube", "SKIN1004", "Some By Mi",
    "Isntree", "Mixsoon", "Numbuzin", "Ma:nyo", "Purito", "Axis-Y", "Haruharu Wonder",
    "Klairs", "I'm From", "Abib", "Jumiso", "Iunik", "By Wishtrend", "Missha",
    "Innisfree", "Laneige", "Etude", "Holika Holika", "Heimish", "Benton",
    "Pyunkang Yul", "Dr. Jart+", "Banila Co", "Biodance", "Celimax", "Goodal",
    "d'Alba", "Medi-Peel", "Tirtir", "VT", "Aestura", "Illiyoon", "Ongredients",
    "Iroha", "Mediheal", "Dr. Ceuracle", "Tocobo", "Skinfood", "Neogen", "Elizavecca",
]

MATCH_THRESHOLD = 85      # 0-100, higher = stricter
# If two "matched" items are both in stock, neither on sale, yet one costs this
# many times the other, it's almost always a bad match (different size/sample or
# a mask vs the product). Refuse it — a miss beats a wrong price.
PRICE_RATIO_GUARD = 2.2
REQUEST_DELAY = 1.0       # seconds between requests, be polite
USER_AGENT = "kbeauty-price-compare/0.1 (personal project)"
OVERRIDES_FILE = Path("data/overrides.json")

# ---------------------------------------------------------------- similarity

try:
    from rapidfuzz import fuzz

    def similarity(a, b):
        # token_set alone scores "x" vs "x foam" as 100; averaging with
        # token_sort penalizes extra words that usually mean a different product.
        return (fuzz.token_set_ratio(a, b) + fuzz.token_sort_ratio(a, b)) / 2
except ImportError:  # pure-python fallback, slower but same idea
    from difflib import SequenceMatcher

    def _r(x, y):
        return SequenceMatcher(None, x, y).ratio() * 100

    def similarity(a, b):
        ta, tb = set(a.split()), set(b.split())
        inter = " ".join(sorted(ta & tb))
        sa = (inter + " " + " ".join(sorted(ta - tb))).strip()
        sb = (inter + " " + " ".join(sorted(tb - ta))).strip()
        tset = max(_r(inter, sa), _r(inter, sb), _r(sa, sb)) if inter else _r(sa, sb)
        tsort = _r(" ".join(sorted(a.split())), " ".join(sorted(b.split())))
        return (tset + tsort) / 2

# ---------------------------------------------------------------- text helpers

STOPWORDS = {"the", "and", "with", "of", "dhe", "me", "per", "for"}
# If two names differ in one of these (or in any token containing a digit),
# they are different products/versions no matter how similar the rest is.
VERSION_WORDS = {"ex", "pro", "plus", "mini", "max", "lite", "light", "rich",
                 "ii", "iii", "iv", "edition", "set", "kit", "duo", "refill",
                 "travel", "jumbo", "sample", "spf",
                 # a mask / pad / patch is a different product from the cream or serum
                 "mask", "maske", "pack", "sheet", "sheets", "patch", "patches", "pad", "pads",
                 # "Cream" vs "Cream Mist", "Cleansing Oil" vs "Cleansing Oil Wipes"
                 "mist", "wipes", "wipe",
                 # "Eye Cream" / "BB Cream" are not the plain "Cream"
                 "eye", "bb", "cc"}
# Product forms. Only a conflict when EACH name has a form the other lacks
# ("Body Lotion" vs "Body Wash"). One store just adding "Serum" to the title
# ("Niacinamide 15%" vs "Niacinamide 15% Serum") is the same product.
FORM_WORDS = {"cream", "serum", "ampoule", "essence", "lotion", "toner", "cleanser", "wash",
              "foam", "oil", "balm", "gel", "powder", "stick", "spray", "cushion", "milk"}


def version_conflict(a, b):
    norm = {"foaming": "foam", "creme": "cream", "creams": "cream", "serums": "serum"}
    sa = {norm.get(t, t) for t in a.split()}
    sb = {norm.get(t, t) for t in b.split()}
    diff = sa ^ sb
    if any(t in VERSION_WORDS or any(c.isdigit() for c in t) for t in diff):
        return True
    return bool((sa - sb) & FORM_WORDS) and bool((sb - sa) & FORM_WORDS)
VOL_RE = re.compile(
    r"(?<![a-z0-9.])(\d+(?:[.,]\d+)?)\s*"
    r"(ml|gr|grams?|g|cope|copa|pcs|pc|pairs?|sheets?)(?![a-z])"
)
UNIT = {"ml": "ml", "g": "g", "gr": "g", "gram": "g", "grams": "g",
        "cope": "pcs", "copa": "pcs", "pcs": "pcs", "pc": "pcs",
        "sheet": "pcs", "sheets": "pcs", "pair": "pairs", "pairs": "pairs"}


def fold(s):
    """unescape html, strip accents (ë -> e), lowercase"""
    s = html.unescape(s or "")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


# emoji/pictographs (+ variation selector, zero-width joiner) that stores put in titles
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")


def clean(s):
    s = EMOJI.sub(" ", html.unescape(s or ""))
    return re.sub(r"\s+", " ", s).strip()


def strip_tags(s):
    return re.sub(r"<[^>]+>", " ", s or "")


def brand_key(s):
    return re.sub(r"[^a-z0-9]", "", fold(s))


def parse_volume(text, default_unit=None):
    """'... 200ML' -> '200ml'; bare '200' with default_unit='ml' -> '200ml'"""
    if not text:
        return None
    f = fold(text)
    m = VOL_RE.search(f)
    if m:
        num, unit = m.group(1).replace(",", "."), UNIT[m.group(2)]
    elif default_unit and re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*", f):
        num, unit = f.strip().replace(",", "."), default_unit
    else:
        return None
    if "." in num:
        num = num.rstrip("0").rstrip(".")
    return f"{num}{unit}"


LIST_VOL_RE = re.compile(
    r"(?<![a-z0-9.])((?:\d+(?:[.,]\d+)?(?:\s*[/|]\s*|,\s+))+\d+(?:[.,]\d+)?)\s*"
    r"(ml|gr|grams?|g|cope|copa|pcs|pc|pairs?|sheets?)(?![a-z])"
)


def listed_volumes(text):
    """every size a text mentions: '30 / 80 ml' -> {'30ml','80ml'}, '50ml, 100ml' -> both"""
    f = fold(text or "")
    out = {parse_volume(n.strip() + u) for nums, u in LIST_VOL_RE.findall(f)
           for n in re.split(r"\s*[/|]\s*|,\s+", nums)}
    out |= {parse_volume(n + u) for n, u in VOL_RE.findall(f)}
    return out - {None}


def volkey(v):
    """size for comparing: 100g and 100ml are the same jar labelled two ways"""
    return v[:-1] + "ml" if v and v.endswith("g") and not v.endswith("ml") else v


def tokenize(s):
    s = fold(s).replace("&", " and ")
    s = re.sub(r"\b([bc])\.\s?\1\b\.?", r"\1\1", s)    # "B.B Cream" -> "bb cream"
    s = VOL_RE.sub(" ", s)                         # volume is matched separately
    s = re.sub(r"[^a-z0-9.]+", " ", s)
    s = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", s)      # keep 0.1, drop other dots
    return [t for t in s.split() if t not in STOPWORDS]


def drop_brand_prefix(toks, bkey):
    for k in range(1, min(5, len(toks)) + 1):
        if "".join(toks[:k]) == bkey:
            return toks[k:]
    return toks


def detect_brand(toks, known):
    """longest known brand at the start of the title; else first word (guessed)"""
    for k in range(min(4, len(toks)), 0, -1):
        key = "".join(toks[:k])
        if key in known:
            return key, False
    return (toks[0], True) if toks else ("", True)


def to_number(x):
    if x in (None, ""):
        return None
    v = float(x)
    return int(v) if v.is_integer() else round(v, 2)

# ---------------------------------------------------------------- fetching


# Some stores let their TLS certificate expire. The product feeds are public
# (no login, no secrets), so rather than drop the store we retry without
# certificate verification and warn loudly, once per host.
_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE
_warned_hosts = set()


def get_json(url, _tries=0):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            return json.load(r)
    except HTTPError as e:
        if e.code == 429 and _tries < 2:       # rate limited: a couple of polite retries, then give up
            wait = min(30, int(e.headers.get("Retry-After") or 0) or 10 * 2 ** _tries)
            print(f"  429 from {urlsplit(url).hostname}; waiting {wait}s then retrying...", file=sys.stderr, flush=True)
            time.sleep(wait)
            return get_json(url, _tries + 1)
        raise
    except URLError as e:
        if not isinstance(e.reason, ssl.SSLCertVerificationError):
            raise
        host = urlsplit(url).hostname
        if host not in _warned_hosts:
            _warned_hosts.add(host)
            print(f"  WARNING: {host} has an invalid TLS certificate ({e.reason.verify_message}); "
                  "fetching its public feed without verification", file=sys.stderr)
        with urlopen(req, timeout=30, context=_INSECURE_CTX) as r:
            return json.load(r)


def fetch_shopify(base):
    out, page = [], 1
    while page <= 200:
        prods = get_json(f"{base}/products.json?limit=250&page={page}").get("products", [])
        if not prods:
            break
        out += prods
        page += 1
        time.sleep(REQUEST_DELAY)
    return out


def fetch_woocommerce(base):
    """Products, then every variation (type=variation): a variable product's own
    price is only its cheapest option, so each size needs its variation's price."""
    out = []
    for extra in ("", "&type=variation"):
        page = 1
        while page <= 200:
            try:
                data = get_json(f"{base}/wp-json/wc/store/v1/products?per_page=100&page={page}{extra}")
            except HTTPError as e:
                if e.code == 400:      # WooCommerce answers 400 past the last page
                    break
                raise
            if not data:
                break
            out += data
            page += 1
            time.sleep(REQUEST_DELAY)
    return out

# ---------------------------------------------------------------- parsing into one shape
# every item: store, title, brand, volume, price, compare_at, in_stock, url, image


def parse_shopify(store, prods):
    items = []
    for p in prods:
        title = clean(p.get("title"))
        if "gift card" in fold(title) or "giftcard" in fold(p.get("product_type") or ""):
            continue      # gift cards aren't products to compare
        brand = clean(p.get("vendor")) if store.get("vendor_is_brand") else None
        tags = p.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        cats = [fold(t) for t in tags]
        if p.get("product_type"):
            cats.append(fold(p["product_type"]))
        best = any("bestseller" in c or "best seller" in c for c in cats)
        opts = [o.get("name", "").lower() for o in p.get("options", [])]
        variants = p.get("variants", [])
        multi = len(variants) > 1
        body_vol = None if multi else parse_volume(strip_tags(p.get("body_html")))
        images = p.get("images") or []
        prod_img = images[0]["src"] if images else None

        # Collapse variants by volume: shade/color variants (same size) become ONE
        # listing; genuine different sizes stay separate (needed to match by size).
        groups = {}
        for v in variants:
            vol = None
            for i, oname in enumerate(opts[:3]):
                val = v.get(f"option{i + 1}")
                if val and val != "Default Title":
                    unit = UNIT.get(oname.strip()) if oname.strip() in UNIT else None
                    vol = vol or parse_volume(val, default_unit=unit)
            vol = vol or parse_volume(title) or body_vol
            price = to_number(v.get("price"))
            cmp_at = to_number(v.get("compare_at_price"))
            avail = bool(v.get("available"))
            # Single-variant products: always the product's main image. Stores
            # (KFarma) often attach a promo/secondary image as the variant image.
            # Multi-variant: the variant image shows that shade/size, keep it.
            img = ((v.get("featured_image") or {}).get("src") if multi else None) or prod_img
            g = groups.get(vol)
            if g is None:
                groups[vol] = {"vid": v.get("id"), "img": img, "price": price,
                               "cmp": cmp_at, "avail": avail}
            else:
                # keep the cheapest variant as the representative for this size
                if price is not None and (g["price"] is None or price < g["price"]):
                    g["price"], g["cmp"], g["vid"] = price, cmp_at, v.get("id")
                    if img:
                        g["img"] = img
                g["avail"] = g["avail"] or avail

        for vol, g in groups.items():
            url = f"{store['base']}/products/{p['handle']}"
            if multi and g["vid"] is not None:
                url += f"?variant={g['vid']}"
            price, cmp_at = g["price"], g["cmp"]
            items.append({
                "store": store["id"], "title": title, "brand": brand, "volume": vol,
                "price": price,
                "compare_at": cmp_at if cmp_at and price and cmp_at > price else None,
                "in_stock": g["avail"], "url": url, "image": g["img"],
                "cats": cats, "bestseller": best,
            })
    return items


def _woo_price(p):
    pr = p.get("prices") or {}
    minor = int(pr.get("currency_minor_unit") or 0)
    price = to_number(int(pr["price"]) / 10 ** minor) if pr.get("price") else None
    reg = to_number(int(pr["regular_price"]) / 10 ** minor) if pr.get("regular_price") else None
    if not price:            # Beautene reports 0 for some sold-out items: that's "no price", not free
        price = None
    return price, (reg if reg and price and reg > price else None)


def _woo_img(p):
    imgs = p.get("images") or []
    return (imgs[0].get("thumbnail") or imgs[0].get("src")) if imgs else None


def parse_woocommerce(store, prods):
    """One item per size. Variable products use their variations (each has its own
    size/price/stock); shades of the same size collapse to the cheapest one."""
    variations = {}
    for v in prods:
        if v.get("type") == "variation" and v.get("parent"):
            variations.setdefault(v["parent"], []).append(v)

    items = []
    for p in prods:
        if p.get("type") == "variation":
            continue
        title = clean(p.get("name"))
        brands = p.get("brands") or []
        brand = clean(brands[0]["name"]) if brands else None
        cats = [fold(c.get("name", "")) for c in (p.get("categories") or [])]
        best = any("bestseller" in c or "best seller" in c for c in cats)
        base = {"store": store["id"], "title": title, "brand": brand, "cats": cats, "bestseller": best}
        own_vol = parse_volume(title) or parse_volume(strip_tags(p.get("short_description")))
        prod_img = _woo_img(p)

        vs = variations.get(p.get("id")) or []
        if vs:
            groups = {}
            for v in vs:
                vol = parse_volume(v.get("variation")) or own_vol
                price, cmp_at = _woo_price(v)
                g = groups.get(vol)
                if g is None or (price is not None and (g["price"] is None or price < g["price"])):
                    avail = (g["avail"] if g else False) or bool(v.get("is_in_stock"))
                    groups[vol] = {"price": price, "cmp": cmp_at, "avail": avail,
                                   "url": v.get("permalink") or p.get("permalink"),
                                   "img": _woo_img(v) or prod_img}
                else:
                    g["avail"] = g["avail"] or bool(v.get("is_in_stock"))
            for vol, g in groups.items():
                items.append({**base, "volume": vol, "price": g["price"], "compare_at": g["cmp"],
                              "in_stock": g["avail"], "url": g["url"], "image": g["img"]})
            continue

        # simple product (or variable product whose variations weren't fetched)
        vol = own_vol
        listed = listed_volumes(strip_tags(p.get("price_html")))
        if not vol:
            if len(listed) > 1:
                continue        # several sizes but one price: can't compare it safely
            vol = next(iter(listed), None)
        price, cmp_at = _woo_price(p)
        items.append({**base, "volume": vol, "price": price, "compare_at": cmp_at,
                      "in_stock": bool(p.get("is_in_stock")), "url": p.get("permalink"),
                      "image": prod_img})
    return items


PARSERS = {"shopify": parse_shopify, "woocommerce": parse_woocommerce}
FETCHERS = {"shopify": fetch_shopify, "woocommerce": fetch_woocommerce}

# ---------------------------------------------------------------- normalize + match


def normalize(items):
    """adds brand_key, brand_guessed, name_key; returns brand display names"""
    known, spellings = {}, defaultdict(Counter)
    for b in EXTRA_BRANDS:
        known[brand_key(b)] = b
    for it in items:
        if it["brand"]:
            known[brand_key(it["brand"])] = it["brand"]
    for it in items:
        toks = tokenize(it["title"])
        if it["brand"]:
            bkey, guessed = brand_key(it["brand"]), False
        else:
            bkey, guessed = detect_brand(toks, known)
        it["brand_key"], it["brand_guessed"] = bkey, guessed
        it["name_key"] = " ".join(drop_brand_prefix(toks, bkey))
        if it["brand"]:
            spellings[bkey][it["brand"]] += 1
    display = {k: (spellings[k].most_common(1)[0][0] if spellings[k] else v) for k, v in known.items()}
    return display


def dedupe_within_store(items):
    """Collapse identical listings from the same store (a store listing the same
    product twice). Keeps one per (store, brand, name, volume), preferring an
    in-stock listing then the cheapest. Needs normalize() to have run first."""
    seen, out = {}, []
    for it in items:
        key = (it["store"], it["brand_key"], it["name_key"], volkey(it["volume"]))
        if key not in seen:
            seen[key] = len(out)
            out.append(it)
            continue
        cur = out[seen[key]]
        better = (it["in_stock"] and not cur["in_stock"]) or (
            it["in_stock"] == cur["in_stock"] and it["price"] is not None
            and (cur["price"] is None or it["price"] < cur["price"]))
        if better:
            out[seen[key]] = it
    return out


def load_overrides():
    if OVERRIDES_FILE.exists():
        return json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return {"force": [], "block": []}


def match(items, overrides=None):
    """greedy clustering: best-scoring cross-store pairs first, max one item per store per cluster"""
    overrides = overrides or {"force": [], "block": []}
    block = {frozenset(p) for p in overrides.get("block", [])}
    parent = list(range(len(items)))
    stores = [{it["store"]} for it in items]
    by_url = {it["url"]: i for i, it in enumerate(items)}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri == rj or stores[ri] & stores[rj]:
            return False
        parent[rj] = ri
        stores[ri] |= stores[rj]
        return True

    for group in overrides.get("force", []):
        idx = [by_url[u] for u in group if u in by_url]
        for j in idx[1:]:
            union(idx[0], j)

    edges = []
    by_brand = defaultdict(list)
    for i, it in enumerate(items):
        by_brand[it["brand_key"]].append(i)
    for idx in by_brand.values():
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                i, j = idx[a], idx[b]
                A, B = items[i], items[j]
                if A["store"] == B["store"]:
                    continue
                if A["volume"] and B["volume"] and volkey(A["volume"]) != volkey(B["volume"]):
                    continue
                if frozenset((A["url"], B["url"])) in block:
                    continue
                if version_conflict(A["name_key"], B["name_key"]):
                    continue
                pa, pb = A["price"], B["price"]
                if pa and pb and not A["compare_at"] and not B["compare_at"]:
                    hi, lo = max(pa, pb), min(pa, pb)
                    if lo > 0 and hi / lo >= PRICE_RATIO_GUARD:
                        continue      # suspicious price gap -> likely a bad match
                s = similarity(A["name_key"], B["name_key"])
                if s >= MATCH_THRESHOLD:
                    edges.append((s, i, j))
    edges.sort(reverse=True)
    scores = {}
    for s, i, j in edges:
        if union(i, j):
            scores[i] = max(scores.get(i, 0), s)
            scores[j] = max(scores.get(j, 0), s)

    clusters = defaultdict(list)
    for i in range(len(items)):
        clusters[find(i)].append(i)
    return list(clusters.values()), scores


def pretty(title):
    letters = [c for c in title if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.8:
        title = title.title()
        title = re.sub(r"(\d)(Ml|Gr|G)\b", lambda m: m.group(1) + m.group(2).lower(), title)
    return title


# ---------------------------------------------------------------- classification
# Map each product to a section, a product type and skin concerns. KFarma tags
# and Beautene categories are reliable; Koral/Glowy give almost nothing, so we
# also infer from the title. Keywords are folded (accent-stripped, lowercase)
# and matched as substrings, so Albanian and English spellings both hit.
# Tune these the same way as the brand list: cheap to extend, review weekly.

# Top-level section. Sunscreen is a skin *type*, not its own section.
SECTION_KW = {
    "fytyra":  ["fytyr", "face", "facial", "kujdesi per lekure", "skincare", "lekur",
                "diell", "sunscreen", "sun cream", "sun serum", "sun stick"],
    "floket":  ["flok", "hair", "shampo", "balsam", "conditioner", "scalp", "leave in"],
    "trupi":   ["trup", "body", "duar", "kembe", "hand cream", "foot", "dush", "shower", "scrub trup"],
    "makeup":  ["make up", "makeup", "make-up", "lipstick", "lip tint", "lip gloss", "mascara",
                "foundation", "concealer", "fondatin", "blush", "eyeliner", "eyeshadow",
                "bb cream", "cc cream", "cushion"],
    "parfume": ["parfum", "perfume", "fragrance", "mist trupi", "eau de", "body mist"],
    # whole-word only (padded with spaces) so "Setting Spray"/"1+1 promo" don't count as sets
    "sete":    [" set ", " sets ", " kit ", " bundle ", " sete ", "gift set", "trial set", "value set", "duo set", "mini set"],
}
# "Perfume" is often just a scent descriptor ("Perfume Dry Shampoo", "perfume
# hand cream"). If any of these product-form words appear, it is NOT a fragrance.
# make-up "creams" (BB/CC/cushion/concealer/foundation) are make-up, not a skincare
# type — so "BB Cream" must not count as a moisturiser (hidratues) type.
MAKEUP_FORMS = ["bb cream", "cc cream", "cushion", "concealer", "fondatin", "foundation",
                "lipstick", "lip tint", "lip gloss", "mascara", "eyeliner", "eyeshadow",
                "blush", "bronzer", "highlighter", "setting spray", "setting powder"]
PARFUME_EXCLUDE = ["shampoo", "shampo", "conditioner", "kondicioner", "balsam", "cream",
                   "krem", "serum", "cleanser", "pastrues", "lotion", "locion", "mask",
                   "maske", "scrub", "essence", "esence", "toner", "tonik", "lares",
                   "oil", "vaj", "deodorant", "stick", "powder", "pudra", "foam", "treatment",
                   "wash", "shower", "dush", "shampoo"]
SUN_WORDS = [" spf", " uv ", " sun ", "sunscreen", "dielli", "suncare"]
FRAGRANCE_NAME = ["body mist", "body spray", "perfume mist", "fragrance mist", "fragranced body mist",
                  "eau de parfum", "eau de toilette", "eau de cologne", "hair perfume", "hair parfume",
                  "perfume balm", "solid perfume"]
# Within Fytyra: skin / eyes / lips. Only skincare eye & lip *care* (not makeup).
AREA_KW = {
    "syte":  ["eye cream", "eye serum", "eye patch", "under-eye", "under eye", "eye mask",
              "eye gel", "rreth syve", "krem syri", "serum syri", "maske syri", "kontur syri"],
    "buzet": ["lip balm", "lip care", "lip mask", "lip sleeping", "lip oil", "lip scrub",
              "lip treatment", "lip serum", "balsam buze", "maske buze", "vaj buze", "kujdes buze"],
}
CONCERN_KW = {
    "akne":     ["akne", "acne", "pimple", "blemish", "spot treatment", "pulliz", "breakout", "mbeturina"],
    "poret":    ["pore", "poret", "yndyr", "oily", "oil control", "sebum", "mitesser", "blackhead", "lares vajor"],
    "rrudha":   ["rrudh", "wrinkle", "anti-age", "antiage", "aging", "plakj", "firming", "elasticit",
                 "collagen", "kolagjen", "lifting", "retinol", "retinal", "peptide"],
    "njolla":   ["hiperpigment", "pigment", "njoll", "dark spot", "brighten", "zbardh", "whitening",
                 "vitamin c", "glow", "ndricim", "radiance", "melasma"],
    "skuqje":   ["skuqje", "redness", "sensitive", "ndjesh", "cica", "centella", "calming", "qetesu",
                 "soothing", "madecassoside", "barrier", "relief"],
    # the hydration *concern* (dry/dehydrated skin) — NOT every moisturizer. Must not
    # match the store's "Hidratues" type category, so no bare "hidrat"/"moistur".
    "hidratim": ["hidratim", "dehidrat", "dehydrat", "dry skin", "lekure e thate", "thate",
                 "thatesi", "hydrating", "hydration", "dewy", "thirsty"],
}
# Section-specific subcategory for hair / body / make-up. ONE per product, chosen
# by priority (first match wins), because stores cross-list everything into their
# broad "shampoo"/"body cream" collections — so those generic buckets come LAST.
KIND_KW = [
    # hair — serum/oil/treatment/conditioner/styling rank above shampoo
    ("vaj_floke",   ["hair oil", "vaj floke", "vaj per flok", "hair serum", "serum floke", "serum per flok",
                     "scalp serum", "scalp tonic", "leave in", "leave-in", "hair ampoule", "ampula floke", "hair essence"]),
    ("maske_floke", ["hair mask", "maske floke", "maske per flok", "hair pack", "hair treatment",
                     "trajtim floke", "trajtime per flok", "scalp mask"]),
    ("balsam",      ["conditioner", "kondicioner", "balsam", "balzam"]),
    ("stilues",     ["styling", "stilues", "hair spray", "spray floke", "gel floke", "wax", "pomade", "mousse", "heat protect"]),
    ("shampo",      ["shampoo", "shampo"]),
    # body — generic body cream/lotion last
    ("scrub",       ["scrub", "peeling trupi", "exfoliat"]),
    ("dush",        ["shower", "dush", "body wash", "shower gel", "larje trupi", "sapun"]),
    ("duar_kembe",  ["hand cream", "krem duar", "foot cream", "kujdesi per duart", "kujdesi per kembet", "duart", "kembet"]),
    ("krem_trupi",  ["body cream", "body lotion", "krem trupi", "locion trupi", "body butter", "body milk", "krem/locion trupi", "kujdesi per trupin"]),
    # make-up
    ("mu_syte",     ["mascara", "eyeliner", "eyeshadow", "eye shadow", "eyebrow", "vetulla", "laps syri"]),
    ("mu_buze",     ["lipstick", "lip tint", "lip gloss", "lip liner", "buzekuq", "laps buze", "lip stick"]),
    ("mu_fytyre",   ["foundation", "concealer", "fondatin", "blush", "powder", "pudra", "bb cream",
                     "cc cream", "cushion", "bronzer", "highlighter", "primer", "contour"]),
]
# Product *form* (not purpose — "anti-age"/"spot" live in CONCERN_KW instead, so
# they don't mislabel a cleanser or serum). Order matters: first match wins.
CREAM_WORDS = [" cream", "krem", "lotion", "locion", "balm", "balsam", "emulsion", "moistur",
               "gel cream", "mask", "masque", "maske"]
TYPE_KW = [
    # sunscreen needs a real sun/UV word — bare "SPF" also appears on makeup cushions
    ("krem_dielli", ["sunscreen", "suncream", "sun cream", "sun stick", "sun serum", "sun fluid",
                     "sun gel", " sun ", "krem dielli", "mbrojtje nga dielli", "uv "]),
    # a spot/local treatment is its own form (applied to a spot, not the whole face)
    ("trajtim",     ["spot treatment", "acne patch", "pimple patch", "spot patch", "spot corrector",
                     "blemish patch", "blemish spot", "spot cream", "cica patch", "trajtim lokal", "patch akne"]),
    ("maske",       ["sheet mask", "maske", " mask", "sleeping pack", "wash off", "clay mask", "modeling pack"]),
    ("pastrues",    ["cleanser", "cleansing", "pastrues", "lares", "foam", "micellar", "face wash",
                     "makeup remover", "gel larje", "cleansing oil", "cleansing balm"]),
    ("toner",       ["toner", "tonik", "essence toner"]),
    ("serum",       ["serum", "esence", "essence", "ampoule", "ampule", "booster"]),
    ("hidratues",   ["moisturiz", "moisturis", "krem hidrat", " cream", "krem ", "locion", "lotion",
                     "emulsion", "gel krem", "balm", "balsam"]),
]


# which section a hair/body/make-up subcategory belongs to
KIND_SECTION = {"vaj_floke": "floket", "maske_floke": "floket", "balsam": "floket",
                "stilues": "floket", "shampo": "floket", "scrub": "trupi", "dush": "trupi",
                "duar_kembe": "trupi", "krem_trupi": "trupi",
                "mu_syte": "makeup", "mu_buze": "makeup", "mu_fytyre": "makeup"}


def classify(members):
    """Classify a product trusting the stores' OWN categories first (the way their
    pages group it); fall back to the product title only when the stores give
    nothing. A dimension stays empty if neither source knows it."""
    # " | " between categories: "Mist" + "Trupi" must not read as the phrase "mist trupi"
    cat = " " + " | ".join(c for m in members for c in m.get("cats", [])) + " "
    name = " " + " ".join(fold(m["title"]) for m in members) + " "

    def first(pairs, t):
        return next((k for k, kws in pairs if any(w in t for w in kws)), None)
    ptype = first(TYPE_KW, cat) or first(TYPE_KW, name)
    # Stores file some serums under "Hidratues"/"Spot Krem" (Celimax Retinal Shot Booster).
    # If the name says serum/booster/ampoule and nothing cream-like, the name wins.
    if ptype == "hidratues" and any(w in name for w in dict(TYPE_KW)["serum"]) \
            and not any(w in name for w in CREAM_WORDS):
        ptype = "serum"
    if ptype and any(w in name for w in MAKEUP_FORMS):
        ptype = None                          # a BB/CC cushion is make-up, not a skincare type
    kind = first(KIND_KW, cat) or first(KIND_KW, name)
    kinds = [kind] if kind else []

    def secs(t):
        return [s for s, kws in SECTION_KW.items() if any(k in t for k in kws)]
    sections = secs(cat)
    from_cats = bool(sections)
    if not sections:                         # stores said nothing -> infer from title
        sections = secs(name)
    if "parfume" in sections and not from_cats and any(w in name for w in PARFUME_EXCLUDE):
        sections.remove("parfume")
    # a fragrance named as such (body mist/spray, perfume) belongs in Parfume even when
    # the store filed it under body; sunscreen mists/sprays never do
    is_sun = any(w in name for w in SUN_WORDS)
    if is_sun and "parfume" in sections:
        sections.remove("parfume")
    elif ("parfume" not in sections and not is_sun and any(w in name for w in FRAGRANCE_NAME)
          and not any(w in name for w in PARFUME_EXCLUDE + ["acne", "scrub", "serum"])):
        sections.append("parfume")
    if not sections:                         # still nothing: trust the detected subcategory/type
        if kind:
            sections = [KIND_SECTION[kind]]
        elif ptype:
            sections = ["fytyra"]            # a toner/serum/cream with no other signal is face

    def area_of(t):
        if any(k in t for k in AREA_KW["syte"]):
            return "syte"
        if any(k in t for k in AREA_KW["buzet"]):
            return "buzet"
        return None
    area = area_of(cat) or area_of(name)
    if area and "fytyra" not in sections:      # eye/lip care implies face skincare
        sections.append("fytyra")
    if "fytyra" in sections and area is None:
        area = "lekura"

    def cons(t):
        return [c for c, kws in CONCERN_KW.items() if any(k in t for k in kws)]
    concerns = cons(cat) or cons(name)        # KFarma tags concerns; title is fallback
    return sections, area, ptype, concerns, kinds


FAMILY_THRESHOLD = 90    # stricter than MATCH_THRESHOLD: different listings, different sizes


def _vol_sort_key(v):
    m = re.match(r"([\d.]+)(\D+)$", v or "")
    return (m.group(2), float(m.group(1))) if m else ("", 0.0)


def strip_volume(name):
    """'Glow Booster Serum 15ml' / 'Toner (200 ml)' / 'Cream – 50ml' -> the name without the size"""
    out = re.sub(r"[\s(\[]*(?<![A-Za-z0-9.])\d+(?:[.,]\d+)?\s*(?:ml|gr|g|copë|cope|pcs)\b[)\]]*",
                 " ", name, flags=re.I)
    return re.sub(r"\s+", " ", re.sub(r"\s*[–\-|,]\s*$", "", out.strip())).strip() or name


def group_families(entries):
    """Join per-size products that are the same product in another size: same brand,
    names agree apart from the size (no version/form conflict), every size distinct.
    Each family becomes one product with sizes[]; size-less products stay alone."""
    parent = list(range(len(entries)))
    vols = [{volkey(e["volume"])} if e["volume"] else None for e in entries]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_brand = defaultdict(list)
    for i, e in enumerate(entries):
        if e["volume"]:
            by_brand[e["_bkey"]].append(i)
    edges = []
    for idx in by_brand.values():
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                A, B = entries[idx[a]], entries[idx[b]]
                if volkey(A["volume"]) == volkey(B["volume"]) or version_conflict(A["_nkey"], B["_nkey"]):
                    continue
                sc = similarity(A["_nkey"], B["_nkey"])
                if sc >= FAMILY_THRESHOLD:
                    edges.append((sc, idx[a], idx[b]))
    edges.sort(reverse=True)
    for _, i, j in edges:
        ri, rj = find(i), find(j)
        if ri != rj and not (vols[ri] & vols[rj]):      # never two of the same size in a family
            parent[rj] = ri
            vols[ri] |= vols[rj]

    fams = defaultdict(list)
    for i in range(len(entries)):
        fams[find(i)].append(entries[i])
    products = []
    for members in fams.values():
        members.sort(key=lambda e: _vol_sort_key(volkey(e["volume"])))
        # default size: carried by the most stores, then in stock, then most popular
        default = max(members, key=lambda e: (len(e["offers"]), any(o["in_stock"] for o in e["offers"]), e["pop"]))
        p = {k: v for k, v in default.items() if not k.startswith("_")}
        if len(members) > 1:
            p["name"] = strip_volume(default["name"])
            p["sizes"] = [{"volume": m["volume"], "offers": m["offers"], "image": m["image"] or default["image"]}
                          for m in members]
            p["dsize"] = members.index(default)
            p["image"] = default["image"] or next((m["image"] for m in members if m["image"]), None)
            for k in ("sections", "concerns", "kinds"):
                p[k] = sorted({x for m in members for x in (m[k] or [])}, key=lambda x: (default[k] or []).index(x)
                              if x in (default[k] or []) else 99)
            p["best"] = any(m["best"] for m in members)
            p["pop"] = max(m["pop"] for m in members)
        products.append(p)
    return products


def build_products(items, clusters, brand_display):
    entries = []
    for c in clusters:
        members = sorted((items[i] for i in c), key=lambda it: TITLE_PRIORITY.index(it["store"])
                         if it["store"] in TITLE_PRIORITY else 99)
        lead = members[0]
        offers = sorted(
            ({k: it[k] for k in ("store", "price", "compare_at", "in_stock", "url")} for it in members),
            key=lambda o: (not o["in_stock"], o["price"] if o["price"] is not None else 1e12))
        bkey = lead["brand_key"]
        sections, area, ptype, concerns, kinds = classify(members)
        best = any(m.get("bestseller") for m in members)
        # Popularity proxy (no sales data): a store tagging it "bestseller" is the
        # strongest signal; carried by more stores = more mainstream; in stock counts.
        # This is the default order on every page.
        pop = (5 if best else 0) + 2 * len(offers) + (1 if any(o["in_stock"] for o in offers) else 0)
        entries.append({
            "name": pretty(lead["title"]),
            "brand": brand_display.get(bkey) or (lead["brand"] or bkey).title(),
            "volume": next((m["volume"] for m in members if m["volume"]), None),
            "image": next((m["image"] for m in members if m["image"]), None),
            "offers": offers,
            "sections": sections, "area": area, "type": ptype,
            "concerns": concerns, "kinds": kinds,
            "best": best, "pop": pop,
            "_bkey": bkey, "_nkey": lead["name_key"],
        })
    products = group_families(entries)
    products.sort(key=lambda p: (-p["pop"], -len(p["offers"]), p["brand"].lower(), p["name"].lower()))
    for i, p in enumerate(products):
        p["i"] = i
    return products


def write_match_report(items, clusters, scores, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cluster", "store", "brand_key", "volume", "price", "in_stock", "score", "title", "url"])
        n = 0
        for c in sorted(clusters, key=len, reverse=True):
            if len(c) < 2:
                continue
            n += 1
            for i in c:
                it = items[i]
                w.writerow([n, it["store"], it["brand_key"], it["volume"], it["price"],
                            it["in_stock"], round(scores.get(i, 0), 1), it["title"], it["url"]])

# ---------------------------------------------------------------- site

from site_build import build_site  # noqa: E402

# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="use saved data/raw/*.json, no network")
    ap.add_argument("--stores", help="comma-separated store ids, default all")
    ap.add_argument("--out", default="site", help="output directory for the static site")
    args = ap.parse_args()

    stores = STORES
    if args.stores:
        wanted = set(args.stores.split(","))
        stores = [s for s in STORES if s["id"] in wanted]
    # a shop that asked to be removed: not fetched, not shown anywhere (data/overrides.json)
    disabled = set(load_overrides().get("disabled_stores", []))
    unknown = disabled - {s["id"] for s in STORES}
    if unknown:
        print(f"  WARNING: unknown store id(s) in disabled_stores: {sorted(unknown)}", file=sys.stderr)
    if disabled & {s["id"] for s in stores}:
        print(f"  Disabled (overrides.json): {', '.join(s['name'] for s in stores if s['id'] in disabled)}")
        stores = [s for s in stores if s["id"] not in disabled]
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    items = []
    for s in stores:
        raw_file = raw_dir / f"{s['id']}.json"
        if args.offline:
            if not raw_file.exists():
                print(f"  {s['name']}: no saved data, skipping", file=sys.stderr)
                continue
            raw = json.loads(raw_file.read_text(encoding="utf-8"))
        else:
            print(f"Fetching {s['name']} ...", flush=True)
            try:
                raw = FETCHERS[s["platform"]](s["base"])
            except Exception as e:  # one broken store must not kill the whole run
                print(f"  FAILED: {e}", file=sys.stderr)
                if not raw_file.exists():
                    continue
                print("  using last saved data instead", file=sys.stderr)
                raw = json.loads(raw_file.read_text(encoding="utf-8"))
            else:
                raw_file.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        parsed = PARSERS[s["platform"]](s, raw)
        parsed = [it for it in parsed if it["price"] != 0]   # free gifts ("100% off"), not for sale
        print(f"  {s['name']}: {len(parsed)} items")
        items += parsed

    if not items:
        sys.exit("No products loaded.")

    brand_display = normalize(items)
    items = dedupe_within_store(items)
    clusters, scores = match(items, load_overrides())
    products = build_products(items, clusters, brand_display)

    Path("data").mkdir(exist_ok=True)
    Path("data/products.json").write_text(json.dumps(products, ensure_ascii=False, indent=1), encoding="utf-8")
    write_match_report(items, clusters, scores, "data/matches.csv")
    # "updated" = when the feeds were actually fetched (newest raw file), not now,
    # so an offline rebuild never claims the prices are fresher than they are.
    raw_mtimes = [(raw_dir / f"{s['id']}.json").stat().st_mtime
                  for s in stores if (raw_dir / f"{s['id']}.json").exists()]
    fetched = max(raw_mtimes) if raw_mtimes else datetime.now(timezone.utc).timestamp()
    updated = datetime.fromtimestamp(fetched, timezone.utc).isoformat(timespec="minutes")
    n_pages = build_site(products, stores, updated, Path(args.out))

    multi = sum(1 for p in products if len(p["offers"]) > 1)
    fams = sum(1 for p in products if p.get("sizes"))
    guessed = sum(1 for it in items if it["brand_guessed"])
    print(f"\n{len(items)} items -> {len(products)} products, {multi} found in 2+ stores, "
          f"{fams} with several sizes")
    print(f"{guessed} items had no known brand (first word used); add them to EXTRA_BRANDS")
    print(f"Review matches in data/matches.csv, built {n_pages} pages at {args.out}/index.html")


if __name__ == "__main__":
    main()
