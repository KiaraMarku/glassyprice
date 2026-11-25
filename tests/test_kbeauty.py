"""
Run:  python -m unittest discover tests

Records marked REAL are copied (trimmed) from the live store feeds on 2026-10-13.
Records marked SYNTHETIC are invented cross-store variants of the same product,
written the way the *other* store formats names, to test matching.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kbeauty as kb  # noqa: E402

S = {s["id"]: s for s in kb.STORES}


def shop(title, price, vendor="Store", opt=None, body="", avail=True, cmp=None, handle=None):
    options = [{"name": opt[0]}] if opt else [{"name": "Title"}]
    return {"title": title, "handle": handle or title.lower().replace(" ", "-"),
            "vendor": vendor, "body_html": body, "options": options, "images": [],
            "variants": [{"id": 1, "option1": opt[1] if opt else "Default Title",
                          "price": f"{price}.00", "compare_at_price": cmp,
                          "available": avail}]}


def woo(name, price, brand, unit_html="", stock=True, slug=None):
    return {"name": name, "permalink": f"https://beautene.al/product/{slug or name}",
            "brands": [{"name": brand}] if brand else [],
            "prices": {"price": str(price), "regular_price": str(price), "currency_minor_unit": 0},
            "price_html": f'<span>{price}&nbsp;<span>L</span></span><span class="wd-price-unit">{unit_html}</span>',
            "is_in_stock": stock, "images": []}


def build():
    items = []
    items += kb.parse_shopify(S["kfarma"], [
        # REAL
        shop("Skin1004 Madagascar Centella Hyalu-Cica Gentle Cleansing Milk", 1790, "Skin1004",
             ("ml", "200"), cmp="2490.00"),
        shop("Ongredients Skin Barrier Calming Lotion EX", 2190, "Ongredients", ("ml", "150")),
        shop("Ongredients Skin Barrier Glow Mist", 1690, "Ongredients", ("ml", "100"), avail=False),
        # SYNTHETIC
        shop("Dr. Sante Azulene Soother Toner", 2390, "Dr. Sante", ("ml", "200")),
        shop("Jumiso Urea 9.9 Intensive Multi Balm", 2190, "Jumiso", ("ml", "50")),
    ])
    items += kb.parse_shopify(S["glowyskin"], [
        # REAL
        shop("DR.SANTE AZULENE SOOTHER TONER 200ML", 2490, "Glowy Skin Albania"),
        shop("DR.SANTE AZULENE SOOTHER CLEANSING MILK 200ML", 2190, "Glowy Skin Albania"),
        shop("DR. SANTE ARTEMISIA AKA CREAM 50G", 2490, "Glowy Skin Albania"),
        shop("Sungboon Editor Silk Peptide EGF Intensive Gold Mask", 450, "Glowy Skin Albania"),
        # SYNTHETIC
        shop("SKIN1004 MADAGASCAR CENTELLA HYALU-CICA GENTLE CLEANSING MILK 200ML", 1990, "Glowy Skin Albania"),
    ])
    items += kb.parse_shopify(S["koral"], [
        # REAL
        shop("CENTELLIAN24+ Madeca Lab Wrinkle Revitalizing V2", 300, "Koral Secrets - tagline",
             body="<p>*24ml<br>*1copë</p>", cmp="400.00"),
        shop("CENTELLIAN24+ Madeca Vitamin Glowing Serum Mask", 600, "Koral Secrets - tagline",
             body="<p>*7copë</p>", cmp="1000.00"),
        # SYNTHETIC
        shop("ONGREDIENTS Skin Barrier Calming Lotion EX", 2290, "Koral Secrets - tagline",
             body="<p>*150ml</p>"),
    ])
    items += kb.parse_woocommerce(S["beautene"], [
        # REAL
        woo("JUMISO &#8211; Urea 9.9 Intensive Multi Balm", 2290, "Jumiso", "50 ml "),
        woo("JUMISO &#8211; Retinal 0.1 PDRN 5000 Cream", 2290, "Jumiso", "20 ml "),
        woo("Jumiso &#8211; Niacinamide 5+ Depuffing Under-Eye Patches (5 pairs)", 1490, "Jumiso"),
        woo("IUNIK &#8211; Beta-Glucan All In One Barrier Lotion", 2290, "Iunik", "300 ml"),
        # SYNTHETIC
        woo("Dr. Sante &#8211; Azulene Soother Toner", 2350, "Dr. Sante", "200 ml"),
        woo("Ongredients &#8211; Skin Barrier Calming Lotion", 2100, "Ongredients", "150 ml"),
    ])
    return items


def groups(items, clusters):
    return [sorted((items[i]["store"], items[i]["title"]) for i in c) for c in clusters if len(c) > 1]


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.items = build()
        self.by_title = {it["title"]: it for it in self.items}

    def test_volume_sources(self):
        t = self.by_title
        self.assertEqual(t["DR.SANTE AZULENE SOOTHER TONER 200ML"]["volume"], "200ml")      # title
        self.assertEqual(t["DR. SANTE ARTEMISIA AKA CREAM 50G"]["volume"], "50g")           # title, grams
        self.assertEqual(t["Ongredients Skin Barrier Glow Mist"]["volume"], "100ml")        # variant option
        self.assertEqual(t["CENTELLIAN24+ Madeca Lab Wrinkle Revitalizing V2"]["volume"], "24ml")  # body
        self.assertEqual(t["CENTELLIAN24+ Madeca Vitamin Glowing Serum Mask"]["volume"], "7pcs")   # copë
        self.assertEqual(t["JUMISO – Retinal 0.1 PDRN 5000 Cream"]["volume"], "20ml")       # price_html
        self.assertEqual(t["Jumiso – Niacinamide 5+ Depuffing Under-Eye Patches (5 pairs)"]["volume"], "5pairs")
        self.assertIsNone(t["Sungboon Editor Silk Peptide EGF Intensive Gold Mask"]["volume"])

    def test_no_false_volume_inside_words(self):
        self.assertIsNone(kb.parse_volume("SKIN1004 Madagascar Centella"))
        self.assertIsNone(kb.parse_volume("Retinal 0.1 PDRN 5000 Cream"))
        self.assertIsNone(kb.parse_volume("Niacinamide 5+ serum"))

    def test_prices_and_sales(self):
        t = self.by_title
        milk = t["Skin1004 Madagascar Centella Hyalu-Cica Gentle Cleansing Milk"]
        self.assertEqual((milk["price"], milk["compare_at"]), (1790, 2490))
        self.assertEqual(t["JUMISO – Urea 9.9 Intensive Multi Balm"]["price"], 2290)
        self.assertFalse(t["Ongredients Skin Barrier Glow Mist"]["in_stock"])

    def test_brand_detection(self):
        kb.normalize(self.items)
        t = self.by_title
        self.assertEqual(t["DR.SANTE AZULENE SOOTHER TONER 200ML"]["brand_key"], "drsante")
        self.assertEqual(t["DR. SANTE ARTEMISIA AKA CREAM 50G"]["brand_key"], "drsante")
        self.assertEqual(t["CENTELLIAN24+ Madeca Vitamin Glowing Serum Mask"]["brand_key"], "centellian24")
        self.assertEqual(t["Sungboon Editor Silk Peptide EGF Intensive Gold Mask"]["brand_key"], "sungbooneditor")
        self.assertFalse(t["DR.SANTE AZULENE SOOTHER TONER 200ML"]["brand_guessed"])
        self.assertEqual(t["DR.SANTE AZULENE SOOTHER TONER 200ML"]["name_key"], "azulene soother toner")


class TestVersionConflict(unittest.TestCase):
    def test_conflicts(self):
        self.assertTrue(kb.version_conflict("calming lotion ex", "calming lotion"))
        self.assertTrue(kb.version_conflict("retinal 0.1 cream", "retinal 0.3 cream"))
        self.assertTrue(kb.version_conflict("wrinkle revitalizing v2", "wrinkle revitalizing"))
        self.assertFalse(kb.version_conflict("azulene soother toner", "azulene soother toner"))
        self.assertFalse(kb.version_conflict("hyalu cica gentle cleansing milk", "hyalu cica cleansing milk"))


class TestMatching(unittest.TestCase):
    def setUp(self):
        self.items = build()
        kb.normalize(self.items)
        self.clusters, _ = kb.match(self.items)
        self.g = groups(self.items, self.clusters)

    def find(self, title):
        return next((g for g in self.g if any(t == title for _, t in g)), None)

    def test_toner_matches_across_three_stores(self):
        g = self.find("DR.SANTE AZULENE SOOTHER TONER 200ML")
        self.assertEqual({s for s, _ in g}, {"kfarma", "glowyskin", "beautene"})

    def test_toner_and_cleansing_milk_stay_separate(self):
        g = self.find("DR.SANTE AZULENE SOOTHER TONER 200ML")
        self.assertNotIn(("glowyskin", "DR.SANTE AZULENE SOOTHER CLEANSING MILK 200ML"), g)

    def test_all_caps_and_shopify_option_volume(self):
        g = self.find("Skin1004 Madagascar Centella Hyalu-Cica Gentle Cleansing Milk")
        self.assertEqual({s for s, _ in g}, {"kfarma", "glowyskin"})

    def test_ex_version_does_not_merge_with_plain(self):
        # "Calming Lotion EX" (KFarma, Koral) vs "Calming Lotion" (Beautene): different versions
        g = self.find("Ongredients Skin Barrier Calming Lotion EX")
        self.assertEqual({s for s, _ in g}, {"kfarma", "koral"})

    def test_same_line_different_product(self):
        balm = self.find("JUMISO – Urea 9.9 Intensive Multi Balm")
        self.assertEqual({s for s, _ in balm}, {"kfarma", "beautene"})
        self.assertIsNone(self.find("JUMISO – Retinal 0.1 PDRN 5000 Cream"))

    def test_block_override(self):
        items = build()
        kb.normalize(items)
        urls = [it["url"] for it in items if "Urea" in it["title"]]
        clusters, _ = kb.match(items, {"force": [], "block": [urls]})
        self.assertIsNone(next((g for g in groups(items, clusters) if any("Urea" in t for _, t in g)), None))

    def test_products_sorted_offers(self):
        products = kb.build_products(self.items, self.clusters, {})
        toner = next(p for p in products if "Azulene Soother Toner" in p["name"])
        prices = [o["price"] for o in toner["offers"]]
        self.assertEqual(prices, sorted(prices))
        self.assertEqual(toner["name"], "Dr. Sante Azulene Soother Toner")


class TestSizes(unittest.TestCase):
    def test_listed_volumes(self):
        self.assertEqual(kb.listed_volumes("Price range: 399 L - 3 490 L 30 / 80 ml"), {"30ml", "80ml"})
        self.assertEqual(kb.listed_volumes("50ml, 100ml"), {"50ml", "100ml"})
        self.assertEqual(kb.listed_volumes("1,5 / 3 g"), {"1.5g", "3g"})
        self.assertEqual(kb.listed_volumes("990 L"), set())

    def test_woo_variations_become_one_item_per_size(self):
        # REAL shape (trimmed): Beautene Aestura cream, 30ml 399 L / 80ml 3490 L
        parent = {"id": 65364, "type": "variable", "name": "AESTURA &#8211; Renew Atobarrier 365 Cream",
                  "permalink": "https://beautene.al/product/aestura/", "brands": [{"name": "Aestura"}],
                  "prices": {"price": "399", "regular_price": "890", "currency_minor_unit": 0},
                  "price_html": "399 L - 3 490 L 30 / 80 ml", "is_in_stock": True, "images": []}
        def var(vid, size, price, reg, stock=True):
            return {"id": vid, "type": "variation", "parent": 65364, "name": parent["name"],
                    "variation": f"Zgjidhni dozimin:: {size}", "is_in_stock": stock, "images": [],
                    "permalink": f"https://beautene.al/product/aestura/?size={size}",
                    "prices": {"price": str(price), "regular_price": str(reg), "currency_minor_unit": 0}}
        items = kb.parse_woocommerce(S["beautene"], [parent, var(71272, "30ml", 399, 890),
                                                     var(65365, "80ml", 3490, 3490)])
        by_vol = {i["volume"]: i for i in items}
        self.assertEqual(set(by_vol), {"30ml", "80ml"})
        self.assertEqual(by_vol["80ml"]["price"], 3490)
        self.assertIsNone(by_vol["80ml"]["compare_at"])
        self.assertEqual((by_vol["30ml"]["price"], by_vol["30ml"]["compare_at"]), (399, 890))

    def test_woo_multi_size_without_variations_is_skipped(self):
        p = woo("Some Cream", 399, "Brand", unit_html="399 L - 3 490 L 30 / 80 ml")
        self.assertEqual(kb.parse_woocommerce(S["beautene"], [p]), [])


class TestProductForms(unittest.TestCase):
    def key(self, s):
        return " ".join(kb.tokenize(s))

    def test_different_forms_conflict(self):
        for a, b in [("Atobarrier 365 Cream", "Atobarrier 365 Cream Mist"),
                     ("Pure Body Lotion", "Pure Body Wash"),
                     ("Intensive Lifting Ampoule", "Intensive Lifting Cream"),
                     ("Centella Cream", "Centella BB Cream"),
                     ("Marine Pearl Sun Stick", "Marine Pearl Sun Spray")]:
            self.assertTrue(kb.version_conflict(self.key(a), self.key(b)), (a, b))

    def test_form_word_only_on_one_side_is_same_product(self):
        for a, b in [("Niacinamide 15%", "The Niacinamide 15% Serum"),
                     ("Cleansing Foam", "Foaming Cleanser"),
                     ("Perfect Cover Serum BB Cream", "Perfect Cover Serum B.B Cream")]:
            self.assertFalse(kb.version_conflict(self.key(a), self.key(b)), (a, b))


class TestSizeFamilies(unittest.TestCase):
    def entry(self, name, vol, n_offers=1, bkey="cerave"):
        offers = [{"store": f"s{k}", "price": 100, "compare_at": None, "in_stock": True, "url": f"u{k}{vol}"}
                  for k in range(n_offers)]
        return {"name": name, "brand": "CeraVe", "volume": vol, "image": None, "offers": offers,
                "sections": [], "area": None, "type": None, "concerns": [], "kinds": [],
                "best": False, "pop": n_offers, "_bkey": bkey, "_nkey": " ".join(kb.tokenize(name))}

    def test_sizes_of_same_product_become_one(self):
        out = kb.group_families([self.entry("Foaming Cleanser 236ml", "236ml", 2),
                                 self.entry("Foaming Cleanser 473ml", "473ml", 1),
                                 self.entry("Foaming Cleanser", "1000ml", 1)])
        self.assertEqual(len(out), 1)
        p = out[0]
        self.assertEqual([s["volume"] for s in p["sizes"]], ["236ml", "473ml", "1000ml"])
        self.assertEqual(p["dsize"], 0)                 # most stores -> default size
        self.assertEqual(p["name"], "Foaming Cleanser")  # size taken out of the name

    def test_different_products_stay_apart(self):
        out = kb.group_families([self.entry("Exosome Shot 2000", "30ml"), self.entry("Exosome Shot 7500", "50ml"),
                                 self.entry("Moisturizing Cream", "50ml"), self.entry("Moisturizing Lotion", "236ml"),
                                 self.entry("Moisturizing Cream", "340ml", bkey="other")])
        self.assertEqual(len(out), 5)

    def test_g_and_ml_same_number_is_same_size(self):
        self.assertEqual(kb.volkey("100g"), kb.volkey("100ml"))
        out = kb.group_families([self.entry("Snail Cream", "100g"), self.entry("Snail Cream", "100ml")])
        self.assertEqual(len(out), 2)   # same size -> never two "sizes" of one card


if __name__ == "__main__":
    unittest.main()
