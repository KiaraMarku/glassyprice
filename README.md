# K-beauty Krahaso

Compares K-beauty prices and stock across four Albanian stores and builds a single-page, mobile-friendly website.

| Store | Platform | Feed |
|---|---|---|
| KFarma | Shopify | `kfarma.al/products.json` |
| Beautene | WooCommerce | `beautene.al/wp-json/wc/store/v1/products` |
| Koral Secrets | Shopify | `koralsecrets.al/products.json` |
| Glowy Skin | Shopify | `glowyskinshop.com/products.json` |

All four are the stores' own public product APIs. No HTML scraping.

## Run it

```bash
pip install -r requirements.txt     # optional, see file
python kbeauty.py                   # fetch, match, build
open site/index.html                # or just double-click it
```

Other modes:

```bash
python kbeauty.py --offline              # rebuild from data/raw/ without hitting the stores
python kbeauty.py --stores kfarma,koral  # only some stores
python -m unittest discover tests        # run the tests
```

If one store is down, the run continues and uses that store's last saved data.

## How matching works

1. **One shape per item.** Each store adapter outputs `{store, title, brand, volume, price, compare_at, in_stock, url, image}`. The stores keep this information in different places:
   - Brand: KFarma `vendor`, Beautene `brands`, Koral and Glowy only inside the title.
   - Volume: KFarma variant option, Beautene `price_html`, Glowy the title, Koral the description (`*24ml`, `*7copë`).
2. **Brand detection.** For title-only stores, the longest known brand at the start of the title wins. Known brands = KFarma vendors + Beautene brands + `EXTRA_BRANDS` in `kbeauty.py`. Brand keys ignore case and punctuation, so `DR.SANTE`, `DR. SANTE` and `Dr. Sante` are the same brand.
3. **Name key.** The title, with accents folded, brand prefix, volume and filler words removed. `DR.SANTE AZULENE SOOTHER TONER 200ML` becomes `azulene soother toner`.
4. **Pairing rules**, applied only within the same brand:
   - Volumes must agree when both stores state one.
   - Names must not differ in a version token (`EX`, `V2`, `mini`, any number like `0.1` vs `0.3`). This exists because "Calming Lotion EX" and "Calming Lotion" score about 90% similar but are different products.
   - Fuzzy score >= `MATCH_THRESHOLD` (85).
5. **Clustering.** Best-scoring pairs merge first, max one item per store per product.

## Checking and fixing matches

After each run, `data/matches.csv` lists every matched product with its score. Sort by `score` ascending and review the lowest ones first.

The run also prints how many items had no known brand. Add those brands to `EXTRA_BRANDS`.

Manual fixes go in `data/overrides.json`, using product URLs:

```json
{
  "force": [["https://kfarma.al/products/x", "https://beautene.al/product/y/"]],
  "block": [["https://koralsecrets.al/products/a", "https://glowyskinshop.com/products/b"]]
}
```

`force` merges listings the matcher missed. `block` separates a wrong match.

## Daily auto-update (free hosting)

`.github/workflows/update.yml` runs every morning on GitHub Actions, refreshes prices, commits `data/`, and publishes `site/` to GitHub Pages.

1. Push this folder to a GitHub repo.
2. Settings > Pages > Source: **GitHub Actions**.
3. Actions tab > update-prices > **Run workflow** for the first build.

## Known limits

- **Variable WooCommerce products** (several sizes in one listing) are read as one item with the base price. Beautene's sampled listings were all single-size; check `matches.csv` if prices look off.
- **Shopify pagination** uses `?page=N`. If a store ever returns the same page repeatedly, switch that fetcher to `since_id`.
- **Brand guessing** falls back to the first word of the title. That works for most K-beauty names but will miss brands written mid-title.
- **Prices go stale between runs.** The site shows the last update time, and the footer tells users to confirm the price in the store.

## Being a good citizen

The script waits 1 second between requests and identifies itself in the User-Agent. Read each store's terms before publishing the site. The stronger long-term move is to tell the stores about it: you send them buyers, and they may give you a proper feed.
