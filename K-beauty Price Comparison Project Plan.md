# K-beauty Price Comparison: Project Plan

Oct 13, 2026 · @Kiara

## Summary

A public website that shows the price and stock of every K-beauty product across Albania's four main online stores, so shoppers check one page instead of four. It launches as a free tool and grows into a business once it has steady traffic.

- **Who it's for:** Albanian shoppers, mostly women 18 to 35, buying K-beauty online and on Instagram.
- **Stores at launch:** KFarma, Beautene, Koral Secrets, Glowy Skin. All four expose open product APIs (checked 2026-10-13).
- **Stack:** Python everywhere: scrapers, matching, FastAPI when the product needs a live API.
- **Hard constraint:** zero monthly server cost. The only paid item is the domain.
- **Launch target:** a public beta about 6 weeks from kickoff, working evenings around the internship.

The key design consequence: no always-on server at launch. Prices refresh on a schedule and the site is served as static files, which free tiers host without limits that matter.

## Brand

Chosen name: **Glass Price**. "Glass" works twice: glass skin is the core K-beauty ideal, and transparent, see-through prices are exactly what the site offers. glassprice.com is taken, so the site needs a different domain (below).

| Domain for Glass Price | Status on 2026-10-13 | Notes |
| --- | --- | --- |
| **getglassprice.com** | appears free | Recommended now: a .com, $10.46/year at Cloudflare |
| glassprice.al | not checked | Best fit for an Albania-only site; get a quote from a local AKEP-authorized registrar |
| glassprice.shop | not checked | Cheap alternative, less trusted than .com |
| glassprice.com, glasprice.com, glassprices.com | taken |  |

Names considered and dropped: Dewdeal, Petal Price, Unnie Deals, Glow Unnie, Blushlist (rejected or weaker); Glass Beauty and Glass Deal (.com taken; "Glass Beauty" is also used by glass packaging companies, which muddies search).

"Appears free" means the .com registry had no record when checked. Confirm at the registrar before you rely on it, and check the handle on Instagram and TikTok, where your users are. Avoid "Kirei": a Tirana store, Kirei Cosmetics, already uses it.

**Tagline:** Clear prices for glass skin. Albanian version for the site: *Çmime transparente për lëkurë si xhami.*

**Voice:** a friend who knows skincare and hates overpaying. Short sentences, Albanian first, product names in English as the stores write them. Never invent claims about products. The site compares prices, it doesn't give skin advice.

**Domain:** buy the chosen .com through Cloudflare Registrar, which sells at cost: $10.46 per year for .com, registration and renewal ([vpsranking](https://vpsranking.com/domain/cloudflare/)). Skip .al for now. Gandi lists it at EUR 304 per year through a corporate contract ([Gandi](https://www.gandi.net/en/domain/tld/al)); a local AKEP-authorized registrar may be cheaper, so get a quote later.

## Visual theme

The look is pastel and pink: a blush background, soft pink, lavender, mint and peach fills, and one deep rose for text and buttons. Pastels are too light to read as text, so every pastel is a background and every word sits on it in a dark shade. All text pairs below pass WCAG AA contrast (4.5:1), checked 2026-10-13.

| Token | Light | Dark | Used for | Contrast (light / dark) |
| --- | --- | --- | --- | --- |
| Background | #FFF5F8 blush | #1E1519 plum | Page |  |
| Surface | #FFFFFF | #2A1E24 | Product cards |  |
| Ink | #2E2129 | #F7EAF0 | Text, prices | 14.4 / 15.3 |
| Muted | #7D6672 | #B8A3AE | Timestamps, secondary text | 4.9 / 7.6 |
| Rose (accent) | #B02A62 | #FF9EC4 | Buttons, links, "cheapest" label | 6.3 on white / 9.3 |
| Soft pink | #FFE1EC | #4A2635 | Cheapest-store row, highlights | ink on it 12.6 |
| Candy pink | #F78FB3 | #F78FB3 | Logo, illustrations only, never text |  |
| Lavender | #ECE6FF, text #5B47A8 |  | Category and brand chips | 6.0 |
| Mint | #DDF5EA, text #1E7553 |  | In-stock badge | 4.9 |
| Peach | #FFE6D8, text #B0431A |  | Sale badge | 4.8 |

- **Type:** Pretendard for everything, a free Korean-designed font with full Latin, which fits the K-beauty feel. Check that ë and ç render cleanly; fall back to Inter if not. Rounded corners (16 px cards, pill buttons) match the soft palette.
- **Logo:** a lowercase wordmark in rose with a small candy-pink glass droplet with a white shine as the mark. Wordmark only at launch; refine it in Canva or with a designer later.
- **Photography:** product images come from the stores. No stock photos of faces.

UI rules:

1. Mobile first. Most shoppers arrive from Instagram on a phone.
2. The price is the hero. Cheapest in-stock store is always the first row, highlighted.
3. Every price shows its store and the time it was checked. No price without a timestamp.
4. Out of stock stays visible but greyed, so users learn where it's usually available.
5. No dark patterns: no fake urgency, no hidden sponsored rankings. Sponsored placements, if they ever exist, are labeled.

The prototype (site/index.html) still uses the older muted rose palette; switching it is a 10-line CSS change.

## Product scope

The MVP does one job well: find a product, see every store's price and stock, tap through to buy. Everything else waits until real users ask for it.

| Feature | Phase | Needs a live API? | Why this phase |
| --- | --- | --- | --- |
| Search by product or brand | MVP | No | The core job |
| Price + stock per store, cheapest highlighted | MVP | No | The core job |
| Sale price vs regular price | MVP | No | Already in the store feeds |
| Product pages with shareable URLs | MVP | No | Needed for Instagram sharing and Google |
| Brand and category browsing | MVP | No | Most users browse, not search |
| "Last checked" time on every price | MVP | No | Trust |
| Price history chart per product | Phase 2 | No | Needs weeks of collected data first |
| Price-drop and back-in-stock alerts by email | Phase 2 | Yes | First feature that needs user data |
| Click tracking per store | Phase 2 | Yes | Proof of traffic for store deals |
| Accounts, wishlists | Phase 3 | Yes | Only if alerts prove demand |
| Ingredient search, routines | Phase 3 | No | Different product; skip unless users ask |
| More stores | Ongoing | No | Each store is a small adapter |

Out of scope for now: selling products yourself, reviews, an app. Each one is a separate business.

## Architecture

No server runs between price updates. A scheduled GitHub Actions job runs the Python pipeline twice a day, generates the whole site as static pages, and pushes it to Cloudflare Pages. Cost: EUR 0 per month.

&#91;embedded content: architecture · launch path solid, Phase 2 dashed\]

At launch only the solid path exists: feeds in, static pages out. The dashed parts arrive in Phase 2 and are the first pieces that need a live API.

| Piece | Service | Free limit that matters | Our use |
| --- | --- | --- | --- |
| Code + scheduler | GitHub Actions | Private repo: 2,000 min/month; public repo: free ([GitHub](https://docs.github.com/en/billing/concepts/product-billing/github-actions)) | \~5 min x 2 runs x 30 days = \~300 min |
| Website hosting | Cloudflare Pages | 500 builds/month, 20,000 files per site ([Cloudflare](https://developers.cloudflare.com/pages/platform/limits)) | 60 deploys/month; one page per product, so watch the 20,000 file cap |
| Visitor traffic | Cloudflare static assets | Free and unlimited ([Cloudflare](https://developers.cloudflare.com/workers/platform/pricing/)) | All page views |
| Database (Phase 2) | Neon Postgres | 1 GB per project, scales to zero after 5 min idle ([Neon](https://neon.com/pricing)) | Price history; a twice-daily batch job doesn't mind cold starts |
| Live API (Phase 2) | FastAPI on Cloudflare Python Workers | 100,000 requests/day, 10 ms CPU per request | Alert sign-ups, click redirects |

**Why not Vercel:** its free Hobby plan is restricted to non-commercial use, and ads or affiliate-driven sites count as commercial ([Vercel](https://vercel.com/docs/limits/fair-use-guidelines)). Cloudflare's free plan has no such rule on that page, which suits a real business.

**Where FastAPI fits:** Cloudflare documents FastAPI support in Python Workers ([Cloudflare](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/)). The open risk is the 10 ms CPU limit per request on the free plan. Measure it with a test endpoint before building Phase 2 on it. If it doesn't fit, the fallback is a \~EUR 5 per month VPS, paid for once the site earns money.

**Why static first:** A few thousand products (an estimate until the first full run) refreshed twice a day is a batch problem, not a live one. Static pages also load fast on mobile and rank well on Google.

## Cloud dev environment

Everything lives on GitHub: code, the scheduled pipeline, and a browser-based dev environment (Codespaces), so you can work from any machine. Setup takes one evening.

GitHub Free includes 120 Codespaces compute hours and 15 GB-month of storage per month, counted at 2x on the default 2-core machine, so about 60 hours of real use ([GitHub](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces)). That covers evening work; stop the codespace when you're done.

Repo layout:

```
glassprice/
  pipeline/      fetchers, normalizer, matcher (today's kbeauty.py, split into modules)
  site/          templates + static assets; build output goes to dist/
  api/           FastAPI app (Phase 2)
  data/          overrides.json, brand list (committed); raw feeds are build artifacts
  tests/
  .devcontainer/ Python 3.12, rapidfuzz, ruff, pytest preinstalled
  .github/workflows/  ci.yml (tests on every push), update.yml (twice-daily refresh + deploy)
```

Setup steps:

- [ ] Create a private GitHub repo `glassprice`, push the current prototype
- [ ] Add `.devcontainer/devcontainer.json` and open the repo in a codespace
- [ ] Split `kbeauty.py` into `pipeline/` modules; keep the tests passing
- [ ] Add `ci.yml`: ruff + pytest on every push
- [ ] Create a Cloudflare account, a Pages project, and an API token scoped to Pages only
- [ ] Store the token and account id as GitHub Actions secrets (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`)
- [ ] Add `update.yml`: cron twice daily, run pipeline, build, deploy with Wrangler
- [ ] Buy the chosen .com on Cloudflare Registrar and attach it to the Pages project

Secrets never go in the repo. The store feeds are public, so the pipeline needs no store credentials.

## Data pipeline and matching

The pipeline already exists as the prototype: 4 store adapters, a normalizer, a fuzzy matcher with a version-token guard, and 12 passing tests. Going public adds a schedule, a quality gate and a weekly review.

1. **Fetch** each store's public JSON feed, 1 second between requests. A failing store falls back to its last good data and is flagged.
2. **Normalize** brand, volume, price and stock into one shape. The stores keep brand and volume in different places (title, `vendor`, `brands`, `price_html`, description).
3. **Match** within each brand: volumes must agree, version tokens (EX, V2, 0.1 vs 0.3) must agree, fuzzy score at least 85.
4. **Quality gate:** abort the deploy if any store returns under 50% of yesterday's product count, or if more than 10% of prices change. That catches a broken feed before it publishes wrong prices.
5. **Build** one page per product plus search, brand and category pages, then deploy.
6. **Store history** (Phase 2): append each run's prices to Neon, which feeds price charts and alerts.

**Schedule:** 07:00 and 19:00 Tirana time. Twice daily keeps stock reasonably fresh while staying polite to the stores.

**Weekly review, 30 minutes:** open `matches.csv`, check the lowest-scoring matches and the "no known brand" list, add fixes to `overrides.json` and new brands to the brand list. Wrong matches show wrong prices, so the matcher prefers missing a match over making a bad one.

**Adding a store:** a Shopify or WooCommerce store is one config line. Anything else needs a new adapter, roughly an evening.

## Business model

Traffic comes first; nothing below pays until a few thousand people use the site each month. Albania is a small market, so plan for a modest side income at first, not a salary.

| Revenue stream | Who pays | Needs first | When |
| --- | --- | --- | --- |
| Referral fee per sale or click | Stores | Click tracking showing traffic you send each store | Phase 2 |
| Price-monitoring reports | Stores, distributors | Price history data; you already collect every competitor's prices | Phase 2 to 3 |
| Featured placement, clearly labeled | Stores, brands | Steady traffic | Phase 3 |
| Newsletter or social sponsorships | Brands, distributors | An email or Instagram audience | Phase 3 |
| Display ads | Ad networks | Large traffic; low pay in Albania | Last resort |

The most interesting stream is **price-monitoring reports**. Every store wants to know competitors' prices and stock, and your pipeline produces exactly that as a side effect. Pitch it carefully: the same stores you compare may see you as a threat before they see you as a customer.

**Growth plan:** Instagram and TikTok content built from your own data, such as "cheapest COSRX snail essence this week" or "10 products on sale today". Each post links to the product page. The data makes the content for you, which is the advantage over a normal beauty account.

I'm not a financial advisor; treat these as options to validate, not forecasts.

## Legal and store relations

Talk to the four stores before the public launch, not after. They can't block public price data easily, but they can ban your crawler, and a store that likes you becomes your first paying customer.

- **Store terms:** read each store's terms of service for clauses on automated access before launch. Respect robots.txt on every site.
- **Product images:** the photos belong to the stores or brands. Ask permission in the outreach email; until then, link to images on the store's own servers rather than copying them.
- **Business registration:** once money comes in, you'll need to register as self-employed or a company with the national business center (QKB) and get a tax number (NIPT). Ask an accountant which form fits; I'm not a lawyer.
- **Personal data:** Phase 2 email alerts collect personal data, which Albania's data protection law regulates (aligned with GDPR). You'll need a privacy policy, explicit opt-in and one-click unsubscribe. Check current rules with the data protection commissioner (IDP).
- **Trademark:** search the chosen name in the Albanian industrial property office (DPPI) database before printing anything.

Outreach email, one per store: who you are, what the site does, that it sends them buyers, a link to the beta, and two asks: permission to use product images, and a contact for a future referral deal.

The tasks in Roadmap below track each of these.

## Roadmap

Public beta lands six weeks after kickoff, on Nov 30, assuming about 8 hours a week. Phase 2 (price history, alerts, click tracking) starts only after that.

&#91;embedded content: roadmap · 6 weeks to public beta, then Phase 2\]

Website work runs two weeks because it holds the brand, product pages and SEO; store outreach runs alongside it so replies arrive before the beta.

**Launch gate:** the public beta ships when all four stores refresh twice daily for 7 days straight, the quality gate has blocked no bad deploy, and 10 beta testers found no wrong price they could not report.

Week by week:

- [ ] Week 1: repo, codespace, CI, Cloudflare Pages, buy the domain
- [ ] Week 2: first full run on real data, tune the brand list and threshold, review matches.csv
- [ ] Weeks 3 to 4: product, search, brand and category pages; logo; Albanian copy
- [ ] Week 4: read the four stores' terms, send the outreach emails
- [ ] Week 5: quality gate, twice-daily deploys, private beta with 10 to 20 friends
- [ ] Week 6: fix what testers found, open Instagram and TikTok, first 5 posts
- [ ] Nov 30: public beta
- [ ] December: Neon price history, Python Workers test endpoint, then alerts

## Risks

The biggest risk is not technical: it's the plan growing faster than the product. The rest have cheap fixes.

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Scope grows (accounts, app, ingredient search) before the MVP ships | High | Never launches | Launch gate: nothing from Phase 2 starts until the beta is public |
| Wrong match shows a wrong price | Medium | Lost trust | Matcher prefers misses; weekly review; "report a wrong price" link on every product |
| A store blocks the crawler or changes its feed | Medium | Store missing | Outreach before launch; quality gate; last good data kept |
| Stale stock or price | Medium | Annoyed users | Twice-daily refresh; "last checked" on every price |
| Python Workers too slow for FastAPI on the free plan | Medium | Phase 2 needs a \~EUR 5/month VPS | Test endpoint before building Phase 2 |
| Cloudflare 20,000-file cap per site | Low | Deploys fail | Group small pages or move product pages to a Worker |
| Not enough traffic to monetize | Medium | Stays a portfolio project | Data-driven social content from week 1 of the beta |
| A store or brand objects to image use | Low | Takedown request | Ask permission in outreach; remove on request |

## Open decisions for Kiara

- [ ] Name decided: Glass Price. Buy getglassprice.com today, and ask a local registrar for a glassprice.al quote. Check @glassprice on Instagram and TikTok.
- [ ] Public or private repo? Public means unlimited free Actions minutes and a portfolio piece; private keeps the matcher away from copycats. Private fits the 2,000-minute quota.
- [ ] Site language: Albanian only, or Albanian with an English toggle? Albanian only is less work at launch.
- [ ] Contact the stores before the beta (recommended) or right after?
- [ ] Weekly time budget: the 6-week timeline assumes about 8 hours a week. Adjust it if that's wrong.

## Sources

Checked 2026-10-13.

- [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits)
- [Cloudflare Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- [FastAPI in Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/)
- [Neon pricing](https://neon.com/pricing)
- [Vercel fair use guidelines](https://vercel.com/docs/limits/fair-use-guidelines)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub Codespaces billing](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces)
- [Cloudflare Registrar pricing (vpsranking)](https://vpsranking.com/domain/cloudflare/)
- [Gandi .al domains](https://www.gandi.net/en/domain/tld/al)
- Domain availability: Verisign RDAP lookups for each .com in the Brand table
