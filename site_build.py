#!/usr/bin/env python3
"""
Multi-page static site generator for Glass Price.

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
    "trajtim": "Trajtim (njolla/akne)",
}
# section-specific subcategories (keys must match kbeauty.KIND_KW)
HAIRKINDS = {"shampo": "Shampo", "balsam": "Balsam", "maske_floke": "Maskë & Trajtim",
             "vaj_floke": "Vaj & Serum", "stilues": "Stilues"}
BODYKINDS = {"krem_trupi": "Krem & Locion", "dush": "Dush & Larje", "scrub": "Scrub",
             "duar_kembe": "Duar & Këmbë"}
MAKEUPKINDS = {"mu_fytyre": "Fytyra", "mu_syte": "Sytë", "mu_buze": "Buzët"}

CSS = r""":root{
  color-scheme:light;      /* always light — ignore the OS dark preference */
  /* palette matched to the logo: mint green + pastel pink on soft white */
  --bg:#fdf8f9; --card:#ffffff; --ink:#3a3137; --muted:#8c8187; --line:#efe6ea;
  --pink:#f4aeb9;          /* the literal logo pink — fills, buttons, highlights */
  --mint:#a5d9c5;          /* the literal logo mint */
  --accent:#c25570;        /* same-hue pink, used only for link/label text */
  --accent-soft:#fdebee;   /* cheapest row + active chips */
  --brand-mint:#83c4aa; --brand-pink:#ec97a6;    /* logo wordmark: glass / price */
  --pinkbadge:#fbe2e8; --pinkbadge-ink:#b23b5a;  /* sale / bestseller badge (pink) */
  --sage:#d3ecdd; --sage-ink:#276b4d;            /* in-stock badge (mint) */
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

/* nav */
.nav{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}
.nav-in{max-width:1080px;margin:auto;padding:11px 16px;display:flex;align-items:center;gap:16px}
.logo{font-size:23px;color:var(--ink);display:flex;align-items:center;gap:9px;line-height:1}
.logo:hover{text-decoration:none}
.logo-icon{width:30px;height:30px;flex:none}
.logo b{color:var(--brand-mint);font-weight:600}
.logo i{color:var(--brand-pink);font-weight:600;font-style:normal}
.hero-logo{display:block;margin-bottom:6px}
.hero-logo:hover{text-decoration:none}
.hero-logo-img{width:240px;max-width:72vw;height:auto;display:block;margin:0 auto}
.nav-links{display:flex;gap:18px;flex-wrap:wrap;align-items:center}
.nav-links a{color:var(--ink);font-size:14.5px;text-decoration:underline;text-underline-offset:5px;
  text-decoration-thickness:1px;text-decoration-color:var(--line)}
.nav-links a:hover{color:var(--accent);text-decoration-color:var(--accent)}
/* search on the right of the header */
.nav-search{margin-left:auto;position:relative;flex:0 1 300px;min-width:190px}
.nav-search input{width:100%;padding:9px 46px 9px 16px;font-size:14px;border:1px solid var(--line);
  border-radius:999px;background:var(--bg);color:var(--ink);outline:none}
.nav-search input:focus{border-color:var(--pink);background:var(--card)}
.nav-search .go{position:absolute;right:4px;top:50%;transform:translateY(-50%);width:30px;height:30px;
  border-radius:50%;border:none;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer}
.nav-search .go svg{width:15px;height:15px}

/* hero */
.hero{position:relative;text-align:center;padding:50px 22px 46px;margin:6px 0 4px;border-radius:28px;
  background:radial-gradient(125% 135% at 50% 0,#fde3ea 0%,#e8f6ef 52%,#fdf8f9 100%);overflow:hidden}
.hero > *{position:relative;z-index:2}
.hero h1{font-size:clamp(31px,6vw,50px);margin:6px 0 12px;line-height:1.08}
.hero h1 em{font-style:italic;color:var(--accent)}
.hero p{color:var(--ink);opacity:.72;font-size:17px;margin:0 auto 24px;max-width:560px}
.hero .search{max-width:540px;margin:auto;display:flex;gap:8px}
.hero .search input{flex:1;min-width:0;padding:15px 20px;font-size:16px;border:1px solid var(--line);
  border-radius:999px;background:var(--card);color:var(--ink);outline:none;box-shadow:0 4px 18px rgba(196,85,112,.1)}
.hero .search input:focus{border-color:var(--pink)}
.hero .search .btn{flex:none;border:none;background:var(--accent);color:#fff;font-weight:700;font-size:15px;
  padding:0 24px;border-radius:999px;cursor:pointer;display:flex;align-items:center;gap:8px}
.hero .search .btn:hover{filter:brightness(1.05)}
/* decorative skincare illustrations */
.hero-deco{position:absolute;top:0;bottom:0;width:230px;z-index:1;pointer-events:none;opacity:.95}
.hero-deco svg{position:absolute}
.hero-deco-l{left:0}
.hero-deco-r{right:0}
@media(max-width:860px){.hero-deco{display:none}}

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

/* category page intro banner (real product photo) */
.pagehead{display:flex;align-items:center;gap:22px;border-radius:24px;margin:6px 0 20px;padding:26px 28px;
  background:linear-gradient(120deg,#eaf6f0 0%,#fde3ea 100%)}
.pagehead .ph-txt{flex:1;min-width:0}
.pagehead h1{margin:0 0 5px;font-size:clamp(25px,4.2vw,36px)}
.pagehead .ph-txt p{margin:0;color:var(--ink);opacity:.68;font-size:15px}
.pagehead .ph-img{width:116px;height:116px;border-radius:20px;object-fit:cover;background:#fff;
  box-shadow:0 6px 20px rgba(196,85,112,.14);flex:none}
@media(max-width:560px){.pagehead{padding:22px}.pagehead .ph-img{display:none}}

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
.dot{width:8px;height:8px;border-radius:50%;flex:none;background:var(--sage-ink)}
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

// decorative skincare illustrations for the hero (mint + pink line art)
var MINT='#86c7b0', PINK='#f4aeb9', MFILL='#e7f4ec', PFILL='#fde3ea';
function gDropper(st){return '<svg style="'+st+'" width="60" height="140" viewBox="0 0 60 140">'+
  '<rect x="22" y="6" width="16" height="30" rx="7" fill="'+PINK+'"/>'+
  '<rect x="24.5" y="34" width="11" height="9" fill="'+MFILL+'" stroke="'+MINT+'" stroke-width="2.5"/>'+
  '<rect x="13" y="43" width="34" height="90" rx="13" fill="'+MFILL+'" stroke="'+MINT+'" stroke-width="2.5"/>'+
  '<rect x="20" y="68" width="20" height="46" rx="4" fill="#fff" stroke="'+PINK+'" stroke-width="2"/></svg>';}
function gTube(st){return '<svg style="'+st+'" width="56" height="140" viewBox="0 0 56 140">'+
  '<rect x="20" y="6" width="16" height="16" rx="3" fill="'+MINT+'"/>'+
  '<rect x="14" y="22" width="28" height="110" rx="13" fill="'+PFILL+'" stroke="'+PINK+'" stroke-width="2.5"/>'+
  '<circle cx="28" cy="86" r="8.5" fill="none" stroke="'+PINK+'" stroke-width="2.5"/>'+
  '<g stroke="'+PINK+'" stroke-width="2.5" stroke-linecap="round">'+
  '<path d="M28 70v4M28 98v4M10 86h4M42 86h4M16 74l3 3M40 74l-3 3M16 98l3-3M40 98l-3-3"/></g></svg>';}
function gJar(st){return '<svg style="'+st+'" width="88" height="68" viewBox="0 0 88 68">'+
  '<rect x="16" y="26" width="56" height="38" rx="11" fill="'+MFILL+'" stroke="'+MINT+'" stroke-width="2.5"/>'+
  '<rect x="12" y="13" width="64" height="18" rx="9" fill="'+PINK+'"/></svg>';}
function gLeaf(st){return '<svg style="'+st+'" width="46" height="46" viewBox="0 0 46 46">'+
  '<path d="M40 6C16 6 6 16 6 40 30 40 40 30 40 6z" fill="#cdeadd" stroke="'+MINT+'" stroke-width="2"/>'+
  '<path d="M9 37C16 26 26 18 37 11" fill="none" stroke="'+MINT+'" stroke-width="2"/></svg>';}
var heroDeco =
  '<div class="hero-deco hero-deco-r">'+gDropper('top:20px;right:122px')+gTube('top:58px;right:30px')+
    gJar('top:196px;right:84px')+gLeaf('top:170px;right:12px')+'</div>'+
  '<div class="hero-deco hero-deco-l">'+gJar('top:42px;left:18px')+gTube('top:150px;left:30px')+
    gLeaf('top:34px;left:150px')+'</div>';

function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function fold(s){return (s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();}
function fmt(n){return n==null?'':n.toLocaleString('sq-AL').replace(/[\s, ]/g,' ')+' L';}
function volfmt(v){return v?v.replace(/^([\d.]+)(\D+)$/,'$1 $2').replace('pcs','copë').replace('pairs','palë'):'';}
function slug(s){return fold(s).replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');}
function qp(k){return new URLSearchParams(location.search).get(k);}
function wordmark(){return '<span class="w"><b>glass</b><i>price</i></span>';}

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
    var bimg = (cfg.photoKey&&PH[cfg.photoKey]) || firstPhoto(cfg.filter||function(){return true;});
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
    '<section class="hero">'+heroDeco+
    '<a class="hero-logo" href="index.html"><img class="hero-logo-img" src="assets/logo.png" alt="glassprice"></a>'+
    '<h1>Çmime <em>transparente</em><br>për lëkurë si <em>xhami</em>.</h1>'+
    '<p>Krahaso çmimin dhe gjendjen e çdo produkti K-beauty në '+Object.keys(S).length+
    ' dyqanet shqiptare — në një faqe të vetme.</p>'+
    '<form class="search" onsubmit="location.href=\'kerko.html?q=\'+encodeURIComponent(this.q.value);return false;">'+
    '<input name="q" type="search" placeholder="Kërko produkt ose markë (p.sh. cosrx snail)">'+
    '<button class="btn" type="submit"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.2-4.2"/></svg>Kërko</button></form></section>'+
    '<div class="sec"><h2>Blej sipas kategorisë</h2></div><div class="cats">'+catCircles+'</div>'+
    '<div class="sec"><h2>Zbritjet më të mëdha</h2><a class="more" href="oferta.html">Të gjitha ofertat →</a></div>'+
    '<div class="grid">'+drops.map(card).join('')+'</div>'+
    '<div class="sec"><h2>Bestsellers</h2><a class="more" href="bestsellers.html">Shiko të gjitha →</a></div>'+
    '<div class="grid">'+best.map(card).join('')+'</div>'+
    '<div class="sec"><h2>Blej sipas problemit</h2></div><div class="cats">'+conCircles+'</div>';
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
  document.title = p.name+' · Glass Price';
  app.innerHTML =
    '<a class="back" href="javascript:history.length>1?history.back():location.href=\'index.html\'">← Kthehu</a>'+
    '<div class="detail"><div>'+(p.image?'<img class="hero-img" src="'+esc(p.image)+'" alt="">':'')+'</div>'+
    '<div><div class="brand">'+esc(p.brand)+'</div><h1>'+esc(p.name)+'</h1>'+
    (p.volume?'<div class="vol">'+esc(volfmt(p.volume))+'</div>':'')+
    '<div class="offers">'+offers+'</div>'+save+
    (chips?'<div class="facets" style="margin-top:18px">'+chips+'</div>':'')+
    '<p class="lead" style="margin-top:18px">Çmimet u kontrolluan së fundmi në kohën te fund i faqes. '+
    'Kliko dyqanin për të konfirmuar çmimin para blerjes.<br>'+
    '<a href="mailto:hello@getglassprice.com?subject='+encodeURIComponent('Çmim i gabuar: '+p.name)+
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
  app.innerHTML = '<div class="sec"><h2>Markat</h2><span class="count">'+names.length+' marka</span></div>'+
    '<div class="tiles">'+names.map(function(n){
      return '<a class="tile" href="marka.html?b='+slug(n)+'"><div class="t">'+esc(n)+'</div>'+
        '<div class="c">'+cnt[n]+' produkte</div></a>';}).join('')+'</div>';
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
  '<input name="q" type="search" placeholder="Kërko… (p.sh. Cosrx, Pyunkang Yul)">'+
  '<button class="go" type="submit" aria-label="Kërko"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.2-4.2"/></svg></button></form></div>';

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
    for asset in ("logo.png", "logo-icon.png", "favicon.png"):
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
        "index.html": ("Glass Price — Krahaso çmimet K-beauty në Shqipëri",
                       "Krahaso çmimin dhe gjendjen e çdo produkti K-beauty në dyqanet shqiptare.", "gp.landing();"),
        "bestsellers.html": ("Bestsellers · Glass Price", "Produktet K-beauty më të shitura.",
                             "gp.collection({heading:'Bestsellers',banner:true,lead:'Produktet më të kërkuara.',filter:function(p){return p.best;},%s});" % SEC_FACET),
        "oferta.html": ("Oferta · Glass Price", "Produktet K-beauty me zbritje.",
                        "gp.collection({heading:'Oferta',banner:true,lead:'Produktet me zbritje, renditur nga zbritja më e madhe.',filter:function(p){return p.offers.some(function(o){return o.compare_at;});},sort:'disc',%s});" % SEC_FACET),
        "marka.html": ("Markat · Glass Price", "Të gjitha markat K-beauty.", "gp.brands();"),
        "produkt.html": ("Produkt · Glass Price", "Krahaso çmimet për këtë produkt.", "gp.product();"),
        "kerko.html": ("Kërko · Glass Price", "Kërko produkte K-beauty.", "gp.search();"),
    }
    for key, label in SECTIONS.items():
        pages[f"{key}.html"] = (f"{label} · Glass Price", f"Produkte K-beauty: {label}.",
                                "gp.collection({heading:%r,banner:true,photoKey:%r,%s,filter:function(p){return (p.sections||[]).indexOf(%r)>=0;}});" % (label, key, SECTION_FACETS[key], key))
    for key, label in CONCERNS.items():
        pages[f"problema-{key}.html"] = (f"{label} · Glass Price", f"Produkte K-beauty për: {label}.",
                                         "gp.collection({heading:%r,banner:true,photoKey:%r,lead:'Produkte K-beauty për: %s.',filter:function(p){return (p.concerns||[]).indexOf(%r)>=0;},facets:[{id:'typ',label:'Lloji',map:'types',field:'type'}]});" % (label, key, label, key))

    for name, (title, desc, init) in pages.items():
        (out / name).write_text(_page(title, desc, init), encoding="utf-8")

    return len(pages)
