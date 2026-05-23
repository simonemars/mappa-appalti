#!/usr/bin/env python3
"""Builds the self-contained interactive HTML map from agg_lombardia.json."""
import json, os, sys

import base64, gzip
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_GZ_PATH = os.path.join(HERE, 'raw', 'agg_italia.json.gz')
REGIONS_PATH = os.path.join(HERE, 'raw', 'italy_regions.geojson')
PLACES_PATH = os.path.join(HERE, 'raw', 'italia_places.json')
OUT_PATH = os.path.join(HERE, 'index.html')

with open(DATA_GZ_PATH, 'rb') as f:
    raw_gz = f.read()
DATA_GZ_B64 = base64.b64encode(raw_gz).decode('ascii')
META_ONLY = json.loads(gzip.decompress(raw_gz).decode('utf-8'))['meta']
with open(REGIONS_PATH, encoding='utf-8') as f:
    REGIONS = json.load(f)
with open(PLACES_PATH, encoding='utf-8') as f:
    PLACES = json.load(f)

HTML = r"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mappa appalti pubblici — Italia</title>
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
  .serif { font-family: 'Fraunces', Georgia, serif; font-style: italic; font-weight: 500; }

  header {
    padding: 22px 28px 18px;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 18px;
  }
  header .brand { grid-column: 2; text-align: center; }
  header h1 {
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic;
    font-weight: 500;
    font-size: 26px;
    color: var(--text);
    letter-spacing: 0.005em;
    margin: 0;
    text-transform: lowercase;
  }
  header .sub {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: lowercase;
    letter-spacing: 0.08em;
    margin-top: 4px;
  }
  header .badge {
    font-family: 'Inter', sans-serif;
    background: transparent;
    border: 1px solid var(--amber);
    color: var(--amber);
    padding: 1px 7px;
    border-radius: 999px;
    font-size: 9.5px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-left: 6px;
  }

  .controls {
    grid-column: 3;
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    align-items: center;
    flex-wrap: wrap;
  }
  .controls select {
    appearance: none;
    -webkit-appearance: none;
    background: var(--bg-card);
    border: 1px solid var(--border-mid);
    border-radius: 999px;
    color: var(--text);
    padding: 8px 32px 8px 16px;
    font-size: 12px;
    font-family: inherit;
    text-transform: lowercase;
    letter-spacing: 0.02em;
    min-width: 260px;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='%238da0bd' d='M0 0l5 6 5-6z'/></svg>");
    background-repeat: no-repeat;
    background-position: right 14px center;
  }
  .controls select:hover { background-color: var(--bg-hover); border-color: var(--border-dash); }
  .controls select:focus { outline: none; border-color: var(--accent); }
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

  main { display:flex; height: calc(100vh - 78px - 38px); }
  #map { flex: 1 1 auto; height: 100%; background: var(--bg); }
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
    width: 32px !important;
    height: 32px !important;
    line-height: 32px !important;
    font-size: 16px !important;
    font-weight: 300 !important;
  }
  .leaflet-control-zoom a:hover { background: var(--bg-hover) !important; color: var(--text) !important; }

  .region-label {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    color: var(--text-muted);
    opacity: 0.7;
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic;
    font-weight: 400;
    font-size: 14px;
    letter-spacing: 0.01em;
    padding: 0;
    text-shadow: 0 1px 3px rgba(0,0,0,0.45);
    pointer-events: none;
    white-space: nowrap;
    text-transform: lowercase;
  }
  .region-label::before { display:none !important; }
  .place-label, .place-label-cap {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    font-family: 'Inter', sans-serif;
    color: var(--text);
    text-shadow: 0 0 3px rgba(10,22,40,0.95), 0 1px 2px rgba(10,22,40,0.9);
    padding: 0;
    pointer-events: none;
    white-space: nowrap;
    text-transform: lowercase;
    letter-spacing: 0.02em;
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
  .sa-cluster > div { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
  .sa-cluster span { font-size: 12px; }

  aside {
    width: 360px;
    height: 100%;
    overflow-y: auto;
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
    font-style: italic;
    font-weight: 400;
    font-size: 11px;
    margin: 0 0 10px 0;
    color: var(--text-muted);
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }
  .card {
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 14px;
  }
  .stat {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 7px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12.5px;
    color: var(--text-muted);
    text-transform: lowercase;
  }
  .stat:last-child { border-bottom: 0; padding-bottom: 0; }
  .stat strong {
    color: var(--text);
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    text-transform: none;
  }

  details { margin-top: 6px; }
  details summary {
    cursor: pointer;
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic;
    font-weight: 500;
    color: var(--accent-strong);
    font-size: 14px;
    text-transform: lowercase;
    list-style: none;
    padding: 4px 0;
  }
  details summary::-webkit-details-marker { display: none; }
  details summary::before { content: '▸  '; color: var(--text-dim); transition: transform 0.15s; display: inline-block; }
  details[open] summary::before { content: '▾  '; }
  details .body { font-size: 12.5px; line-height: 1.6; color: var(--text-muted); margin-top: 8px; }
  details .body p { margin: 8px 0; }
  details .body ul { padding-left: 18px; margin: 8px 0; }
  details .body strong { color: var(--text); font-weight: 500; }
  details .body em { color: var(--text); font-style: italic; }
  details .body code {
    background: var(--bg-card);
    color: var(--accent-strong);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 11px;
    font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  }

  /* Popup — dark card matching the rest of the UI */
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

  .popup { font-size: 12.5px; min-width: 280px; }
  .popup h3 {
    margin: 0 0 4px;
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic;
    font-weight: 500;
    font-size: 16px;
    color: var(--text);
    text-transform: lowercase;
    line-height: 1.25;
  }
  .popup .meta { color: var(--text-dim); font-size: 11px; margin-bottom: 10px; text-transform: lowercase; letter-spacing: 0.02em; }
  .popup .meta em { color: var(--accent); font-style: italic; }
  .popup .tot {
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 5px 0; border-bottom: 1px solid var(--border);
    font-size: 12px; color: var(--text-muted); text-transform: lowercase;
  }
  .popup .tot strong { color: var(--text); font-weight: 500; font-variant-numeric: tabular-nums; }
  .popup .section-label {
    margin-top: 10px; font-size: 10px; color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 0.18em;
    font-family: 'Fraunces', Georgia, serif; font-style: italic; font-weight: 400;
  }
  .popup ol { padding-left: 0; margin: 6px 0; list-style: none; counter-reset: opc; }
  .popup ol li {
    counter-increment: opc;
    padding: 6px 0 7px;
    line-height: 1.35;
    border-bottom: 1px solid var(--border);
    position: relative;
    padding-left: 22px;
  }
  .popup ol li:last-child { border-bottom: 0; }
  .popup ol li::before {
    content: counter(opc);
    position: absolute; left: 0; top: 7px;
    color: var(--text-dim); font-size: 10px;
    font-variant-numeric: tabular-nums;
  }
  .popup .opname { color: var(--text); font-size: 12px; }
  .popup .opmeta { color: var(--text-dim); font-size: 10.5px; display: block; font-variant-numeric: tabular-nums; margin-top: 2px; }
  .popup .pill {
    display: inline-block;
    background: var(--accent-soft);
    color: var(--accent-strong);
    font-size: 9px; padding: 1px 7px;
    border-radius: 999px;
    margin-left: 4px;
    text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500;
    vertical-align: middle;
  }
  .popup .pill.rti { background: rgba(212,165,116,0.15); color: var(--amber); }
  .popup .pill.ih { background: var(--accent-soft); color: var(--accent-strong); }
  .popup .conc {
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 5px 0; font-size: 11px; color: var(--text-muted);
    text-transform: lowercase;
  }
  .popup .conc strong { color: var(--text); font-variant-numeric: tabular-nums; font-weight: 500; }
  .popup .ih-note {
    background: var(--accent-soft); color: var(--accent-strong);
    padding: 8px 10px; border-radius: 8px; margin-top: 8px; font-size: 11px;
    line-height: 1.4;
  }

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

  .note {
    background: transparent;
    border: 1px dashed var(--border-dash);
    color: var(--text-muted);
    padding: 12px 14px;
    border-radius: 12px;
    font-size: 11.5px;
    line-height: 1.55;
    margin-bottom: 14px;
    text-transform: lowercase;
    letter-spacing: 0.01em;
  }
  .note strong { color: var(--text); font-weight: 500; text-transform: none; }
</style>
</head>
<body>
<header>
  <div></div>
  <div class="brand">
    <h1>mappa appalti pubblici — italia</h1>
    <div class="sub">concentrazione delle aggiudicazioni per stazione appaltante · <span id="window-label">2024</span> · fonte anac<span class="badge">campione 1 anno</span></div>
  </div>
  <div class="controls">
    <select id="cat-select"></select>
    <div class="toggle" id="metric-toggle">
      <button data-m="v" class="active">per valore</button>
      <button data-m="c">per numero</button>
    </div>
  </div>
</header>
<main>
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
<script id="appdata-gz" type="text/plain">__DATA_GZ_B64__</script>
<script id="regionsdata" type="application/json">__REGIONS__</script>
<script id="placesdata" type="application/json">__PLACES__</script>
<script>
async function loadData() {
  const b64 = document.getElementById('appdata-gz').textContent.trim();
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const ds = new DecompressionStream('gzip');
  const stream = new Blob([bin]).stream().pipeThrough(ds);
  const text = await new Response(stream).text();
  return JSON.parse(text);
}

(async function(){
  const DATA = await loadData();
  const CPV = DATA.cpv_divs;
  const SAS = DATA.sas;
  const META = DATA.meta;

  // Format helpers — Italian conventions
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

  // Category dropdown — "Tutte" first then 10 divisions
  const sel = document.getElementById('cat-select');
  function addOpt(v,l){ const o=document.createElement('option'); o.value=v; o.textContent=l; sel.appendChild(o); }
  addOpt('ALL','tutte le categorie');
  // sorted by label
  const cpvEntries = Object.entries(CPV).sort((a,b)=>a[1].localeCompare(b[1],'it'));
  for (const [code, label] of cpvEntries) addOpt(code, code + ' — ' + label.toLowerCase());

  // Map — blank canvas with Italian regions as the only base layer
  const ITALY_BOUNDS = [[35, 6], [48, 19]];
  const map = L.map('map', {
    preferCanvas: true,
    minZoom: 6,
    maxZoom: 12,
    maxBounds: ITALY_BOUNDS,
    maxBoundsViscosity: 0.9,
    zoomControl: true,
    attributionControl: false,
  }).setView([42.5, 12.5], 6);

  // Italian regions as solid navy fill, no tile layer at all
  const REGIONS = JSON.parse(document.getElementById('regionsdata').textContent);
  const NAVY = '#1e3a5f';
  const regionLabels = [];
  const regionsLayer = L.geoJSON(REGIONS, {
    style: () => ({
      fillColor: NAVY,
      fillOpacity: 1,
      color: '#15294a',
      weight: 0.6,
      lineJoin: 'round',
    }),
    onEachFeature: (feature, layer) => {
      const name = feature.properties.name;
      const tooltip = L.tooltip({
        permanent: true,
        direction: 'center',
        className: 'region-label',
        opacity: 1,
      }).setContent(name).setLatLng(layer.getBounds().getCenter());
      tooltip.addTo(map);
      regionLabels.push(tooltip);
    },
  }).addTo(map);

  // Place labels (capitals + comuni) — appear when region labels disappear
  const PLACES = JSON.parse(document.getElementById('placesdata').textContent);
  const capitalLabels = PLACES.capitals.map(p => {
    return L.tooltip({ permanent: true, direction: 'center', className: 'place-label-cap', opacity: 1 })
      .setContent(p.n).setLatLng([p.la, p.lo]);
  });
  const comuneLabels = PLACES.comuni.map(p => {
    const t = L.tooltip({ permanent: true, direction: 'center', className: 'place-label', opacity: 1 })
      .setContent(p.n).setLatLng([p.la, p.lo]);
    t._lat = p.la; t._lon = p.lo;
    return t;
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
    // Region labels: zoom 6-8 only
    for (const t of regionLabels) {
      const el = t.getElement();
      if (el) el.style.display = (z <= 8) ? '' : 'none';
    }
    // Capitals: zoom 9+ always (they help orient even when comuni show)
    setLabelsLayer(capitalLabels, z >= 9);
    // Comuni: zoom 11+, viewport-clipped
    if (z >= 11) {
      const b = map.getBounds();
      const capNames = new Set(PLACES.capitals.map(c => c.n));
      for (const t of comuneLabels) {
        const inView = b.contains([t._lat, t._lon]);
        const isCap = capNames.has(t.getContent());
        const want = inView && !isCap;
        const onMap = !!t._map;
        if (want && !onMap) t.addTo(map);
        else if (!want && onMap) map.removeLayer(t);
      }
    } else {
      setLabelsLayer(comuneLabels, false);
    }
  }
  map.on('zoomend moveend', updateLabels);
  setTimeout(updateLabels, 50);

  // Size: based on log of metric value
  function radiusFor(metric, value){
    if (value <= 0) return 4;
    const lv = Math.log10(value + 1);
    if (metric === 'v') {
      // value in EUR. typical range: ~1k .. 1e10. log10: 3..10. map 3->5px, 10->28px
      return Math.max(5, Math.min(28, 5 + (lv-3)*3.3));
    } else {
      // count. typical 1..4000. log10 0..3.6. map 0->5, 3.6->24
      return Math.max(5, Math.min(24, 5 + (lv)*5.2));
    }
  }

  // Cluster group — uniform white styling (no count-based color)
  const cluster = L.markerClusterGroup({
    maxClusterRadius: 50,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    chunkedLoading: true,
    iconCreateFunction: (c) => {
      const n = c.getChildCount();
      const size = n < 10 ? 32 : n < 100 ? 38 : n < 1000 ? 44 : 52;
      return L.divIcon({
        html: '<div><span>' + n + '</span></div>',
        className: 'sa-cluster',
        iconSize: L.point(size, size),
      });
    },
  });
  map.addLayer(cluster);

  // Build markers (one per SA), keep references for restyling.
  // Slight position jitter for SAs sharing the same comune centroid so they don't overlap exactly.
  const markers = [];
  const jitterBuckets = {};
  for (const cf in SAS) {
    const s = SAS[cf];
    const k = s.la.toFixed(4) + ',' + s.lo.toFixed(4);
    jitterBuckets[k] = (jitterBuckets[k] || 0) + 1;
    const idx = jitterBuckets[k] - 1;
    let lat = s.la, lon = s.lo;
    if (idx > 0) {
      const angle = (idx * 137.5) * Math.PI/180; // golden angle for spread
      const r = 0.002 + 0.0008 * Math.sqrt(idx);
      lat += r * Math.cos(angle);
      lon += r * Math.sin(angle) / Math.cos(lat*Math.PI/180);
    }
    const m = L.circleMarker([lat, lon], {
      radius: 6, color: '#0f172a', weight: 0.8, fillColor: '#ffffff', fillOpacity: 0.95
    });
    m._sa = s;
    m._cf = cf;
    m.bindPopup('', { maxWidth: 360 });
    m.on('click', () => { renderPopup(m); m.openPopup(); });
    markers.push(m);
  }

  // Current state
  let currentCat = 'ALL';
  let currentMetric = 'v'; // 'v' or 'c'

  function selectedCat() { return currentCat; }
  function bucketFor(s){
    const k = selectedCat();
    return s.cats[k];
  }

  function restyleAll(){
    cluster.clearLayers();
    const toAdd = [];
    let totV=0, totC=0, totSA=0;
    let maxV=0, maxC=0;
    for (const m of markers){
      const b = bucketFor(m._sa);
      if (!b) continue;
      const val = currentMetric==='v' ? b.v : b.c;
      m.setStyle({
        radius: radiusFor(currentMetric, val),
        fillColor: '#ffffff',
        color: '#0f172a',
        weight: 0.8,
        fillOpacity: 0.95,
      });
      // refresh popup content if it's open
      if (m.isPopupOpen()) renderPopup(m);
      toAdd.push(m);
      totV += b.v; totC += b.c; totSA++;
      if (b.v>maxV) maxV=b.v; if (b.c>maxC) maxC=b.c;
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
      html += '<li>';
      html += '<span class="opname">' + esc((nm || '(non specificato)').toLowerCase()) + '</span>';
      if (rti) html += ' <span class="pill rti">rti</span>';
      html += '<span class="opmeta">' + eur(val) + ' · ' + itf0.format(cnt) + ' contratti · ' + pct(share) + '</span>';
      html += '</li>';
    }
    html += '</ol>';
    html += '<div class="conc"><span>quota primo operatore (' + (currentMetric==='v'?'valore':'numero')+')</span><strong>' + pct(currentMetric==='v'?b.t1v:b.t1c) + '</strong></div>';
    html += '<div class="conc"><span>quota primi 3 operatori</span><strong>' + pct(currentMetric==='v'?b.t3v:b.t3c) + '</strong></div>';
    if (s.ih) html += '<div class="ih-note">sa classificata come in-house — può procurare per conto di un altro ente.</div>';
    html += '</div>';
    m.getPopup().setContent(html);
  }

  function esc(s){ return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]); }

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

  // Meta info at top of sidebar
  document.getElementById('meta-info').innerHTML =
    '<div class="note"><strong>dataset:</strong> ' + esc(META.region.toLowerCase()) + ' · finestra ' + esc(META.window) +
    ' · ' + itf0.format(META.n_contracts) + ' contratti aggiudicati · ' +
    itf0.format(META.n_sas) + ' stazioni appaltanti · ' +
    itf0.format(META.n_operators_distinct||0) + ' operatori distinti.</div>';

  // Methodology block — lowercase editorial style
  document.getElementById('metodologia').innerHTML = `
    <p><strong>cosa rappresenta ogni punto.</strong> una stazione appaltante (sa) iscritta all'anagrafe anac con sede in italia, posizionata sul centroide del comune istat. con leggero scostamento quando più sa condividono lo stesso centroide.</p>
    <p><strong>cosa misura il valore.</strong> somma degli <em>importi di aggiudicazione</em> (campo <code>importo_aggiudicazione</code> del dataset <code>aggiudicazioni</code>) dei cig aggiudicati nella categoria cpv selezionata. è il valore dell'aggiudicazione, non il pagato.</p>
    <p><strong>finestra temporale.</strong> solo anno 2024 (campione v1). l'estensione a 5 anni richiede ~1 gb aggiuntivo di dati cig da anac e processamento più lungo.</p>
    <p><strong>operatori — deduplicazione.</strong> aggregati per codice fiscale (cf / partita iva). quando il cf manca, normalizzazione del nome (maiuscolo, rimozione di srl/spa/ecc.) e raggruppamento. operatori esteri trattati separatamente.</p>
    <p><strong>rti e consorzi.</strong> per ogni cig si attribuisce l'aggiudicazione al ruolo prevalente: prima <code>operatore economico monosoggettivo</code>, poi <code>mandataria</code>, poi consorzio. le aggiudicazioni a rti sono segnalate con il tag <span class="pill rti">rti</span>.</p>
    <p><strong>categoria cpv.</strong> 2 cifre iniziali del codice cpv "prevalente" del cig. i cig fuori scopo dalle 10 divisioni mostrate confluiscono solo nel totale "tutte le categorie".</p>
    <p><strong>concentrazione.</strong> quota del primo operatore (top-1) e dei primi 3 (top-3) sulla metrica attiva (valore o numero).</p>
    <p><strong>centrali di committenza.</strong> alcune sa (es. aria spa, consip per parte nazionale) acquistano per conto di altri enti. il loro valore è alto perché aggregato.</p>
  `;

  // Set window label in header
  document.getElementById('window-label').textContent = META.window;
  // Footer placeholders done at render time (above)

  // Wire up controls
  sel.addEventListener('change', () => { currentCat = sel.value; restyleAll(); });
  document.querySelectorAll('#metric-toggle button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#metric-toggle button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentMetric = btn.dataset.m;
      restyleAll();
    });
  });

  // Expose for debugging / programmatic use
  window.__app = { map, markers, cluster, SAS, restyleAll, get currentCat(){return currentCat}, get currentMetric(){return currentMetric} };

  // initial render
  restyleAll();
})();

</script>
</body>
</html>"""

# Inject data, regions, and meta
regions_json = json.dumps(REGIONS, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
places_json = json.dumps(PLACES, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')

out = HTML.replace('__DATA_GZ_B64__', DATA_GZ_B64) \
          .replace('__REGIONS__', regions_json) \
          .replace('__PLACES__', places_json) \
          .replace('__FETCHED__', META_ONLY['fetched']) \
          .replace('__WINDOW__', META_ONLY['window'])

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(out)

print(f'Wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)/1e6:.2f} MB)')
