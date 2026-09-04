# Coverage check: tan_ext (t≈311-334s), core window 315-330s

Model: claude-sonnet-5

## Observation about the footage
This clip is not a single steady pan across one "tan" cabinet. It sweeps across (at least) four
distinct drawer sections in the frame sequence:
- **Resistor-value cabinet** (olive, printed tags like "150R", "1.5k", "10k") — seen at t311(edge)/314(edge)/315.1/316.3 (start of core).
- **Tan "CD" cabinet** (dot-matrix tan tags, "CD 40xx"/"CD 45xx") — the cabinet the task describes — seen at t311.1-312.1 (edge, drawers CD4015-CD4066) and again at t318.0-323.0 (core, drawers CD4071-CD4556).
- **"HC"-prefixed cabinet** (tan tags "HC nnn" plus handwritten white tags like "112", "140") — seen at t325.8-329.7 (core) and t331.7 (edge, different HC numbers).
- **74x-series IC cabinet** (multi-part printed tags "74x nnn/nnn/nnn") — seen only at t331.7(edge)-334.0(edge), entirely outside the core window, never overlapping core content.

t0324.1 is a blurred transition frame with drawers/tabs visible but no legible text.

## Distinct labels legible in the CORE window (315-330s), with legible-frame counts across ALL 17 frames

### Resistor cabinet (edge-proven correctly — matches expected pattern)
| Label | Frames legible | Count |
|---|---|---|
| 150R, 560, 820, 1k, 1.5k, 2.2k, 2.7k, 3.9k, 4.7k, 5.6k, 6.8k, 10k, 12k, 18k, 27k, 33k, 47k | t0314.0(edge), t0315.1, t0316.3 | 3 each (2 inside core) |

### Tan "CD" cabinet (subject cabinet)
| Label | Frames legible | Count |
|---|---|---|
| CD 4071 | t0318.0 | 1 |
| CD 4072 | t0318.0 | 1 |
| CD 4081 | t0318.0, t0319.1 | 2 |
| CD 4082 | t0318.0, t0319.1 | 2 |
| CD 40106 | t0318.0, t0319.1 | 2 |
| CD 4511 | t0319.1(partial/edge), t0320.9 | 2 (borderline) |
| CD 4512 | t0318.0, t0319.1 | 2 |
| CD 4515 | t0318.0, t0319.1 | 2 |
| CD 4528 | t0318.0, t0319.1, t0322.0(partial) | 3 |
| CD 4532 | t0318.0, t0319.1 | 2 |
| CD 4075 | t0320.9, t0322.0 | 2 |
| CD 4076 | t0320.9 | 1 |
| CD 4098 | t0320.9, t0322.0 | 2 |
| CD 4099 | t0320.9 | 1 |
| CD 4503 (hand-written tag) | t0320.9, t0322.0, t0323.0(partial) | 3 |
| CD 4520 | t0320.9, t0322.0, t0323.0 | 3 |
| CD 4526 | t0320.9 | 1 |
| CD 4556 | t0320.9 (partial, bottom-edge cut) | 1 |
| CD 4073 | t0322.0, t0323.0 | 2 |
| CD 4093 | t0322.0, t0323.0 | 2 |
| CD 4502 | t0322.0, t0323.0 | 2 |
| CD 4516 | t0322.0, t0323.0 | 2 |
| CD 4555 | t0322.0, t0323.0 | 2 |
| 80C95 (partial, right-edge, adjacent transistor drawer bleeding into frame) | t0318.0, t0319.1 | 2 (partial both times) |

### "HC"-prefixed cabinet (only in core, no repeat in any other frame incl. extended)
| Label | Frames legible | Count |
|---|---|---|
| HC 145 | t0325.8 | 1 |
| "12 6" (handwritten) | t0325.8 | 1 |
| HC 132 | t0327.7 | 1 |
| 112 (handwritten) | t0327.7 | 1 |
| HC 150 | t0327.7 | 1 |
| 140 (handwritten) | t0327.7 | 1 |
| 123 (handwritten) | t0327.7 | 1 |
| 163 (handwritten) | t0327.7 | 1 |
| HC 173 | t0329.7 | 1 |
| HC 148 | t0329.7 | 1 |
| HC 74 | t0329.7 | 1 |
| 176 (handwritten) | t0329.7 | 1 |
| 177 (handwritten) | t0329.7 | 1 |
| 182 (handwritten) | t0329.7 | 1 |
| HC 174 | t0329.7 | 1 |

## Never-legible drawer faces visible in the core window
- t0324.1: multiple drawer faces are visibly open/present but blurred enough that no tag text is legible in any frame (this position/timestamp is not otherwise duplicated by a sharp frame).
- The bottom-right partial tag in t0318.0/t0319.1 (transcribed "80C95") is only ever partially visible (edge-cut) — never a full, unambiguous read.

## VERDICT
**COVERAGE: FAIL**

Reasons:
1. Several tan "CD"-cabinet labels appear in only 1 legible frame within the core window and are never repeated in any extended frame: **CD 4071, CD 4072, CD 4076, CD 4099, CD 4526, CD 4556** (CD4556 additionally only ever partially visible/edge-cut).
2. The entire "HC"-prefixed cabinet section shown between t0325.8 and t0329.7 has a systemic gap: every single label in that section (HC145, "12 6", HC132, 112, HC150, 140, 123, 163, HC173, HC148, HC74, 176, 177, 182, HC174) is legible in exactly **one** keyframe and is never repeated — not even by the extended edge frames (t0331.7 shows different HC numbers: HC375, 624). This whole 3-frame span (325.8→329.7) pans fast enough that no drawer is captured twice.
3. By contrast, the resistor-value cabinet (150R...47k) and most of the CD40xx/45xx-cabinet labels ARE properly covered (≥2 legible frames), and the extended pre/post frames correctly backstop edge drawers for those sections — this is the pattern the task description implies is expected everywhere.

Borderline/partial-legibility items worth flagging even though nominally counted ≥2: CD 4511 (one of its two reads is edge-cut/partial), CD 4528/CD4503/CD4520 (one of the reads is partial), "80C95" (both reads partial).
