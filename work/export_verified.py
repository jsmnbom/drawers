#!/usr/bin/env python3
"""Merge human edits (../verify.json, written by tool.py) into the OCR inventory.

Run from work/:  ../.venv/bin/python export_verified.py
Reads  ../inventory.json, ../verify.json
Writes ../inventory_verified.json, ../inventory_verified.md   (inventory.json is left untouched)

Rules:
  lines / category / note in an edit override the OCR values (originals kept under `ocr`)
  status not_drawer  -> dropped
  status old         -> kept as is; the drawer is real but probably empty/outdated (superseded by another
                        cabinet, due for consolidation). The site shows it with an 'old' badge.
  status duplicate   -> collapsed into its same_as target (target gets also_seen_at + merged frames);
                        a duplicate without a valid same_as is kept and flagged
  category           -> human and OCR categories both go through categorize.canon() (merged category names)
  lines / item labels-> value formatting normalised with categorize.norm_value() ("470uF/16V" -> "470µF/16V",
                        "4.7KΩ" -> "4,7kΩ"); this is presentation, so it is not recorded under `ocr`
  contents           -> list of {label, category, description} items on the entry (multi-item drawers/boxes):
                        the human list from verify.json, else the auto-detected `items` from categorize.py;
                        every item gets category + description from categorize.describe_item() (a human
                        item category wins; the description is derived from that category)
  description        -> recomputed with categorize.describe() whenever lines or category were edited
                        (the OCR-time text described the old label/category); original kept under `ocr`
  name               -> manufacturer part number(s) / values from the label (categorize.name_of(); the whole
                        label when it has none); the site lists entries by it. Items get name = canon_part(label).
                        A leading part number the name already says is stripped from descriptions (strip_name()).
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
edits = load(P(ROOT, 'verify.json'), {})

# Same id/key assignment as tool.py
entries = []
for e in inv:
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
        val = categorize.canon(d[fld]) if fld == 'category' and fld in d else d.get(fld)
        if fld in d and val != e.get(fld):
            ocr[fld] = e.get(fld)
            n[fld] = val
    if 'category' in d and d['category'] != e.get('category'):
        n['category_source'] = 'human'
        n['category_confidence'] = 'high'
    if n.get('category') == 'Resistor (SMD 0603)' and n.get('kind') == 'drawer':
        n['kind'] = 'reel'  # OCR missed the red reel tag; the SMD category (human or rule) says it is a reel
    n['human'] = {'status': status, **({'edited_at': d['edited_at']} if 'edited_at' in d else {}),
                  **({'same_as': d['same_as']} if 'same_as' in d else {})}
    edited = 'lines' in ocr or 'category' in ocr
    n['lines'] = [categorize.norm_value(l, n.get('category')) for l in n['lines']]
    if edited or n['lines'] != e['lines']:
        new_desc = categorize.describe(n)
        if new_desc != e.get('description'):
            if edited:
                ocr['description'] = e.get('description')
            n['description'] = new_desc
    n['name'] = categorize.name_of(n['lines'], n.get('category')) or ' / '.join(n['lines'])
    n['description'] = categorize.strip_name(n.get('description'), n['name'])
    items = d.get('contents') or e.get('items') or []
    n.pop('items', None)
    if items:
        n['contents'] = []
        for c in items:
            if not (c.get('label') or c.get('category')):
                continue
            c = {k: v for k, v in c.items() if k in ('label', 'category')}
            if c.get('label'):
                c['label'] = categorize.norm_value(c['label'], c.get('category') or n.get('category'))
                c['category'], desc = categorize.describe_item(c['label'], n, c.get('category'))
                c['name'] = categorize.canon_part(c['label'], c.get('category') or n.get('category'))
                desc = categorize.strip_name(desc, c['name'])
                if desc:
                    c['description'] = desc
            else:
                c['category'] = categorize.canon(c['category'])
            n['contents'].append(c)
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
