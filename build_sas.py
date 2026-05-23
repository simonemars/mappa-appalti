#!/usr/bin/env python3
"""Build per-(SA, CPV) aggregates → data/sas.json.gz, from the honest
contracts dataset (annualized 2024 values).

Also computes a per-bucket framework dominance signal:
- 'fd': highest share that a single `cig_accordo_quadro` family contributes
  to this (SA, CPV) bucket's value. If > 0.5, the bucket is dominated by
  one framework agreement.
"""
import json, re, gzip, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_PATH = os.path.join(HERE, 'raw', 'italy_contracts_honest_2024.json')
SAS_PATH = os.path.join(HERE, 'raw', 'italy_sas_geo.json')
OUT_PATH = os.path.join(HERE, 'data', 'sas.json.gz')

CPV_DIVS = {
    '45':'Lavori di costruzione','33':'Apparecchiature mediche, farmaceutici',
    '85':'Servizi sanitari e di assistenza sociale','71':'Servizi architettonici, di ingegneria',
    '90':'Servizi ambientali, rifiuti, fognari','50':'Servizi di riparazione e manutenzione',
    '79':'Servizi per le imprese','72':'Servizi informatici (IT)',
    '60':'Servizi di trasporto','09':'Prodotti petroliferi, combustibili, energia elettrica',
}
SCOPE = set(CPV_DIVS.keys())

LEGAL = re.compile(r"\b(s\.?r\.?l\.?|s\.?p\.?a\.?|s\.?n\.?c\.?|s\.?a\.?s\.?|s\.?c\.?a\.?r\.?l\.?|s\.?c\.?p\.?a\.?|soc\.? coop\.?|società cooperativa|s\.?b\.?|società benefit)\b", re.IGNORECASE)
def canon(name):
    if not name: return ''
    return re.sub(r'[^A-Z0-9]+',' ', LEGAL.sub('', name.upper())).strip()
def op_key(c):
    cf = (c.get('op_cf') or '').strip()
    if cf and cf != '00000000000': return cf
    nm = canon(c.get('op_nome',''))
    return 'NM:'+nm if nm else None
def short(n, lim=55):
    n = (n or '').strip()
    return (n[:lim-1]+'…') if len(n)>lim else n

print('Loading contracts...')
with open(CONTRACTS_PATH) as f:
    contracts = json.load(f)
print(f'  {len(contracts):,} contracts')
with open(SAS_PATH) as f:
    sas = json.load(f)

# Aggregate per (sa, cat) — track operators + framework groups
agg = defaultdict(lambda: defaultdict(lambda: {
    'v': 0.0, 'c': 0,
    'ops': defaultdict(lambda: {'n':'','v':0.0,'c':0,'r':False}),
    'akq': defaultdict(float),       # framework parent CIG -> value contributed
}))

n_kept = 0
for c in contracts:
    imp = c.get('importo', 0) or 0
    if imp <= 0: continue
    div = c.get('cpv_div','')
    if not div: continue
    k = op_key(c)
    if not k: continue
    sa = c['sa_cf']
    n_kept += 1
    akq = c.get('akq', '') or ''
    for cat in (div, 'ALL'):
        if cat != 'ALL' and cat not in SCOPE: continue
        b = agg[sa][cat]
        b['v'] += imp; b['c'] += 1
        o = b['ops'][k]
        nm = c.get('op_nome','')
        if len(nm) > len(o['n']): o['n'] = nm
        o['v'] += imp; o['c'] += 1
        if c.get('op_is_rti'): o['r'] = True
        if akq:
            b['akq'][akq] += imp

out_sa = {}
n_cat_dropped = 0
for sa_cf, divs in agg.items():
    sa_info = sas.get(sa_cf)
    if not sa_info: continue
    cats = {}
    for div, b in divs.items():
        if div != 'ALL' and b['c'] < 2 and b['v'] < 10000:
            n_cat_dropped += 1; continue
        ops_all = list(b['ops'].items())
        by_val = sorted(ops_all, key=lambda x:-x[1]['v'])[:5]
        by_cnt = sorted(ops_all, key=lambda x:-x[1]['c'])[:5]
        seen = {}
        for k, o in by_val + by_cnt:
            if k not in seen: seen[k] = o
        ops_payload = [[short(o['n']), round(o['v']), o['c'], 1 if o['r'] else 0] for _, o in seen.items()]
        tot_v = b['v']; tot_c = b['c']
        t1v = by_val[0][1]['v']/tot_v if tot_v>0 else 0
        t3v = sum(o['v'] for _,o in by_val[:3])/tot_v if tot_v>0 else 0
        t1c = by_cnt[0][1]['c']/tot_c if tot_c>0 else 0
        t3c = sum(o['c'] for _,o in by_cnt[:3])/tot_c if tot_c>0 else 0
        # Framework dominance: highest share from a single parent framework
        fd = 0.0
        if b['akq'] and tot_v > 0:
            fd = max(b['akq'].values()) / tot_v
        cats[div] = {
            'v': round(tot_v), 'c': tot_c, 'no': len(b['ops']),
            'o': ops_payload,
            't1v': round(t1v,3), 't3v': round(t3v,3),
            't1c': round(t1c,3), 't3c': round(t3c,3),
            'fd': round(fd, 3),
        }
    if not cats: continue
    out_sa[sa_cf] = {
        'n': sa_info['nome'],'nt': sa_info.get('natura',''),
        'pv': sa_info['prov'],'ct': sa_info['citta'],'rg': sa_info['regione'],
        'la': round(sa_info['lat'],5),'lo': round(sa_info['lon'],5),
        'ih': bool(sa_info.get('in_house', False)),
        'pa': bool(sa_info.get('partecipata', False)),
        'cats': cats,
    }

n_ops_distinct = len({op_key(c) for c in contracts if op_key(c)})
total_value = sum(c['importo'] for c in contracts)
data = {'sas': out_sa, 'cpv_divs': CPV_DIVS, 'meta': {
    'source':'ANAC — BDNCP','datasets':['aggiudicazioni','aggiudicatari','cig-2024','stazioni-appaltanti'],
    'fetched':'2026-05-22','window':'2024 (annualizzato)','region':'Italia',
    'n_contracts': len(contracts),'n_sas': len(out_sa),
    'n_operators_distinct': n_ops_distinct,
    'total_value': total_value,
    'honest_v1': True,    # flag — annualized + 2024-filtered + framework-parent-skipped
}}
raw = json.dumps(data, separators=(',',':'), ensure_ascii=False).encode('utf-8')
gz = gzip.compress(raw, compresslevel=9)
with open(OUT_PATH, 'wb') as f: f.write(gz)
print(f'\nSAs with data: {len(out_sa):,}')
print(f'Trivial cats dropped: {n_cat_dropped:,}')
print(f'Raw:  {len(raw)/1e6:.2f} MB')
print(f'Gzip: {len(gz)/1e6:.2f} MB → {OUT_PATH}')
