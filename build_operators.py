#!/usr/bin/env python3
"""Build per-operator aggregates from italy_contracts_2024.json into operators.json.gz.

For each operator (keyed by codice fiscale, with canonical-name fallback):
- total value, total count, n distinct SAs, n distinct regions
- CPV breakdown
- top SAs by value (top 10, with position for the mini-map)
- top-1 SA revenue concentration
- RTI flag (was the operator ever part of a temporary group?)

Filters out operators with v<10,000 EUR AND c<2 — those are statistical noise
not worth indexing for search.
"""
import json, re, gzip, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_PATH = os.path.join(HERE, 'raw', 'italy_contracts_honest_2024.json')
SAS_PATH = os.path.join(HERE, 'raw', 'italy_sas_geo.json')
OUT_PATH = os.path.join(HERE, 'data', 'operators.json.gz')

CPV_DIVS = {
    '45':'Lavori di costruzione','33':'Apparecchiature mediche, farmaceutici',
    '85':'Servizi sanitari e di assistenza sociale','71':'Servizi architettonici, di ingegneria',
    '90':'Servizi ambientali, rifiuti, fognari','50':'Servizi di riparazione e manutenzione',
    '79':'Servizi per le imprese','72':'Servizi informatici (IT)',
    '60':'Servizi di trasporto','09':'Prodotti petroliferi, combustibili, energia elettrica',
}

LEGAL = re.compile(r"\b(s\.?r\.?l\.?|s\.?p\.?a\.?|s\.?n\.?c\.?|s\.?a\.?s\.?|s\.?c\.?a\.?r\.?l\.?|s\.?c\.?p\.?a\.?|soc\.? coop\.?|società cooperativa|s\.?b\.?|società benefit)\b", re.IGNORECASE)
def canon(name):
    if not name: return ''
    return re.sub(r'[^A-Z0-9]+', ' ', LEGAL.sub('', name.upper())).strip()
def op_key(c):
    cf = (c.get('op_cf') or '').strip()
    if cf and cf != '00000000000': return cf
    nm = canon(c.get('op_nome',''))
    return 'NM:' + nm if nm else None
def short(n, lim=60):
    n = (n or '').strip()
    return (n[:lim-1] + '…') if len(n) > lim else n

print('Loading contracts...')
with open(CONTRACTS_PATH) as f:
    contracts = json.load(f)
print(f'  {len(contracts):,} contracts')

print('Loading SAs...')
with open(SAS_PATH) as f:
    sas = json.load(f)
print(f'  {len(sas):,} SAs')

# Aggregate per operator
print('Aggregating per operator...')
# ops[key] = {'name': str, 'cf': str, 'kind': 'CF'|'NM', 'v': float, 'c': int,
#             'rti': bool, 'cpv': {div: {v,c}}, 'sas': {sa_cf: {v, c}}}
ops = defaultdict(lambda: {'name': '', 'cf': '', 'kind': '', 'v': 0.0, 'c': 0,
                            'rti': False, 'cpv': defaultdict(lambda: {'v':0.0,'c':0}),
                            'sas': defaultdict(lambda: {'v':0.0,'c':0})})

for c in contracts:
    imp = c.get('importo', 0) or 0
    if imp <= 0: continue
    key = op_key(c)
    if not key: continue
    o = ops[key]
    nm = c.get('op_nome', '') or ''
    if len(nm) > len(o['name']):
        o['name'] = nm
    if not o['kind']:
        o['kind'] = 'CF' if not key.startswith('NM:') else 'NM'
        o['cf'] = key if o['kind'] == 'CF' else ''
    o['v'] += imp
    o['c'] += 1
    if c.get('op_is_rti'):
        o['rti'] = True
    div = c.get('cpv_div', '') or ''
    if div:
        o['cpv'][div]['v'] += imp
        o['cpv'][div]['c'] += 1
    sa_cf = c.get('sa_cf', '')
    if sa_cf:
        o['sas'][sa_cf]['v'] += imp
        o['sas'][sa_cf]['c'] += 1

print(f'  Distinct operators: {len(ops):,}')

# Filter: keep operators with c>=3 OR v>=50000 — keeps the long tail of
# tiny one-off awards out, and the result stays under 10 MB gzipped.
filtered = {k: o for k, o in ops.items() if o['c'] >= 3 or o['v'] >= 50000}
print(f'  After threshold (c>=3 OR v>=50k): {len(filtered):,}')

# Build the output records — compact
out_ops = {}
for key, o in filtered.items():
    # top 10 SAs by value, attach SA metadata for the map
    top_sas = sorted(o['sas'].items(), key=lambda x: -x[1]['v'])[:10]
    sa_records = []
    distinct_regions = set()
    distinct_provs = set()
    for sa_cf, agg in top_sas:
        sa = sas.get(sa_cf)
        if not sa: continue
        sa_records.append({
            's': sa_cf,
            'n': short(sa['nome'], 70),
            'ct': sa['citta'],
            'pv': sa['prov'],
            'rg': sa['regione'],
            'la': round(sa['lat'], 5),
            'lo': round(sa['lon'], 5),
            'v': round(agg['v']),
            'c': agg['c'],
        })
    # Count distinct regions / provs across ALL SAs (not just top 10)
    for sa_cf in o['sas']:
        sa = sas.get(sa_cf)
        if sa:
            distinct_regions.add(sa['regione'])
            distinct_provs.add(sa['prov'])
    total_v = o['v']
    t1s = top_sas[0][1]['v'] / total_v if total_v > 0 else 0
    t3s = sum(s[1]['v'] for s in top_sas[:3]) / total_v if total_v > 0 else 0
    # CPV breakdown — only include scope CPVs + total elsewhere
    cpv_payload = {}
    for div, agg in o['cpv'].items():
        if div in CPV_DIVS:
            cpv_payload[div] = [round(agg['v']), agg['c']]
    out_ops[key] = {
        'n': short(o['name'], 70),
        'cf': o['cf'],
        'k': o['kind'],
        'v': round(o['v']),
        'c': o['c'],
        'nsa': len(o['sas']),
        'nrg': len(distinct_regions),
        'npv': len(distinct_provs),
        'rti': 1 if o['rti'] else 0,
        'cpv': cpv_payload,
        'sas': sa_records,
        't1s': round(t1s, 3),
        't3s': round(t3s, 3),
    }

data = {
    'operators': out_ops,
    'cpv_divs': CPV_DIVS,
    'meta': {
        'source': 'ANAC — BDNCP',
        'datasets': ['aggiudicazioni','aggiudicatari','cig-2024','stazioni-appaltanti'],
        'fetched': '2026-05-22',
        'window': '2024 (anno solare)',
        'region': 'Italia',
        'n_operators': len(out_ops),
        'n_contracts': sum(o['c'] for o in out_ops.values()),
        'total_value': sum(o['v'] for o in out_ops.values()),
    }
}

raw = json.dumps(data, separators=(',',':'), ensure_ascii=False).encode('utf-8')
gz = gzip.compress(raw, compresslevel=9)
with open(OUT_PATH, 'wb') as f:
    f.write(gz)
print(f'\nRaw JSON:  {len(raw)/1e6:.2f} MB')
print(f'Gzipped:   {len(gz)/1e6:.2f} MB → {OUT_PATH}')

# Print top 15 operators as sanity check
print('\nTop 15 operators by total value:')
top = sorted(out_ops.values(), key=lambda x: -x['v'])[:15]
for o in top:
    print(f"  EUR {o['v']/1e9:>7.2f} bn  ({o['c']:>5}) {o['nsa']:>3} SAs  [{o['cf'] or 'no-CF'}] {o['n']}")
