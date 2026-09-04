# Drawer inventory — handoff v3: data is done, next is a verification web tool

Goal of the project: turn `20260903_165847.mp4` (a 6m36s pan across cabinets of electronic
component drawers, plus a shelf of SMD resistor reels) into a structured, verified list of
what each drawer holds.

Supersedes `HANDOFF2.md` (which supersedes `handoff.md`). Those files still hold the video
facts, keyframe-selection reasoning, OCR fan-out details and Phase 1/2 outcomes; they are not
repeated here. This file describes the **current data**, how it was produced, its known
weaknesses, and what the next session should build.

## ⚠️ Read this first

- **Do NOT load the `claude-api` skill.** It auto-triggers on "Claude", "OCR", "vision model"
  etc. and dumps ~100k tokens into context. Nothing here uses the Anthropic API.
- **Do NOT invoke the `claude` CLI as a subprocess** (user instruction).
- User preferences: `uv` for Python (venv at `.venv/`, has `opencv-python-headless`, `numpy`),
  `rg` not `grep`/`find`, ask if intent is unclear.
- Physical position (cabinet/row/col) and stock quantity are **not wanted**. Identity only.

## Current state — the deliverables

| File | What |
|---|---|
| `inventory.json` | **Primary artifact.** `{"inventory": [...], "review_queue": [...]}` — 1,340 entries; review_queue is the subset with flags. |
| `inventory.md` | Human-readable table of the same data plus category counts. |
| `frames/k_0000.jpg … k_0528.jpg` | 529 keyframes, 1125×2000 portrait JPEGs (201 MB total). `frames/keyframes.json` maps `{seq, frame, t, sharp, file}`. |
| `work/excluded_boxes.json` | 18 entries excluded from the inventory (see "Boxes" below). |

### Entry schema (`inventory.json`)

```json
{
  "lines": ["CD 4526"],                 // verbatim label text lines from the best read
  "part_key": "CD4526",                 // normalised: uppercase, no spaces, dots only between digits
  "kind": "drawer",                     // drawer | reel | bin | column_label
  "category": "Logic (CMOS 4000)",
  "category_source": "part_number",     // label | part_number | context | inferred
  "category_confidence": "high",        // high | medium | low
  "description": "CD4526 programmable 4-bit down counter",
  "note": "…",                          // optional caveat (e.g. non-E96 reel value)
  "label_category": null,               // category word the OCR saw on the label, if any
  "reads_total": 4,                     // independent OCR reads of this label
  "reads_agreeing": 4,                  // reads matching the canonical text
  "confidence": 1.0,                    // reads_agreeing / reads_total
  "t_first": 317.3,                     // video time (s) of first read
  "frames": ["k_0448.jpg", "k_0449.jpg"], // keyframes where it was read
  "where": "row 3, second from left",   // coarse hint for finding it in the frame
  "variants": {"CD4528": 1},            // optional: other texts read for the same cluster
  "review": ["variants"]                // flags: single read | variants | low-confidence category
}
```

`category_source` meaning:
- `label` — the OCR read a category word on the label itself (e.g. "Zener", "OP. AMP.").
- `part_number` — derived from a recognised part number / value / Danish word.
- `context` — only from neighbouring drawers in the same pan segment.
- `inferred` — a guess about what such a drawer or a bought kit usually holds (user asked
  for these but said not to flag them high confidence; they are medium or low).

Review flag counts: 1053 entries clean, 250 single-read, 31 with text variants,
13 low-confidence category.

### Counts

| | |
|---|---|
| OCR reads (Sonnet subagents, 28 agents) | 4,702 |
| Entries after dedup | 1,340 (1,155 drawers, 84 SMD reels, 8 bins, 93 column labels) |
| Excluded box labels | 18 |
| Category confidence high / medium / low | 1,075 / 252 / 13 |
| Review queue | 287 |

Biggest categories: Resistor 307, Logic (74-series) 151, Capacitor (electrolytic) 79, Resistor (SMD 0603) 79, Logic (CMOS 4000) 71, Resistor (power) 66, Logic (74HC) 42, Capacitor (film/ceramic) 35, Op amp 26. Full list at the top of `inventory.md`.

## Pipeline (all in `work/`, run from `work/`)

```
ocr/agent_NN.jsonl   (raw OCR reads, one JSON object per label per frame — do not regenerate)
      │
      ▼  .venv/bin/python dedup3.py          → dedup3_out.json
      │
      ▼  .venv/bin/python categorize.py      → ../inventory.json, ../inventory.md, excluded_boxes.json
```

- `dedup3.py` (v3). Clusters reads within an 8 s window whose normalised line-sets are equal,
  or one is a subset of the other with a real anchor line (≥4 chars, contains a digit,
  not a package code). Multi-value "column label" reads never anchor a subset merge. Confusables O/0, I/1, B/8, S/5, Z/2 are folded for matching only.
  v2 bugs fixed here: dots were stripped (2.21Ω = 22.1Ω = 221Ω) and bare "0603" / folded
  "V0LTAGE" could anchor merges — this had collapsed all reels into one entry.
- `categorize.py`. ~200 ordered regex rules on `part_key` (Danish hardware vocabulary,
  part-number prefixes, 74xx and CD4000 function tables, resistor/capacitor value parsing),
  then a neighbour-context pass (±6 s), then a manual override dict for oddballs, then
  part-number descriptions. `kind` comes from the OCR `where` hints ("reel row", "bin").
  E96/E24 check on reel values adds a `note` when a value is not a standard one.
  **All categorisation is rule-based and re-runnable** — edit the rule tables, rerun, diff.

## Known weaknesses of the data (what a human needs to verify)

1. **Single reads (250).** Labels seen in only one keyframe; no corroboration. Some are
   genuine drawers at fast-pan spots, some are OCR hallucinations of cut-off labels.
2. **Variants (31).** Clusters where reads disagree on text. Most remaining ones are a
   partial read of the same label (e.g. `ZILOG/Z80A/CPU` vs `ZILOG/Z80A`); a few are OCR
   confusions like CD4526/CD4528. The earlier flood of resistor "variants" was a merge bug,
   now fixed (see column labels below).
3. **Duplicate drawers across the pan.** The camera passed some areas twice (e.g. CMOS 4000
   at t≈213 and t≈233; diodes at t≈85 and t≈174; op amps at t≈52 and t≈196). Dedup only
   merges within 8 s, so these appear twice on purpose. Position is not tracked, so the tool
   should let the user mark "same drawer as #N".
4. **Column labels (93, `kind: column_label`).** The old resistor cabinet has
   white labels listing every value in a column (e.g. `1.1KΩ / 11KΩ / 110KΩ/1.1MΩ / POWER`).
   These used to swallow the individual drawers via subset-merging; `dedup3.py` now treats a
   read with ≥3 values, or ≥2 values + POWER, as a column label that only merges with
   identical reads. User wants to decide keep/drop **case by case** in the tool. Whether a
   value-only drawer is a power resistor is also uncertain there (POWER is a column word).
5. **Tan dot-matrix cabinet (t≈300–345).** Bare handwritten numbers ("112", "140") were
   inferred to be 74HCxxx from neighbours — medium confidence.
6. **Inferred / low-confidence (13 low).** Stock-number-looking labels ("60001596"),
   "8A" cards next to bulbs (guessed Fuse), "STAG", "MOB", "?" etc.
7. **Boxes (18 excluded).** Entries first tagged as section headers ("DIODER", "MODSTANDE",
   "SMD-0603" dividers, "4071" tape label, "M6" bin, "MOB", "MEGET SMÅ", two POWER reads at
   t≈146). User said these are boxes with things in them, not headers; excluded for now,
   kept in `work/excluded_boxes.json`. They will need their own contents recorded.
8. **Non-standard reel values.** 519 Ω, 280 Ω, 22.0 Ω are not E96 — flagged with `note`.
9. **Non-existent part numbers** kept as read: LM353 (→LF353?), LM356 (→LF356?), BD738
   (→BD138?), "IRFB130 / P-CH" (contradictory).

## Next session: build the verification web tool

User's stated intent: *"a small webtool where the info can be edited and verified by the
user."* Nothing has been built yet. Decisions to confirm with the user before building
(ask, don't guess — user preference):

- **Hosting/runtime.** Options: (a) a single static HTML page that loads `inventory.json` and
  the frames from disk via a tiny local server (`python -m http.server` in the project dir),
  saving edits by download/paste-back; (b) a small Python server (FastAPI/Flask via `uv`)
  that serves frames and writes `inventory.json` in place. (b) is more convenient; (a) has no
  dependencies. The frames are 201 MB, local either way — not something to publish.
- **Edit model.** Per-entry: correct `lines`, pick a `category` (dropdown from the existing
  category list + free text), mark `verified` / `wrong` / `not a drawer`, merge with another
  entry (duplicate pass), add `note`. Keep the original OCR fields untouched and store human
  edits in separate fields (e.g. `human: {lines, category, status, merged_into, note,
  edited_at}`) so the rule pipeline can be rerun without clobbering them.
- **Verification UX** that the data supports well:
  - Show the entry's keyframe (`frames[0]`, or cycle through all `frames`) with the `where`
    hint; a crop is not available (bounding boxes were deliberately not collected), so a
    zoomable full frame is the right thing.
  - Work queue ordered by `review` flags first, then by `category_confidence`, then by
    `t_first` so neighbouring drawers come in sequence.
  - Filter by category / kind / source / flag; keyboard shortcuts for accept / next.
  - Side-by-side of `lines` vs `variants` for disagreement cases.
- **Output.** Write back to `inventory.json` (same schema plus `human` block), and regenerate
  `inventory.md`. Consider a `verified.json` export of only accepted entries.

Suggested first step for that session: probe the user with 3–4 questions (runtime choice,
whether edits go into `inventory.json` or a separate file, whether the excluded boxes should
appear in the tool as their own queue, whether duplicates across passes should be merged or
kept), then build the smallest version that shows frame + fields + accept/edit.

## Reproduce / extend

```bash
cd /home/jas/dev/tests/drawers/work
../.venv/bin/python dedup3.py        # ~2 s
../.venv/bin/python categorize.py    # ~1 s, prints counts and any uncategorised keys
```

To change a category rule: edit `RULES` (ordered; first match wins), `OVR` (per-key
overrides), `PDESC` (descriptions) in `categorize.py`. To re-include the boxes, remove the
`section_label` filter near the bottom of `categorize.py`.
