# Coverage validation: green_ext2 (t=81-104s, core window 85-100s)

36 frames read (k_t0081.2.jpg ... k_t0103.4.jpg). Core window = 85 ≤ t ≤ 100
(frames 85.2 through 100.0 inclusive, 26 frames). Edge frames (81.2-84.6 and
100.6-103.4) exist to prove drawers near the core boundary are covered.

Three cabinets are traversed across the full 36-frame set:
A) BJT/MOSFET/IGBT transistor cabinet (t≈81-85.6)
B) Diode/Zener cabinet (t≈85.2-91.4)
C) Resistor cabinet, pink Ω labels + a couple of TVS/Bridge-Rectifier drawers
   (t≈93.6-103.4)

## A. Transistor cabinet (legible drawer labels, with frame counts across all 36)
Only the labels still visible at the trailing edge of this cabinet fall inside
the core window (t=85.2, 85.6); the rest of the cabinet is only in the pre-core
edge frames (81.2-84.6), which is fine since none of it is inside the core.

In-core-window labels (BC107, 2N6292, BFT40, 2N3738, BC640, BFT80, IRFD120,
GBC40F) each appear legibly in 5+ of the 36 frames (81.2, 81.7, 84.6, 85.2,
85.6). All ≥2. PASS for this group.

Labels only in pre-core edge frames (not in core window, no coverage
requirement, counts across all 36 shown for completeness):
BC337(2), BC547B(5), BDY16(2), BDY15(5), BC301(2), MJ3001(5), 2N3055(5),
BD413(5), BC327(3), BD234(2), MJE15031(5), IRFP250(2),
RFP4N100/IRF740/19N20L(5), U1899E(2), IRFD9210(1), BC639(2), BUT90(2),
MJE3055T(2), BD950(2), IRF9130(2).

## B. Diode/Zener cabinet (all core-window; frame counts across all 36)
1N5401(4), 1N5404(2), BY229(2), RHC5-15(5), 1N6267A(4), 1N5921B(3),
1N5062(5), RGP10G(5), BZX79 C5V6PH(6), BZX79 C2V4PH(5), 1N748A(6),
1N967B/1N974B/1N979B(5), ZD27(6), 1N4942(3), 1N5624(4), BY359(5), AAZ18(5),
BZX55C12(5), 1N749A(5), 1N972B/1N973B(3), 1N5818(4).
All ≥2. PASS for this group.

## C. Resistor / rectifier cabinet
BZW04-13 TVS(2, t93.6/93.9), Bridge Rectifiers(2, t93.6/93.9).
Pink resistance labels 0.10Ω-0.13Ω, 1.0Ω-1.3Ω, 10Ω-13Ω, 100Ω-130Ω,
1.0KΩ-1.3KΩ, 10KΩ-13KΩ, 100KΩ-130KΩ, 1.0MΩ-1.3MΩ, 10MΩ-13MΩ, plus the
white combined "POWER" variant labels: each of these appears legibly in
~13-14 core frames (93.6 through 100.0) and continues into 100.6 (edge).
All ≥2. PASS.

Higher-value resistor drawers (15KΩ, 16KΩ, 18KΩ, 150KΩ..200KΩ, 1.5MΩ..2.0MΩ,
15MΩ..20MΩ, 1.6Ω-2.0Ω range, etc.) are visible ONLY in edge frames after
t=100.6, never inside the core window — consistent with the edge frames'
purpose, not a coverage failure.

### Coverage gap found
- **"68pF/500V / 82pF/500V / 100pF/500V" capacitor drawer card** (bottom
  shelf of the resistor cabinet): visible at the core-window boundary frame
  t=100.0 and is legible there, but the only other frame showing it
  (t=100.6, outside core) is too motion-blurred to read. Legible in only
  **1** of the 36 keyframes total. This is inside the core window and fails
  the ≥2 legible-frame requirement.

### Drawer visible but never legible in any frame
- A small green sticker label on one of the blue-component (capacitor?)
  drawers in the transition shelf between the diode cabinet and the resistor
  cabinet (visible in frames t≈92.4, 93.0, 93.3, 93.6, 93.9) — the sticker is
  present in multiple frames but its text is never resolvable (too small /
  blurred in every occurrence). Never legible in any of the 36 frames.

## Verdict
COVERAGE: FAIL — "68pF/500V / 82pF/500V / 100pF/500V" capacitor card legible
in only 1 keyframe (t=100.0); all other distinct core-window drawer labels
are legible in ≥2 keyframes.
