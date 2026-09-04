# Coverage check — green_ext keyframe set (core window t=85–100s)

Model: claude-sonnet-5

## Scope note
The 17 keyframes in this set actually cross TWO physical cabinets during the core
window:
- Cabinet A: Diode / Zener (green labels) + edge of an adjacent Transistor cabinet
  (red/white labels) — visible t=81.0 through t=92.4.
- Cabinet B: Resistor cabinet (magenta/white value labels) — visible from t=94.5
  (transition frame) through t=104.0.

Frames read (17 total): t=81.0, 83.0, 84.0 (extension, before core), 85.6, 87.0,
89.0, 91.0, 92.4, 94.5, 96.0, 97.0, 99.0, 100.0 (CORE, 85–100s), 102.0, 102.6,
103.4, 104.0 (extension, after core).

## Distinct labels legible in the CORE window, with total legible-frame counts (all 17 frames)

### Cabinet A — Diode/Zener/Transistor edge (core frames 85.6–92.4)
| Label | Legible frames (timestamps) | Count |
|---|---|---|
| 1N5401 / Diode | 85.6, 87.0, 89.0 | 3 |
| 1N5404 / Diode | 85.6, 87.0 | 2 |
| RHC5-15 / Diode | 85.6, 87.0, 89.0 | 3 |
| BY229 / Diode | 85.6, 87.0 | 2 |
| 1N5062 / Diode | 87.0, 89.0 | 2 |
| RGP10G / Diode | 87.0, 89.0 | 2 |
| 1N4942 / Diode | 89.0 only | **1 — FAIL** |
| **1N5624 / Diode** | 89.0 only | **1 — FAIL** |
| BY359 / Diode | 89.0 only | **1 — FAIL** |
| AAZ18 / Signal | 89.0, 91.0 | 2 |
| BZX55C12 / Zener | 89.0, 91.0 | 2 |
| BZX79 C5V6PH / Zener | 87.0, 89.0, 91.0 | 3 |
| BZX79 C2V4PH / Zener | 85.6, 87.0, 89.0, 91.0, 92.4 | 5 |
| 1N6267A / Zener | 87.0, 91.0, 92.4 | 3 |
| 1N749A / Zener | 89.0, 91.0 | 2 |
| 1N748A / Zener | 87.0, 89.0, 91.0 | 3 |
| 1N967B/974B/979B / Zener | 87.0, 89.0, 91.0, 92.4 | 4 |
| 1N972B/973B / Zener | 89.0, 91.0 | 2 |
| 1N5921B / Zener | 87.0, 92.4 | 2 |
| ZD27 / Zener | 89.0, 91.0 | 2 |
| 1N5818 / Schottky | 91.0 only | **1 — FAIL** |
| BZW04-13 / TVS | 94.5 only | **1 — FAIL** |
| Bridge Rectifiers | 94.5 only | **1 — FAIL** |
| BC107 / NPN | 81.0 (ext), 85.6 | 2 |
| 2N6292 / NPN | 81.0 (ext), 85.6 | 2 |
| BFT40 / NPN | 81.0 (ext), 85.6 | 2 |
| 2N3738 / NPN | 81.0 (ext), 85.6 | 2 |
| BC640 / PNP | 81.0 (ext), 85.6 | 2 |
| BFT80 / PNP | 81.0 (ext), 85.6 | 2 |
| IRFD120 / N-CH | 81.0 (ext), 85.6 | 2 |
| GBC40F / IGBT-NCH | 81.0 (ext) only — cut off/illegible at 85.6 | **1 — FAIL** |

Illegible/unreadable drawer faces visible in core window but never legible in
any of the 17 frames:
- A blue-component drawer, top-left in the 94.5 frame — no readable text in any frame.
- A drawer with a plain green sticker (no printed text resolvable) next to it, 94.5.
- A drawer with a blank/illegible white index card, center of 94.5.

### Cabinet B — Resistor cabinet (core frames 94.5–100.0)
Most Ω-value drawers are covered by 2 overlapping frames as the camera pans
(mainly 96.0 & 97.0 for the 0.1Ω–13MΩ block, 99.0 & partial 100.0 for the
1.1–13MΩ POWER block). Representative counts:
| Label(s) | Legible frames | Count |
|---|---|---|
| 0.12Ω / 0.13Ω / 1.2Ω / 1.3Ω | 94.5, 96.0 (,97.0 for 1.2/1.3) | 2–3 |
| 0.11Ω, 1.1Ω, 10–13Ω, 100–130Ω, 1.0–1.3KΩ, 10–13KΩ, 100–130KΩ, 1.0–1.3MΩ, 11–13MΩ | 96.0, 97.0 | 2 |
| 1.1MΩ, 1.2MΩ, 11MΩ, 12MΩ | 96.0, 97.0, 99.0 | 3 |
| POWER labels "0.11Ω/1.1Ω", "0.12Ω/1.2Ω", "11Ω/110Ω", "12Ω/120Ω", "1.1KΩ/11KΩ/110KΩ/1.1MΩ", "1.2KΩ/12KΩ/120KΩ/1.2MΩ" | 99.0 only | **1 — FAIL** |
| 16KΩ, 160KΩ, 1.6MΩ, 16MΩ | 100.0, 102.0 (ext) | 2 |
| **15KΩ, 150KΩ, 1.5MΩ, 15MΩ** | 100.0 only (no overlap in 102.0/other frames) | **1 — FAIL** |
| POWER "0.16Ω/1.6Ω", "16Ω/160Ω" | 100.0, 102.0 (ext) | 2 |
| **POWER "0.15Ω/1.5Ω", "15Ω/150Ω"** | 100.0 only | **1 — FAIL** |

## VERDICT
COVERAGE: FAIL

Labels legible in only 1 keyframe (need ≥2):
- 1N4942 (t=89.0)
- **1N5624** (t=89.0) — the example label from the task prompt itself
- BY359 (t=89.0)
- 1N5818 Schottky (t=91.0)
- BZW04-13 TVS (t=94.5)
- Bridge Rectifiers (t=94.5)
- GBC40F IGBT-NCH (t=81.0, extension frame only; cut off/illegible at t=85.6, its only core appearance)
- Resistor POWER-block labels: "0.11Ω/1.1Ω", "0.12Ω/1.2Ω", "11Ω/110Ω", "12Ω/120Ω", "1.1KΩ/11KΩ/110KΩ/1.1MΩ", "1.2KΩ/12KΩ/120KΩ/1.2MΩ" (all t=99.0 only)
- Resistor drawers 15KΩ, 150KΩ, 1.5MΩ, 15MΩ and their POWER variants "0.15Ω/1.5Ω", "15Ω/150Ω" (all t=100.0 only — the last core frame, no adjacent frame recaptures this column)

## Drawer faces present in core window but never legible in any frame
- Blue-component drawer (top-left, frame t=94.5) — no readable text.
- Green-stickered drawer with unresolvable text (t=94.5).
- Blank/illegible white index-card drawer (center, t=94.5).
