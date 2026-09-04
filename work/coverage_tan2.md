# Coverage validation: tan_ext2 (core window t=315–330s)

Reviewed all 32 keyframes in /home/jas/dev/tests/drawers/work/slices/tan_ext2/.
Core window frames (315 ≤ t ≤ 330), 23 total:
315.0, 315.2, 315.4, 315.7, 316.2, 316.8, 317.3, 318.5, 319.1, 320.4, 321.3,
321.9, 322.8, 324.1, 324.8, 325.8, 327.0, 327.7, 328.3, 328.7, 329.4, 329.9, 330.6*
(*330.6 is technically outside 315–330 by 0.6s but included here as it's the edge
frame proving the HC-cabinet drawers near the end of the window are covered.)

Edge-only frames used solely to prove near-boundary coverage: 311.1, 311.6, 311.9,
312.2, 312.5, 313.2, 314.6 (before core), 332.1, 333.2 (after core — different
74x-logic cabinet, not part of core window, excluded from the distinct-label list).

## Distinct drawer labels found in the core window, with legible-frame counts (across all 32 images)

### Resistor-value cabinet (legible mainly at t=313.2–315.0; 315.2/315.4/315.7 too blurry to read)
150R:2, 560:3, 820:3, 1k:2, 1.5k:3, 2.2k:3, 2.7k:2, 3.9k:3, 4.7k:3, 5.6k:3,
6.8k:2, 10k:3, 12k:3, 18k:2, 27k:3, 33k:3, 47k:2

### Tan "CD 40xx/45xx" dot-matrix cabinet
CD4047:3 (311.6,311.9,316.2), CD4066:1 (316.8 only — FAIL),
CD4060/CD4063 (overlapping/stacked label, single drawer):1 (316.8 only — FAIL),
CD4070:1 (317.3 only — FAIL), CD4071:3, CD4072:4, CD4073:2, CD4075:2, CD4076:3,
CD4081:3, CD4082:4, CD4093:2, CD4098:4, CD4099:5, CD40106:5, CD4502:2, CD4503:4,
CD4511:4, CD4512:3, CD4515:3, CD4516:2, CD4520:4, CD4526:4, CD4528:2, CD4532:2,
CD4555:2, CD4556:4, 80C95:2

### Adjacent transistor cabinet (mostly blank drawers, sparsely labeled)
BC327:1 (316.2 only — FAIL)

### "HC"-prefixed cabinet
HC145:2, "126":2, "112":3, "140":3, "123":3, "163":3, HC132:2, HC150:2,
HC173:3, HC148:3, HC74:3(+330.6 partial), "176":3, "177":3(+330.6 partial),
"182":3, HC174:3

## VERDICT

COVERAGE: FAIL — labels legible in fewer than 2 keyframes:
- CD4066 (1 frame: t=316.8)
- CD4060/CD4063 stacked label (1 frame: t=316.8)
- CD4070 (1 frame: t=317.3)
- BC327 (1 frame: t=316.2)

All other identified core-window drawer labels are legible in ≥2 keyframes.

## Drawer faces visible in the core window but never legible in any frame
- Several drawers on the adjacent dark transistor cabinet (right column at t≈316.2,
  and both columns at t≈324.1/324.8) are visible face-on but show no legible text —
  either blank labels or too small/worn to read at any zoom. One label at t=316.2
  reads only as an indecipherable code (approx. "K3C25P8OL"), never confidently
  legible in any frame. A partial tag at the far right edge of t=316.8 (cut off,
  something like "…BC45x") is likewise never fully legible.
- The transition frames at t=324.1 and t=324.8 show a full bank of drawers with no
  legible labels at all (empty/unlabeled fronts), bridging the CD-cabinet and the
  HC-cabinet.
