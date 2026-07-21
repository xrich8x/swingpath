"""hud_ocr.py — read SwingVision's burned-in shot panel as ground truth (E3).

Several of our sourced clips (yt_rally2, demo30) carry SwingVision's own HUD:
after every stroke it prints the stroke type, the spin style, and the shot speed
in MPH. E1 established that our physics arc fit needs an INDEPENDENT reference —
its own reprojection error certifies nothing — and this panel is one sitting in
footage we already own, at zero annotation cost.

Honesty: SwingVision is another single-camera estimate, not radar. Agreement
with it is evidence our numbers are in the right world; it is NOT accuracy
against truth, and must never be reported as such.

No OCR dependency. The HUD font is fixed, so glyphs are segmented by connected
components and matched against templates bootstrapped once from the clip itself:

  scan   collect every distinct glyph, write a contact sheet to eyeball
  label  attach characters to those glyphs (one-time, by hand)
  read   emit per-frame readings, then collapse them into per-shot records

  cd backend
  .venv\\Scripts\\python.exe ..\\tools\\hud_ocr.py scan  --video ..\\data\\yt_rally2.mp4
  .venv\\Scripts\\python.exe ..\\tools\\hud_ocr.py label --chars "4,9,..."
  .venv\\Scripts\\python.exe ..\\tools\\hud_ocr.py read  --video ..\\data\\yt_rally2.mp4
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]

# The panel sits at a fixed spot in these 1280x720 clips (top-right, under the
# court minimap). We crop only the MPH NUMBER — right-aligned on the panel's top
# line — because that alone is the reference we need, and cropping tight keeps
# the ceiling-light streaks that cross the panel's rounded corners out of the
# glyph bank. The word "MPH" below and the orange stroke/spin lines are excluded.
PANEL = (1150, 258, 1266, 283)          # x0, y0, x1, y1
GLYPH_WH = (16, 24)


def panel_of(frame, panel=PANEL):
    x0, y0, x1, y1 = panel
    return frame[y0:y1, x0:x1]


def white_mask(bgr, thresh=170):
    """Near-white, low-saturation pixels — the MPH digits and the word MPH."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return ((hsv[:, :, 2] >= thresh) & (hsv[:, :, 1] <= 60)).astype(np.uint8) * 255


def glyph_boxes(mask, min_area=18, min_h=8):
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    boxes = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a >= min_area and h >= min_h and w >= 3:
            boxes.append((x, y, w, h))
    return sorted(boxes, key=lambda b: (b[1] // 10, b[0]))   # row-major


def norm_glyph(mask, box):
    x, y, w, h = box
    g = mask[y:y + h, x:x + w]
    return cv2.resize(g, GLYPH_WH, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float((a * b).sum() / d) if d > 1e-9 else 0.0


# --------------------------------------------------------------------------- scan
def cmd_scan(args):
    cap = cv2.VideoCapture(args.video)
    uniq: list[np.ndarray] = []
    counts: list[int] = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % args.step == 0:
            m = white_mask(panel_of(frame))
            for box in glyph_boxes(m):
                g = norm_glyph(m, box)
                best, bi = 0.0, -1
                for i, u in enumerate(uniq):
                    s = ncc(g, u)
                    if s > best:
                        best, bi = s, i
                if best >= args.merge:
                    counts[bi] += 1
                else:
                    uniq.append(g); counts.append(1)
        idx += 1
    cap.release()

    order = np.argsort(counts)[::-1]
    uniq = [uniq[i] for i in order]; counts = [counts[i] for i in order]
    gw, gh = GLYPH_WH
    pad, cols = 6, min(10, len(uniq))
    rows = int(np.ceil(len(uniq) / cols)) if cols else 0
    sheet = np.zeros(((gh + 22) * rows + pad, (gw + pad) * cols + pad), np.uint8)
    for i, g in enumerate(uniq):
        r, c = divmod(i, cols)
        y = r * (gh + 22) + pad; x = c * (gw + pad) + pad
        sheet[y:y + gh, x:x + gw] = (g * 255).astype(np.uint8)
        cv2.putText(sheet, str(i), (x, y + gh + 14), cv2.FONT_HERSHEY_PLAIN, 0.8, 255, 1)
    sheet = cv2.resize(sheet, None, fx=args.zoom, fy=args.zoom,
                       interpolation=cv2.INTER_NEAREST)
    Path(args.sheet).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(args.sheet, sheet)
    np.savez(args.glyphs, glyphs=np.stack(uniq), counts=np.array(counts))
    print(f"{len(uniq)} distinct glyphs (counts {counts})")
    print(f"contact sheet -> {args.sheet}\nglyph bank   -> {args.glyphs}")
    print("Now read the sheet and run:  hud_ocr.py label --chars \"<c0>,<c1>,...\"")


# -------------------------------------------------------------------------- label
def cmd_label(args):
    data = np.load(args.glyphs)
    glyphs = data["glyphs"]
    chars = [c.strip() for c in args.chars.split(",")]
    if len(chars) != len(glyphs):
        raise SystemExit(f"{len(glyphs)} glyphs but {len(chars)} labels given")
    Path(args.templates).write_text(json.dumps(
        {"glyph_wh": list(GLYPH_WH),
         "templates": [{"char": c, "pix": g.round(3).tolist()}
                       for c, g in zip(chars, glyphs) if c not in ("", "?")]},
        indent=None), encoding="utf-8")
    kept = sum(c not in ("", "?") for c in chars)
    print(f"wrote {args.templates} ({kept}/{len(chars)} glyphs labelled)")


# --------------------------------------------------------------------------- read
def load_templates(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return [(t["char"], np.array(t["pix"], np.float32)) for t in d["templates"]]


def read_panel(frame, templates, min_score):
    """-> (text, min_glyph_score). Empty text when the panel shows nothing."""
    m = white_mask(panel_of(frame))
    boxes = glyph_boxes(m)
    if not boxes:
        return "", 0.0
    out, worst = [], 1.0
    for box in boxes:
        g = norm_glyph(m, box)
        best, bc = -1.0, "?"
        for c, t in templates:
            s = ncc(g, t)
            if s > best:
                best, bc = s, c
        out.append(bc if best >= min_score else "?")
        worst = min(worst, best)
    return "".join(out), worst


def cmd_read(args):
    templates = load_templates(args.templates)
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    per_frame = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % args.step == 0:
            txt, sc = read_panel(frame, templates, args.min_score)
            per_frame.append({"frame": idx, "text": txt, "score": round(sc, 3)})
        idx += 1
    cap.release()

    # The HUD holds one reading on screen for many frames; collapse runs into
    # shots and keep only readings that are a clean number (the MPH value).
    shots, run = [], None
    for r in per_frame:
        digits = "".join(ch for ch in r["text"] if ch.isdigit())
        val = int(digits) if digits and "?" not in r["text"] else None
        if run and run["mph"] == val:
            run["end"] = r["frame"]; run["n"] += 1
        else:
            if run and run["mph"] is not None and run["n"] >= args.min_run:
                shots.append(run)
            run = {"mph": val, "start": r["frame"], "end": r["frame"], "n": 1}
    if run and run["mph"] is not None and run["n"] >= args.min_run:
        shots.append(run)

    # The panel dips through a fade between strokes, which splits one reading
    # into neighbouring runs of the same value. Rejoin those.
    merged: list[dict] = []
    for s in shots:
        if merged and merged[-1]["mph"] == s["mph"] and \
                (s["start"] - merged[-1]["end"]) / fps <= args.merge_gap_s:
            merged[-1]["end"] = s["end"]
            merged[-1]["n"] += s["n"]
        else:
            merged.append(s)
    shots = merged

    for s in shots:
        s["t_start_s"] = round(s["start"] / fps, 2)
        s["t_end_s"] = round(s["end"] / fps, 2)
        s["kmh"] = round(s["mph"] * 1.609344, 1)

    out = {"video": Path(args.video).name, "fps": fps, "step": args.step,
           "source": "SwingVision burned-in HUD (an independent single-camera "
                     "estimate, NOT radar ground truth)",
           "shots": shots}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"{len(shots)} HUD shot readings")
    for s in shots:
        print(f"  t={s['t_start_s']:>6.2f}-{s['t_end_s']:>6.2f}s  "
              f"{s['mph']:>3} MPH ({s['kmh']:.1f} km/h)  {s['n']} frames")
    print(f"wrote {args.out}")

    if args.contact_sheet:
        cap = cv2.VideoCapture(args.video)
        tiles = []
        for s in shots:
            mid = (s["start"] + s["end"]) // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
            ok, frame = cap.read()
            if not ok:
                continue
            crop = cv2.resize(panel_of(frame), None, fx=3, fy=3,
                              interpolation=cv2.INTER_NEAREST)
            crop = cv2.copyMakeBorder(crop, 4, 30, 4, 4, cv2.BORDER_CONSTANT, value=0)
            cv2.putText(crop, f"read {s['mph']}", (8, crop.shape[0] - 8),
                        cv2.FONT_HERSHEY_PLAIN, 1.4, (255, 255, 255), 2)
            tiles.append(crop)
        cap.release()
        cols = 6
        rows = [np.hstack(tiles[i:i + cols] + [np.zeros_like(tiles[0])] *
                          (cols - len(tiles[i:i + cols])))
                for i in range(0, len(tiles), cols)]
        cv2.imwrite(args.contact_sheet, np.vstack(rows))
        print(f"verification sheet -> {args.contact_sheet}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    gl = str(REPO / "data" / "gold" / "hud_glyphs.npz")
    tp = str(REPO / "data" / "gold" / "hud_templates.json")

    s = sub.add_parser("scan"); s.set_defaults(fn=cmd_scan)
    s.add_argument("--video", required=True)
    s.add_argument("--step", type=int, default=10)
    s.add_argument("--merge", type=float, default=0.93,
                   help="NCC above which two glyphs are the same character")
    s.add_argument("--glyphs", default=gl)
    s.add_argument("--sheet", default=str(REPO / "data" / "output" / "hud_glyphs.png"))
    s.add_argument("--zoom", type=int, default=4)

    s = sub.add_parser("label"); s.set_defaults(fn=cmd_label)
    s.add_argument("--chars", required=True,
                   help="comma-separated characters in contact-sheet order; "
                        "use ? to drop a glyph")
    s.add_argument("--glyphs", default=gl)
    s.add_argument("--templates", default=tp)

    s = sub.add_parser("read"); s.set_defaults(fn=cmd_read)
    s.add_argument("--video", required=True)
    s.add_argument("--templates", default=tp)
    s.add_argument("--step", type=int, default=2)
    s.add_argument("--min-score", type=float, default=0.80)
    s.add_argument("--min-run", type=int, default=3)
    s.add_argument("--merge-gap-s", type=float, default=0.6,
                   help="rejoin same-value runs split by the panel's fade")
    s.add_argument("--contact-sheet", default=None,
                   help="write one crop per shot, stamped with what was read, "
                        "so the OCR can be checked by eye before it is trusted")
    s.add_argument("--out", default=str(REPO / "data" / "gold" / "hud_yt_rally2.json"))

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
