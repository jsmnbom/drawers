import json,numpy as np
rows=json.load(open('profile.json'))
# best (sharpest) frame per 1s window
best={}
for r in rows:
    w=int(r["t"])
    if w not in best or r["sharp"]>best[w]["sharp"]: best[w]=r
sel=[best[w] for w in sorted(best)]
json.dump(sel,open('best_per_sec.json','w'))
s=np.array([r["sharp"] for r in sel])
print(f"best-per-sec frames={len(sel)} sharp med={np.median(s):.0f} min={s.min():.0f} p10={np.percentile(s,10):.0f}")
print("weak seconds (sharp<150):", [r["t"] for r in sel if r["sharp"]<150][:20])
