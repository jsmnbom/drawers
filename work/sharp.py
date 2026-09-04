import cv2, numpy as np, glob, json
fs = sorted(glob.glob('probe/f_*.jpg'))
rows=[]
prev=None
for i,f in enumerate(fs):
    g = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    lv = cv2.Laplacian(g, cv2.CV_64F).var()
    # motion: mean abs diff vs prev
    md = float(np.mean(np.abs(g.astype(np.int16)-prev))) if prev is not None else 0.0
    prev = g.astype(np.int16)
    rows.append({"i":i,"t":round(i/4,2),"sharp":round(lv,1),"motion":round(md,2)})
json.dump(rows, open('profile.json','w'))
s=np.array([r["sharp"] for r in rows]); m=np.array([r["motion"] for r in rows])
print(f"frames={len(rows)}  sharp: min={s.min():.0f} med={np.median(s):.0f} p90={np.percentile(s,90):.0f} max={s.max():.0f}")
for q in [50,70,80,90,95]:
    print(f"  frames above p{q} sharpness ({np.percentile(s,q):.0f}): {(s>np.percentile(s,q)).sum()}")
print(f"motion: med={np.median(m):.1f} p10={np.percentile(m,10):.1f} p90={np.percentile(m,90):.1f}")
print(f"low-motion frames (<p25={np.percentile(m,25):.1f}): {(m<np.percentile(m,25)).sum()}")
