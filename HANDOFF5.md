# Drawer inventory — handoff v5: static browse site built

Supersedes `HANDOFF4.md` for the "next task" section only; everything else there still applies
(read its ⚠️ section first: no `claude-api` skill, no `claude` subprocess, never touch `verify.json`).

## What was decided (user answers, 2026-09-04)

- Single `index.html` with embedded JSON; images as downscaled keyframes, ~50 MB max total;
  show all entries with a status badge; host on GitHub Pages or similar.

## What exists

| File | What |
|---|---|
| `work/build_site.py` | Runs `export_verified.py`, downscales referenced frames (720 px wide, JPEG q68) into `site/frames/`, embeds slimmed inventory JSON into `work/site_template.html` → `site/index.html`. `--no-images` skips frames. Incremental: `site/frames/.build.json` records what is built. |
| `work/site_template.html` | Vue 3 (jsdelivr CDN) page. `/*__DATA__*/` is replaced by the JSON. |
| `site/` | Output folder, ~37 MB (449 frames + 0.4 MB HTML). Deploy this folder as-is. Not committed anywhere yet. |

`export_verified.py` recomputes `description` (via `categorize.describe()`) for every entry whose
`lines` or `category` were edited in `verify.json`; the OCR-time text is kept under `ocr.description`.
Human `contents` items get a per-part description via `categorize.describe_item()` when a part rule
matches. `categorize.py` is importable for this (its pipeline runs only under `__main__`).

Rebuild after more verification:  `cd work && ../.venv/bin/python build_site.py`  (≈7 s; frames only rebuilt if new).

## Page features

Search (label, category, description, note, contents, original OCR), category / kind / status
filters, grouped-by-category or flat table view, sort by value (Ω and F parsed numerically),
label, or video order. Detail panel: lines, category, description, note, contents, struck-through
OCR read when corrected, video time, keyframe browser with "open image". State lives in the URL
hash (`#cat=Resistor&id=75`), so links are shareable. Light/dark follows the system theme.
Status badges: verified / corrected / unsure / unreviewed (`ok` / `wrong` / `unsure` / `''`).

## Possible follow-ups (not requested)

- Per-drawer crops instead of whole keyframes (would need bounding boxes from the OCR step).
- Vendor `vue.global.prod.js` into `site/` to remove the CDN dependency.
