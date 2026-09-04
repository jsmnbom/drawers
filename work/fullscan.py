import subprocess, numpy as np, cv2, json
SRC="/home/jas/dev/tests/drawers/20260903_165847.mp4"
W,H=320,569
FPS=60000/1001
cmd=["ffmpeg","-v","error","-hwaccel","cuda","-i",SRC,
     "-vf",f"scale={W}:{H}","-pix_fmt","gray","-f","rawvideo","-"]
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,bufsize=W*H*32)
n=W*H; rows=[]; prev=None; i=0
while True:
    buf=p.stdout.read(n)
    if len(buf)<n: break
    g=np.frombuffer(buf,dtype=np.uint8).reshape(H,W)
    lv=float(cv2.Laplacian(g,cv2.CV_64F).var())
    gi=g.astype(np.int16)
    md=float(np.mean(np.abs(gi-prev))) if prev is not None else 0.0
    prev=gi
    rows.append({"i":i,"t":round(i/FPS,3),"sharp":round(lv,1),"motion":round(md,2)})
    i+=1
p.stdout.close(); p.wait()
json.dump({"fps":FPS,"rows":rows},open("fullsharp.json","w"))
s=np.array([r["sharp"] for r in rows])
print(f"frames={len(rows)} med={np.median(s):.0f} p90={np.percentile(s,90):.0f} max={s.max():.0f}")
