# Frozen OCR prompt template (Phase 1.5)

Placeholders: {OUTFILE} = absolute JSONL output path, {FRAMELIST} = newline list of absolute image paths.

---

MANDATORY FIRST LINE of your final report: "MODEL: <exact model id>" copied from your system prompt; reports without it are discarded.

You are an OCR agent reading electronic-component drawer labels from video keyframes (a camera panning across drawer cabinets).

Process these image files IN ORDER, one at a time (the filename encodes the video timestamp in seconds, e.g. k_t0093.0.jpg = t=93.0s):

{FRAMELIST}

For EACH image: Read it, find every drawer label with legible text, and record one JSON object per label. After finishing each image, APPEND its records to {OUTFILE} as JSONL (one compact JSON object per line) using a Bash heredoc:

    cat >> {OUTFILE} <<'JSONL'
    {"lines": [...], ...}
    {"lines": [...], ...}
    JSONL

Do not wait until the end to write; append after each image so no work is lost.

JSON object schema (one per drawer label per frame):
{"lines": ["1N972B", "1N973B", "Zener"], "category": "Zener", "frame": "k_t0093.0.jpg", "t": 93.0, "where": "row 3, second from left", "confidence": 0.9}

Rules:
- "lines": every text line on the label, verbatim, top to bottom. Transcribe exactly what you see; do NOT normalize, expand, or correct part numbers.
- "category": the component-category word if the label carries one (e.g. Diode, Zener, Schottky, Transistor), else null.
- "frame": the image's basename; "t": its timestamp from the filename.
- "where": a short human-findable location hint within the frame (e.g. "top-left area", "row ~4, middle").
- "confidence": your 0-1 confidence in this transcription.
- Skip labels too blurred/small/cut-off to read reliably — do NOT guess whole labels. If you can read most characters but are unsure of one or two, include the record with lower confidence.
- The same drawer appears in multiple overlapping frames — expected. Report each frame independently; do NOT dedup across frames.
- Some frames are motion-blurred transitions with nothing legible; write no records for those and move on.

Efficiency rules (strict):
- Read each image exactly once. You may additionally crop/zoom (via Bash + Read of the crop) ONLY when a specific label is genuinely ambiguous.
- NEVER re-read or "validate" the output JSONL file; append and move on.
- No summary prose in the final report beyond the two required lines.

Final report: just the MODEL line plus one line: "<N> records written for <M> of <K> frames".
