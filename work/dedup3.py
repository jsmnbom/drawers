"""Dedup OCR reads into inventory.json, v3.

Changes vs v2 (dedup.py):
- norm() keeps dots between digits (2.21Ω vs 22.1Ω vs 221Ω are different reels),
  still strips whitespace and other dots (OP. AMP. -> OPAMP).
- Subset-merge anchor line must contain a digit and not be a bare package code
  (0603/0805/1206/0402) — prevents "0603" or "VOLTAGE/REGULATOR" partial reads
  from chaining unrelated drawers into one cluster.
- Reads consisting only of a bare package code are dropped (no information).
- Keeps every read's `where` hint per cluster (used later to tag reels).
"""
import json, glob, re, collections

WINDOW = 8.0
FOLD = str.maketrans('OIBSZ', '01852')
PACKAGES = {'0402', '0603', '0805', '1206'}

def norm(s):
    s = re.sub(r'\s+', '', s.upper())
    s = re.sub(r'(?<!\d)\.|\.(?!\d)', '', s)   # drop dots not between digits
    return s

def is_anchor(l):
    return len(l) >= 4 and any(c.isdigit() for c in l) and l not in PACKAGES

RVAL = re.compile(r'(\d+(?:[.,]\d+)?)(R|K|M)?Ω?(/(\d+(?:[.,]\d+)?)(R|K|M)?Ω?)*')
def is_column_label(lines):
    """A read listing >=3 resistor values (optionally + POWER) is a column label,
    not a drawer; it must never anchor a subset merge (it would swallow the drawers)."""
    vals = [l for l in lines if RVAL.fullmatch(l) and any(c.isdigit() for c in l)]
    rest = [l for l in lines if l not in vals]
    return all(r == 'POWER' for r in rest) and (len(vals) >= 3 or (len(vals) >= 2 and rest))

recs = []
for path in sorted(glob.glob('ocr/agent_*.jsonl')):
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        lines = [norm(l) for l in r['lines'] if l and norm(l)]
        if not lines or all(l in PACKAGES for l in lines):
            continue
        r['_key'] = '/'.join(lines)
        r['_set'] = frozenset(l.translate(FOLD) for l in lines)
        r['_column'] = is_column_label(lines)
        r['_anchors'] = frozenset() if r['_column'] else frozenset(l.translate(FOLD) for l in lines if is_anchor(l))
        recs.append(r)
recs.sort(key=lambda r: r['t'])

def match(a, b):
    A, B = a['_set'], b['_set']
    if A == B:
        return True
    small, big = (a, b) if len(A) < len(B) else (b, a)
    if big['_column'] or small['_column']:
        return False
    return small['_set'] <= big['_set'] and bool(small['_anchors'])

parent = list(range(len(recs)))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    parent[find(a)] = find(b)

for i, a in enumerate(recs):
    for j in range(i + 1, len(recs)):
        b = recs[j]
        if b['t'] - a['t'] > WINDOW:
            break
        if match(a, b):
            union(i, j)

clusters = collections.defaultdict(list)
for i in range(len(recs)):
    clusters[find(i)].append(recs[i])

inventory = []
for members in clusters.values():
    keys = collections.Counter(m['_key'] for m in members)
    canon_key, agree = keys.most_common(1)[0]
    best = max((m for m in members if m['_key'] == canon_key),
               key=lambda m: (len(m['lines']), m.get('confidence', 0)))
    cats = collections.Counter(m['category'] for m in members if m.get('category'))
    entry = {
        'lines': best['lines'],
        'part_key': canon_key,
        'label_category': cats.most_common(1)[0][0] if cats else None,
        'reads_total': len(members),
        'reads_agreeing': agree,
        'confidence': round(agree / len(members), 2),
        't_first': round(min(m['t'] for m in members), 1),
        'frames': sorted({m['frame'] for m in members}),
        'where': best.get('where'),
        '_wheres': [m.get('where') or '' for m in members],
        '_column': best['_column'],
    }
    if len(keys) > 1:
        entry['variants'] = {k: c for k, c in keys.items() if k != canon_key}
    inventory.append(entry)

inventory.sort(key=lambda e: e['t_first'])
json.dump(inventory, open('dedup3_out.json', 'w'), indent=1, ensure_ascii=False)
print(f'{len(recs)} reads -> {len(inventory)} entries')
print(f'single-read: {sum(1 for e in inventory if e["reads_total"]==1)}, '
      f'disagreements: {sum(1 for e in inventory if "variants" in e)}, '
      f'max reads: {max(e["reads_total"] for e in inventory)}')
