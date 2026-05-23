#!/usr/bin/env python3
"""Builds the two pages of the procurement map app:

- index.html       — authority-centric view (current map)
- operatori.html   — operator-centric view (search + profile)

Both pages share:
- the same top navigation bar
- the same dark-navy editorial style
- the embedded regions GeoJSON and places lookup (small static data)
- they fetch their large dataset (sas.json.gz / operators.json.gz)
  from /data/ on load via DecompressionStream

This split means the HTML files stay tiny (~2 MB each) and the heavy
data files are cached by the browser across page switches.
"""
import json, os, gzip

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS_PATH = os.path.join(HERE, 'raw', 'italy_regions.geojson')
PLACES_PATH = os.path.join(HERE, 'raw', 'italia_places.json')
SAS_GZ_PATH = os.path.join(HERE, 'data', 'sas.json.gz')

with open(REGIONS_PATH, encoding='utf-8') as f:
    REGIONS = json.load(f)
with open(PLACES_PATH, encoding='utf-8') as f:
    PLACES = json.load(f)

# Read meta out of the gzipped sas data (no need for a separate uncompressed copy)
with open(SAS_GZ_PATH, 'rb') as f:
    META_ONLY = json.loads(gzip.decompress(f.read()).decode('utf-8'))['meta']

REGIONS_JSON = json.dumps(REGIONS, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
PLACES_JSON = json.dumps(PLACES, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')

# Shared CSS + nav block
SHARED_HEAD = r"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" crossorigin="">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" crossorigin="">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Fraunces:ital,opsz,wght@1,9..144,400;1,9..144,500;1,9..144,600&display=swap">
<style>
  :root {
    --bg:           #0a1628;
    --bg-elev:      #11213d;
    --bg-card:      #16294a;
    --bg-hover:     #1c3358;
    --border:       rgba(255,255,255,0.06);
    --border-mid:   rgba(255,255,255,0.12);
    --border-dash:  rgba(255,255,255,0.18);
    --text:         #e6ecf5;
    --text-muted:   #8da0bd;
    --text-dim:     #5a6b85;
    --accent:       #6e9ddf;
    --accent-strong:#88b3ee;
    --accent-soft:  rgba(110,157,223,0.13);
    --navy-fill:    #1e3a5f;
    --amber:        #d4a574;
  }
  * { box-sizing: border-box; }
  html, body {
    margin:0; padding:0; height:100%;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    color: var(--text); background: var(--bg);
    font-weight: 400; font-size: 14px; line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
  }

  header.topbar {
    padding: 18px 28px 14px;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 18px;
  }
  header .nav { grid-column: 1; display: flex; gap: 4px; align-items: center; }
  header .nav a {
    display: inline-block;
    padding: 7px 14px;
    border-radius: 999px;
    font-size: 12px;
    color: var(--text-muted);
    text-decoration: none;
    text-transform: lowercase;
    letter-spacing: 0.02em;
    transition: background 0.15s, color 0.15s;
  }
  header .nav a:hover { background: var(--bg-card); color: var(--text); }
  header .nav a.active {
    background: var(--accent-soft);
    color: var(--accent-strong);
    font-weight: 500;
  }
  header .brand { grid-column: 2; text-align: center; }
  header h1 {
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic;
    font-weight: 500;
    font-size: 22px;
    color: var(--text);
    letter-spacing: 0.005em;
    margin: 0;
    text-transform: lowercase;
  }
  header .sub {
    font-size: 10.5px;
    color: var(--text-dim);
    text-transform: lowercase;
    letter-spacing: 0.08em;
    margin-top: 3px;
  }
  header .badge {
    font-family: 'Inter', sans-serif;
    background: transparent;
    border: 1px solid var(--amber);
    color: var(--amber);
    padding: 1px 7px;
    border-radius: 999px;
    font-size: 9px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-left: 6px;
  }
  header .controls {
    grid-column: 3;
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    align-items: center;
    flex-wrap: wrap;
  }
  .pill-select, select.pill {
    appearance: none; -webkit-appearance: none;
    background: var(--bg-card);
    border: 1px solid var(--border-mid);
    border-radius: 999px;
    color: var(--text);
    padding: 8px 32px 8px 16px;
    font-size: 12px;
    font-family: inherit;
    text-transform: lowercase;
    letter-spacing: 0.02em;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='%238da0bd' d='M0 0l5 6 5-6z'/></svg>");
    background-repeat: no-repeat;
    background-position: right 14px center;
  }
  .pill-select:hover, select.pill:hover { background-color: var(--bg-hover); border-color: var(--border-dash); }
  .pill-select:focus, select.pill:focus { outline: none; border-color: var(--accent); }
  .toggle {
    display: inline-flex;
    background: var(--bg-card);
    border: 1px solid var(--border-mid);
    border-radius: 999px;
    padding: 3px;
    gap: 2px;
  }
  .toggle button {
    background: transparent;
    color: var(--text-muted);
    padding: 5px 14px;
    border: 0;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    border-radius: 999px;
    text-transform: lowercase;
    letter-spacing: 0.02em;
    transition: background 0.15s, color 0.15s;
  }
  .toggle button:hover { color: var(--text); }
  .toggle button.active {
    background: var(--accent-soft);
    color: var(--accent-strong);
    font-weight: 500;
  }

  /* loading state */
  .loading {
    position: fixed; inset: 0;
    display: flex; align-items: center; justify-content: center;
    background: var(--bg);
    z-index: 9999;
    transition: opacity 0.3s;
    color: var(--text-muted);
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic;
    font-size: 16px;
    letter-spacing: 0.03em;
  }
  .loading.gone { opacity: 0; pointer-events: none; }

  /* Map styling — shared between pages */
  #map, .mini-map { background: var(--bg) !important; }
  .leaflet-container { background: var(--bg) !important; outline: none; font-family: inherit; }
  .leaflet-control-zoom {
    border: 1px solid var(--border-mid) !important;
    border-radius: 12px !important;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }
  .leaflet-control-zoom a {
    background: var(--bg-card) !important;
    color: var(--text-muted) !important;
    border-bottom: 1px solid var(--border) !important;
    width: 32px !important; height: 32px !important;
    line-height: 32px !important;
    font-size: 16px !important;
    font-weight: 300 !important;
  }
  .leaflet-control-zoom a:hover { background: var(--bg-hover) !important; color: var(--text) !important; }
  .region-label {
    background: transparent !important; border: 0 !important; box-shadow: none !important;
    color: var(--text-muted); opacity: 0.7;
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic; font-weight: 400;
    font-size: 14px; letter-spacing: 0.01em;
    text-shadow: 0 1px 3px rgba(0,0,0,0.45);
    pointer-events: none; white-space: nowrap;
    text-transform: lowercase;
  }
  .region-label::before { display:none !important; }
  .place-label, .place-label-cap {
    background: transparent !important; border: 0 !important; box-shadow: none !important;
    font-family: 'Inter', sans-serif;
    color: var(--text);
    text-shadow: 0 0 3px rgba(10,22,40,0.95), 0 1px 2px rgba(10,22,40,0.9);
    pointer-events: none; white-space: nowrap;
    text-transform: lowercase; letter-spacing: 0.02em;
  }
  .place-label-cap { font-size: 12px; font-weight: 500; opacity: 0.92; }
  .place-label { font-size: 10px; font-weight: 400; opacity: 0.7; color: var(--text-muted); }
  .place-label::before, .place-label-cap::before { display:none !important; }
  .sa-cluster {
    background: rgba(230,236,245,0.96);
    border: 1px solid rgba(10,22,40,0.5);
    border-radius: 50%;
    color: #0a1628;
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.35);
  }
  .sa-cluster > div { width:100%; height:100%; display:flex; align-items:center; justify-content:center; }
  .sa-cluster span { font-size: 12px; }

  /* Popups — shared */
  .leaflet-popup-content-wrapper {
    background: var(--bg-elev) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-mid) !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
    padding: 4px !important;
  }
  .leaflet-popup-tip { background: var(--bg-elev) !important; border: 1px solid var(--border-mid) !important; }
  .leaflet-popup-close-button { color: var(--text-muted) !important; font-size: 20px !important; padding: 6px 8px 0 0 !important; }
  .leaflet-popup-close-button:hover { color: var(--text) !important; background: transparent !important; }
  .leaflet-popup-content { margin: 14px 18px !important; line-height: 1.45 !important; }

  /* footer — shared */
  footer {
    padding: 10px 22px;
    background: var(--bg);
    border-top: 1px solid var(--border);
    font-size: 10.5px;
    color: var(--text-dim);
    text-transform: lowercase;
    letter-spacing: 0.04em;
    text-align: center;
  }
  footer a { color: var(--text-muted); text-decoration: none; border-bottom: 1px solid var(--border-mid); }
  footer a:hover { color: var(--text); border-bottom-color: var(--text-muted); }
  footer strong { color: var(--text-muted); font-weight: 500; }
  footer code { font-family: 'SF Mono', 'Monaco', monospace; color: var(--text-muted); font-size: 10px; }
"""

# --------- PAGE 1: AUTHORITY VIEW (index.html) ---------
INDEX_STYLE_EXTRA = r"""
  main.split { display:flex; height: calc(100vh - 76px - 38px); }
  #map { flex: 1 1 auto; height: 100%; }
  aside {
    width: 360px; height: 100%; overflow-y: auto;
    background: var(--bg);
    border-left: 1px solid var(--border);
    padding: 22px 22px 30px;
    font-size: 13px;
  }
  aside::-webkit-scrollbar { width: 8px; }
  aside::-webkit-scrollbar-track { background: transparent; }
  aside::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 4px; }
  aside h2 {
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic; font-weight: 400;
    font-size: 11px; margin: 0 0 10px 0;
    color: var(--text-muted);
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }
  .card { background: var(--bg-elev); border: 1px solid var(--border); border-radius: 14px; padding: 14px 16px; margin-bottom: 14px; }
  .stat { display:flex; justify-content:space-between; align-items:baseline; padding:7px 0; border-bottom: 1px solid var(--border); font-size: 12.5px; color: var(--text-muted); text-transform: lowercase; }
  .stat:last-child { border-bottom: 0; padding-bottom: 0; }
  .stat strong { color: var(--text); font-variant-numeric: tabular-nums; font-weight: 500; text-transform: none; }
  details summary {
    cursor: pointer;
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic; font-weight: 500;
    color: var(--accent-strong);
    font-size: 14px;
    text-transform: lowercase;
    list-style: none;
    padding: 4px 0;
  }
  details summary::-webkit-details-marker { display: none; }
  details summary::before { content: '▸  '; color: var(--text-dim); display: inline-block; }
  details[open] summary::before { content: '▾  '; }
  details .body { font-size: 12.5px; line-height: 1.6; color: var(--text-muted); margin-top: 8px; }
  details .body p { margin: 8px 0; }
  details .body strong { color: var(--text); font-weight: 500; }
  details .body em { color: var(--text); font-style: italic; }
  details .body code { background: var(--bg-card); color: var(--accent-strong); padding: 1px 5px; border-radius: 4px; font-size: 11px; font-family: 'SF Mono', monospace; }

  .popup { font-size:12.5px; min-width: 280px; }
  .popup h3 {
    margin: 0 0 4px;
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic; font-weight: 500;
    font-size: 16px; color: var(--text);
    text-transform: lowercase; line-height: 1.25;
  }
  .popup .meta { color: var(--text-dim); font-size: 11px; margin-bottom: 10px; text-transform: lowercase; letter-spacing: 0.02em; }
  .popup .meta em { color: var(--accent); font-style: italic; }
  .popup .tot { display:flex; justify-content:space-between; align-items:baseline; padding:5px 0; border-bottom: 1px solid var(--border); font-size: 12px; color: var(--text-muted); text-transform: lowercase; }
  .popup .tot strong { color: var(--text); font-weight: 500; font-variant-numeric: tabular-nums; }
  .popup .section-label { margin-top: 10px; font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.18em; font-family: 'Fraunces', Georgia, serif; font-style: italic; font-weight: 400; }
  .popup ol { padding-left: 0; margin: 6px 0; list-style: none; counter-reset: opc; }
  .popup ol li { counter-increment: opc; padding: 6px 0 7px; line-height: 1.35; border-bottom: 1px solid var(--border); position: relative; padding-left: 22px; }
  .popup ol li:last-child { border-bottom: 0; }
  .popup ol li::before { content: counter(opc); position: absolute; left: 0; top: 7px; color: var(--text-dim); font-size: 10px; font-variant-numeric: tabular-nums; }
  .popup .opname { color: var(--text); font-size: 12px; }
  .popup .opname a { color: var(--accent-strong); text-decoration: none; border-bottom: 1px dotted var(--border-mid); }
  .popup .opname a:hover { border-bottom-color: var(--accent); }
  .popup .opmeta { color: var(--text-dim); font-size: 10.5px; display: block; font-variant-numeric: tabular-nums; margin-top: 2px; }
  .popup .pill { display:inline-block; background: var(--accent-soft); color: var(--accent-strong); font-size: 9px; padding: 1px 7px; border-radius: 999px; margin-left: 4px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500; vertical-align: middle; }
  .popup .pill.rti { background: rgba(212,165,116,0.15); color: var(--amber); }
  .popup .pill.ih { background: var(--accent-soft); color: var(--accent-strong); }
  .popup .conc { display:flex; justify-content:space-between; align-items:baseline; padding: 5px 0; font-size: 11px; color: var(--text-muted); text-transform: lowercase; }
  .popup .conc strong { color: var(--text); font-variant-numeric: tabular-nums; font-weight: 500; }
  .popup .ih-note { background: var(--accent-soft); color: var(--accent-strong); padding: 8px 10px; border-radius: 8px; margin-top: 8px; font-size: 11px; line-height: 1.4; }
  .note { background: transparent; border: 1px dashed var(--border-dash); color: var(--text-muted); padding: 12px 14px; border-radius: 12px; font-size: 11.5px; line-height: 1.55; margin-bottom: 14px; text-transform: lowercase; letter-spacing: 0.01em; }
  .note strong { color: var(--text); font-weight: 500; text-transform: none; }
"""

INDEX_HTML = r"""<!doctype html>
<html lang="it">
<head>
__SHARED_HEAD__
__INDEX_STYLE_EXTRA__
</style>
<title>mappa appalti — stazioni appaltanti</title>
</head>
<body>
<div class="loading" id="loading">caricamento dati…</div>
<header class="topbar">
  <nav class="nav">
    <a href="./" class="active">stazioni appaltanti</a>
    <a href="operatori.html">operatori</a>
  </nav>
  <div class="brand">
    <h1>mappa appalti pubblici — italia</h1>
    <div class="sub">2024 · valori annualizzati · fonte anac<span class="badge">campione 1 anno</span></div>
  </div>
  <div class="controls">
    <select id="cat-select" class="pill"></select>
    <div class="toggle" id="metric-toggle">
      <button data-m="v" class="active">per valore</button>
      <button data-m="c">per numero</button>
    </div>
  </div>
</header>
<main class="split">
  <div id="map"></div>
  <aside id="sidebar">
    <div id="meta-info"></div>
    <div id="stats"></div>
    <details open>
      <summary>metodologia</summary>
      <div class="body" id="metodologia"></div>
    </details>
  </aside>
</main>
<footer>
  fonte dati: <strong>anac — banca dati nazionale dei contratti pubblici</strong> · dataset: <code>aggiudicazioni</code>, <code>aggiudicatari</code>, <code>cig-2024</code>, <code>stazioni-appaltanti</code> · fetch __FETCHED__ · finestra __WINDOW__ · geocoding istat via opendatasicilia/comuni-italiani · mappa <a href="https://leafletjs.com">leaflet</a>
</footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js" crossorigin=""></script>
<script id="regionsdata" type="application/json">__REGIONS__</script>
<script id="placesdata" type="application/json">__PLACES__</script>
<script>
async function loadGz(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('Fetch ' + url + ': ' + resp.status);
  const ds = new DecompressionStream('gzip');
  const stream = resp.body.pipeThrough(ds);
  const text = await new Response(stream).text();
  return JSON.parse(text);
}

(async function(){
  const DATA = await loadGz('data/sas.json.gz');
  document.getElementById('loading').classList.add('gone');
  const CPV = DATA.cpv_divs;
  const SAS = DATA.sas;
  const META = DATA.meta;

  const itf = new Intl.NumberFormat('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const itf0 = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 0 });
  function eur(n){ return '€ ' + itf.format(n); }
  function eurShort(n){
    if (n>=1e9) return '€ ' + (n/1e9).toFixed(2).replace('.',',') + ' mld';
    if (n>=1e6) return '€ ' + (n/1e6).toFixed(2).replace('.',',') + ' mln';
    if (n>=1e3) return '€ ' + (n/1e3).toFixed(1).replace('.',',') + ' k';
    return eur(n);
  }
  function pct(x){ return (x*100).toFixed(1).replace('.',',') + '%'; }
  function esc(s){ return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]); }

  const sel = document.getElementById('cat-select');
  function addOpt(v,l){ const o=document.createElement('option'); o.value=v; o.textContent=l; sel.appendChild(o); }
  addOpt('ALL','tutte le categorie');
  const cpvEntries = Object.entries(CPV).sort((a,b)=>a[1].localeCompare(b[1],'it'));
  for (const [code, label] of cpvEntries) addOpt(code, code + ' — ' + label.toLowerCase());

  const ITALY_BOUNDS = [[35, 6], [48, 19]];
  const map = L.map('map', {
    preferCanvas: true, minZoom: 6, maxZoom: 12,
    maxBounds: ITALY_BOUNDS, maxBoundsViscosity: 0.9,
    zoomControl: true, attributionControl: false,
  }).setView([42.5, 12.5], 6);

  const REGIONS = JSON.parse(document.getElementById('regionsdata').textContent);
  const NAVY = '#1e3a5f';
  const regionLabels = [];
  L.geoJSON(REGIONS, {
    style: () => ({ fillColor: NAVY, fillOpacity: 1, color: '#15294a', weight: 0.6, lineJoin: 'round' }),
    onEachFeature: (feature, layer) => {
      const t = L.tooltip({ permanent: true, direction: 'center', className: 'region-label', opacity: 1 })
        .setContent(feature.properties.name).setLatLng(layer.getBounds().getCenter());
      t.addTo(map); regionLabels.push(t);
    },
  }).addTo(map);

  const PLACES = JSON.parse(document.getElementById('placesdata').textContent);
  const capitalLabels = PLACES.capitals.map(p => L.tooltip({ permanent: true, direction: 'center', className: 'place-label-cap', opacity: 1 }).setContent(p.n).setLatLng([p.la, p.lo]));
  const comuneLabels = PLACES.comuni.map(p => {
    const t = L.tooltip({ permanent: true, direction: 'center', className: 'place-label', opacity: 1 }).setContent(p.n).setLatLng([p.la, p.lo]);
    t._lat = p.la; t._lon = p.lo; return t;
  });
  function setLabelsLayer(layer, visible) {
    for (const t of layer) {
      const onMap = !!t._map;
      if (visible && !onMap) t.addTo(map);
      else if (!visible && onMap) map.removeLayer(t);
    }
  }
  function updateLabels() {
    const z = map.getZoom();
    for (const t of regionLabels) { const el = t.getElement(); if (el) el.style.display = (z <= 8) ? '' : 'none'; }
    setLabelsLayer(capitalLabels, z >= 9);
    if (z >= 11) {
      const b = map.getBounds();
      const capNames = new Set(PLACES.capitals.map(c => c.n));
      for (const t of comuneLabels) {
        const want = b.contains([t._lat, t._lon]) && !capNames.has(t.getContent());
        const onMap = !!t._map;
        if (want && !onMap) t.addTo(map);
        else if (!want && onMap) map.removeLayer(t);
      }
    } else setLabelsLayer(comuneLabels, false);
  }
  map.on('zoomend moveend', updateLabels);
  setTimeout(updateLabels, 50);

  function radiusFor(metric, value){
    if (value <= 0) return 4;
    const lv = Math.log10(value + 1);
    if (metric === 'v') return Math.max(5, Math.min(28, 5 + (lv-3)*3.3));
    return Math.max(5, Math.min(24, 5 + lv*5.2));
  }

  const cluster = L.markerClusterGroup({
    maxClusterRadius: 50, spiderfyOnMaxZoom: true,
    showCoverageOnHover: false, chunkedLoading: true,
    iconCreateFunction: (c) => {
      const n = c.getChildCount();
      const size = n < 10 ? 32 : n < 100 ? 38 : n < 1000 ? 44 : 52;
      return L.divIcon({ html: '<div><span>' + n + '</span></div>', className: 'sa-cluster', iconSize: L.point(size, size) });
    },
  });
  map.addLayer(cluster);

  const markers = [];
  const jitterBuckets = {};
  for (const cf in SAS) {
    const s = SAS[cf];
    const k = s.la.toFixed(4) + ',' + s.lo.toFixed(4);
    jitterBuckets[k] = (jitterBuckets[k] || 0) + 1;
    const idx = jitterBuckets[k] - 1;
    let lat = s.la, lon = s.lo;
    if (idx > 0) {
      const angle = (idx * 137.5) * Math.PI/180;
      const r = 0.002 + 0.0008 * Math.sqrt(idx);
      lat += r * Math.cos(angle);
      lon += r * Math.sin(angle) / Math.cos(lat*Math.PI/180);
    }
    const m = L.circleMarker([lat, lon], { radius: 6, color: '#0f172a', weight: 0.8, fillColor: '#ffffff', fillOpacity: 0.95 });
    m._sa = s; m._cf = cf;
    m.bindPopup('', { maxWidth: 360 });
    m.on('click', () => { renderPopup(m); m.openPopup(); });
    markers.push(m);
  }

  let currentCat = 'ALL', currentMetric = 'v';
  const bucketFor = s => s.cats[currentCat];

  function restyleAll(){
    cluster.clearLayers();
    const toAdd = []; let totV=0, totC=0, totSA=0;
    for (const m of markers){
      const b = bucketFor(m._sa);
      if (!b) continue;
      const val = currentMetric==='v' ? b.v : b.c;
      m.setStyle({ radius: radiusFor(currentMetric, val), fillColor: '#ffffff', color: '#0f172a', weight: 0.8, fillOpacity: 0.95 });
      if (m.isPopupOpen()) renderPopup(m);
      toAdd.push(m);
      totV += b.v; totC += b.c; totSA++;
    }
    cluster.addLayers(toAdd);
    updateStats(totV, totC, totSA);
  }

  function renderPopup(m){
    const s = m._sa; const b = bucketFor(s); if (!b) return;
    const catLabel = currentCat==='ALL' ? 'tutte le categorie' : (currentCat + ' — ' + CPV[currentCat].toLowerCase());
    const sortIdx = currentMetric==='v' ? 1 : 2;
    const list = b.o.slice().sort((a,bb) => bb[sortIdx] - a[sortIdx]).slice(0, 5);
    const totalForShare = currentMetric==='v' ? b.v : b.c;
    let html = '<div class="popup">';
    html += '<h3>' + esc(s.n.toLowerCase()) + '</h3>';
    let metaParts = [];
    if (s.nt) metaParts.push(esc(s.nt.toLowerCase()));
    metaParts.push(esc(s.ct.toLowerCase()) + ' (' + esc(s.pv) + ')');
    if (s.ih) metaParts.push('<span class="pill ih">in-house</span>');
    if (s.pa) metaParts.push('<span class="pill">partecipata</span>');
    html += '<div class="meta">' + metaParts.join(' · ') + '<br><em>' + esc(catLabel) + '</em></div>';
    html += '<div class="tot"><span>valore totale aggiudicato</span><strong>' + eur(b.v) + '</strong></div>';
    html += '<div class="tot"><span>numero di contratti</span><strong>' + itf0.format(b.c) + '</strong></div>';
    html += '<div class="tot"><span>operatori distinti</span><strong>' + itf0.format(b.no) + '</strong></div>';
    html += '<div class="section-label">top 5 operatori · ' + (currentMetric==='v'?'per valore':'per numero di gare') + '</div>';
    html += '<ol>';
    for (const row of list){
      const [nm, val, cnt, rti] = row;
      const metric = currentMetric==='v' ? val : cnt;
      const share = totalForShare>0 ? metric/totalForShare : 0;
      const safeName = esc((nm || '(non specificato)').toLowerCase());
      const queryName = encodeURIComponent(nm || '');
      html += '<li>';
      html += '<span class="opname"><a href="operatori.html?q=' + queryName + '">' + safeName + '</a></span>';
      if (rti) html += ' <span class="pill rti">rti</span>';
      html += '<span class="opmeta">' + eur(val) + ' · ' + itf0.format(cnt) + ' contratti · ' + pct(share) + '</span>';
      html += '</li>';
    }
    html += '</ol>';
    html += '<div class="conc"><span>quota primo operatore (' + (currentMetric==='v'?'valore':'numero')+')</span><strong>' + pct(currentMetric==='v'?b.t1v:b.t1c) + '</strong></div>';
    html += '<div class="conc"><span>quota primi 3 operatori</span><strong>' + pct(currentMetric==='v'?b.t3v:b.t3c) + '</strong></div>';
    if (b.fd && b.fd > 0.5) {
      html += '<div class="ih-note" style="background:rgba(212,165,116,0.15);color:var(--amber)">attenzione: ' + pct(b.fd) + ' del valore di questa categoria proviene da un singolo accordo quadro pluriennale (annualizzato).</div>';
    }
    if (s.ih) html += '<div class="ih-note">sa classificata come in-house — può procurare per conto di un altro ente.</div>';
    html += '</div>';
    m.getPopup().setContent(html);
  }

  function updateStats(totV, totC, totSA){
    const el = document.getElementById('stats');
    const catLabel = currentCat==='ALL' ? 'tutte le categorie' : (currentCat + ' — ' + CPV[currentCat].toLowerCase());
    el.innerHTML = '<h2>selezione attiva</h2>' +
      '<div class="card">' +
      '<div class="stat"><span>categoria</span><strong>' + esc(catLabel) + '</strong></div>' +
      '<div class="stat"><span>stazioni appaltanti</span><strong>' + itf0.format(totSA) + '</strong></div>' +
      '<div class="stat"><span>valore aggiudicato</span><strong>' + eurShort(totV) + '</strong></div>' +
      '<div class="stat"><span>numero contratti</span><strong>' + itf0.format(totC) + '</strong></div>' +
      '</div>';
  }

  document.getElementById('meta-info').innerHTML =
    '<div class="note"><strong>dataset:</strong> ' + esc(META.region.toLowerCase()) + ' · finestra ' + esc(META.window) +
    ' · ' + itf0.format(META.n_contracts) + ' contratti aggiudicati · ' +
    itf0.format(META.n_sas) + ' stazioni appaltanti · ' +
    itf0.format(META.n_operators_distinct||0) + ' operatori distinti.</div>';

  document.getElementById('metodologia').innerHTML = `
    <p><strong>cosa rappresenta ogni punto.</strong> una stazione appaltante (sa) iscritta all'anagrafe anac con sede in italia, posizionata sul centroide del comune istat. con leggero scostamento quando più sa condividono lo stesso centroide.</p>
    <p><strong>valori annualizzati 2024.</strong> per ogni cig si prende l'<code>importo_lotto</code> (valore del singolo lotto) — non l'<code>importo_aggiudicazione</code>, che nei dati anac è spesso duplicato sul totale dell'accordo quadro padre. il valore viene poi <em>amortizzato</em> sulla <code>durata_prevista</code> del contratto: un appalto triennale da € 30 mln contribuisce € 10 mln al 2024.</p>
    <p><strong>filtri applicati.</strong> tenuti solo i cig con <code>data_aggiudicazione_definitiva</code> nel 2024 (esclude le aggiudicazioni 2023 che compaiono nei record cig-2024). esclusi i cig "padre" degli accordi quadro (il loro valore è già contato nei figli).</p>
    <p><strong>operatori — deduplicazione.</strong> aggregati per codice fiscale (cf / partita iva). quando il cf manca, normalizzazione del nome (maiuscolo, rimozione di srl/spa/ecc.) e raggruppamento.</p>
    <p><strong>rti e consorzi.</strong> per ogni cig si attribuisce l'aggiudicazione al ruolo prevalente. le aggiudicazioni a rti sono segnalate con il tag <span class="pill rti">rti</span>.</p>
    <p><strong>categoria cpv.</strong> 2 cifre iniziali del codice cpv "prevalente" del cig. i cig fuori scopo dalle 10 divisioni mostrate confluiscono solo nel totale "tutte le categorie".</p>
    <p><strong>concentrazione.</strong> quota del primo operatore (top-1) e dei primi 3 (top-3) sulla metrica attiva.</p>
    <p><strong>dominio da accordo quadro.</strong> quando una singola gara accordo-quadro pluriennale rappresenta più del 50% del valore di una categoria per una sa, viene segnalato esplicitamente nel popup.</p>
    <p><strong>centrali di committenza.</strong> alcune sa (es. aria spa, consip, asp cosenza) acquistano per conto di altri enti — il loro valore è alto perché aggregato regionalmente.</p>
  `;

  sel.addEventListener('change', () => { currentCat = sel.value; restyleAll(); });
  document.querySelectorAll('#metric-toggle button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#metric-toggle button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentMetric = btn.dataset.m;
      restyleAll();
    });
  });
  window.__app = { map, markers, cluster, SAS, restyleAll };
  restyleAll();
})();
</script>
</body>
</html>"""

# --------- PAGE 2: OPERATOR VIEW (operatori.html) ---------
OPERATORI_STYLE_EXTRA = r"""
  main.split { display:flex; height: calc(100vh - 76px - 38px); }
  .op-list-panel {
    width: 380px; height: 100%; overflow-y: auto;
    background: var(--bg);
    border-right: 1px solid var(--border);
    padding: 18px 0 30px;
  }
  .op-list-panel::-webkit-scrollbar { width: 8px; }
  .op-list-panel::-webkit-scrollbar-track { background: transparent; }
  .op-list-panel::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 4px; }

  .search-wrap {
    padding: 0 20px 14px;
    position: sticky; top: 0;
    background: var(--bg);
    z-index: 5;
    border-bottom: 1px solid var(--border);
  }
  .search-input {
    width: 100%;
    background: var(--bg-card);
    border: 1px solid var(--border-mid);
    border-radius: 999px;
    color: var(--text);
    padding: 9px 16px 9px 38px;
    font-size: 13px;
    font-family: inherit;
    text-transform: lowercase;
    letter-spacing: 0.02em;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%238da0bd' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='8'/><path d='m21 21-4.35-4.35'/></svg>");
    background-repeat: no-repeat;
    background-position: 14px center;
  }
  .search-input:focus { outline: none; border-color: var(--accent); }
  .search-input::placeholder { color: var(--text-dim); text-transform: lowercase; }
  .search-meta { font-size: 10.5px; color: var(--text-dim); padding: 8px 4px 4px; letter-spacing: 0.04em; text-transform: lowercase; }

  .op-list { padding: 8px 12px; }
  .op-row {
    display: block;
    padding: 11px 14px;
    border: 1px solid transparent;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.12s, border-color 0.12s;
    margin-bottom: 4px;
  }
  .op-row:hover { background: var(--bg-elev); }
  .op-row.active { background: var(--accent-soft); border-color: var(--border-mid); }
  .op-row .name {
    font-size: 12.5px; color: var(--text);
    line-height: 1.3;
    text-transform: lowercase;
    margin-bottom: 4px;
  }
  .op-row .meta {
    font-size: 10.5px; color: var(--text-dim);
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.02em;
    text-transform: lowercase;
  }
  .op-row .meta strong { color: var(--text-muted); font-weight: 500; }

  .op-detail {
    flex: 1 1 auto;
    height: 100%;
    overflow-y: auto;
    padding: 26px 30px 40px;
    background: var(--bg);
  }
  .op-detail::-webkit-scrollbar { width: 8px; }
  .op-detail::-webkit-scrollbar-track { background: transparent; }
  .op-detail::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 4px; }
  .op-detail .empty {
    height: 100%;
    display: flex; align-items: center; justify-content: center;
    color: var(--text-dim);
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic; font-size: 16px;
    text-transform: lowercase; letter-spacing: 0.03em;
  }
  .op-detail h2 {
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic; font-weight: 500;
    font-size: 28px; color: var(--text);
    text-transform: lowercase; line-height: 1.2;
    margin: 0 0 6px;
  }
  .op-detail .op-meta {
    color: var(--text-dim); font-size: 11.5px;
    text-transform: lowercase; letter-spacing: 0.04em;
    margin-bottom: 22px;
  }
  .op-detail .op-meta .pill { display: inline-block; background: var(--accent-soft); color: var(--accent-strong); font-size: 9px; padding: 1px 7px; border-radius: 999px; margin-left: 6px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500; }
  .op-detail .op-meta .pill.rti { background: rgba(212,165,116,0.15); color: var(--amber); }
  .op-detail .stats-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
    margin-bottom: 26px;
  }
  .stat-card {
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
  }
  .stat-card .label {
    font-size: 10px; color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 0.14em;
    font-family: 'Fraunces', Georgia, serif; font-style: italic; font-weight: 400;
    margin-bottom: 6px;
  }
  .stat-card .value {
    font-size: 22px; color: var(--text);
    font-variant-numeric: tabular-nums;
    font-weight: 400;
    font-family: 'Fraunces', Georgia, serif; font-style: italic;
  }
  .stat-card .sub {
    font-size: 10.5px; color: var(--text-dim);
    margin-top: 3px; text-transform: lowercase;
    font-variant-numeric: tabular-nums;
  }

  .section-title {
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic; font-weight: 400;
    font-size: 11px; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.18em;
    margin: 24px 0 12px;
  }
  .footprint-wrap {
    display: grid;
    grid-template-columns: 1fr 1.3fr;
    gap: 18px;
    margin-bottom: 22px;
  }
  .top-sas-list {
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 4px 0;
    max-height: 380px;
    overflow-y: auto;
  }
  .top-sas-list::-webkit-scrollbar { width: 6px; }
  .top-sas-list::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 3px; }
  .sa-row {
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 12px;
    align-items: baseline;
  }
  .sa-row:last-child { border-bottom: 0; }
  .sa-row .sa-name { font-size: 12px; color: var(--text); text-transform: lowercase; line-height: 1.3; }
  .sa-row .sa-loc { font-size: 10px; color: var(--text-dim); text-transform: lowercase; letter-spacing: 0.02em; margin-top: 2px; }
  .sa-row .sa-value { font-size: 11.5px; color: var(--text); font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
  .sa-row .sa-value .count { display: block; font-size: 10px; color: var(--text-dim); margin-top: 2px; }

  .mini-map-wrap {
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    height: 380px;
  }
  .mini-map { width: 100%; height: 100%; }

  .cpv-bars {
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 16px;
  }
  .cpv-bar { margin-bottom: 8px; }
  .cpv-bar:last-child { margin-bottom: 0; }
  .cpv-bar .bar-label {
    display: flex; justify-content: space-between;
    font-size: 11px; color: var(--text-muted);
    margin-bottom: 3px; text-transform: lowercase;
  }
  .cpv-bar .bar-label strong { color: var(--text); font-weight: 500; font-variant-numeric: tabular-nums; }
  .cpv-bar .bar-track { background: var(--bg-card); border-radius: 4px; height: 6px; overflow: hidden; }
  .cpv-bar .bar-fill { background: var(--accent); height: 100%; border-radius: 4px; }
"""

OPERATORI_HTML = r"""<!doctype html>
<html lang="it">
<head>
__SHARED_HEAD__
__OPERATORI_STYLE_EXTRA__
</style>
<title>mappa appalti — operatori</title>
</head>
<body>
<div class="loading" id="loading">caricamento dati…</div>
<header class="topbar">
  <nav class="nav">
    <a href="./">stazioni appaltanti</a>
    <a href="operatori.html" class="active">operatori</a>
  </nav>
  <div class="brand">
    <h1>mappa appalti pubblici — italia</h1>
    <div class="sub">vista operatore · 2024 · valori annualizzati · fonte anac<span class="badge">campione 1 anno</span></div>
  </div>
  <div class="controls">
    <select id="cat-filter" class="pill"></select>
    <div class="toggle" id="sort-toggle">
      <button data-s="v" class="active">per valore</button>
      <button data-s="c">per numero</button>
    </div>
  </div>
</header>
<main class="split">
  <div class="op-list-panel">
    <div class="search-wrap">
      <input class="search-input" id="search" type="text" placeholder="cerca operatore (es. a2a, vodafone, philips)…" autocomplete="off" spellcheck="false">
      <div class="search-meta" id="search-meta"></div>
    </div>
    <div class="op-list" id="op-list"></div>
  </div>
  <div class="op-detail" id="op-detail">
    <div class="empty">seleziona un operatore dalla lista a sinistra</div>
  </div>
</main>
<footer>
  fonte dati: <strong>anac — banca dati nazionale dei contratti pubblici</strong> · dataset: <code>aggiudicazioni</code>, <code>aggiudicatari</code>, <code>cig-2024</code>, <code>stazioni-appaltanti</code> · fetch __FETCHED__ · finestra __WINDOW__ · mappa <a href="https://leafletjs.com">leaflet</a>
</footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script id="regionsdata" type="application/json">__REGIONS__</script>
<script>
async function loadGz(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('Fetch ' + url + ': ' + resp.status);
  const ds = new DecompressionStream('gzip');
  const stream = resp.body.pipeThrough(ds);
  const text = await new Response(stream).text();
  return JSON.parse(text);
}

(async function(){
  const DATA = await loadGz('data/operators.json.gz');
  document.getElementById('loading').classList.add('gone');
  const CPV = DATA.cpv_divs;
  const OPS = DATA.operators;
  const META = DATA.meta;

  const itf = new Intl.NumberFormat('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const itf0 = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 0 });
  function eur(n){ return '€ ' + itf.format(n); }
  function eurShort(n){
    if (n>=1e9) return '€ ' + (n/1e9).toFixed(2).replace('.',',') + ' mld';
    if (n>=1e6) return '€ ' + (n/1e6).toFixed(2).replace('.',',') + ' mln';
    if (n>=1e3) return '€ ' + (n/1e3).toFixed(1).replace('.',',') + ' k';
    return eur(n);
  }
  function pct(x){ return (x*100).toFixed(1).replace('.',',') + '%'; }
  function esc(s){ return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]); }

  // Category filter
  const catFilter = document.getElementById('cat-filter');
  function addOpt(v,l){ const o=document.createElement('option'); o.value=v; o.textContent=l; catFilter.appendChild(o); }
  addOpt('ALL','tutte le categorie');
  const cpvEntries = Object.entries(CPV).sort((a,b)=>a[1].localeCompare(b[1],'it'));
  for (const [code, label] of cpvEntries) addOpt(code, code + ' — ' + label.toLowerCase());

  // Build a list of operator entries for ranking
  const ALL_OPS = Object.entries(OPS).map(([key, o]) => ({ key, ...o, _search: (o.n || '').toLowerCase() }));
  console.log('Operators loaded:', ALL_OPS.length);

  // Render list — by current filter + search + sort metric
  let currentFilter = 'ALL';
  let currentSearch = '';
  let currentSort = 'v';   // 'v' for value, 'c' for contract count
  let selectedKey = null;
  const LIST_LIMIT = 200;

  function filteredSorted() {
    let arr = ALL_OPS;
    if (currentSearch) {
      const q = currentSearch;
      arr = arr.filter(o => o._search.includes(q));
    }
    if (currentFilter !== 'ALL') {
      arr = arr.filter(o => o.cpv && o.cpv[currentFilter]);
      arr = arr.map(o => ({ ...o, _filt_v: o.cpv[currentFilter][0], _filt_c: o.cpv[currentFilter][1] }));
      arr.sort((a,b) => currentSort === 'v' ? b._filt_v - a._filt_v : b._filt_c - a._filt_c);
    } else {
      arr = arr.slice();
      arr.sort((a,b) => currentSort === 'v' ? b.v - a.v : b.c - a.c);
    }
    return arr;
  }

  function renderList(){
    const arr = filteredSorted();
    const meta = document.getElementById('search-meta');
    meta.textContent = arr.length.toLocaleString('it-IT') + ' operatori' +
      (arr.length > LIST_LIMIT ? ' · mostro i primi ' + LIST_LIMIT : '');
    const list = document.getElementById('op-list');
    const shown = arr.slice(0, LIST_LIMIT);
    list.innerHTML = shown.map(o => {
      const v = currentFilter==='ALL' ? o.v : o._filt_v;
      const c = currentFilter==='ALL' ? o.c : o._filt_c;
      const active = o.key === selectedKey ? ' active' : '';
      // Bold whichever metric is currently driving the sort
      const valStr = currentSort === 'v' ? '<strong>' + eurShort(v) + '</strong>' : eurShort(v);
      const cntStr = currentSort === 'c' ? '<strong>' + itf0.format(c) + ' contratti</strong>' : itf0.format(c) + ' contratti';
      return '<div class="op-row' + active + '" data-key="' + esc(o.key) + '">' +
        '<div class="name">' + esc((o.n || '').toLowerCase()) + '</div>' +
        '<div class="meta">' + valStr + ' · ' + cntStr + ' · ' + itf0.format(o.nsa) + ' sa · ' + itf0.format(o.nrg) + ' regioni</div>' +
        '</div>';
    }).join('');
    // hook up clicks
    list.querySelectorAll('.op-row').forEach(el => {
      el.addEventListener('click', () => selectOperator(el.dataset.key));
    });
  }

  // mini-map setup
  const REGIONS = JSON.parse(document.getElementById('regionsdata').textContent);
  let miniMap = null;
  let miniMapMarkers = [];

  function setupMiniMap(containerId) {
    if (miniMap) { miniMap.remove(); miniMap = null; miniMapMarkers = []; }
    const map = L.map(containerId, {
      preferCanvas: true, minZoom: 5, maxZoom: 12,
      zoomControl: true, attributionControl: false,
    }).setView([42.5, 12.5], 5);
    L.geoJSON(REGIONS, {
      style: () => ({ fillColor: '#1e3a5f', fillOpacity: 1, color: '#15294a', weight: 0.5 }),
      interactive: false,
    }).addTo(map);
    miniMap = map;
    return map;
  }

  function selectOperator(key) {
    selectedKey = key;
    document.querySelectorAll('.op-row').forEach(r => r.classList.toggle('active', r.dataset.key === key));
    renderDetail(OPS[key]);
  }

  function renderDetail(o) {
    if (!o) return;
    const detail = document.getElementById('op-detail');
    let html = '<h2>' + esc((o.n || '').toLowerCase()) + '</h2>';
    let metaParts = [];
    if (o.cf) metaParts.push('cf: ' + esc(o.cf));
    if (o.rti) metaParts.push('<span class="pill rti">rti</span>');
    html += '<div class="op-meta">' + metaParts.join(' · ') + '</div>';

    // Stats grid
    html += '<div class="stats-grid">';
    html += '<div class="stat-card"><div class="label">valore totale</div><div class="value">' + eurShort(o.v) + '</div><div class="sub">€ ' + itf.format(o.v) + '</div></div>';
    html += '<div class="stat-card"><div class="label">contratti</div><div class="value">' + itf0.format(o.c) + '</div><div class="sub">media ' + eurShort(o.v/o.c) + '</div></div>';
    html += '<div class="stat-card"><div class="label">stazioni appaltanti</div><div class="value">' + itf0.format(o.nsa) + '</div><div class="sub">distinte</div></div>';
    html += '<div class="stat-card"><div class="label">regioni · province</div><div class="value">' + itf0.format(o.nrg) + ' · ' + itf0.format(o.npv) + '</div><div class="sub">copertura geografica</div></div>';
    html += '</div>';

    // Concentration row
    html += '<div class="stats-grid" style="grid-template-columns: repeat(2, 1fr);">';
    html += '<div class="stat-card"><div class="label">quota top-1 cliente</div><div class="value">' + pct(o.t1s) + '</div><div class="sub">peso del primo cliente sul fatturato</div></div>';
    html += '<div class="stat-card"><div class="label">quota top-3 clienti</div><div class="value">' + pct(o.t3s) + '</div><div class="sub">peso dei primi 3 clienti</div></div>';
    html += '</div>';

    // Footprint: top SAs list + mini map
    html += '<div class="section-title">footprint · top 10 stazioni appaltanti per valore</div>';
    html += '<div class="footprint-wrap">';
    html += '<div class="top-sas-list">';
    for (const sa of o.sas) {
      html += '<div class="sa-row">' +
        '<div>' +
          '<div class="sa-name">' + esc((sa.n || '').toLowerCase()) + '</div>' +
          '<div class="sa-loc">' + esc((sa.ct || '').toLowerCase()) + ' (' + esc(sa.pv) + ') · ' + esc((sa.rg || '').toLowerCase()) + '</div>' +
        '</div>' +
        '<div class="sa-value">' + eurShort(sa.v) + '<span class="count">' + itf0.format(sa.c) + ' contratti</span></div>' +
      '</div>';
    }
    html += '</div>';
    html += '<div class="mini-map-wrap"><div class="mini-map" id="mini-map-' + Date.now() + '"></div></div>';
    html += '</div>';

    // CPV breakdown
    if (o.cpv && Object.keys(o.cpv).length > 0) {
      html += '<div class="section-title">composizione per categoria cpv (sulle 10 in scope)</div>';
      html += '<div class="cpv-bars">';
      const cpvEntries = Object.entries(o.cpv).sort((a,b) => b[1][0] - a[1][0]);
      const totalShownV = cpvEntries.reduce((s, [_, [v, _c]]) => s + v, 0);
      for (const [code, [v, c]] of cpvEntries) {
        const w = totalShownV > 0 ? (v / totalShownV * 100) : 0;
        html += '<div class="cpv-bar">' +
          '<div class="bar-label"><span>' + esc(code) + ' — ' + esc(CPV[code].toLowerCase()) + '</span><strong>' + eurShort(v) + ' · ' + itf0.format(c) + '</strong></div>' +
          '<div class="bar-track"><div class="bar-fill" style="width:' + w.toFixed(1) + '%"></div></div>' +
        '</div>';
      }
      html += '</div>';
    }

    detail.innerHTML = html;
    detail.scrollTop = 0;

    // Set up mini-map after DOM insertion
    const miniContainer = detail.querySelector('.mini-map');
    if (miniContainer) {
      const map = setupMiniMap(miniContainer.id);
      // Add markers for top SAs
      const maxV = Math.max(...o.sas.map(s => s.v));
      const bounds = [];
      for (const sa of o.sas) {
        const r = 5 + Math.sqrt(sa.v / maxV) * 18;
        const m = L.circleMarker([sa.la, sa.lo], {
          radius: r, color: '#0f172a', weight: 0.8, fillColor: '#ffffff', fillOpacity: 0.95
        });
        m.bindTooltip(sa.n + '<br>' + eurShort(sa.v) + ' · ' + sa.c + ' contratti', { direction: 'top', offset: [0, -2], className: 'place-label-cap' });
        m.addTo(map);
        bounds.push([sa.la, sa.lo]);
        miniMapMarkers.push(m);
      }
      // Fit map to bounds (with padding)
      if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 10 });
      }
    }
  }

  // Event handlers
  document.getElementById('search').addEventListener('input', (e) => {
    currentSearch = e.target.value.toLowerCase().trim();
    renderList();
  });
  catFilter.addEventListener('change', (e) => {
    currentFilter = e.target.value;
    renderList();
  });
  document.querySelectorAll('#sort-toggle button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#sort-toggle button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentSort = btn.dataset.s;
      renderList();
    });
  });

  renderList();

  // If URL has ?q=NAME, auto-search and select first match
  const urlParams = new URLSearchParams(window.location.search);
  const q = urlParams.get('q');
  if (q) {
    document.getElementById('search').value = q;
    currentSearch = q.toLowerCase().trim();
    renderList();
    const matches = filteredSorted();
    if (matches.length > 0) selectOperator(matches[0].key);
  }

  window.__app = { OPS, ALL_OPS, selectOperator };
})();
</script>
</body>
</html>"""

def render(template, **subs):
    out = template
    for k, v in subs.items():
        out = out.replace('__' + k + '__', v)
    return out

shared = {
    'SHARED_HEAD': SHARED_HEAD,
    'REGIONS': REGIONS_JSON,
    'PLACES': PLACES_JSON,
    'FETCHED': META_ONLY['fetched'],
    'WINDOW': META_ONLY['window'],
}

index_out = render(INDEX_HTML, INDEX_STYLE_EXTRA=INDEX_STYLE_EXTRA, **shared)
oper_out = render(OPERATORI_HTML, OPERATORI_STYLE_EXTRA=OPERATORI_STYLE_EXTRA, **shared)

for path, content in [('index.html', index_out), ('operatori.html', oper_out)]:
    with open(os.path.join(HERE, path), 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Wrote {path}  ({os.path.getsize(os.path.join(HERE, path))/1e6:.2f} MB)')
