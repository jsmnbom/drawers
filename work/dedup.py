"""Dedup OCR reads into inventory.json (HANDOFF2 revisions 3 & 5), v2.

- Normalize per line: uppercase, strip whitespace/dots.
- Fold confusables (O/0, I/1, B/8, S/5, Z/2) for matching only.
- Cluster (union-find): reads within WINDOW seconds merge when their folded
  line-SETS are equal, or one is a subset of the other and the shared part
  includes a line of length >= 4 (handles a missed category/extra line without
  merging short resistor values like 13K vs 130K).
- Confidence = reads_agreeing / reads_total (exact normalized-key majority).
- Review queue: single-read clusters and clusters with any key disagreement.
"""
import json, glob, re, collections

WINDOW = 8.0
FOLD = str.maketrans('OIBSZ', '01852')

def norm(s):
    return re.sub(r'[\s.]+', '', s.upper())

recs = []
for path in sorted(glob.glob('ocr/agent_*.jsonl')):
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        lines = [norm(l) for l in r['lines'] if l and norm(l)]
        if not lines:
            continue
        r['_key'] = '/'.join(lines)
        r['_set'] = frozenset(l.translate(FOLD) for l in lines)
        recs.append(r)
recs.sort(key=lambda r: r['t'])

def match(a, b):
    A, B = a['_set'], b['_set']
    if A == B:
        return True
    small, big = (A, B) if len(A) < len(B) else (B, A)
    return small <= big and any(len(l) >= 4 for l in small)

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

inventory, review = [], []
for members in clusters.values():
    keys = collections.Counter(m['_key'] for m in members)
    canon_key, agree = keys.most_common(1)[0]
    best = max((m for m in members if m['_key'] == canon_key),
               key=lambda m: (len(m['lines']), m.get('confidence', 0)))
    cats = collections.Counter(m['category'] for m in members if m.get('category'))
    entry = {
        'lines': best['lines'],
        'part_key': canon_key,
        'category': cats.most_common(1)[0][0] if cats else None,
        'reads_total': len(members),
        'reads_agreeing': agree,
        'confidence': round(agree / len(members), 2),
        't_first': round(min(m['t'] for m in members), 1),
        'frames': sorted({m['frame'] for m in members}),
        'where': best.get('where'),
    }
    if len(keys) > 1:
        entry['variants'] = {k: c for k, c in keys.items() if k != canon_key}
    inventory.append(entry)
    if len(members) == 1 or len(keys) > 1:
        review.append(entry)

inventory.sort(key=lambda e: e['t_first'])
review.sort(key=lambda e: e['t_first'])
json.dump({'inventory': inventory, 'review_queue': review},
          open('../inventory.json', 'w'), indent=1)
print(f'{len(recs)} reads -> {len(inventory)} drawers, {len(review)} in review queue')
print(f'single-read: {sum(1 for e in inventory if e["reads_total"]==1)}, '
      f'disagreements: {sum(1 for e in inventory if "variants" in e)}')
