# Drawer inventory from video — handoff

Goal: turn `20260903_165847.mp4` (a pan across electronic component drawers) into a
structured list of what's in each drawer, via OCR of the drawer labels.

## ⚠️ Read this first

**Do NOT load the `claude-api` skill.** It auto-triggers on words like "Claude", "OCR
via Claude", "vision model", etc. and dumps ~100k tokens of SDK reference into context.
It ended the previous session. We are **not** using the Anthropic API — see Decisions.

## Source material

`/home/jas/dev/tests/drawers/20260903_165847.mp4` — 3.5 GB, h264 + aac.

| Property | Value |
|---|---|
| Resolution | 3840x2160 stored, **rotated to 2160x3840 portrait** on decode |
| Frame rate | 59.94 fps |
| Duration | 395.7 s (6m36s) |
| Frames | 23,665 |
| Full decode time | ~108 s with `-hwaccel cuda` |

## Established findings

**At least two cabinets with two label styles.**

1. Green/white printed label tape — e.g. `1N5624 / Diode`, `BZX55C12 / Zener`,
   `1N5818 / Schottky`. High contrast, easy. Usually part number + category, often
   with a schematic symbol glyph.
2. Tan dot-matrix/typewriter labels — e.g. `CD 4076`, `CD 40106`, `CD 4511`. Low
   contrast, no category line. This is the hard set.

**Label content is not a fixed schema.** Some have part + category, some part only,
some have two part numbers (`1N972B / 1N973B  Zener`). Capture all text lines found
rather than forcing fixed fields.

**Motion blur is the real constraint, not OCR.** Sharpness (Laplacian variance on
320x569 grayscale) ranges 4 → 1562, median 158. Many frames are unusable garbage
(e.g. t=15s). Frame *selection* is the load-bearing stage.

**tesseract is not viable.** Confirmed by test: on a sharp tan-label frame it produced
pure noise; on a sharp green-label frame it recovered exactly one string (`NS5624`,
itself a misread of `1N5624`) out of ~12 labels. It has no layout prior and the labels
are small within a cluttered 4K scene. Don't revisit this.

**A vision model reads these correctly.** In-session, reading a full frame downscaled
to 1125x2000, Claude recovered every label on the hard tan cabinet:
`CD 4076, CD 4081, CD 4099, CD 40106, CD 4511, CD 4512, CD 4526, CD 4528`.

**No tiling required.** Because the downscaled full frame was sufficient above, frames
can be fed whole. This cuts the job from ~3,200 tiles to ~400 reads. (Re-verify if
accuracy disappoints on the tan cabinet.)

## Decisions made

- **Backend: subagents inside the Claude Code session**, not the Anthropic API.
  A Claude subscription does not grant API credits, but the session itself is covered
  by the subscription and subagents are multimodal and can `Read` images. No API key
  needed. User explicitly asked for this ("can you subagent it out").
- **Model: undecided, lean Sonnet.** Haiku 4.5 would likely handle the crisp green
  labels but risks silent misreads on the low-contrast tan ones (`CD 4526` vs
  `CD 4528`). Planned test: run one Haiku agent and one Sonnet agent over the *same*
  30-frame slice and diff. If they agree, use Haiku for bulk + Sonnet to re-read
  low-confidence entries.
- **Output fields** (user-selected): all text lines on the label, category when
  present, source frame timestamp, path to saved crop, and a confidence score.
  User added: "label may have more or less data" — so keep the schema flexible.
- **Deferred:** cabinet/row/column physical position. User did not select it. Would
  require tracking the camera pan to build a consistent grid.

## State of work

| Stage | Status |
|---|---|
| Probe video metadata | done |
| Sample frames, confirm legibility | done |
| tesseract viability test | done — rejected |
| Sharpness profile @ 4 fps (1,583 frames) | done → `work/profile.json` |
| Sharpness profile @ full 60 fps | **NOT done** — process was killed mid-run |
| Keyframe extraction | not started |
| OCR fan-out | not started |
| Dedup / final list | not started |

### Preserved artifacts — `/home/jas/dev/tests/drawers/work/`

- `profile.json` — per-frame `{i, t, sharp, motion}` at 4 fps.
- `best_per_sec.json` — sharpest-of-4 frame per second (396 entries). Usable as a
  fallback if you skip the full-fps rescan.
- `sharp.py`, `best.py` — scripts that produced the above.
- `fullscan.py` — the full-fps scan that did not get to run. Writes `fullsharp.json`.
- `samples/`, `ocrtest/` — sample extracted frames used for the legibility tests.

Note: the previous session's scratchpad under `/tmp/claude-1000/...` is ephemeral and
should be assumed gone. A Python venv with `opencv-python-headless` + `numpy` was
created there and will need recreating (`uv venv .venv && uv pip install
opencv-python-headless numpy`).

## Resume from here

1. **Recreate the venv**, then run `fullscan.py` (~3 min). It scores all 23,665 frames
   by piping raw grayscale from ffmpeg into OpenCV. Run it *foreground* or via the
   proper background-task mechanism — a `nohup ... &` inside a Bash call gets killed
   when the turn ends, which is what happened last time.

   Rationale for full-fps over the existing 4 fps data: picking the sharpest of ~60
   candidates per second instead of the sharpest of 4 should measurably raise the
   floor. At 4 fps, best-per-second sharpness has median 210 but a p10 of only 72.

2. **Extract keyframes** — sharpest frame per 1 s window, dropping windows whose best
   frame is still below a sharpness floor (~60). Expect ~380–396 frames. A written-but-
   never-run `extract.py` was planned: build an ffmpeg `select='eq(n\,X)+...'`
   expression from the chosen indices, one decode pass, `-vsync 0`, write
   `frames/k_%04d.jpg` plus a `keyframes.json` of `{seq, frame, t, sharp, file}`.

3. **Model bake-off** on a 30-frame slice spanning both cabinets (green ~t=90s, tan
   ~t=320s). Haiku vs Sonnet, diff the outputs.

4. **Fan out** ~10 subagents, each given a contiguous chunk of frames. Each agent
   `Read`s its frames and appends one JSON object per drawer to its own JSONL file —
   have them write to disk rather than return data in their final report, since agent
   reports are not shown to the user and large payloads are wasteful.

5. **Dedup.** Consecutive keyframes overlap heavily (the camera pans continuously), so
   the same drawer appears in many frames. Fuzzy-match part numbers across adjacent
   frames, keep the highest-confidence read, and preserve the overlap as corroboration.
   Flag disagreements for manual review.

6. **Emit** the final list plus a review queue of low-confidence entries.

## Open questions for the user

- Physical position (cabinet/row/col) — deferred, confirm if actually wanted.
- Output format for the final list: CSV, JSON, Markdown table?
- Whether quantity/stock level matters, or just identity of each drawer.
