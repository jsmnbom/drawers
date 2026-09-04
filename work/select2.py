"""Motion-bounded keyframe selection.

Greedy: from the last kept frame, look at candidate frames whose cumulative
motion since the kept frame lies in [TMIN, MMAX]; keep the sharpest candidate
(prefer those above the sharpness floor). This bounds the view shift between
consecutive keyframes (coverage) while still skipping static stretches (dedup).
If the camera is static (motion never reaches TMIN before the video ends), stop.
"""
import json, sys, numpy as np

d = json.load(open('fullsharp.json'))
rows = d["rows"]
FLOOR = 60.0
cum = np.concatenate([[0.0], np.cumsum([r["motion"] for r in rows])])

def mb(i0, i1):  # motion over (i0, i1]
    return cum[i1 + 1] - cum[i0 + 1]

def select(MMAX, TMIN):
    kept = [max(rows[:60], key=lambda r: r["sharp"])]  # sharpest of first second
    n = len(rows)
    j = kept[0]["i"] + 1
    while j < n:
        last = kept[-1]
        # candidate window: motion in [TMIN, MMAX]
        cands = []
        k = j
        while k < n and mb(last["i"], rows[k]["i"]) <= MMAX:
            if mb(last["i"], rows[k]["i"]) >= TMIN:
                cands.append(rows[k])
            k += 1
        if not cands:
            if k >= n:
                break  # static tail
            # motion jumped from <TMIN to >MMAX across one frame: take frame k-1
            cands = [rows[k - 1]] if k - 1 >= j else [rows[k]]
        good = [c for c in cands if c["sharp"] >= FLOOR]
        pick = max(good or cands, key=lambda r: r["sharp"])
        kept.append(pick)
        j = pick["i"] + 1
    return kept

if len(sys.argv) > 2:
    MMAX, TMIN = float(sys.argv[1]), float(sys.argv[2])
    kept = select(MMAX, TMIN)
    s = np.array([r["sharp"] for r in kept])
    gaps = np.diff([r["t"] for r in kept])
    json.dump({"mmax": MMAX, "tmin": TMIN, "kept": kept}, open('keyframe_sel2.json', 'w'))
    print(f"MMAX={MMAX} TMIN={TMIN}: kept={len(kept)} sharp min={s.min():.0f} "
          f"p10={np.percentile(s,10):.0f} med={np.median(s):.0f} "
          f"max_time_gap={gaps.max():.1f}s -> keyframe_sel2.json")
else:
    print(f"{'MMAX':>6} {'TMIN':>5} {'kept':>5} {'sharp_p10':>9} {'sharp_min':>9}")
    for MMAX in [500, 600, 800, 1000, 1200]:
        for TMIN in [100, 200, 300]:
            kept = select(MMAX, TMIN)
            s = np.array([r["sharp"] for r in kept])
            print(f"{MMAX:>6.0f} {TMIN:>5.0f} {len(kept):>5} "
                  f"{np.percentile(s,10):>9.0f} {s.min():>9.0f}")
