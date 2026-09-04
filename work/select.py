import json, sys, numpy as np
d=json.load(open('fullsharp.json'))
rows=d["rows"]; fps=d["fps"]
FLOOR=60.0

# sharpest frame per 1s window, drop windows below floor
best={}
for r in rows:
    w=int(r["t"])
    if w not in best or r["sharp"]>best[w]["sharp"]: best[w]=r
base=[best[w] for w in sorted(best) if best[w]["sharp"]>=FLOOR]
s=np.array([r["sharp"] for r in base])
print(f"base keyframes={len(base)} (windows dropped by floor: {len(best)-len(base)}) "
      f"sharp min={s.min():.0f} p10={np.percentile(s,10):.0f} med={np.median(s):.0f}")

# cumulative per-frame motion, for summing between arbitrary frame indices
cum=np.concatenate([[0.0], np.cumsum([r["motion"] for r in rows])])
def motion_between(i0,i1):  # sum of motion over frames (i0, i1]
    return cum[i1+1]-cum[i0+1]

def thin(T):
    kept=[base[0]]
    for r in base[1:]:
        if motion_between(kept[-1]["i"], r["i"])>=T: kept.append(r)
    return kept

print(f"\n{'T':>6} {'kept':>5}")
for T in [0,10,20,30,40,50,60,80,100,150,200]:
    print(f"{T:>6} {len(thin(T)):>5}")

if len(sys.argv)>1:
    T=float(sys.argv[1])
    kept=thin(T)
    kept_i={r["i"] for r in kept}
    dropped=[r for r in base if r["i"] not in kept_i]
    json.dump({"threshold":T,"kept":kept,"dropped":dropped},open('keyframe_sel.json','w'))
    print(f"\nT={T}: kept={len(kept)} dropped={len(dropped)} -> keyframe_sel.json")
