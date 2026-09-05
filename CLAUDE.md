# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Searchable inventory of electronic-component drawers, OCR'd from a video pan (`20260903_165847.mp4`)
across the cabinets. Published at https://jsmnbom.github.io/drawers/. This file replaces the former
`HANDOFF*.md` notes (removed in git; pipeline history lives in the git log and `work/` docstrings).

## Hard rules

- **Never delete, rewrite or hand-edit `verify.json`.** It holds the user's human verification edits;
  only `tool.py` (via the browser UI) writes it. Also never hand-edit `inventory.json` (generated).
- **Do not load the `claude-api` skill.** It auto-triggers on "OCR"/"vision"/"Claude" but nothing here
  calls the Anthropic API; it only wastes context. Do not invoke the `claude` CLI as a subprocess.
- Physical position (cabinet/row/col) and stock quantity are **not wanted** in the data or UI. Identity only.
- Tools are for internal use: no polish needed, but text must be readable in dark mode (no low-contrast
  greys or default link colours).
- Python via the existing `uv` venv at `.venv/` (stdlib + `numpy`, `opencv-python-headless`; no pyproject).
  No tests or linters exist.

## Commands

```bash
# verification tool (needs full-size keyframes in frames/, local only) -> http://127.0.0.1:8765
.venv/bin/python tool.py            # "address in use" => pkill -f tool.py

# rebuild the static site (run from work/)
cd work && ../.venv/bin/python build_site.py              # also downscales newly referenced frames (needs frames/)
cd work && ../.venv/bin/python build_site.py --no-images  # what CI runs; then open site/index.html

# regenerate the OCR-derived data (rarely needed; run from work/)
cd work && ../.venv/bin/python dedup3.py && ../.venv/bin/python categorize.py && ../.venv/bin/python export_verified.py

# refresh the 74 / 4000 / LM part tables from Wikipedia (manual, rarely; writes work/logic_parts.json)
cd work && ../.venv/bin/python fetch_logic_tables.py
```

CI (`.github/workflows`) runs `build_site.py --no-images` on every push to `main` and deploys `site/`.
Commit `site/frames/` only when new frames were generated locally; `site/index.html`,
`inventory_verified.*` and `inventory.md` are gitignored build outputs.

## Data flow

```
work/ocr/agent_*.jsonl  --dedup3.py-->  work/dedup3_out.json  --categorize.py-->  inventory.json
inventory.json + verify.json  --export_verified.py-->  inventory_verified.json
inventory_verified.json + work/site_template.html   --build_site.py-------->  site/index.html (JSON embedded at /*__DATA__*/)
```

- **Entry identity**: `verify.json` is keyed `"{part_key}|{t_first}"`; `same_as` references use the
  entry `id`, which is the index into `inventory.json` (assigned identically by `tool.py` and
  `export_verified.py`). `categorize.py` appends the `section_label` boxes after all other entries
  (they used to live in a separate `excluded_boxes.json`); boxes that are not real containers get
  `not_drawer`. Changing `dedup3.py` or category rules can change keys and orphan
  edits, so diff keys before and after.
- **Edit record fields** (all optional): `status` (`ok | wrong | not_drawer | duplicate | unsure | old`),
  `lines`, `category`, `note`, `same_as`, `contents`, `edited_at`. `wrong` means "OCR misread, lines
  corrected" (still a real drawer); `old` means a real but superseded/likely-empty drawer, kept and badged.
- **Export semantics** (`work/export_verified.py` docstring is authoritative): human `lines/category/note`
  override OCR values with originals kept under `ocr`; `not_drawer` dropped; `duplicate` collapsed into
  its `same_as` target; `description` recomputed via `categorize.describe()` when lines/category changed;
  `contents` = human list or auto-detected `items`. `categorize.py` is importable for this because its
  pipeline only runs under `__main__`.
- **Category rules** live in `work/categorize.py`: `RULES` (ordered; `(regex, category, confidence,
  description[, note])`), `OVR` (per-key overrides, same shape plus source), `PDESC` (per-part
  descriptions, beat rule text), `CAT_MERGE`/`canon()` (fine rule names -> published categories; also
  applied to human categories), `split_items()`/`DESCR` (multi-item labels). `describe()` is the single
  description path (OCR pipeline, post-edit re-describe, and `describe_item()` for contents items);
  `description` is part identity only, OCR/position/translation remarks go in `note`.
  `work/logic_parts.json` (from `fetch_logic_tables.py`) supplies 74 / 4000 / LM part functions.
- **Frontends**: both `tool.html` and `work/site_template.html` are single-file Vue 3 pages (jsdelivr CDN).
  The site defaults to items mode, keeps search/filter/sort/selection state in the URL hash; the tool has keyboard shortcuts
  `j/k a w x u o d m [ ] e /`.
- `work/select.py` shadows the stdlib `select` module; scripts in `work/` that use `subprocess` strip the
  script dir from `sys.path` first (see `build_site.py`).
