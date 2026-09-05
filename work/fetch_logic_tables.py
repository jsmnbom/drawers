#!/usr/bin/env python3
"""Fetch part-number -> description tables from Wikipedia into logic_parts.json.

Run from work/ (manually, when the tables should be refreshed; CI does not run this):
    ../.venv/bin/python fetch_logic_tables.py

Sources (MediaWiki API, wikitext):
    List of 7400-series integrated circuits   -> "74":   {"00": "quad 2-input NAND gate", ...}
    List of 4000-series integrated circuits   -> "4000": {"4001": "quad 2-input NOR gate", ...}
    List of LM-series integrated circuits     -> "LM":   {"LM317": "adjustable positive regulator", ...}

categorize.py loads the result next to its hand-written F74 / F4000 tables (hand entries win).
"""
import json
import os
import re
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = 'https://en.wikipedia.org/w/api.php?action=parse&prop=wikitext&format=json&formatversion=2&page='
PAGES = {'74': 'List_of_7400-series_integrated_circuits',
         '4000': 'List_of_4000-series_integrated_circuits',
         'LM': 'List_of_LM-series_integrated_circuits'}


def fetch(page):
    req = urllib.request.Request(API + urllib.parse.quote(page), headers={'User-Agent': 'drawers-inventory/1.0 (personal parts list)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)['parse']['wikitext']


def clean(s):
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    s = re.sub(r'<ref[^>]*/>', '', s)
    s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    s = re.sub(r'<br\s*/?>', '; ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\{\{\s*TOC tab\|([^}|]*)[^}]*\}\}', r'\1', s)
    s = re.sub(r'\{\{\s*(?:N/A|n/a|anchor\|[^}]*|Dead link[^}]*|cite[^}]*)\}\}', '', s)
    for _ in range(3):  # nested templates: keep the last argument ({{overline|Q}} -> Q, {{nowrap|x}} -> x)
        s = re.sub(r'\{\{[^{}|]*(?:\|[^{}]*)?\}\}', lambda m: m.group(0)[2:-2].split('|')[-1].strip(), s)
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', s)
    s = re.sub(r'\[https?://\S+\s+([^\]]*)\]', r'\1', s)
    s = re.sub(r'\[https?://\S+\]', '', s)
    s = s.replace('&nbsp;', ' ').replace("'''", '').replace("''", '')
    s = re.sub(r'\s+', ' ', s).strip(' ;')
    return s


def tables(wt):
    """Yield (header_cells, rows) for every wikitable, cells as raw strings."""
    for m in re.finditer(r'\{\|.*?\n\|\}', wt, flags=re.S):
        body = m.group(0)
        header, rows, cur = [], [], None
        for line in body.split('\n')[1:-1]:
            line = line.strip()
            if line.startswith('|-'):
                if cur is not None:
                    rows.append(cur)
                cur = []
                continue
            if line.startswith('!'):
                header += [c.strip() for c in re.split(r'\s*!!\s*', line[1:])]
                continue
            if line.startswith('|'):
                if cur is None:
                    cur = []
                cells = re.split(r'\s*\|\|\s*', line[1:])
                # drop cell attributes ("style=... | value")
                cur += [c.split('|', 1)[1] if re.match(r'\s*[a-z-]+=[^|]*\|', c) else c for c in cells]
            elif cur:
                cur[-1] += ' ' + line  # continuation line inside a cell
        if cur:
            rows.append(cur)
        if header and rows:
            yield [clean(h) for h in header], rows


def col(header, *names):
    for i, h in enumerate(header):
        if any(h.lower().startswith(n) for n in names):
            return i
    return None


def parse(series, wt):
    out = {}
    for header, rows in tables(wt):
        pn, ds = col(header, 'part number'), col(header, 'description')
        if pn is None or ds is None:
            continue
        inp, outp = col(header, 'input'), col(header, 'output')
        for r in rows:
            if len(r) <= max(pn, ds):
                continue
            desc = clean(r[ds])
            if not desc:
                continue
            quals = [clean(r[i]) for i in (inp, outp) if i is not None and len(r) > i and clean(r[i])]
            desc = desc[0].lower() + desc[1:] if desc[:2].isupper() is False else desc
            if quals:
                desc += ', ' + ', '.join(quals)
            pns = clean(r[pn])
            if series == '74':
                keys = re.findall(r'74x(\d{2,5})\b', pns)
            elif series == '4000':
                keys = re.findall(r'\b(4\d{3,4})\b', pns)
            else:
                keys = re.findall(r'\b(LM\d{2,5}[A-Z]?)\b', pns)
            for k in keys:
                out.setdefault(k, desc)
    return out


if __name__ == '__main__':
    result = {}
    for series, page in PAGES.items():
        result[series] = parse(series, fetch(page))
        print(f'{series}: {len(result[series])} parts')
    json.dump(result, open(os.path.join(HERE, 'logic_parts.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False, sort_keys=True)
