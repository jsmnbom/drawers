#!/usr/bin/env python3
"""Merge human edits (../verify.json, written by tool.py) into the OCR inventory.

Run from work/:  ../.venv/bin/python export_verified.py
Reads  ../inventory.json, excluded_boxes.json, ../verify.json
Writes ../inventory_verified.json, ../inventory_verified.md   (inventory.json is left untouched)

Rules:
  lines / category / note in an edit override the OCR values (originals kept under `ocr`)
  status not_drawer  -> dropped
  status duplicate   -> collapsed into its same_as target (target gets also_seen_at + merged frames);
                        a duplicate without a valid same_as is kept and flagged
  contents           -> list of {label, category} items copied onto the entry (multi-item drawers/boxes);
                        falls back to the auto-detected `items` from categorize.py when no human contents;
                        each human item gets a description via categorize.describe_item() when a part rule matches
  description        -> recomputed with categorize.describe() whenever lines or category were edited,
                        and for column labels marked ok/wrong (drops the "keep or drop case by case" advice)
                        (the OCR-time text described the old label/category); original kept under `ocr`
  everything else    -> kept, with human.status ('' if unreviewed)
"""
import collections
import json
import os

import categorize  # importable: its pipeline only runs under __main__

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
P = lambda *a: os.path.join(*a)  # noqa: E731


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


inv = (load(P(ROOT, 'inventory.json')) or {'inventory': []})['inventory']
boxes = load(P(HERE, 'excluded_boxes.json'), [])
edits = load(P(ROOT, 'verify.json'), {})

# Same id/key assignment as tool.py
entries = []
for e in inv + boxes:
    e = {k: v for k, v in e.items() if not k.startswith('_')}
    e.setdefault('review', [])
    e['id'] = len(entries)
    e['key'] = f"{e['part_key']}|{e['t_first']}"
    entries.append(e)

# resolve duplicate chains (a -> b -> c) to the final target
def target_of(i, seen=()):
    d = edits.get(entries[i]['key'], {})
    if d.get('status') != 'duplicate' or not isinstance(d.get('same_as'), int):
        return i
    t = d['same_as']
    if t < 0 or t >= len(entries) or t == i or t in seen:
        return i
    return target_of(t, seen + (i,))

out, dropped, dup_into, dup_bad = [], 0, 0, 0
by_id = {}
for e in entries:
    d = edits.get(e['key'], {})
    status = d.get('status', '')
    if status == 'not_drawer':
        dropped += 1
        continue
    n = {k: v for k, v in e.items() if k != 'key'}
    ocr = {}
    for fld in ('lines', 'category', 'note'):
        if fld in d and d[fld] != e.get(fld):
            ocr[fld] = e.get(fld)
            n[fld] = d[fld]
    if 'category' in d and d['category'] != e.get('category'):
        n['category_source'] = 'human'
        n['category_confidence'] = 'high'
    if n.get('category') == 'Resistor (SMD 0603)' and n.get('kind') == 'drawer':
        n['kind'] = 'reel'  # OCR missed the red reel tag; the SMD category (human or rule) says it is a reel
    n['human'] = {'status': status, **({'edited_at': d['edited_at']} if 'edited_at' in d else {}),
                  **({'same_as': d['same_as']} if 'same_as' in d else {})}
    if 'lines' in ocr or 'category' in ocr:
        new_desc = categorize.describe(n)
        if new_desc != e.get('description'):
            ocr['description'] = e.get('description')
            n['description'] = new_desc
    if n.get('kind') == 'column_label' and status in ('ok', 'wrong'):
        # a person confirmed this column label, so the OCR-time "keep or drop case by case" advice is
        # moot: describe it like a drawer with the same lines (e.g. "Power resistor(s): 0.10Ω, 1Ω")
        new_desc = categorize.describe({**n, 'kind': 'drawer'})
        if not new_desc or new_desc.startswith('Label: '):
            new_desc = 'Column label: ' + ' | '.join(n['lines'])
        if new_desc != n.get('description'):
            ocr.setdefault('description', e.get('description'))
            n['description'] = new_desc
    if d.get('contents'):
        n['contents'] = []
        for c in d['contents']:
            if not (c.get('label') or c.get('category')):
                continue
            c = {k: v for k, v in c.items() if k in ('label', 'category')}
            if c.get('label'):
                auto_cat, desc = categorize.describe_item(c['label'], n)
                c.setdefault('category', auto_cat)
                if desc and (c.get('category') or '').startswith(auto_cat or '\0'):
                    c['description'] = desc
            n['contents'].append(c)
    elif e.get('items'):
        n['contents'] = [{'label': c['label'], 'category': c.get('category')} for c in e['items']]
        n.pop('items', None)
    if ocr:
        n['ocr'] = ocr
    n['review'] = list(e['review'])
    if status == 'duplicate' and target_of(e['id']) == e['id']:
        n['review'].append('duplicate without valid same_as')
        dup_bad += 1
    by_id[e['id']] = n

for i, n in list(by_id.items()):
    if n['human']['status'] != 'duplicate':
        continue
    t = target_of(i)
    if t == i or t not in by_id:
        continue  # bad link or target dropped: keep as is
    tgt = by_id[t]
    tgt.setdefault('also_seen_at', []).append(n['t_first'])
    tgt['frames'] = tgt['frames'] + [f for f in n['frames'] if f not in tgt['frames']]
    tgt['reads_total'] += n['reads_total']
    tgt['reads_agreeing'] += n['reads_agreeing']
    tgt['confidence'] = round(tgt['reads_agreeing'] / tgt['reads_total'], 2)
    del by_id[i]
    dup_into += 1

out = sorted(by_id.values(), key=lambda e: e['t_first'])
json.dump({'inventory': out, 'unreviewed': [e['id'] for e in out if not e['human']['status']]},
          open(P(ROOT, 'inventory_verified.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

# markdown (same shape as categorize.py's)
st = collections.Counter(e['human']['status'] or 'unreviewed' for e in out)
cats = collections.Counter(e['category'] or 'UNCATEGORISED' for e in out)
kinds = collections.Counter(e['kind'] for e in out)
md = ['# Drawer inventory (verified)', '',
      f'{len(out)} entries ({kinds["drawer"]} drawers, {kinds["reel"]} SMD reels, {kinds["bin"]} bins, '
      f'{kinds["column_label"]} column labels, {kinds["section_label"]} boxes). '
      f'{dropped} dropped as not-a-drawer, {dup_into} duplicates collapsed, {dup_bad} duplicates with a bad link.', '',
      'Status: ' + ', '.join(f'{k} {v}' for k, v in st.most_common()) + '.', '',
      '## Categories', '', '| Category | Entries |', '|---|---|']
md += [f'| {c} | {n} |' for c, n in sorted(cats.items(), key=lambda x: (-x[1], x[0]))]
md += ['', '## Entries', '', 'Status = human verification status. Cat = category confidence (H/M/L) and source.', '',
       '| # | t (s) | Kind | Label | Category | Cat | Description | Status | Note | Flag |', '|---|---|---|---|---|---|---|---|---|---|']
SRC = {'label': 'label', 'part_number': 'part', 'context': 'ctx', 'inferred': 'inf', 'human': 'human', None: '-'}
KD = {'drawer': '', 'reel': 'reel', 'bin': 'bin', 'section_label': 'box', 'column_label': 'column'}
esc = lambda s: str(s).replace('|', '\\|')  # noqa: E731
for e in out:
    lab = esc(' / '.join(e['lines']))
    if e.get('contents'):
        lab += ' — contains: ' + esc('; '.join(f"{c.get('label','')} [{c.get('category','')}]" if c.get('category') else c.get('label','') for c in e['contents']))
    also = (' (also at ' + ', '.join(f'{t}s' for t in e['also_seen_at']) + ')') if e.get('also_seen_at') else ''
    md.append(f'| {e["id"]} | {e["t_first"]}{also} | {KD.get(e["kind"], e["kind"])} | {lab} | {esc(e["category"] or "")} | '
              f'{(e.get("category_confidence") or "-")[0].upper()}/{SRC.get(e.get("category_source"), "-")} | '
              f'{esc(e.get("description") or "")} | {e["human"]["status"]} | {esc(e.get("note") or "")} | {esc("; ".join(e["review"]))} |')
open(P(ROOT, 'inventory_verified.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
print(f'{len(out)} entries written; dropped {dropped}, collapsed {dup_into} duplicates, {dup_bad} bad duplicate links; '
      'status: ' + ', '.join(f'{k} {v}' for k, v in st.most_common()))
