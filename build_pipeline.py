#!/usr/bin/env python3
"""Honest rebuild of the contracts dataset with four corrections:

1. Use `importo_lotto` instead of `importo_aggiudicazione` for framework
   child CIGs (where the latter is duplicated framework total, not lot value).
2. Filter by `data_aggiudicazione_definitiva` year == 2024
   (excludes contracts awarded in 2023 that leaked through CIG-2024).
3. Annualize multi-year contracts by `durata_prevista` (in days).
   value_2024 = lot_value * min(12 months / contract months, 1.0)
   So a 3-year framework awarded in 2024 contributes 1/3 of its total.
4. Skip framework PARENT CIGs (those that appear as `cig_accordo_quadro` of
   other CIGs) so their value isn't double-counted with their children.

Also tracks per-CIG framework parent so we can compute a "framework-dominated"
flag per (SA, CPV).
"""
import json, csv, sys, glob, os
from collections import defaultdict
csv.field_size_limit(sys.maxsize)

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
OUT_PATH = os.path.join(RAW, 'italy_contracts_honest_2024.json')

print('Loading Lombardia SA registry (national)...')
with open(os.path.join(RAW, 'italy_sas_geo.json')) as f:
    sas = json.load(f)
sa_cfs = set(sas.keys())
print(f'  {len(sa_cfs):,} national SAs (geocoded, active)')

# ============== PASS 1: identify framework PARENT CIGs ==============
# Any CIG that appears in some other CIG's `cig_accordo_quadro` is a parent.
print('\nPass 1: identifying framework parent CIGs...')
parent_cigs = set()
n_rows = 0
for path in sorted(glob.glob(os.path.join(RAW, 'cig2024', 'cig_csv_2024_*.csv'))):
    with open(path, encoding='utf-8') as f:
        r = csv.DictReader(f, delimiter=';')
        for row in r:
            n_rows += 1
            akq = (row.get('cig_accordo_quadro') or '').strip()
            if akq:
                parent_cigs.add(akq)
print(f'  Scanned {n_rows:,} CIG rows')
print(f'  Framework parents identified: {len(parent_cigs):,}')

# ============== PASS 2: pull CIG records for our national SAs, skipping parents ==============
print('\nPass 2: collecting CIG metadata (skipping framework parents)...')
cig_records = {}
skipped_parents = 0
for path in sorted(glob.glob(os.path.join(RAW, 'cig2024', 'cig_csv_2024_*.csv'))):
    with open(path, encoding='utf-8') as f:
        r = csv.DictReader(f, delimiter=';')
        for row in r:
            cf = (row.get('cf_amministrazione_appaltante') or '').strip()
            if cf not in sa_cfs:
                continue
            cig = (row.get('cig') or '').strip()
            if not cig:
                continue
            if cig in parent_cigs:
                skipped_parents += 1
                continue
            prev = (row.get('flag_prevalente') or '').strip()
            is_prev = prev in ('1','true','True')
            existing = cig_records.get(cig)
            if existing is not None and not is_prev:
                continue  # keep the prevalente row if available
            try: lot = float(row.get('importo_lotto') or 0)
            except: lot = 0.0
            try: comp = float(row.get('importo_complessivo_gara') or 0)
            except: comp = 0.0
            try: dur = float(row.get('DURATA_PREVISTA') or row.get('durata_prevista') or 0)
            except: dur = 0.0
            cpv = (row.get('cod_cpv') or '').strip()
            akq = (row.get('cig_accordo_quadro') or '').strip()
            cig_records[cig] = {
                'sa_cf': cf,
                'cpv': cpv,
                'cpv_div': cpv[:2] if cpv else '',
                'lot': lot,
                'comp': comp,
                'dur_days': dur,
                'akq': akq,           # parent framework CIG (if child); else ''
                'oggetto': (row.get('oggetto_lotto') or row.get('oggetto_gara') or '')[:120],
                '_prev': is_prev,
            }
for v in cig_records.values():
    v.pop('_prev', None)
print(f'  Skipped {skipped_parents:,} framework-parent CIG rows')
print(f'  Unique national child/standalone CIGs: {len(cig_records):,}')

# ============== PASS 3: join aggiudicatari for winner info ==============
print('\nPass 3: joining aggiudicatari (winner per CIG)...')
RUOLO_PRIO = {
    'OPERATORE ECONOMICO MONOSOGGETTIVO': 0,
    'MANDATARIA': 1,
    'CONSORZIO STABILE': 2,
    'CONSORZIO ORDINARIO': 3,
    'CONSORZIO FRA SOCIETÀ COOPERATIVE DI PRODUZIONE E LAVORO': 4,
    'CONSORZIO TRA IMPRESE ARTIGIANE': 5,
    '': 10,
    'MANDANTE': 99,
    'IMPRESA AUSILIARIA': 100,
}
winners = {}
n=0
with open(os.path.join(RAW, 'aggiudicatari_csv.csv'), encoding='utf-8') as f:
    r = csv.DictReader(f, delimiter=';')
    for row in r:
        n += 1
        cig = (row.get('cig') or '').strip()
        if cig not in cig_records: continue
        ruolo = (row.get('ruolo') or '').strip().upper()
        cf = (row.get('codice_fiscale') or '').strip()
        nome = (row.get('denominazione') or '').strip()
        if not cf and not nome: continue
        prio = RUOLO_PRIO.get(ruolo, 50)
        existing = winners.get(cig)
        if existing is None:
            winners[cig] = {'cf': cf, 'nome': nome, 'prio': prio, 'is_rti': False}
        else:
            if cf and existing.get('cf') and cf != existing['cf']:
                existing['is_rti'] = True
            if prio < existing.get('prio', 999):
                existing['cf'] = cf; existing['nome'] = nome; existing['prio'] = prio
print(f'  CIGs with winner: {len(winners):,}')

# ============== PASS 4: join aggiudicazioni — get importo + date ==============
print('\nPass 4: joining aggiudicazioni (importo + date)...')
awards = {}  # cig -> {agg_value, agg_date, year, n_rows, n_bidders, ribasso_pct}
n=0
with open(os.path.join(RAW, 'aggiudicazioni_csv.csv'), encoding='utf-8') as f:
    r = csv.DictReader(f, delimiter=';')
    for row in r:
        n += 1
        cig = (row.get('cig') or '').strip()
        if cig not in cig_records: continue
        try: imp = float(row.get('importo_aggiudicazione') or 0)
        except: imp = 0.0
        d = (row.get('data_aggiudicazione_definitiva') or '')[:10]
        yr = None
        if len(d) >= 4 and d[:4].isdigit():
            yr = int(d[:4])
        # Competition signals
        try: nbid = int(float(row.get('numero_offerte_ammesse') or 0))
        except: nbid = 0
        try: noff = int(float(row.get('num_imprese_offerenti') or 0))
        except: noff = 0
        # Prefer numero_offerte_ammesse; fall back to num_imprese_offerenti
        bidders = nbid if nbid > 0 else noff
        try: rib = float(row.get('ribasso_aggiudicazione') or 0)
        except: rib = 0.0
        # Ribasso in ANAC is stored as a fraction (0.05 = 5%) for sane rows, but
        # there are corrupted rows with absurd values. Clamp to [0, 1] (0-100%).
        if rib < 0 or rib > 1.0:
            rib = None   # ignore obviously invalid
        existing = awards.get(cig)
        if existing is None:
            awards[cig] = {'agg_value': imp, 'agg_date': d, 'year': yr, 'n_rows': 1,
                           'bidders': bidders, 'rib': rib}
        else:
            existing['agg_value'] += imp
            existing['n_rows'] += 1
            if d and (not existing['agg_date'] or d > existing['agg_date']):
                existing['agg_date'] = d; existing['year'] = yr
            if bidders > (existing.get('bidders') or 0):
                existing['bidders'] = bidders
            if existing.get('rib') is None and rib is not None:
                existing['rib'] = rib
print(f'  CIGs with aggiudicazione record: {len(awards):,}')

# ============== ASSEMBLE: honest 2024 value ==============
# Hard sanity cap on per-CIG annualized value. Any single CIG above this
# is almost always an ANAC data-entry typo (e.g. EUR 14bn for a year of gas,
# EUR 1.9bn for a dishwasher, EUR 3bn for a school field trip). Legitimate
# multi-year frameworks above this threshold are already annualized down
# via durata_prevista. Real single-year contracts essentially never exceed
# this number — even huge national procurements get split into lots.
ANOMALY_CAP_EUR = 100_000_000   # 100 million

print('\nAssembling honest contracts dataset for 2024...')
contracts = []
n_no_winner = n_no_award = n_wrong_year = n_no_value = 0
n_capped = 0
sum_capped_excess = 0.0
for cig, meta in cig_records.items():
    w = winners.get(cig)
    if not w: n_no_winner += 1; continue
    a = awards.get(cig)
    if not a: n_no_award += 1; continue
    if a['year'] != 2024:
        n_wrong_year += 1
        continue
    val_lot = meta['lot']
    val_used = val_lot if val_lot > 0 else a['agg_value']
    if val_used <= 0:
        n_no_value += 1
        continue
    dur = meta['dur_days']
    if dur and dur > 0 and dur <= 3650:
        years = dur / 365.25
        annual_factor = min(1.0, 1.0 / years)
    else:
        annual_factor = 1.0
    val_2024 = val_used * annual_factor
    # Apply anomaly cap
    capped = False
    if val_2024 > ANOMALY_CAP_EUR:
        sum_capped_excess += (val_2024 - ANOMALY_CAP_EUR)
        n_capped += 1
        val_2024 = ANOMALY_CAP_EUR
        capped = True
    # Nominal value: full lot value, NO typo cap. The nominal-mode total
    # reproduces ANAC's official methodology — which means it inherits
    # ANAC's source typos too (€14bn gas, €288bn Dulbecco, etc.). The UI
    # makes this trade-off explicit.
    val_nominal = val_used
    contracts.append({
        'cig': cig,
        'sa_cf': meta['sa_cf'],
        'cpv_div': meta['cpv_div'],
        'op_cf': w['cf'],
        'op_nome': w['nome'],
        'op_is_rti': w['is_rti'],
        'importo': val_2024,
        'importo_n': val_nominal,
        'importo_full': val_used,
        'akq': meta['akq'],
        'dur_days': dur,
        'capped': capped,
        'bidders': a.get('bidders') or 0,
        'rib': a.get('rib'),
    })

print(f'  Final 2024 contracts: {len(contracts):,}')
print(f'  Dropped — no winner:         {n_no_winner:,}')
print(f'  Dropped — no aggiudicazione: {n_no_award:,}')
print(f'  Dropped — not 2024:          {n_wrong_year:,}')
print(f'  Dropped — zero value:        {n_no_value:,}')
print(f'  Capped at EUR {ANOMALY_CAP_EUR/1e6:.0f}M: {n_capped:,} contracts ({sum_capped_excess/1e9:.1f} bn removed as anomalies)')

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(contracts, f, separators=(',',':'), ensure_ascii=False)
print(f'\nWrote {OUT_PATH}  ({os.path.getsize(OUT_PATH)/1e6:.1f} MB)')

# Sanity: top SAs by annualized value
print('\n=== SANITY: top 15 SAs by ANNUALIZED 2024 value ===')
by_sa = defaultdict(lambda: {'v':0.0, 'c':0, 'name':''})
for c in contracts:
    b = by_sa[c['sa_cf']]
    b['v'] += c['importo']
    b['c'] += 1
    if c['sa_cf'] in sas:
        b['name'] = sas[c['sa_cf']]['nome']
for cf, b in sorted(by_sa.items(), key=lambda x: -x[1]['v'])[:15]:
    s = sas.get(cf, {})
    print(f"  EUR {b['v']/1e6:>9.1f}m  ({b['c']:>5}) {b['name'][:60]}  [{s.get('citta','?')}, {s.get('regione','?')[:15]}]")

# Dulbecco specifically
DULBECCO_CF = '01991530799'
db = by_sa.get(DULBECCO_CF, {'v':0,'c':0})
print(f'\n>> DULBECCO (Catanzaro) check:')
print(f'   Annualized 2024 value: EUR {db["v"]/1e6:.1f}m ({db["c"]} contracts)')

# Region totals
print('\n=== Regional totals (annualized) ===')
by_reg = defaultdict(float)
for c in contracts:
    s = sas.get(c['sa_cf'])
    if s: by_reg[s['regione']] += c['importo']
total = sum(by_reg.values())
print(f'Italy total: EUR {total/1e9:.1f} bn (was EUR 824.5 bn before honest fix)')
for r, v in sorted(by_reg.items(), key=lambda x:-x[1])[:10]:
    print(f'  {r:<35} EUR {v/1e9:>6.2f} bn')
