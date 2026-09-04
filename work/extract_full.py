"""Single-pass keyframe extraction: decode whole video scaled to 1125x2000,
write JPEGs only for selected frame indices."""
import json, os, subprocess, sys
import numpy as np, cv2

sel = json.load(open('keyframe_sel2.json'))
wanted = {r['i']: r for r in sel['kept']}
os.makedirs('../frames', exist_ok=True)

W, H = 1125, 2000
FRAME_BYTES = W * H * 3
proc = subprocess.Popen(
    ['ffmpeg', '-loglevel', 'error', '-hwaccel', 'cuda',
     '-i', '../20260903_165847.mp4',
     '-vf', f'scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'],
    stdout=subprocess.PIPE, bufsize=FRAME_BYTES * 4)

meta = []
i = 0
written = 0
while True:
    buf = proc.stdout.read(FRAME_BYTES)
    if len(buf) < FRAME_BYTES:
        break
    if i in wanted:
        r = wanted[i]
        seq = len(meta)
        fn = f'../frames/k_{seq:04d}.jpg'
        im = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        cv2.imwrite(fn, im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        meta.append({'seq': seq, 'frame': r['i'], 't': round(r['t'], 2),
                     'sharp': round(r['sharp'], 1), 'file': f'frames/k_{seq:04d}.jpg'})
        written += 1
        if written % 50 == 0:
            print(f'{written}/{len(wanted)} at frame {i}', flush=True)
    i += 1
proc.wait()
json.dump(meta, open('../frames/keyframes.json', 'w'), indent=1)
print(f'done: {written} keyframes written of {len(wanted)} selected, {i} frames decoded')
