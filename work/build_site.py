#!/usr/bin/env python3
"""Build the static browse site:  site/index.html (Vue page with embedded data) + site/frames/*.jpg

Run from work/:  ../.venv/bin/python build_site.py [--no-images] [--width 720] [--quality 68]

Steps:
  1. runs export_verified.py  (inventory.json + excluded_boxes.json + verify.json -> inventory_verified.json)
  2. downscales every keyframe referenced by the exported inventory into ../site/frames/ (skips ones already
     built at the same width/quality, tracked in ../site/frames/.build.json)
  3. writes ../site/index.html from site_template.html with the inventory JSON embedded

The result is a plain folder: drop it on GitHub Pages / any static host, or open index.html directly.
"""
import sys
# work/select.py shadows the stdlib `select` module that subprocess needs; drop the script dir from sys.path
sys.path = [p for p in sys.path if p not in ('', __import__('os').path.dirname(__import__('os').path.abspath(__file__)))]
import argparse
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.join(ROOT, 'site')
FRAMES_SRC = os.path.join(ROOT, 'frames')
FRAMES_DST = os.path.join(SITE, 'frames')

ap = argparse.ArgumentParser()
ap.add_argument('--no-images', action='store_true', help='skip frame generation (page still links to site/frames/)')
ap.add_argument('--width', type=int, default=720)
ap.add_argument('--quality', type=int, default=68)
args = ap.parse_args()

# 1. export
subprocess.run([sys.executable, os.path.join(HERE, 'export_verified.py')], check=True, cwd=HERE)
with open(os.path.join(ROOT, 'inventory_verified.json'), encoding='utf-8') as f:
    exported = json.load(f)['inventory']

# 2. slim the data for the page
KEEP = ('id', 'lines', 'kind', 'category', 'description', 'note', 'contents', 't_first', 'frames',
        'also_seen_at', 'confidence', 'review')
entries = []
for e in exported:
    n = {k: e[k] for k in KEEP if k in e and e[k] not in (None, [], '')}
    n['status'] = e['human']['status']            # '' | ok | wrong | unsure | duplicate
    if e['human'].get('edited_at'):
        n['edited_at'] = e['human']['edited_at'][:10]
    if e.get('ocr', {}).get('lines'):
        n['ocr_lines'] = e['ocr']['lines']
    if e.get('category_source') == 'human':
        n['cat_human'] = True
    entries.append(n)

needed = sorted({f for e in entries for f in e.get('frames', [])})

# 3. frames
os.makedirs(FRAMES_DST, exist_ok=True)
if not args.no_images:
    import cv2
    stamp_path = os.path.join(FRAMES_DST, '.build.json')
    try:
        with open(stamp_path) as f:
            built = json.load(f)
    except (OSError, ValueError):
        built = {}
    tag = f'{args.width}x{args.quality}'
    n_new = 0
    for fn in needed:
        dst = os.path.join(FRAMES_DST, fn)
        if built.get(fn) == tag and os.path.exists(dst):
            continue
        im = cv2.imread(os.path.join(FRAMES_SRC, fn))
        if im is None:
            print('missing source frame', fn, file=sys.stderr)
            continue
        h = round(im.shape[0] * args.width / im.shape[1])
        small = cv2.resize(im, (args.width, h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(dst, small, [cv2.IMWRITE_JPEG_QUALITY, args.quality])
        built[fn] = tag
        n_new += 1
    # drop frames no longer referenced
    for fn in list(built):
        if fn not in needed:
            try:
                os.remove(os.path.join(FRAMES_DST, fn))
            except OSError:
                pass
            del built[fn]
    with open(stamp_path, 'w') as f:
        json.dump(built, f)
    total = sum(os.path.getsize(os.path.join(FRAMES_DST, fn)) for fn in needed if os.path.exists(os.path.join(FRAMES_DST, fn)))
    print(f'frames: {len(needed)} referenced, {n_new} (re)built, {total / 1e6:.1f} MB')

# 4. page
with open(os.path.join(HERE, 'site_template.html'), encoding='utf-8') as f:
    tpl = f.read()
data = json.dumps({'entries': entries, 'built': __import__('datetime').date.today().isoformat()},
                  ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
assert '/*__DATA__*/' in tpl
html = tpl.replace('/*__DATA__*/', data)
with open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(html)
print(f'site/index.html: {len(entries)} entries, {len(html) / 1e6:.2f} MB')
