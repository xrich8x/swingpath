"""mask_hud.py — find the burned-in graphics in a clip and paint them out.

WHY THIS EXISTS
---------------
The far-court label queue puts source-resolution frames in front of a human and
asks "where is the ball?". On footage carrying a burned-in scoreboard the pilot
labeller clicked *inside the graphic* — see data/output/farcourt_label_yield.md
and data/output/farcourt_anchor_audit.md. A label on a scoreboard teaches the
detector that a scoreboard is a ball, which is a confuser it already fires on,
so those clicks are worse than no clicks. This masks the graphic before the
frame reaches the labeller.

Paint it flat, never crop: cropping changes the frame geometry and every click
coordinate would stop matching the source video.

WHAT ACTUALLY SEPARATES A GRAPHIC FROM THE SCENE, MEASURED
----------------------------------------------------------
The obvious rule — "a HUD is static across the clip, so low temporal variance
finds it" — DOES NOT WORK on this footage, and it fails in both directions
(numbers in data/output/farcourt_hud_mask.md):

  * these clips are edited compilations with cuts and auto-exposure, so per-pixel
    std over the whole clip has NOTHING below 6/255 on 3 of 12 clips — including
    two that carry an obvious scoreboard;
  * on the two clips with a locked-off camera and an empty court, HALF THE FRAME
    is below the same threshold, so a variance mask paints the court.

Four things make it work, and only the first is temporal:

  1. agreement with the temporal MEDIAN (the share of sampled frames within TOL
     of it) instead of std. It survives the score digits changing and it
     survives a cut, because a cut moves a minority of frames far away rather
     than inflating everything;
  2. SMALL and FLUSH TO A FRAME BORDER — an overlay is composited by software
     against an edge. The court is neither;
  3. RIGID AGAINST A NON-RIGID SURROUND. This is the constraint that keeps the
     court out. A patch of empty court and a patch of sky are rigid, but so is
     everything around them; a scoreboard is rigid while the scene behind it
     moves. Measured as agreement inside minus agreement in a ring outside;
  4. SYNTHETIC STRUCTURE — text and panel borders give a high edge density in
     the median plate. Flat court and flat sky give almost none.

3 and 4 are both required, because each alone lets one real failure through: 3
alone accepts the far treeline (rigid, structured, edge-adjacent) and 4 alone
accepts a strip of court beneath a busy sideline.

WHAT THIS DOES NOT CLAIM, AND IT IS MOST OF IT
----------------------------------------------
It is a proposer, not an oracle. MEASURED on the 12 training clips: the
automatic rule finds the "Shots Tracked by SWINGVISION" watermark — the class
that matters most, because its logo is literally a yellow tennis ball — on
every clip that carries one, and finds **none of the six score panels**. Those
sit over sky or over dark stands, which are as rigid as the panel, so test 3
rejects them by construction and no threshold recovers them: on 3 of the 12
clips the panel is not a candidate at ANY setting because whole-clip agreement
inside it never reaches even 0.60 (the score digits and the player names change
mid-clip).

So a burned-in graphic is NOT reliably separable from static scenery by any
temporal statistic on this footage — std, median-agreement and correlation with
global exposure were all measured and all fail (data/output/farcourt_hud_mask.md).
The clips are a known, fixed set of twelve, so the rest of the boxes are
HAND-AUTHORED, carry `"src": "manual"`, survive a re-run of the detector, and
are verified on the same contact sheet. The manifest records exactly what was
painted and who chose it. That is the honest division of labour; a cleverer
detector is not on the critical path for a 12-clip pool.

The mask is proposed automatically and verified BY EYE on a contact sheet —
a wrong mask on a labelling input is worse than no mask, so this is not a step
to skip:

    py tools/mask_hud.py --all --contact-sheet data/output/hud_masks.jpg \
        --json data/hud_masks.json

Then `select_farcourt_labels.py --hud-masks data/hud_masks.json` applies it and
records the boxes it painted in the queue manifest, so any label can be audited
against the mask that was in force when it was made.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# --- the rule, as constants so the tests can pin it ---------------------------
N_SAMPLE = 80          # frames spread over the whole clip
WORK_LONG = 960        # stats run here; boxes are scaled back to source pixels
TOL = 3.0              # "this frame agrees with the median at this pixel"
AGREE_MIN = 0.60       # ... on at least this share of sampled frames
BORDER_FRAC = 0.04     # a composited overlay is flush to a frame border
MAX_AREA_FRAC = 0.06   # ... and small. The court and the sky are not
MIN_AREA_FRAC = 0.0004 # below this it is noise, not a graphic
RING_MIN = 0.15        # rigid INSIDE by this much more than in a ring outside
STRUCT_MIN = 0.06      # share of pixels on an edge in the median plate
FILL = (60, 60, 60)    # flat, dark, featureless: nothing here resembles a ball


def _sample(video: str, n: int = N_SAMPLE):
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_wh = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
              int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    frames = []
    for i in np.linspace(0, max(0, total - 1), n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, im = cap.read()
        if ok:
            s = WORK_LONG / max(im.shape[:2])
            frames.append(cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)))
                          if s < 1 else im)
    cap.release()
    if len(frames) < 8:
        raise SystemExit(f"{video}: only {len(frames)} readable frames")
    return np.stack(frames), src_wh


def boxes_from_agreement(agree, src_wh, plate=None, *, agree_min=AGREE_MIN,
                         border_frac=BORDER_FRAC, max_area_frac=MAX_AREA_FRAC,
                         min_area_frac=MIN_AREA_FRAC, ring_min=RING_MIN,
                         struct_min=STRUCT_MIN):
    """Rigid + small + flush-to-a-border + rigid-against-its-surround +
    structured -> a burned-in graphic, in SOURCE pixels.

    Split out from the video reading so a test can drive it with a hand-built
    agreement map and pin each constraint separately. `plate` (the median frame
    at the same resolution as `agree`) is what the structure test reads; without
    it that test is skipped.
    """
    import cv2
    import numpy as np

    h, w = agree.shape
    rigid = (agree >= agree_min).astype(np.uint8)
    # OPEN first: a HUD panel that happens to touch a rigid patch of court by a
    # one-pixel bridge would otherwise be one component with it, and the pair
    # fails the area cap together. CLOSE after, so a panel whose digits changed
    # stays ONE component rather than a spray that each fail the area floor.
    k3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    rigid = cv2.morphologyEx(rigid, cv2.MORPH_OPEN, k3)
    rigid = cv2.morphologyEx(rigid, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
    edges = None
    if plate is not None:
        g = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY) if plate.ndim == 3 else plate
        mag = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, 3)) + \
            np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1, 3))
        edges = (mag > 120).astype(np.float32)

    num, lab, st, _ = cv2.connectedComponentsWithStats(rigid, 8)
    bx, by = max(1, int(border_frac * w)), max(1, int(border_frac * h))
    sx, sy = src_wh[0] / w, src_wh[1] / h
    out = []
    for i in range(1, num):
        x, y, cw, ch, area = st[i]
        frac = area / float(w * h)
        if not (min_area_frac <= frac <= max_area_frac):
            continue
        # Flush to a border. An overlay is drawn against an edge of the frame;
        # a bench or a line marker in the middle of the court is not.
        if not (x <= bx or y <= by or x + cw >= w - bx or y + ch >= h - by):
            continue
        m = lab[y:y + ch, x:x + cw] == i
        # Rigid against a NON-rigid surround. A ring one component-radius wide,
        # excluding the component itself; empty court and sky fail here because
        # their surroundings are just as still as they are.
        pad = max(4, int(0.4 * max(cw, ch)))
        rx0, ry0 = max(0, x - pad), max(0, y - pad)
        rx1, ry1 = min(w, x + cw + pad), min(h, y + ch + pad)
        ring = np.ones((ry1 - ry0, rx1 - rx0), bool)
        ring[y - ry0:y - ry0 + ch, x - rx0:x - rx0 + cw] = ~m
        a_in = float(agree[y:y + ch, x:x + cw][m].mean())
        a_ring = float(agree[ry0:ry1, rx0:rx1][ring].mean()) if ring.any() else 0.0
        if a_in - a_ring < ring_min:
            continue
        if edges is not None and float(edges[y:y + ch, x:x + cw][m].mean()) < struct_min:
            continue
        out.append({"x": int(round(x * sx)), "y": int(round(y * sy)),
                    "w": int(round(cw * sx)), "h": int(round(ch * sy)),
                    "area_frac": round(frac, 5), "src": "auto"})
    # Re-apply the area cap AFTER merging: a union of legal boxes is not itself
    # legal, and letting one through is how a first cut painted 37% of a frame.
    cap = max_area_frac * src_wh[0] * src_wh[1]
    return [b for b in _merge(out) if b["w"] * b["h"] <= cap]


def _merge(boxes, pad=2):
    """Union overlapping boxes so one panel is one entry, not eleven."""
    out = []
    for b in sorted(boxes, key=lambda b: -b["w"] * b["h"]):
        for o in out:
            if (b["x"] < o["x"] + o["w"] + pad and o["x"] < b["x"] + b["w"] + pad
                    and b["y"] < o["y"] + o["h"] + pad
                    and o["y"] < b["y"] + b["h"] + pad):
                x0, y0 = min(o["x"], b["x"]), min(o["y"], b["y"])
                o["w"] = max(o["x"] + o["w"], b["x"] + b["w"]) - x0
                o["h"] = max(o["y"] + o["h"], b["y"] + b["h"]) - y0
                o["x"], o["y"] = x0, y0
                o["area_frac"] = round(o.get("area_frac", 0) + b.get("area_frac", 0), 5)
                # A merged box inherits "manual" so the next re-run still
                # protects it; otherwise absorbing an auto box would quietly
                # make a hand-authored region disposable.
                if "manual" in (o.get("src"), b.get("src")):
                    o["src"] = "manual"
                break
        else:
            out.append(dict(b))
    return sorted(out, key=lambda b: (b["y"], b["x"]))


def detect(video: str, n: int = N_SAMPLE, **kw):
    """(boxes in source px, plate at work res, agreement map, source (w, h))."""
    import numpy as np

    st, src_wh = _sample(video, n)
    g = st[..., :3].astype(np.float32).mean(3)
    agree = (np.abs(g - np.median(g, 0)) <= TOL).mean(0)
    plate = np.median(st, 0).astype(np.uint8)
    return boxes_from_agreement(agree, src_wh, plate, **kw), plate, agree, src_wh


def apply_mask(img, boxes, fill=FILL):
    """Paint the boxes flat, IN PLACE-safe, at whatever resolution img is.

    Boxes are stored in the source video's pixels; a frame handed to the
    labeller is that same frame, so no rescaling is needed. Anything else would
    have to rescale here, so this asserts nothing and simply clips.
    """
    import cv2

    out = img.copy()
    h, w = out.shape[:2]
    for b in (b for b in boxes if b.get("src") != "rejected"):
        x0, y0 = max(0, b["x"]), max(0, b["y"])
        x1, y1 = min(w, b["x"] + b["w"]), min(h, b["y"] + b["h"])
        if x1 > x0 and y1 > y0:
            cv2.rectangle(out, (x0, y0), (x1 - 1, y1 - 1), fill, -1)
    return out


def covers(boxes, x, y) -> bool:
    return any(b["x"] <= x < b["x"] + b["w"] and b["y"] <= y < b["y"] + b["h"]
               for b in boxes)


def load_masks(path, *, all_entries=False):
    """{video filename -> [box, ...]} from a mask JSON, or {} if there is none.

    Rejected proposals are stored alongside the real boxes so the record of what
    a human refused survives; they are dropped here, because a caller asking for
    the mask wants what gets PAINTED. `all_entries` returns them too.
    """
    p = Path(path)
    if not p.is_file():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return {k: [b for b in (v.get("boxes") or [])
                if all_entries or b.get("src") != "rejected"]
            for k, v in (d.get("clips") or {}).items()}


def _human(existing, video_name):
    """(hand-authored boxes, rejected proposals) for one clip.

    Both survive a re-run of the detector. Re-detecting must never silently
    delete a box a human added after looking at the contact sheet — that is the
    only thing covering the score panels — and it must never resurrect a
    proposal a human already looked at and refused. Two of the auto boxes here
    lie on the COURT, and on a labelling input that is the expensive direction
    to get wrong.
    """
    bs = existing.get(video_name, [])
    return ([dict(b) for b in bs if b.get("src") == "manual"],
            [dict(b) for b in bs if b.get("src") == "rejected"])


def _drop_rejected(boxes, rejected):
    def inside(b):
        cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        return any(r["x"] <= cx < r["x"] + r["w"] and r["y"] <= cy < r["y"] + r["h"]
                   for r in rejected)
    return [b for b in boxes if b.get("src") == "manual" or not inside(b)]


def main() -> None:
    import cv2
    import numpy as np

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clips", nargs="*", default=[],
                    help="video paths; or use --all")
    ap.add_argument("--all", action="store_true",
                    help="every mp4 in data/train_clips")
    ap.add_argument("--json", default=str(REPO / "data/hud_masks.json"))
    ap.add_argument("--contact-sheet", default="",
                    help="write a before/after sheet. VERIFY THE MASK BY EYE — a "
                         "wrong mask on a labelling input is worse than none")
    ap.add_argument("--samples", type=int, default=N_SAMPLE)
    ap.add_argument("--verify-sheet", default="",
                    help="THE GATE. Crops each box out of several REAL frames "
                         "with the mask applied, at 1:1 and with a margin, so a "
                         "graphic leaking past an edge is visible. The median "
                         "plate cannot show this — a panel that moves or grows "
                         "mid-clip averages away in the plate and is still there "
                         "on the frame the labeller gets")
    ap.add_argument("--verify-frames", type=int, default=4)
    ap.add_argument("--verify-margin", type=int, default=45)
    args = ap.parse_args()

    vids = [Path(v) for v in args.clips]
    if args.all:
        vids += sorted((REPO / "data/train_clips").glob("*.mp4"))
    if not vids:
        raise SystemExit("nothing to do: pass --clips or --all")

    prev = load_masks(args.json, all_entries=True)
    out, tiles = {}, []
    for v in vids:
        boxes, plate, agree, src_wh = detect(str(v), args.samples)
        manual, rejected = _human(prev, v.name)
        boxes = _drop_rejected(_merge(manual + boxes), rejected)
        frac = sum(b["w"] * b["h"] for b in boxes) / float(src_wh[0] * src_wh[1])
        out[v.name] = {"video": v.name, "src_wh": list(src_wh),
                       "boxes": boxes + rejected, "masked_frac": round(frac, 4)}
        n_man = sum(1 for b in boxes if b.get("src") == "manual")
        print(f"{v.stem:<22} {len(boxes)} box(es) ({n_man} manual, "
              f"{len(rejected)} rejected)  {frac * 100:5.2f}% of frame  "
              f"{[ (b['x'],b['y'],b['w'],b['h']) for b in boxes ]}")
        if args.contact_sheet:
            sc = plate.shape[1] / src_wh[0]
            sb = [{k: (int(b[k] * sc) if k in "xywh" else b[k]) for k in b}
                  for b in boxes]
            t = np.hstack([plate, apply_mask(plate, sb)])
            t = cv2.resize(t, (1120, int(1120 * t.shape[0] / t.shape[1])))
            cv2.putText(t, v.stem, (6, 20), 0, 0.6, (0, 255, 255), 2)
            tiles.append(t)

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(
        {"tool": "mask_hud.py", "created": time.strftime("%Y-%m-%d %H:%M:%S"),
         "params": {"samples": args.samples, "tol": TOL, "agree_min": AGREE_MIN,
                    "border_frac": BORDER_FRAC, "max_area_frac": MAX_AREA_FRAC,
                    "min_area_frac": MIN_AREA_FRAC, "fill": list(FILL)},
         "clips": out}, indent=1), encoding="utf-8")
    print(f"\nwrote {args.json}")
    if tiles:
        wmax = max(t.shape[1] for t in tiles)
        cv2.imwrite(args.contact_sheet, np.vstack(
            [np.pad(t, ((0, 0), (0, wmax - t.shape[1]), (0, 0))) for t in tiles]),
            [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"wrote {args.contact_sheet} — CHECK IT BY EYE before labelling")

    if args.verify_sheet:
        _verify_sheet(vids, out, args)


def _verify_sheet(vids, masks, args):
    import cv2
    import numpy as np

    rows = []
    for v in vids:
        boxes = [b for b in masks[v.name]["boxes"] if b.get("src") != "rejected"]
        if not boxes:
            continue
        cap = cv2.VideoCapture(str(v))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames = []
        for i in np.linspace(0.1 * total, 0.9 * total, args.verify_frames).astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, im = cap.read()
            if ok:
                frames.append((int(i), apply_mask(im, boxes)))
        cap.release()
        m = args.verify_margin
        for b in boxes:
            strip = []
            for fi, im in frames:
                x0, y0 = max(0, b["x"] - m), max(0, b["y"] - m)
                x1 = min(im.shape[1], b["x"] + b["w"] + m)
                y1 = min(im.shape[0], b["y"] + b["h"] + m)
                c = im[y0:y1, x0:x1].copy()
                cv2.rectangle(c, (b["x"] - x0, b["y"] - y0),
                              (b["x"] + b["w"] - x0 - 1, b["y"] + b["h"] - y0 - 1),
                              (0, 0, 255), 1)
                cv2.putText(c, f"{v.stem[:14]} f{fi} {b.get('what', b.get('src'))}",
                            (3, 14), 0, 0.4, (0, 255, 255), 1)
                strip.append(c)
            h = max(s.shape[0] for s in strip)
            rows.append(np.hstack([np.pad(s, ((0, h - s.shape[0]), (0, 0), (0, 0)))
                                   for s in strip]))
    if not rows:
        print("nothing to verify: no boxes")
        return
    wmax = max(r.shape[1] for r in rows)
    cv2.imwrite(args.verify_sheet, np.vstack(
        [np.pad(r, ((0, 0), (0, wmax - r.shape[1]), (0, 0))) for r in rows]),
        [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"wrote {args.verify_sheet} — {len(rows)} box(es) x "
          f"{args.verify_frames} real frames. A graphic visible OUTSIDE a red "
          f"rectangle is a gate failure")


if __name__ == "__main__":
    main()
