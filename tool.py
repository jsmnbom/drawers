#!/usr/bin/env python3
"""Drawer inventory verification tool — stdlib-only local server.

Run:  .venv/bin/python tool.py [--port 8765]
Serves tool.html, the keyframes in frames/, and reads/writes verify.json.
"""
import argparse
import glob
import json
import re
import os
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(ROOT, 'frames')
VERIFY = os.path.join(ROOT, 'verify.json')
LOCK = threading.Lock()


def _norm(s):
    """Same normalisation as work/dedup3.py so keys line up with part_key."""
    s = re.sub(r'\s+', '', s.upper())
    return re.sub(r'(?<!\d)\.|\.(?!\d)', '', s)


_FOLD = str.maketrans('OIBSZ', '01852')


def load_reads():
    """(frame, key) -> where hint and per-frame read list, from the raw OCR reads.
    Each read has its own 'where'; dedup kept only the best read's hint per cluster,
    so the tool rebuilds a per-frame hint here."""
    exact, by_frame = {}, {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'work', 'ocr', 'agent_*.jsonl'))):
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                lines = [_norm(l) for l in r.get('lines') or [] if l and _norm(l)]
                if not lines or not r.get('where'):
                    continue
                key = '/'.join(lines)
                exact.setdefault((r['frame'], key), r['where'])
                by_frame.setdefault(r['frame'], []).append((frozenset(l.translate(_FOLD) for l in lines), r['where']))
    return exact, by_frame


def where_by_frame(e, exact, by_frame):
    keys = [e['part_key']] + list((e.get('variants') or {}).keys())
    full = frozenset(l.translate(_FOLD) for l in e['part_key'].split('/'))
    out = {}
    for fr in e.get('frames') or []:
        w = next((exact[(fr, k)] for k in keys if (fr, k) in exact), None)
        if w is None:  # partial (subset-merged) read of this label in this frame
            w = next((wh for s, wh in by_frame.get(fr, []) if s and s <= full), None)
        if w is not None:
            out[fr] = w
    return out


def load_entries():
    inv = json.load(open(os.path.join(ROOT, 'inventory.json'), encoding='utf-8'))['inventory']
    boxes_path = os.path.join(ROOT, 'work', 'excluded_boxes.json')
    boxes = json.load(open(boxes_path, encoding='utf-8')) if os.path.exists(boxes_path) else []
    exact, by_frame = load_reads()
    entries = []
    for e in inv + boxes:
        e = {k: v for k, v in e.items() if not k.startswith('_')}
        e['where_by_frame'] = where_by_frame(e, exact, by_frame)
        e.setdefault('kind', 'drawer')
        e.setdefault('review', [])
        e['id'] = len(entries)
        e['key'] = f"{e['part_key']}|{e['t_first']}"
        entries.append(e)
    # Flag later occurrences of the same part_key as possible duplicates;
    # the earliest (by t_first, then id) is treated as the original.
    by_key = {}
    for e in entries:
        by_key.setdefault(e['part_key'], []).append(e)
    for group in by_key.values():
        if len(group) > 1:
            group.sort(key=lambda e: (e['t_first'], e['id']))
            for e in group[1:]:
                if 'possible duplicate' not in e['review']:
                    e['review'].append('possible duplicate')
    return entries


def load_edits():
    if not os.path.exists(VERIFY):
        return {}
    with open(VERIFY, encoding='utf-8') as f:
        return json.load(f)


def save_edits(edits):
    fd, tmp = tempfile.mkstemp(dir=ROOT, prefix='.verify.', suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(edits, f, indent=1, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, VERIFY)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # quieter
        if '/frames/' not in (args[0] if args else ''):
            sys.stderr.write("%s\n" % (format % args))

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype, cache=False):
        if not os.path.isfile(path):
            self.send_error(404)
            return
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(size))
        self.send_header('Cache-Control', 'max-age=86400' if cache else 'no-store')
        self.end_headers()
        with open(path, 'rb') as f:
            while chunk := f.read(1 << 16):
                self.wfile.write(chunk)

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ('/', '/index.html'):
            return self._file(os.path.join(ROOT, 'tool.html'), 'text/html; charset=utf-8')
        if p == '/api/data':
            entries = load_entries()
            cats = sorted({e.get('category') for e in entries if e.get('category')})
            with LOCK:
                edits = load_edits()
            return self._json({'entries': entries, 'edits': edits, 'categories': cats})
        if p.startswith('/frames/'):
            name = os.path.basename(unquote(p[len('/frames/'):]))
            return self._file(os.path.join(FRAMES, name), 'image/jpeg', cache=True)
        self.send_error(404)

    def do_POST(self):
        p = urlparse(self.path).path
        if p != '/api/save':
            return self.send_error(404)
        n = int(self.headers.get('Content-Length', 0))
        try:
            req = json.loads(self.rfile.read(n).decode('utf-8'))
            key, edit = req['key'], req['edit']
        except Exception as ex:  # noqa: BLE001
            return self._json({'error': str(ex)}, 400)
        with LOCK:
            edits = load_edits()
            if edit is None or not edit:
                edits.pop(key, None)
            else:
                edits[key] = edit
            save_edits(edits)
        self._json({'ok': True, 'n': len(edits)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--host', default='127.0.0.1')
    a = ap.parse_args()
    os.chdir(ROOT)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f'Drawer verify tool: http://{a.host}:{a.port}/   (edits -> {VERIFY})')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
