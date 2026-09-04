# Drawer inventory from video — handoff v2

Goal: turn `20260903_165847.mp4` (a pan across electronic component drawers) into a
structured list of what's in each drawer, via OCR of the drawer labels.

Supersedes `handoff.md`. That file's **Source material**, **Established findings**,
and **Preserved artifacts** sections remain accurate — read them there; they are not
repeated here. This file records the user's answers to the open questions, and revises
the pipeline.

## ⚠️ Read this first

**Do NOT load the `claude-api` skill.** It auto-triggers on words like "Claude", "OCR
via Claude", "vision model", etc. and dumps ~100k tokens of SDK reference into context.
It ended a previous session. We are **not** using the Anthropic API — OCR runs as
multimodal subagents inside the Claude Code session (covered by subscription, agents
can `Read` images).

## User decisions (2026-09-03, previously open questions)

- **Output format: JSON** (primary artifact). Deriving a Markdown/CSV view afterwards
  is fine but JSON is the deliverable.
- **Physical position: not wanted.** Identity only. No grid tracking, no cabinet/row/col.
- **Quantity/stock: not wanted.** Just what part each drawer holds.
- **Model bake-off: yes, run it** (user explicitly chose this over "just use Sonnet").
  Haiku 4.5 vs Sonnet on the same 30-frame slice spanning both cabinets
  (green ~t=90s, tan ~t=320s), then diff. If Haiku matches Sonnet on the tan labels,
  use Haiku for bulk + Sonnet re-reads on disagreements/low confidence; otherwise
  Sonnet everywhere.

## Revisions to the previous plan

1. **Drop the "path to saved crop" output field → "source frame path" instead.**
   The no-tiling decision means crops were never going to exist. Having agents emit
   bounding boxes to cut crops from is unreliable (vision models localize poorly).
   Each record instead carries the keyframe file path plus a coarse human-findable
   hint (e.g. `"where": "top-left area"`) so a human can verify against the frame.

2. **Thin the keyframes before OCR, don't just take best-per-second.**
   Consecutive 1 s keyframes overlap heavily during slow pan segments and are near
   identical when the camera is stationary. After picking sharpest-per-window, drop a
   keyframe if cumulative inter-frame motion since the previously *kept* keyframe is
   below a threshold (the 4 fps `profile.json` already has a `motion` field; the full
   scan should record it too). Expect this to cut ~400 reads to maybe 250–300 with no
   coverage loss. Keep *some* overlap deliberately — it's the corroboration signal
   for dedup.

3. **Confidence = cross-frame agreement, not self-reported score.**
   Keep the agent's 0–1 confidence field (it's cheap), but treat it as advisory. The
   real signal: the same drawer appears in several overlapping keyframes; during dedup,
   count independent reads that agree (after normalization). `reads_agreeing /
   reads_total` becomes the confidence in the final output. Flag anything with a
   disagreement (e.g. `CD 4526` vs `CD 4528`) for the review queue.

4. **Smaller OCR chunks per agent.** The old plan said ~10 agents × ~40 frames. A
   2000 px-tall image is expensive in context; 40 per agent risks truncation/quality
   fade late in the batch. Use ~15 frames per agent (so ~20 agents for 300 frames),
   launched in waves. Each agent writes one JSON object per drawer-label to its own
   JSONL file on disk (`work/ocr/agent_NN.jsonl`) — do **not** have agents return the
   data in their final report.

5. **Normalize part numbers during dedup.** Uppercase, strip internal whitespace
   (`CD 4076` → `CD4076` for matching, keep original text too), and compare with a
   small confusion set (O/0, I/1, B/8, S/5) before declaring two reads "different".
   Fuzzy match only across *adjacent* keyframes (timestamps within ~5 s) — the pan is
   monotonic-ish, so distant matches are more likely genuinely different drawers with
   similar numbers.

6. **Run long scans via the harness background-task mechanism, not `nohup ... &`.**
   That's what killed the full-fps scan last time. Foreground is fine too —
   `fullscan.py` is only ~3 min.

## Record schema (JSONL, one object per drawer-label read; dedup merges these)

```json
{
  "lines": ["1N972B", "1N973B", "Zener"],   // all text lines, verbatim
  "category": "Zener",                       // when present, else null
  "frame": "frames/k_0231.jpg",
  "t": 231.0,
  "where": "row ~3, second from left",       // coarse hint for human verification
  "confidence": 0.9                          // agent self-report, advisory only
}
```

Final output (`inventory.json`): merged records with `reads_total`,
`reads_agreeing`, list of source frames, and a separate `review_queue` array for
disagreements and low-agreement entries.

## Plan: two phases

**Phase 1 tunes the two load-bearing choices — frame selection and model — on small
slices. Phase 2 is the full run with those choices locked in. Do not start Phase 2
until Phase 1's exit criteria are met.**

### Phase 1 — find the best frame-selection algorithm and model

| # | Step | Status |
|---|---|---|
| 1.1 | Recreate venv (`uv venv .venv && uv pip install opencv-python-headless numpy`) | **done** (2026-09-03) |
| 1.2 | Full-fps sharpness scan (`work/fullscan.py` → `fullsharp.json`, ~3 min) — motion recording added | **done** — 23,718 frames, sharp med=406 p90=932 (4 fps med was 158) |
| 1.3 | **Selection tuning:** implement keyframe pick (sharpest per 1 s window, floor ~60) + motion-thinning (revision 2). Sweep the thinning threshold on the full data — plot/tabulate keyframe count vs threshold. Sanity-check by extracting the *thinned-away* frames for 2–3 dense segments and eyeballing that no drawer face appears only in a dropped frame. | **done** — T=350 → 270 keyframes (from 396), max time gap 3.0 s; `work/select.py`, selection in `work/keyframe_sel.json`; eyeball check on 3 dense segments (`work/thincheck/`) verdict SAFE (Haiku agent — see session notes) |
| 1.4 | **Selection validation:** extract the chosen keyframe set for two test slices (green ~t=85–100s, tan ~t=315–330s), downscaled to ~1125x2000. Confirm every drawer visible in those segments appears legibly in ≥2 kept keyframes (overlap is needed for agreement scoring later). | **partially done** — frames extracted (`work/slices/{green,tan}/` core, `{green,tan}_ext/` widened ±5 s with manifests). A Haiku read reported gaps, but mostly at slice edges; needs a proper Sonnet re-check on the `_ext` sets judging only the core window |
| 1.5 | **Model bake-off:** Haiku 4.5 vs Sonnet, same ~30 test-slice frames, same prompt/schema. Diff normalized part numbers. Decision rule: Haiku matches Sonnet on the tan labels → Haiku for bulk + Sonnet re-reads on review-queue entries; any tan-label divergence → Sonnet everywhere. | not started (was blocked — see session notes 2026-09-03) |
| 1.6 | Record the outcome (threshold, keyframe count, model choice, prompt used) at the bottom of this file before proceeding. | not started |

### Session notes 2026-09-03 (restart required, resume at 1.4)

- **Why the restart:** `~/.claude/settings.json` had `CLAUDE_CODE_SUBAGENT_MODEL: "haiku"`,
  which silently pinned **all** subagents to Haiku — the Agent tool's per-call `model:`
  override was ignored (verified by probes: `sonnet`, `opus`, and default all returned
  `claude-haiku-4-5-20251001`). With user approval the setting was removed (backup:
  `~/.claude/settings.json.bak-drawers`). New session should re-probe before trusting overrides.
- **Every subagent must state its model:** start each subagent prompt with
  *'MANDATORY FIRST LINE of your final report: "MODEL: <exact model id>" copied from your
  system prompt; reports without it are discarded.'* This is what caught the pin. Verify the
  line matches the requested model before trusting output.
- **Do NOT invoke the `claude` CLI as a subprocess** — user instruction, no exceptions.
- A project agent def `.claude/agents/ocr-sonnet.md` (model: sonnet) exists and should be
  loadable after restart; plain `model: "sonnet"` on general-purpose agents should also work
  now — either is fine, but check the MODEL line.
- Selection is settled: **floor 60, thinning T=350, 270 keyframes** (`work/keyframe_sel.json`
  has `kept` + `dropped`). Slice frame extraction pattern that works fast: per-frame accurate
  seek `ffmpeg -ss (i-0.5)/fps -i src -frames:v 1` (a full-video `select=` pass times out).
- Remaining: 1.4 Sonnet coverage re-check on `work/slices/{green,tan}_ext/` (17 frames each,
  core windows t=85–100 / t=315–330); 1.5 bake-off (Haiku subagents vs Sonnet subagents,
  21 core frames, JSONL to `work/bakeoff/`); 1.6 record outcomes below.

**Phase 1 exit criteria:** thinning threshold chosen with eyeball evidence; every
test-slice drawer legible in ≥2 keyframes; bulk model decided by diff, not vibes;
prompt frozen.

Fallback if the full-fps scan fails again: `work/best_per_sec.json` (4 fps
best-per-second, 396 entries) is usable directly for step 1.3, at the cost of a lower
sharpness floor (p10 ≈ 72 vs. hopefully ~2× that at 60 fps).

### Phase 2 — run it all

| # | Step | Status |
|---|---|---|
| 2.1 | Extract the full keyframe set (done via single decode pass piped into OpenCV — `work/extract_full.py` — not ffmpeg `select=`; 528 frames → `frames/` + `frames/keyframes.json`) | **done** (2026-09-03) |
| 2.2 | OCR fan-out: 28 Sonnet agents (00–05 at 15 frames, 06–27 at 20 frames after mid-run efficiency trim), waves of 6, JSONL in `work/ocr/agent_NN.jsonl` — 4,710 records, all MODEL lines verified claude-sonnet-5 | **done** |
| 2.3 | Dedup + agreement scoring (`work/dedup.py` v2: confusion-fold O/I/B/S/Z, line-set subset matching, 8 s window). No Sonnet re-read wave needed (bulk model was already Sonnet) | **done** — 1,081 drawers, 1,014 distinct labels |
| 2.4 | Emitted `inventory.json` (inventory + review_queue: 211 single-read, 98 with variants) and `inventory.md` summary table | **done** |
| 2.5 | Presented to user | **done** |

### Session notes (2026-09-03, session 3, mid-run efficiency trim)

Per user request during the fan-out: `ocr-sonnet` tools cut to `Read, Bash` (Write was
unused), prompt gained strict efficiency rules (read each image once, never re-read the
output JSONL, two-line report), and remaining chunks were rebuilt at 20 frames/agent
(28 agents total instead of 36). Subagent context was probed: no skills/MCP listings
leak into subagents; tool schemas are the main controllable overhead.

## Phase 1 outcomes (recorded 2026-09-03, session 3)

- **Selection algorithm changed** (supersedes step 1.3's thin-only approach): the
  1.4 re-check FAILED on both slices — whole sections (HC cabinet, several CD labels)
  were legible in only 1 keyframe. Root cause was NOT thinning: even the unthinned
  sharpest-per-second base set has inter-keyframe motion of 1000–2300 during fast
  pans, so consecutive keyframes don't overlap. Fix: motion-*bounded* greedy
  selection (`work/select2.py`): from each kept frame, keep the sharpest frame whose
  cumulative motion lies in [TMIN, MMAX]. This adds mid-second frames during fast
  pans and skips static stretches.
- **Parameters: MMAX=800, TMIN=300, floor 60 → 528 keyframes**
  (`work/keyframe_sel2.json`, sharp p10=120 med=436, max time gap 3.0 s).
- **Coverage re-validation (ext2 slices, 36+32 frames):** ~90%+ of labels legible in
  ≥2 keyframes; residual single-read labels: green 1 (a capacitor card at the core
  boundary), tan 4 (CD4066, CD4060/4063, CD4070, BC327) — all legible once, handled
  by the review-queue path in dedup. Accepted.
- **Bulk model: Sonnet everywhere.** Bake-off (13 green + 22 tan frames, both models,
  `work/bakeoff/*.jsonl`): Haiku produced silent misreads on green (B2X79/B7X79 for
  BZX79, 2N6282 for 2N6292, 1N5082 for 1N5062, RFD120, GBT-NCH) and diverged on tan
  (missed CD4526 entirely — Sonnet read it 5×; invented CD4074/CD4077/CD4085/CD4521/
  SC327 that Sonnet never saw). Decision rule triggered: tan divergence → Sonnet.
- **Frozen OCR prompt:** `work/ocr_prompt.md` (template with {OUTFILE}/{FRAMELIST}).
- Model-pin fix verified: ocr-sonnet agent → claude-sonnet-5, general-purpose with
  model:haiku → claude-haiku-4-5-20251001.

## Phase 3 — dedup fix + categorisation (2026-09-04, session 4)

User asked: fill categories from context + general knowledge; SMD reels were also filmed;
likely-contents guesses allowed but must not be flagged high confidence.

- **Dedup v3** (`work/dedup3.py`, output `work/dedup3_out.json`). Two v2 bugs found:
  `norm()` stripped all dots so 2.21Ω / 22.1Ω / 221Ω shared a key, and any ≥4-char line
  (incl. bare `0603`, and `VOLTAGE`→`V0LTAGE` after confusable folding) could anchor a
  subset merge. Result in v2: all ~85 SMD reels collapsed into one 271-read entry and
  20 regulator drawers into one 90-read entry. v3 keeps dots between digits, requires an
  anchor line to contain a real digit and not be a package code, drops bare-`0603` reads.
  4,702 reads → **1,226 entries** (was 1,081), max cluster 27 reads.
- **Categoriser** (`work/categorize.py`, run from `work/`, reads `dedup3_out.json`, writes
  `../inventory.json` + `../inventory.md`). Adds per entry: `kind`
  (drawer/reel/section_label/bin from the `where` hints), `category`, `category_source`
  (label / part_number / context / inferred), `category_confidence` (high/medium/low),
  `description` (part function, Danish→English), optional `note`, `review` flags.
  Rules: ~200 regexes on the normalised key (Danish hardware vocab, part-number prefixes,
  74/4000 function tables), then a neighbour-context pass, then manual overrides for
  oddballs. `inferred`/`low` mark guesses (e.g. bare "112" among HC drawers → 74HC112,
  stock-number-looking labels → Unknown, "8A" labels next to bulbs → Fuse).
- Review queue now also includes low-confidence categories (345 entries).
- `inventory.json` schema changed (new fields above; `variants` kept); `confidence` still
  = reads_agreeing/reads_total.
- User clarified: the 18 `section_label` entries are boxes with contents, not headers.
  Excluded from `inventory.json`/`.md` for now; kept in `work/excluded_boxes.json`.
- **Column labels** (2026-09-04): the old resistor cabinet has white labels listing every
  value in a column (e.g. `1.1KΩ / 11KΩ / 110KΩ/1.1MΩ / POWER`). Under subset-merging they
  swallowed the individual drawers (1.1KΩ and 11KΩ became one entry with "variants").
  `dedup3.py` now treats a read of ≥3 values, or ≥2 values + POWER, as a column label:
  it only merges with identical reads and never anchors a subset merge. Such entries are
  kept with `kind: column_label` — user wants to decide keep/drop case by case in the
  web tool. Rule tightened to ≥2 values + POWER after 0.75Ω/7.5Ω still merged. Result: 1,340 entries (1,155 drawers, 84 reels, 8 bins, 93 column labels), variants down from 101 to 31.
