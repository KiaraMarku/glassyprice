#!/usr/bin/env python3
"""
Multi-page static site generator for Glassyprice.

build_site(products, stores, updated, out_dir) writes:
    <out>/data.js            window.GP = {...} shared by every page (works from file://)
    <out>/assets/app.css     the Milky Mauve theme
    <out>/assets/app.js      shared nav, rendering, filtering
    <out>/index.html         landing page
    <out>/bestsellers.html   <out>/oferta.html
    <out>/<section>.html     fytyra, floket, trupi, makeup, dielli, parfume, sete
    <out>/problema-*.html    one page per skin concern
    <out>/marka.html         brand index (?b=slug filters to one brand)
    <out>/produkt.html       product detail (?p=<id>)
    <out>/kerko.html         search

Pages are flat files sharing one data.js + app.css + app.js, so the whole site
is a handful of tiny HTML files plus one data file. Double-click index.html to
preview offline, or deploy the folder to Cloudflare Pages unchanged.
"""
import json
import shutil
from pathlib import Path

BRAND_DIR = Path(__file__).parent / "brand"

# Albanian display labels. Keys must match kbeauty.classify().
SECTIONS = {
    "fytyra": "Fytyra", "floket": "Flokët", "trupi": "Trupi",
    "makeup": "Make Up", "parfume": "Parfume", "sete": "Sete",
}
AREAS = {"lekura": "Lëkura", "syte": "Sytë", "buzet": "Buzët"}
CONCERNS = {
    "akne": "Akne", "poret": "Poret & Yndyra", "rrudha": "Rrudha & Plakje",
    "njolla": "Njolla & Hiperpigmentim", "skuqje": "Skuqje & Ndjeshmëri", "hidratim": "Hidratim",
}
TYPES = {
    "pastrues": "Pastrues", "toner": "Toner", "serum": "Serum & Esencë",
    "hidratues": "Hidratues", "maske": "Maskë", "krem_dielli": "Krem Dielli",
    "trajtim": "Trajtim lokal",
}
# section-specific subcategories (keys must match kbeauty.KIND_KW)
HAIRKINDS = {"shampo": "Shampo", "balsam": "Balsam", "maske_floke": "Maskë & Trajtim",
             "vaj_floke": "Vaj & Serum", "stilues": "Stilues"}
BODYKINDS = {"krem_trupi": "Krem & Locion", "dush": "Dush & Larje", "scrub": "Scrub",
             "duar_kembe": "Duar & Këmbë"}
MAKEUPKINDS = {"mu_fytyre": "Fytyra", "mu_syte": "Sytë", "mu_buze": "Buzët"}

CSS = r""":root{
  color-scheme:light;      /* always light — ignore the OS dark preference */
  /* palette matched to the logo: aquamarine (logo #a2d8c6, hue ~162) + pastel pink on soft white */
  --bg:#fdf8f9; --card:#ffffff; --ink:#3a3137; --muted:#8c8187; --line:#efe6ea;
  --pink:#f4aeb9;          /* the literal logo pink — fills, buttons, highlights */
  --mint:#a2d8c6;          /* the literal logo mint */
  --accent:#c25570;        /* same-hue pink, used only for link/label text */
  --accent-soft:#fdebee;   /* cheapest row + active chips */
  --brand-mint:#86cbb8; --brand-pink:#ec97a6;    /* logo wordmark: glass / price */
  --pinkbadge:#fbe2e8; --pinkbadge-ink:#b23b5a;  /* sale / bestseller badge (pink) */
  --sage:#d6efe9; --sage-ink:#23705f;            /* in-stock badge (mint) */
  --no:#a79da2;
  --shadow:0 1px 2px rgba(59,46,53,.04), 0 6px 20px rgba(158,74,110,.06);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
h1,h2,h3,.logo{font-family:Fraunces,Georgia,"Times New Roman",serif;font-weight:600;letter-spacing:-.01em}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:auto;padding:20px 16px 48px}

/* header */
.nav{background:rgba(255,252,253,.8);-webkit-backdrop-filter:saturate(1.3) blur(14px);backdrop-filter:saturate(1.3) blur(14px);
  border-bottom:1px solid var(--line);box-shadow:0 2px 14px rgba(120,100,110,.06);position:sticky;top:0;z-index:20}
.nav-in{max-width:1120px;margin:auto;padding:14px 18px;display:flex;align-items:center;gap:22px;flex-wrap:wrap}
.logo{font-size:24px;color:var(--ink);display:flex;align-items:center;gap:9px;line-height:1;flex:none}
.logo:hover{text-decoration:none}
.logo-icon{width:32px;height:32px;flex:none}
.logo b{color:var(--brand-mint);font-weight:600}
.logo i{color:var(--brand-pink);font-weight:600;font-style:normal}
.nav-links{flex:1;display:flex;justify-content:center;gap:26px;flex-wrap:wrap}
.nav-links a{position:relative;color:var(--ink);font-family:Fraunces,Georgia,serif;font-size:16px;
  font-weight:500;padding:3px 1px;white-space:nowrap;text-decoration:none}
.nav-links a::after{content:"";position:absolute;left:0;right:0;bottom:-3px;height:2px;border-radius:2px;
  background:var(--pink);transform:scaleX(0);transition:transform .18s ease}
.nav-links a:hover{color:var(--accent);text-decoration:none}
.nav-links a:hover::after,.nav-links a.active::after{transform:scaleX(1)}
.nav-links a.active{color:var(--accent)}
/* search on the right of the header — light outlined pill, magnifier left */
.nav-search{flex:0 0 auto;position:relative;width:250px;max-width:40vw}
.nav-search .mag{position:absolute;left:15px;top:50%;transform:translateY(-50%);width:16px;height:16px;color:var(--muted);pointer-events:none}
.nav-search input{width:100%;padding:9px 16px 9px 40px;font-size:14px;border:1px solid var(--line);
  border-radius:999px;background:transparent;color:var(--ink);outline:none}
.nav-search input::placeholder{color:var(--muted)}
.nav-search input:focus{border-color:var(--pink)}
/* live-search dropdown */
.ac{position:absolute;top:calc(100% + 7px);left:0;right:0;background:#fff;border:1px solid var(--line);
  border-radius:16px;box-shadow:0 14px 38px rgba(120,100,110,.18);overflow:hidden;z-index:40;display:none;text-align:left}
.ac.open{display:block}
.ac a{display:flex;align-items:center;gap:11px;padding:9px 13px;color:var(--ink)}
.ac a:hover{background:var(--accent-soft);text-decoration:none}
.ac img{width:42px;height:42px;object-fit:cover;border-radius:9px;background:var(--line);flex:none}
.ac .meta{display:flex;flex-direction:column;min-width:0}
.ac .b{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--accent);font-weight:700}
.ac .n{font-size:13px;line-height:1.25;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ac .p{margin-left:auto;font-weight:700;white-space:nowrap;font-size:13px;font-variant-numeric:tabular-nums}
.ac .all{padding:11px 13px;font-size:13px;color:var(--accent);font-weight:600;border-top:1px solid var(--line)}
.ac .no{padding:14px 13px;color:var(--muted);font-size:13px}
/* phone header: row 1 = logo + search, row 2 = one swipeable line of links */
@media(max-width:760px){
  .nav-in{padding:10px 14px 0;gap:10px 12px;flex-wrap:wrap}
  .logo{font-size:20px;gap:7px}
  .logo-icon{width:26px;height:26px}
  .nav-search{order:2;flex:1 1 0;width:auto;max-width:none;min-width:0}
  .nav-search input{font-size:16px;padding:7px 12px 7px 34px}   /* 16px stops iOS zoom-on-focus */
  .nav-search .mag{left:12px;width:15px;height:15px}
  .nav-links{order:3;flex:0 0 calc(100% + 28px);margin:0 -14px;padding:2px 14px 9px;
    justify-content:flex-start;flex-wrap:nowrap;gap:20px;overflow-x:auto;
    -webkit-overflow-scrolling:touch;scrollbar-width:none}
  .nav-links::-webkit-scrollbar{display:none}
  .nav-links a{font-size:15px}
  .ac{position:fixed;top:56px;left:10px;right:10px}
}

/* hero — full-bleed gradient entrance */
.hero{position:relative;margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw);margin-top:-20px;min-height:78vh;overflow:hidden;
  display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:36px 22px 54px;
  background:linear-gradient(105deg,#fbe3ec 0%,#fdeef2 50%,#e3f5f0 100%)}
.hero-in{position:relative;z-index:2;width:100%;max-width:640px;margin:auto}
.hero-logo{display:block;margin:0 auto}
.hero-logo:hover{text-decoration:none}
.hero-logo-img{width:clamp(108px,13vw,150px);height:auto;display:block;margin:0 auto -2px}
.hero h1{font-size:clamp(26px,4.6vw,42px);margin:4px 0 12px;line-height:1.08}
.hero h1 em{font-style:italic;color:var(--accent);font-weight:600}
.hero p{color:var(--ink);opacity:.74;font-size:clamp(14px,1.8vw,17px);margin:0 auto 22px;max-width:480px}
/* glass-skin face cutout, top-left, soft bottom fade into the gradient */
.hero-face{position:absolute;top:62px;left:max(0px,1vw);z-index:1;pointer-events:none;
  width:clamp(230px,26vw,360px);height:auto;opacity:.92;
  -webkit-mask-image:radial-gradient(circle at 50% 44%,#000 36%,transparent 62%);
          mask-image:radial-gradient(circle at 50% 44%,#000 36%,transparent 62%)}
@media(max-width:1000px){.hero-face{display:none}}
.hero .search{position:relative;display:flex;align-items:center;max-width:600px;width:100%;margin:0 auto;background:#fff;
  border:1px solid var(--line);border-radius:999px;padding:6px 6px 6px 22px;box-shadow:0 8px 26px rgba(196,85,112,.13)}
.hero .search input{flex:1;min-width:0;border:none;outline:none;background:transparent;font-size:16px;padding:11px 0;color:var(--ink)}
.hero .search .mag{width:20px;height:20px;color:var(--muted);margin:0 14px;flex:none}
.hero .search .btn{flex:none;border:none;background:var(--accent);color:#fff;font-weight:600;font-size:15px;
  padding:12px 28px;border-radius:999px;cursor:pointer}
.hero .search .btn:hover{filter:brightness(1.05)}
/* hero decoration: the illustration cluster, edges feathered into the gradient */
.hero-deco{position:absolute;top:50%;right:max(6px,3vw);transform:translateY(-50%);
  width:clamp(250px,26vw,380px);z-index:1;pointer-events:none}
.hero-art{width:100%;height:auto;display:block}
@media(max-width:1000px){.hero-deco{display:none}}

/* category circles (real product photos, no boxes) */
.cats{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin:4px 0 6px}
.cat{display:flex;flex-direction:column;align-items:center;gap:10px;width:94px;color:var(--ink);text-align:center}
.cat:hover{text-decoration:none}
.cat .cat-img{width:86px;height:86px;border-radius:50%;background-size:cover;background-position:center;
  background-color:var(--accent-soft);box-shadow:0 4px 16px rgba(196,85,112,.12);
  outline:2px solid #fff;outline-offset:-2px;border:2px solid var(--line);transition:.14s}
.cat:hover .cat-img{border-color:var(--pink);transform:translateY(-3px)}
.cat .cat-ic{width:86px;height:86px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  background:var(--sage);color:var(--sage-ink);border:2px solid var(--line);
  box-shadow:0 4px 16px rgba(111,189,162,.18);transition:.14s}
.cat:hover .cat-ic{border-color:var(--mint);transform:translateY(-3px)}
.cat .cat-ic svg{width:38px;height:38px}
.cat .cat-t{font-size:13px;font-weight:600;line-height:1.2}

/* section headers */
.sec{margin:34px 0 14px;display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.sec h2{font-size:23px;margin:0}
.sec .more{margin-left:auto;font-size:14px}
.lead{color:var(--muted);margin:2px 0 0}

/* category page header — clean editorial, no gradient */
.pagehead{display:flex;align-items:center;gap:24px;margin:2px 0 22px;padding:2px 2px 20px;border-bottom:1px solid var(--line)}
.pagehead .ph-txt{flex:1;min-width:0}
.pagehead h1{margin:0 0 5px;font-size:clamp(26px,4.4vw,40px)}
.pagehead .ph-txt p{margin:0;color:var(--muted);font-size:15px}
.pagehead .ph-img{width:116px;height:116px;border-radius:50%;object-fit:cover;flex:none;
  border:4px solid #fff;box-shadow:0 10px 26px rgba(120,100,110,.16);outline:1px solid var(--line);outline-offset:-1px}
@media(max-width:560px){.pagehead .ph-img{width:86px;height:86px}}

/* filter panel — keep category selection clean */
.filters-panel{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px 18px;margin:0 0 20px}
.filters-panel .facet-group:last-child{margin-bottom:0}

/* tiles */
.tiles{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(148px,1fr))}
.tile{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 16px;
  display:flex;flex-direction:column;align-items:flex-start;gap:9px;color:var(--ink);box-shadow:var(--shadow);transition:.12s}
.tile:hover{text-decoration:none;border-color:var(--accent);transform:translateY(-2px)}
.tile .tic{width:40px;height:40px;color:var(--sage-ink);background:var(--sage);
  border-radius:12px;padding:8px;display:flex;align-items:center;justify-content:center}
.tile .tic svg{width:100%;height:100%}
.tile .t{font-weight:600;font-size:15px}
.tile .c{color:var(--muted);font-size:13px;margin-top:-5px}

/* brand list — simple pink links in columns */
.brandlist{column-width:188px;column-gap:30px;margin-top:2px}
.brandlink{display:block;padding:5px 0;color:var(--accent);font-size:15px;break-inside:avoid}
.brandlink:hover{text-decoration:underline}
.brandlink span{color:var(--muted);font-size:12px;margin-left:3px}

/* section heading icon */
.sec h2 .hic{width:22px;height:22px;color:var(--accent);vertical-align:-4px;margin-right:9px}

/* area sub-nav */
.subnav{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 20px}
.subnav a{padding:8px 15px;border-radius:999px;border:1px solid var(--line);background:var(--card);
  color:var(--ink);font-size:14px;display:inline-flex;align-items:center;gap:7px}
.subnav a:hover{border-color:var(--accent);text-decoration:none}
.subnav a.active{background:var(--pink);border-color:var(--pink);color:var(--ink);font-weight:600}
.subnav a svg{width:16px;height:16px}

/* toolbar + chips */
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:4px 0 16px}
.toolbar input[type=search]{flex:1;min-width:180px;padding:11px 14px;font-size:15px;
  border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--ink);outline:none}
.toolbar input[type=search]:focus{border-color:var(--accent)}
.chip{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;
  padding:7px 13px;font-size:13px;cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center}
.chip:hover{border-color:var(--accent)}
.chip svg{width:15px;height:15px;margin-right:6px}
.chip[aria-pressed=true]{background:var(--accent-soft);border-color:var(--accent);color:var(--accent);font-weight:600}
select.chip{appearance:none}
.facets{display:flex;gap:7px;flex-wrap:wrap;margin:0}
.facet-group{margin:0 0 12px}
.fg-label{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:700;margin:0 0 8px}
.count{color:var(--muted);font-size:13px;margin-left:auto}

/* product grid + cards */
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(280px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;
  display:flex;flex-direction:column;gap:11px;box-shadow:var(--shadow)}
.card:hover{border-color:var(--accent)}
.card .top{display:flex;gap:12px}
.card .top a.img{flex:none}
.card img{width:70px;height:70px;object-fit:cover;border-radius:12px;background:var(--line)}
.brand{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--accent);font-weight:700}
.name{font-weight:600;line-height:1.3}
.name a{color:var(--ink)}
.vol{color:var(--muted);font-size:13px;margin-top:2px}
.badges{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.badge{font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px}
.badge.stock{background:var(--sage);color:var(--sage-ink)}
.badge.sale{background:var(--pinkbadge);color:var(--pinkbadge-ink)}
.badge.best{background:var(--pinkbadge);color:var(--pinkbadge-ink)}
.offers{display:flex;flex-direction:column;gap:4px}
.offer{display:flex;align-items:center;gap:9px;padding:8px 10px;border-radius:11px;color:inherit;
  border:1px solid transparent}
.offer:hover{border-color:var(--line);text-decoration:none}
.offer.best{background:var(--accent-soft)}
.offer.out{color:var(--muted)}
.dot{width:8px;height:8px;border-radius:50%;flex:none;background:#6cc4ad}   /* in-stock dot: lighter logo aquamarine */
.offer.out .dot{background:var(--no)}
.store{flex:1;font-size:14px}
.tag{font-size:11px;font-weight:700;color:var(--accent);margin-left:5px}
.price{font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
.was{color:var(--muted);text-decoration:line-through;font-size:12px;margin-right:5px;font-weight:400}
.price.sale{color:var(--accent)}
.more-btn{grid-column:1/-1;justify-self:center;margin-top:8px}
.empty{grid-column:1/-1;text-align:center;color:var(--muted);padding:48px 0}

/* product detail */
.detail{display:grid;gap:26px;grid-template-columns:1fr;max-width:720px}
.detail .hero-img{width:100%;max-width:300px;aspect-ratio:1;object-fit:cover;border-radius:18px;
  background:var(--line);box-shadow:var(--shadow)}
.detail h1{font-size:28px;margin:8px 0 4px}
.detail .offers{margin-top:8px}
.detail .offer{padding:13px 15px;font-size:16px;border:1px solid var(--line)}
.save{background:var(--sage);color:var(--sage-ink);display:inline-block;padding:5px 12px;
  border-radius:999px;font-size:13px;font-weight:600;margin-top:10px}
.back{display:inline-block;margin-bottom:10px;font-size:14px}

/* footer */
footer{border-top:1px solid var(--line);background:var(--card)}
.foot-in{max-width:1080px;margin:auto;padding:22px 16px 34px;color:var(--muted);font-size:13px}
.foot-in a{color:var(--accent)}
.foot-in .tag-line{font-family:Fraunces,Georgia,serif;font-size:16px;color:var(--ink);margin-bottom:8px}
"""

JS = r"""(function(){
var GP = window.GP, S = GP.stores, L = GP.labels;
var SEC = L.sections, AR = L.areas, CON = L.concerns, TYP = L.types;
var HK = L.hairkinds, BK = L.bodykinds, MU = L.makeupkinds;
// facet specs on inline page scripts reference maps by name (they can't see these closure vars)
var MAPS = {sections:SEC, areas:AR, concerns:CON, types:TYP, hairkinds:HK, bodykinds:BK, makeupkinds:MU};
var PAGE = 48;

// line icons (stroke = currentColor)
var ICON = {
  fytyra:'<circle cx="12" cy="12" r="8"/><path d="M9.3 10h.01M14.7 10h.01M9 14c1.2 1.3 4.8 1.3 6 0"/>',
  floket:'<path d="M5 21c0-7 2-13 7-13s7 6 7 13"/><path d="M9 21c0-6 1-10 3-10s3 4 3 10"/>',
  trupi:'<circle cx="12" cy="5" r="2.3"/><path d="M7.5 22v-6l-1.8-1 1.8-5A3 3 0 0 1 10.3 8h3.4a3 3 0 0 1 2.8 2l1.8 5-1.8 1v6"/>',
  makeup:'<rect x="8.5" y="12" width="6.5" height="9" rx="1.4"/><path d="M9.6 12l.9-7 3 1-1 6"/>',
  parfume:'<rect x="8" y="9" width="8" height="12" rx="2"/><path d="M10 9V6h4v3"/><path d="M11 3h2v2h-2z"/>',
  sete:'<rect x="4" y="9" width="16" height="11" rx="1.3"/><path d="M4 13h16M12 9v11"/><path d="M12 9c-3 0-4.5-.6-4.5-2S9 5 12 9zM12 9c3 0 4.5-.6 4.5-2S15 5 12 9z"/>',
  lekura:'<circle cx="12" cy="12" r="7.5"/><path d="M12 8c1.5 1.6 2 2.6 2 4a2 2 0 1 1-4 0c0-1.4.5-2.4 2-4z"/>',
  syte:'<path d="M2.5 12S6.5 6 12 6s9.5 6 9.5 6-4 6-9.5 6-9.5-6-9.5-6z"/><circle cx="12" cy="12" r="2.6"/>',
  buzet:'<path d="M4 12s3-3 8-3 8 3 8 3-3 4-8 4-8-4-8-4z"/><path d="M4 12c2-2 5-2 8 0 3-2 6-2 8 0"/>',
  pastrues:'<rect x="7.5" y="9" width="9" height="12" rx="2"/><path d="M9.5 9V6h5v3"/><path d="M9.5 13h5"/>',
  toner:'<rect x="8" y="8" width="8" height="13" rx="2"/><path d="M10 8V5h4v3"/><path d="M8 12.5h8"/>',
  serum:'<rect x="9" y="11" width="6" height="10" rx="1.5"/><path d="M10 11V7.5h4V11"/><path d="M12 7.5V3"/>',
  hidratues:'<rect x="6" y="10" width="12" height="9" rx="2"/><path d="M6.5 10l1-3h9l1 3"/><path d="M9 7V5h6v2"/>',
  maske:'<path d="M12 3c5 0 7 3 7 7 0 5-3 11-7 11s-7-6-7-11c0-4 2-7 7-7z"/><path d="M9.3 10h.01M14.7 10h.01M9.5 15c1 .8 4 .8 5 0"/>',
  krem_dielli:'<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19"/>',
  trajtim:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>',
  antiage:'<path d="M7 3h10M7 21h10"/><path d="M8 3c0 4 8 5 8 9s-8 5-8 9"/><path d="M16 3c0 4-8 5-8 9s8 5 8 9"/>',
  akne:'<circle cx="12" cy="12" r="8"/><circle cx="14.3" cy="9.7" r="1.4"/>',
  poret:'<circle cx="8" cy="8" r="1.1"/><circle cx="14" cy="7" r="1.1"/><circle cx="17" cy="12" r="1.1"/><circle cx="11" cy="12" r="1.1"/><circle cx="7" cy="14" r="1.1"/><circle cx="14.5" cy="16" r="1.1"/>',
  rrudha:'<path d="M4 8c3-1 13-1 16 0M4 13c3-1 13-1 16 0M4 18c3-1 13-1 16 0"/>',
  njolla:'<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/>',
  skuqje:'<path d="M20 4C9 4 4 10 4 20c10 0 16-5 16-16z"/><path d="M4.5 19.5C8 14 12 11 18 9"/>',
  hidratim:'<path d="M12 3c4 6 7 9 7 12a7 7 0 1 1-14 0c0-3 3-6 7-12z"/><path d="M9 14.5a3 3 0 0 0 3 3"/>'
};
var IALIAS = {shampo:'pastrues',balsam:'hidratues',maske_floke:'maske',vaj_floke:'serum',stilues:'toner',
  krem_trupi:'hidratues',dush:'pastrues',scrub:'poret',duar_kembe:'trupi',
  mu_fytyre:'fytyra',mu_syte:'syte',mu_buze:'buzet'};
function icon(k){k=IALIAS[k]||k;return ICON[k]?'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+ICON[k]+'</svg>':'';}

// hero decoration: the hand-drawn skincare illustration cluster (brand/hero-art.png)
function heroDecoHTML(){
  return '<div class="hero-deco"><img class="hero-art" src="assets/hero-art.png" alt=""></div>';
}

function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function fold(s){return (s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();}
function fmt(n){return n==null?'':n.toLocaleString('sq-AL').replace(/[\s, ]/g,' ')+' L';}
function volfmt(v){return v?v.replace(/^([\d.]+)(\D+)$/,'$1 $2').replace('pcs','copë').replace('pairs','palë'):'';}
function slug(s){return fold(s).replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');}
function qp(k){return new URLSearchParams(location.search).get(k);}
function wordmark(){return '<span class="w"><b>glassy</b><i>price</i></span>';}

GP.products.forEach(function(p){
  var ins = p.offers.filter(function(o){return o.in_stock&&o.price!=null;});
  p._min = ins.length?Math.min.apply(null,ins.map(function(o){return o.price;})):Infinity;
  p._max = ins.length?Math.max.apply(null,ins.map(function(o){return o.price;})):0;
  p._save = ins.length>1?p._max-p._min:0;
  p._any = ins.length>0;
  p._disc = 0;
  p.offers.forEach(function(o){if(o.compare_at&&o.price){
    p._disc=Math.max(p._disc,Math.round((1-o.price/o.compare_at)*100));}});
  p._hay = fold([p.brand,p.name,p.volume,(p.sections||[]).join(' '),(p.concerns||[]).join(' ')].join(' '));
});

function offerHTML(o,best){
  var was = o.compare_at?'<span class="was">'+fmt(o.compare_at)+'</span>':'';
  return '<a class="offer '+(o.in_stock?'':'out')+' '+(best?'best':'')+'" href="'+esc(o.url)+
    '" target="_blank" rel="noopener"><span class="dot"></span><span class="store">'+
    esc(S[o.store]||o.store)+(best?'<span class="tag">më i lirë</span>':'')+
    (o.in_stock?'':' · mbaroi')+'</span><span class="price '+(o.compare_at?'sale':'')+'">'+
    was+fmt(o.price)+'</span></a>';
}
// hand-picked category photos (brand/photos/<key>.*) override product photos
var PH = GP.photos || {};
// first product (most popular, since data is pop-sorted) matching a test, with an image
function firstPhoto(testFn){var p=GP.products.find(function(x){return x.image&&testFn(x);});return p?p.image:'';}

// live-search dropdown: show matching products as you type, under a search form
function attachLiveSearch(form, input){
  if(!form||!input) return;
  var ac=document.createElement('div'); ac.className='ac'; form.appendChild(ac);
  function close(){ac.className='ac';}
  var t;
  function render(){
    var raw=input.value.trim(), q=fold(raw);
    if(q.length<2){close();return;}
    var terms=q.split(/\s+/).filter(Boolean);
    var r=GP.products.filter(function(p){return terms.every(function(w){return p._hay.indexOf(w)>=0;});});
    var top=r.slice(0,6).map(function(p){
      var img=p.image?'<img src="'+esc(p.image)+'" alt="">':'<img alt="">';
      var price=p._min<Infinity?'<span class="p">'+fmt(p._min)+'</span>':'';
      return '<a href="produkt.html?p='+p.i+'">'+img+'<span class="meta"><span class="b">'+esc(p.brand)+
        '</span><span class="n">'+esc(p.name)+'</span></span>'+price+'</a>';
    }).join('');
    ac.innerHTML = r.length
      ? top+'<a class="all" href="kerko.html?q='+encodeURIComponent(raw)+'">Shiko të gjitha '+r.length+' rezultatet →</a>'
      : '<div class="no">Asnjë produkt për “'+esc(raw)+'”.</div>';
    ac.className='ac open';
  }
  input.addEventListener('input',function(){clearTimeout(t);t=setTimeout(render,110);});
  input.addEventListener('focus',function(){if(input.value.trim().length>=2) render();});
  document.addEventListener('click',function(e){if(!form.contains(e.target)) close();});
  input.addEventListener('keydown',function(e){if(e.key==='Escape') close();});
}
function keyPhoto(key, testFn){return PH[key] || firstPhoto(testFn);}
function badges(p){
  var b='';
  if(p.best) b+='<span class="badge best">Bestseller</span>';
  if(p._disc>0) b+='<span class="badge sale">-'+p._disc+'%</span>';
  if(p._any) b+='<span class="badge stock">Në gjendje</span>';
  return b?'<div class="badges">'+b+'</div>':'';
}
function card(p){
  var offers = p.offers.map(function(o){
    return offerHTML(o, o.in_stock&&o.price===p._min&&p.offers.length>1);}).join('');
  var img = p.image?'<img loading="lazy" src="'+esc(p.image)+'" alt="">':'<img alt="">';
  var href = 'produkt.html?p='+p.i;
  return '<article class="card"><div class="top"><a class="img" href="'+href+'">'+img+'</a><div>'+
    '<div class="brand">'+esc(p.brand)+'</div><div class="name"><a href="'+href+'">'+esc(p.name)+'</a></div>'+
    (p.volume?'<div class="vol">'+esc(volfmt(p.volume))+'</div>':'')+badges(p)+'</div></div>'+
    '<div class="offers">'+offers+'</div></article>';
}

function grid(list, mount, shown){
  shown = shown||PAGE;
  if(!list.length){mount.innerHTML='<div class="grid"><div class="empty">Asnjë produkt nuk u gjet.</div></div>';return;}
  var html = '<div class="grid">'+list.slice(0,shown).map(card).join('');
  if(list.length>shown) html += '<button class="chip more-btn" id="more">Shfaq më shumë ('+(list.length-shown)+')</button>';
  html += '</div>';
  mount.innerHTML = html;
  var m = document.getElementById('more');
  if(m) m.onclick = function(){grid(list,mount,shown+PAGE);};
}

function sortList(list,how){
  list = list.slice();
  if(how==='cheap') list.sort(function(a,b){return a._min-b._min;});
  else if(how==='save') list.sort(function(a,b){return b._save-a._save;});
  else if(how==='disc') list.sort(function(a,b){return b._disc-a._disc;});
  // 'pop' (default): keep the data.js order, which Python sorted by popularity
  return list;
}

// a labelled group of filter chips, each with an icon
function facetGroup(g){
  var m = typeof g.map==='string' ? MAPS[g.map] : g.map;
  return '<div class="facet-group"><div class="fg-label">'+esc(g.label)+'</div>'+
    '<div class="facets" id="fg-'+g.id+'">'+Object.keys(m).map(function(k){
      return '<button class="chip" data-k="'+k+'">'+icon(k)+esc(m[k])+'</button>';
    }).join('')+'</div></div>';
}
function matchGroup(g, key, p){
  if(!key) return true;
  if(g.field==='type')    return p.type===key;
  if(g.field==='section') return (p.sections||[]).indexOf(key)>=0;
  if(g.field==='concern') return (p.concerns||[]).indexOf(key)>=0;
  if(g.field==='kind')    return (p.kinds||[]).indexOf(key)>=0;
  return true;
}

// ---- generic collection page ----
function collection(cfg){
  var app = document.getElementById('app');
  var base = GP.products.filter(cfg.filter||function(){return true;});
  var facets = cfg.facets||[];
  var st = {q:'', stock:false, multi:false, sort:cfg.sort||'pop', area:'', f:{}};
  facets.forEach(function(g){st.f[g.id]='';});

  var areaNav = '';
  if(cfg.area){
    areaNav = '<div class="subnav" id="fa"><a data-area="" class="active">Të gjitha</a>'+
      Object.keys(AR).map(function(k){
        return '<a data-area="'+k+'">'+icon(k)+esc(AR[k])+'</a>';}).join('')+'</div>';
  }
  var facetsHTML = facets.map(facetGroup).join('');
  var hasFilters = cfg.area || facets.length;

  var head;
  if(cfg.banner){
    var bimg = cfg.photoKey && PH[cfg.photoKey];
    if(!bimg){
      var pool = base.filter(function(p){return p.image && p._any;});       // prefer in-stock
      if(!pool.length) pool = base.filter(function(p){return p.image;});
      if(cfg.bannerSort==='disc') pool = pool.slice().sort(function(a,b){return b._disc-a._disc;});
      bimg = pool.length ? pool[0].image : '';
    }
    head = '<div class="pagehead"><div class="ph-txt"><h1>'+esc(cfg.heading)+'</h1>'+
      (cfg.lead?'<p>'+esc(cfg.lead)+'</p>':'')+'</div>'+
      (bimg?'<img class="ph-img" src="'+esc(bimg)+'" alt="">':'')+'</div>';
  } else {
    head = '<div class="sec"><h2>'+(cfg.icon?'<span class="hic">'+icon(cfg.icon)+'</span>':'')+esc(cfg.heading)+'</h2></div>'+
      (cfg.lead?'<p class="lead" style="margin-bottom:16px">'+esc(cfg.lead)+'</p>':'');
  }

  app.innerHTML = head + areaNav +
    (hasFilters?'<div class="filters-panel">'+facetsHTML+'</div>':'')+
    '<div class="toolbar">'+
      '<input type="search" id="q" placeholder="Kërko brenda kësaj faqeje…" autocomplete="off">'+
      '<button class="chip" id="fStock" aria-pressed="false">Vetëm në gjendje</button>'+
      '<button class="chip" id="fMulti" aria-pressed="false">Në 2+ dyqane</button>'+
      '<select class="chip" id="sort">'+
        '<option value="pop">Rendit: më të njohurat</option>'+
        '<option value="cheap">Rendit: çmimi më i ulët</option>'+
        '<option value="save">Rendit: diferenca më e madhe</option>'+
        '<option value="disc">Rendit: zbritja më e madhe</option>'+
      '</select><span class="count" id="count"></span></div>'+
    '<div id="list"></div>';
  document.getElementById('sort').value = st.sort;
  var list = document.getElementById('list');

  function run(){
    var terms = fold(st.q).split(/\s+/).filter(Boolean);
    var r = base.filter(function(p){
      return terms.every(function(t){return p._hay.indexOf(t)>=0;}) &&
        (!st.stock||p._any) && (!st.multi||p.offers.length>1) &&
        (!st.area||p.area===st.area) &&
        facets.every(function(g){return matchGroup(g, st.f[g.id], p);});
    });
    r = sortList(r, st.sort);
    document.getElementById('count').textContent = r.length+' produkte';
    grid(r, list);
  }
  var t;
  document.getElementById('q').addEventListener('input',function(e){
    clearTimeout(t);t=setTimeout(function(){st.q=e.target.value;run();},120);});
  document.getElementById('fStock').onclick=function(e){st.stock=!st.stock;e.target.setAttribute('aria-pressed',st.stock);run();};
  document.getElementById('fMulti').onclick=function(e){st.multi=!st.multi;e.target.setAttribute('aria-pressed',st.multi);run();};
  document.getElementById('sort').onchange=function(e){st.sort=e.target.value;run();};
  if(cfg.area) document.querySelectorAll('#fa a').forEach(function(b){
    b.onclick=function(){st.area=b.dataset.area;
      document.querySelectorAll('#fa a').forEach(function(x){x.className=(x===b?'active':'');});run();};});
  facets.forEach(function(g){
    document.querySelectorAll('#fg-'+g.id+' .chip').forEach(function(b){
      b.onclick=function(){var k=b.dataset.k;st.f[g.id]=st.f[g.id]===k?'':k;
        document.querySelectorAll('#fg-'+g.id+' .chip').forEach(function(x){x.setAttribute('aria-pressed',x===b&&!!st.f[g.id]);});
        run();};});
  });
  run();
}

// ---- landing ----
function landing(){
  var app = document.getElementById('app');
  var multi = GP.products.filter(function(p){return p.offers.length>1;});
  var drops = multi.filter(function(p){return p._disc>0&&p._any;}).sort(function(a,b){return b._disc-a._disc;}).slice(0,8);
  var best = GP.products.filter(function(p){return p.best;});
  best = (best.length?best:multi).slice(0,8);

  function circle(href, label, img){
    var bg = img?' style="background-image:url('+esc(img)+')"':'';
    return '<a class="cat" href="'+href+'"><span class="cat-img"'+bg+'></span>'+
      '<span class="cat-t">'+esc(label)+'</span></a>';
  }
  var catCircles = Object.keys(SEC).map(function(k){
    return circle(k+'.html', SEC[k], keyPhoto(k, function(x){return (x.sections||[]).indexOf(k)>=0;}));
  }).join('');
  var conCircles = Object.keys(CON).map(function(k){
    return circle('problema-'+k+'.html', CON[k], keyPhoto(k, function(x){return (x.concerns||[]).indexOf(k)>=0;}));
  }).join('');

  app.innerHTML =
    '<section class="hero">'+heroDecoHTML()+
    /* hero face hidden for now; to restore add back:
       '<img class="hero-face" src="assets/hero-face.png" alt="">'+ */
    '<div class="hero-in">'+
    '<a class="hero-logo" href="index.html"><img class="hero-logo-img" src="assets/logo-icon.png" alt="glassyprice"></a>'+
    '<h1>Çmime <em>transparente</em><br>për një lëkurë <em>transparente</em>.</h1>'+
    '<p>Krahaso çmimin dhe gjendjen e çdo produkti K-beauty në '+Object.keys(S).length+
    ' dyqanet shqiptare, në një faqe të vetme.</p>'+
    '<form class="search" onsubmit="location.href=\'kerko.html?q=\'+encodeURIComponent(this.q.value);return false;">'+
    '<input name="q" type="search" placeholder="Kërko produkt ose markë (p.sh. cosrx snail)">'+
    '<svg class="mag" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.2-4.2"/></svg>'+
    '<button class="btn" type="submit">Kërko</button></form></div></section>'+
    '<div class="sec"><h2>Blej sipas kategorisë</h2></div><div class="cats">'+catCircles+'</div>'+
    '<div class="sec"><h2>Zbritjet më të mëdha</h2><a class="more" href="oferta.html">Të gjitha ofertat →</a></div>'+
    '<div class="grid">'+drops.map(card).join('')+'</div>'+
    '<div class="sec"><h2>Bestsellers</h2><a class="more" href="bestsellers.html">Shiko të gjitha →</a></div>'+
    '<div class="grid">'+best.map(card).join('')+'</div>'+
    '<div class="sec"><h2>Blej sipas problemit</h2></div><div class="cats">'+conCircles+'</div>';
  attachLiveSearch(document.querySelector('.hero .search'), document.querySelector('.hero .search input'));
}

// ---- product detail ----
function product(){
  var app = document.getElementById('app');
  var p = GP.products[parseInt(qp('p'),10)];
  if(!p){app.innerHTML='<p class="empty">Produkti nuk u gjet. <a href="index.html">Kthehu në ballinë</a></p>';return;}
  var offers = p.offers.map(function(o){
    return offerHTML(o, o.in_stock&&o.price===p._min&&p.offers.length>1);}).join('');
  var chips = (p.sections||[]).map(function(k){return '<a class="chip" href="'+k+'.html">'+icon(k)+esc(SEC[k]||k)+'</a>';})
    .concat(p.type?['<a class="chip" href="kerko.html?q='+encodeURIComponent(TYP[p.type]||p.type)+'">'+icon(p.type)+esc(TYP[p.type])+'</a>']:[])
    .concat((p.concerns||[]).map(function(k){return '<a class="chip" href="problema-'+k+'.html">'+icon(k)+esc(CON[k]||k)+'</a>';})).join(' ');
  var save = p._save>0?'<span class="save">Kurse deri në '+fmt(p._save)+' duke blerë te më i liri</span>':'';
  document.title = p.name+' · Glassyprice';
  app.innerHTML =
    '<a class="back" href="javascript:history.length>1?history.back():location.href=\'index.html\'">← Kthehu</a>'+
    '<div class="detail"><div>'+(p.image?'<img class="hero-img" src="'+esc(p.image)+'" alt="">':'')+'</div>'+
    '<div><div class="brand">'+esc(p.brand)+'</div><h1>'+esc(p.name)+'</h1>'+
    (p.volume?'<div class="vol">'+esc(volfmt(p.volume))+'</div>':'')+
    '<div class="offers">'+offers+'</div>'+save+
    (chips?'<div class="facets" style="margin-top:18px">'+chips+'</div>':'')+
    '<p class="lead" style="margin-top:18px">Çmimet u kontrolluan së fundmi në kohën te fund i faqes. '+
    'Kliko dyqanin për të konfirmuar çmimin para blerjes.<br>'+
    '<a href="mailto:hello@getglassyprice.com?subject='+encodeURIComponent('Çmim i gabuar: '+p.name)+
    '">Raporto një çmim të gabuar</a></p></div></div>';
}

// ---- brand index / one brand ----
function brands(){
  var b = qp('b');
  if(b){
    collection({heading:'Marka: '+b.replace(/-/g,' ').replace(/\b\w/g,function(c){return c.toUpperCase();}),
      filter:function(p){return slug(p.brand)===b;}});
    return;
  }
  var app = document.getElementById('app');
  var cnt = {};
  GP.products.forEach(function(p){cnt[p.brand]=(cnt[p.brand]||0)+1;});
  var names = Object.keys(cnt).sort(function(a,b){return a.toLowerCase()<b.toLowerCase()?-1:1;});
  app.innerHTML =
    '<div class="sec"><h2>Markat</h2><span class="count" id="bcount"></span></div>'+
    '<div class="toolbar"><input type="search" id="bq" placeholder="Kërko markë…" autocomplete="off"></div>'+
    '<div class="brandlist" id="blist"></div>';
  var list = document.getElementById('blist'), q = document.getElementById('bq');
  function run(){
    var term = fold(q.value);
    var r = names.filter(function(n){return fold(n).indexOf(term)>=0;});
    document.getElementById('bcount').textContent = r.length+' marka';
    list.innerHTML = r.length ? r.map(function(n){
      return '<a class="brandlink" href="marka.html?b='+slug(n)+'">'+esc(n)+' <span>'+cnt[n]+'</span></a>';
    }).join('') : '<div class="empty">Asnjë markë nuk u gjet.</div>';
  }
  var t;
  q.addEventListener('input', function(){clearTimeout(t);t=setTimeout(run,100);});
  run();
}

// ---- search ----
function search(){
  collection({heading:'Kërko', filter:function(){return true;},
    facets:[{id:'sec',label:'Kategoria',map:SEC,field:'section'}]});
  var q = qp('q');
  if(q){var i=document.getElementById('q');i.value=q;i.dispatchEvent(new Event('input'));}
}

// ---- nav + footer on every page ----
document.getElementById('nav').className='nav';
document.getElementById('nav').innerHTML =
  '<div class="nav-in"><a class="logo" href="index.html">'+
  '<img class="logo-icon" src="assets/logo-icon.png" alt="">'+wordmark()+'</a>'+
  '<nav class="nav-links"><a href="fytyra.html">Fytyra</a><a href="floket.html">Flokët</a>'+
  '<a href="trupi.html">Trupi</a><a href="makeup.html">Make Up</a>'+
  '<a href="oferta.html">Oferta</a><a href="bestsellers.html">Bestsellers</a><a href="marka.html">Markat</a></nav>'+
  '<form class="nav-search" onsubmit="location.href=\'kerko.html?q=\'+encodeURIComponent(this.q.value);return false;">'+
  '<svg class="mag" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.2-4.2"/></svg>'+
  '<input name="q" type="search" placeholder="Kërko produkt ose markë"></form></div>';
// highlight the current page in the nav
var here = location.pathname.split('/').pop() || 'index.html';
document.querySelectorAll('.nav-links a').forEach(function(a){
  if(a.getAttribute('href')===here) a.className='active';
});
attachLiveSearch(document.querySelector('.nav-search'), document.querySelector('.nav-search input'));

var when = new Date(GP.updated);
document.getElementById('foot').innerHTML =
  '<div class="foot-in"><div class="tag-line">Çmime transparente për lëkurë si xhami.</div>'+
  'Çmimet merren automatikisht nga faqet e dyqaneve dhe mund të ndryshojnë. '+
  'Kontrolloni çmimin në dyqan para blerjes.<br>'+
  'Përditësuar: '+when.toLocaleString('sq-AL',{dateStyle:'medium',timeStyle:'short'})+
  ' · Pa reklama të fshehura, pa renditje sponsor të pashënuara.</div>';

window.gp = {collection:collection, landing:landing, product:product, brands:brands, search:search};
})();
"""

FONT_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&display=swap" rel="stylesheet">')

PAGE = """<!doctype html>
<html lang="sq">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@TITLE@</title>
<meta name="description" content="@DESC@">
@FONT@
<link rel="icon" href="assets/favicon.png">
<link rel="stylesheet" href="assets/app.css">
</head>
<body>
<header id="nav"></header>
<main id="app" class="wrap"></main>
<footer id="foot"></footer>
<script src="data.js"></script>
<script src="assets/app.js"></script>
<script>@INIT@</script>
</body>
</html>
"""


def _page(title, desc, init):
    return (PAGE.replace("@TITLE@", title).replace("@DESC@", desc)
            .replace("@FONT@", FONT_LINK).replace("@INIT@", init))


def build_site(products, stores, updated, out_dir):
    out = Path(out_dir)
    (out / "assets").mkdir(parents=True, exist_ok=True)

    # Optional hand-picked category/concern photos: drop files named by taxonomy
    # key (akne.jpg, fytyra.jpg, poret.png, …) into brand/photos/ and they are
    # used for that category's circle and page banner, overriding product photos.
    photos = {}
    photo_dir = BRAND_DIR / "photos"
    if photo_dir.exists():
        (out / "assets" / "photos").mkdir(parents=True, exist_ok=True)
        for f in sorted(photo_dir.iterdir()):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                shutil.copyfile(f, out / "assets" / "photos" / f.name)
                photos[f.stem] = "assets/photos/" + f.name

    payload = {
        "updated": updated,
        "stores": {s["id"]: s["name"] for s in stores},
        "labels": {"sections": SECTIONS, "areas": AREAS, "concerns": CONCERNS, "types": TYPES,
                   "hairkinds": HAIRKINDS, "bodykinds": BODYKINDS, "makeupkinds": MAKEUPKINDS},
        "photos": photos,
        "products": products,
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    (out / "data.js").write_text("window.GP=" + data + ";", encoding="utf-8")
    (out / "assets" / "app.css").write_text(CSS, encoding="utf-8")
    (out / "assets" / "app.js").write_text(JS, encoding="utf-8")
    for asset in ("logo.png", "logo-icon.png", "favicon.png", "hero-art.png", "hero-face.png"):
        src = BRAND_DIR / asset
        if src.exists():
            shutil.copyfile(src, out / "assets" / asset)

    # mixed pages filter by section; section pages show their own subcategories
    SEC_FACET = "facets:[{id:'sec',label:'Kategoria',map:'sections',field:'section'}]"
    SECTION_FACETS = {
        "fytyra": "area:true,facets:[{id:'typ',label:'Lloji',map:'types',field:'type'},"
                  "{id:'con',label:'Problematika',map:'concerns',field:'concern'}]",
        "floket": "facets:[{id:'k',label:'Lloji',map:'hairkinds',field:'kind'}]",
        "trupi":  "facets:[{id:'k',label:'Lloji',map:'bodykinds',field:'kind'}]",
        "makeup": "facets:[{id:'k',label:'Lloji',map:'makeupkinds',field:'kind'}]",
        "parfume": "facets:[]",
        "sete":   "facets:[]",
    }
    pages = {
        "index.html": ("Glassyprice · Krahaso çmimet K-beauty në Shqipëri",
                       "Krahaso çmimin dhe gjendjen e çdo produkti K-beauty në dyqanet shqiptare.", "gp.landing();"),
        "bestsellers.html": ("Bestsellers · Glassyprice", "Produktet K-beauty më të shitura.",
                             "gp.collection({heading:'Bestsellers',banner:true,photoKey:'bestsellers',lead:'Produktet më të kërkuara.',filter:function(p){return p.best;},%s});" % SEC_FACET),
        "oferta.html": ("Oferta · Glassyprice", "Produktet K-beauty me zbritje.",
                        "gp.collection({heading:'Oferta',banner:true,photoKey:'oferta',bannerSort:'disc',lead:'Produktet me zbritje, renditur nga zbritja më e madhe.',filter:function(p){return p.offers.some(function(o){return o.compare_at;});},sort:'disc',%s});" % SEC_FACET),
        "marka.html": ("Markat · Glassyprice", "Të gjitha markat K-beauty.", "gp.brands();"),
        "produkt.html": ("Produkt · Glassyprice", "Krahaso çmimet për këtë produkt.", "gp.product();"),
        "kerko.html": ("Kërko · Glassyprice", "Kërko produkte K-beauty.", "gp.search();"),
    }
    for key, label in SECTIONS.items():
        pages[f"{key}.html"] = (f"{label} · Glassyprice", f"Produkte K-beauty: {label}.",
                                "gp.collection({heading:%r,banner:true,photoKey:%r,%s,filter:function(p){return (p.sections||[]).indexOf(%r)>=0;}});" % (label, key, SECTION_FACETS[key], key))
    for key, label in CONCERNS.items():
        pages[f"problema-{key}.html"] = (f"{label} · Glassyprice", f"Produkte K-beauty për: {label}.",
                                         "gp.collection({heading:%r,banner:true,photoKey:%r,lead:'Produkte K-beauty për: %s.',filter:function(p){return (p.concerns||[]).indexOf(%r)>=0;},facets:[{id:'typ',label:'Lloji',map:'types',field:'type'}]});" % (label, key, label, key))

    for name, (title, desc, init) in pages.items():
        (out / name).write_text(_page(title, desc, init), encoding="utf-8")

    return len(pages)
