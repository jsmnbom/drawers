"""Build per-agent OCR prompts: ~15 contiguous frames each."""
import json, os, math

meta = json.load(open('../frames/keyframes.json'))
tmpl = open('ocr_prompt.md').read().split('---\n', 1)[1]
os.makedirs('ocr', exist_ok=True)

CHUNK = 15
n_agents = math.ceil(len(meta) / CHUNK)
for a in range(n_agents):
    chunk = meta[a * CHUNK:(a + 1) * CHUNK]
    paths = '\n'.join(f'/home/jas/dev/tests/drawers/{m["file"]}' for m in chunk)
    out = f'/home/jas/dev/tests/drawers/work/ocr/agent_{a:02d}.jsonl'
    p = tmpl.replace('{OUTFILE}', out).replace('{FRAMELIST}', paths)
    p = p.replace('the filename encodes the video timestamp in seconds, e.g. k_t0093.0.jpg = t=93.0s',
                  'timestamps for each file are listed below')
    ts = '\n'.join(f'{m["file"].split("/")[-1]}: t={m["t"]}' for m in chunk)
    p += f'\nTimestamps (use for the "t" field):\n{ts}\n'
    open(f'ocr/prompt_{a:02d}.txt', 'w').write(p)
print(f'{n_agents} prompts for {len(meta)} frames')
