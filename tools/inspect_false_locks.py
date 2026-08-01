"""inspect_false_locks.py — WHAT is the detector firing at? (Session F step 2)

Every false-alarm fix this project has shipped assumed the confusers were
fixtures. That assumption is now measurably wrong on the clip that needs it most:
the E6 per-gate counters report `fixture = 0` on am_hard_utr across 28,998
frames — the static-lock gate never fires there, because that clip has no
burned-in HUD — yet its raw false-fire is the worst of any gold clip at 45.3%.
So the survivors MOVE, and the hard-negative miner's entire criterion ("a lock
that does not move for several frames is provably a fixture") cannot address
them. Before spending a GPU hour on a retrain or on motion attention, look at
what is actually there.

For every human-labelled no-ball frame the detector fires on, this reports
position, court projection, local roam, run length, and — with
--contact-sheet — a cropped image of the thing itself, so the classification is
done by eye rather than by adjective.

  py tools/inspect_false_locks.py --stage raw --all-clips --contact-sheet \\
      --device cuda --json data/output/f_falselocks_raw.json

TWO POPULATIONS, AND THEY ARE NOT INTERCHANGEABLE
-------------------------------------------------
  --stage raw    the detector alone, no tracker, exactly what
                 eval_detector_gold.py scores. Cheap (one 3-frame window per
                 labelled frame, ~204 windows for all six clips) and it runs on
                 every gold clip, calibrated or not. THIS is the population a
                 retrain or a new architecture can act on.
  --stage chain  what survives rectify -> suppress_false_locks ->
                 gate_ball_to_court -> smooth_forecast, i.e. what the user
                 actually sees drawn. Needs a full-video GPU pass and a
                 calibration, so it is the three calibrated clips only.

Do NOT pool the two tables: they are different pipelines and the chain is a
subset of a differently-measured whole.

THREE THINGS THE PREVIOUS VERSION GOT WRONG
-------------------------------------------
1. It read data/output/yt_rally2_v2.perception.json — a cache built by the v2
   detector, when the shipped default has been ballnet_v21 since E5+. CLAUDE.md
   and the session brief both warn never to quote a current-state number from a
   stale cache. Perception is now always fresh.
2. It indexed the track with a bare `f // step` and no `f % step == 0` guard.
   That is the exact bug that understated the tracker through E6 part 2 and
   forced a set of published numbers to be withdrawn. Harmless on yt_rally2
   (100% even frames), wrong on am_hard_utr (48.6% odd). It now imports the one
   guard in the repo.
3. It was hardcoded to one clip, so the clip with the worst false-fire had never
   been inspected at all.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from eval_detector_gold import CLIPS as RAW_CLIPS, load_H  # noqa: E402
from eval_model_filters import build_calib, index_of  # noqa: E402

SHEET_COLS = 6


def gold_noball(clip):
    labels = json.loads((REPO / f"data/gold/{clip}.labels.json").read_text(
        encoding="utf-8"))["labels"]
    return sorted(int(k) for k, v in labels.items()
                  if v.get("ball") is False and not v.get("unsure"))


def describe(locks, i, radius=15.0, R=8):
    """Local motion around one lock: how far it roams, and how long it holds.

    A real ball traverses the frame; a fixture sits still; a mislock on a moving
    player flares for a few frames without ever forming a track. These two
    numbers are what separate those cases without needing the court projection,
    which is the whole reason suppress_false_locks works where the court gate
    does not.
    """
    n = len(locks)
    run = 0
    if locks[i] is not None:
        c0, run = locks[i], 1
        for d in (1, -1):
            j = i + d
            while 0 <= j < n and locks[j] is not None \
                    and math.dist(locks[j], c0) <= radius:
                run += 1
                j += d
    pts = [locks[j] for j in range(max(0, i - R), min(n, i + R + 1))
           if locks[j] is not None]
    roam = 0.0 if len(pts) < 2 else max(math.dist(a, b) for a in pts for b in pts)
    return roam, run


def raw_locks(clip, video, device, weights):
    """The detector alone on each labelled no-ball frame.

    Mirrors eval_detector_gold.score_clip's window exactly — 3 frames ending on
    the labelled one, det.reset() between windows — so a lock counted here is a
    lock counted in that tool's false-fire column, and the two tables can be
    reconciled.
    """
    os.environ["BALLNET_WEIGHTS"] = weights
    from swingvision.ball import OurBallDetector
    det = OurBallDetector(device=device)
    cap = cv2.VideoCapture(str(REPO / video))
    out = {}
    for f in gold_noball(clip):
        frames = []
        for j in (f - 2, f - 1, f):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, j))
            ok, im = cap.read()
            if ok:
                frames.append(im)
        if len(frames) < 3:
            continue
        det.reset()
        p = None
        for im in frames:
            p = det.detect(im)
        out[f] = None if p is None else [float(p[0]), float(p[1])]
    cap.release()
    return out


def chain_locks(clip, video, pts_rel, device, weights, frame_step):
    """What survives the shipped post-chain — i.e. what the renderer draws.

    Reuses eval_model_filters.perceive so the tracker configuration cannot drift
    from the ladder's, and re-applies the same four stages in the same order as
    pipeline.analyze_video.
    """
    from eval_model_filters import perceive
    from swingvision import ball as B, calibration
    cap = cv2.VideoCapture(str(REPO / video))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    H, hfov = build_calib(pts_rel, (W, Hh))
    step = frame_step or max(1, round(src_fps / 30.0))
    fps_eff = src_fps / step
    cam_xyz = calibration.camera_position_m(H, (W, Hh), hfov)
    raw = perceive(REPO / video, weights, device, H, cam_xyz, W, Hh,
                   fps_eff, step)
    rs = Hh / 720.0
    tr = B.remove_outliers(list(raw), max_jump=max(W, Hh) * 0.06)
    tr = B.rectify_track(tr, max_speed_px=3000.0 * rs / fps_eff, resid_px=35.0 * rs)
    tr = B.suppress_false_locks(tr, fps_eff=fps_eff, res_scale=rs)
    tr = B.gate_ball_to_court(tr, H, (W, Hh), hfov_deg=hfov)
    tr, coasted, _ = B.smooth_forecast(tr, fps_eff=fps_eff, res_scale=rs)
    at = index_of(step, len(tr))
    out, ctx = {}, {}
    for f in gold_noball(clip):
        pf = at(f)
        if pf is None:
            continue                       # unprocessed: unscoreable, not a miss
        out[f] = None if tr[pf] is None else [float(x) for x in tr[pf]]
        ctx[f] = (tr, pf, coasted[pf] if pf < len(coasted) else None, fps_eff)
    return out, ctx, step


def contact_sheet(rows, path, crop_px=140, tile=224):
    """A grid of what the detector actually fired at, cropped from the gold
    frames already on disk (all 204 no-ball frames are extracted, so this costs
    no video decode).

    ML_PRACTICES: show a human the examples before anything is built on them.
    The crop deliberately shows CONTEXT, not just the lock: at ball-sized zoom
    every false lock is an ambiguous blob, and the question here is what the
    blob belongs to — a racquet, a shoe, a line, a fence.
    """
    tiles = []
    for r in rows:
        src = REPO / f"data/gold/frames/{r['clip']}/f{r['frame']:05d}.jpg"
        im = cv2.imread(str(src)) if src.exists() else None
        if im is None:
            continue
        h, w = im.shape[:2]
        x, y = int(r["x"]), int(r["y"])
        x0, y0 = max(0, x - crop_px // 2), max(0, y - crop_px // 2)
        x1, y1 = min(w, x0 + crop_px), min(h, y0 + crop_px)
        crop = im[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        sx, sy = tile / max(x1 - x0, 1), tile / max(y1 - y0, 1)
        crop = cv2.resize(crop, (tile, tile), interpolation=cv2.INTER_LINEAR)
        # Cross-hair on the lock, drawn as an open gap so the pixels underneath
        # stay visible — a marker that covers the evidence defeats the purpose.
        cx, cy = int((x - x0) * sx), int((y - y0) * sy)
        for dx in (-16, 8):
            cv2.line(crop, (cx + dx, cy), (cx + dx + 8, cy), (0, 0, 255), 1)
            cv2.line(crop, (cx, cy + dx), (cx, cy + dx + 8), (0, 0, 255), 1)
        cv2.putText(crop, f"{r['clip']}:{r['frame']}", (3, tile - 5),
                    cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 255, 255), 1)
        tiles.append(crop)
    if not tiles:
        return 0
    cols = min(SHEET_COLS, len(tiles))
    rows_n = (len(tiles) + cols - 1) // cols
    sheet = np.zeros((rows_n * tile, cols * tile, 3), np.uint8)
    for i, t in enumerate(tiles):
        r_, c_ = divmod(i, cols)
        sheet[r_ * tile:(r_ + 1) * tile, c_ * tile:(c_ + 1) * tile] = t
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), sheet)
    return len(tiles)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", action="append", default=None,
                    help="repeatable; default is every gold clip the stage supports")
    ap.add_argument("--stage", choices=("raw", "chain"), default="raw")
    ap.add_argument("--weights", default="weights/ballnet_v21.pt")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--frame-step", type=int, default=None,
                    help="chain stage only; 1 makes every gold frame scoreable")
    ap.add_argument("--contact-sheet", default=None,
                    help="write a labelled grid of the false locks to this path. "
                         "With more than one clip, also writes a per-clip sheet "
                         "alongside it — the pooled grid is too dense to classify "
                         "from, and classifying is the point")
    ap.add_argument("--crop-px", type=int, default=140,
                    help="source pixels around each lock; context, not ball zoom")
    ap.add_argument("--tile-px", type=int, default=224)
    ap.add_argument("--classes", default="data/gold/false_lock_classes.json",
                    help="reviewer classification of each lock, keyed clip/frame. "
                         "Kept as data so the tally is an artifact that can be "
                         "re-derived and disagreed with, not a paragraph.")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    table = {t: (v, p) for t, v, p in RAW_CLIPS}
    if args.stage == "chain":
        table = {t: (v, p) for t, (v, p) in table.items() if p}
    clips = args.clip or list(table)
    bad = [c for c in clips if c not in table]
    if bad:
        raise SystemExit(f"{bad} not available at stage={args.stage}; "
                         f"have {sorted(table)}")

    hdr = (f"{'clip':<12}{'frame':>7} {'img(x,y)':>13} {'court(x,y)m':>15} "
           f"{'inCourt':>8} {'roam':>6} {'runLen':>7} {'coast':>6}")
    print(f"stage={args.stage}  weights={args.weights}  device={args.device}\n")
    print(hdr); print("-" * len(hdr))

    rows, per_clip = [], {}
    for clip in clips:
        video, pts_rel = table[clip]
        H = load_H(pts_rel)
        step = 1
        if args.stage == "raw":
            locks = raw_locks(clip, video, args.device, args.weights)
            ctx = {}
        else:
            locks, ctx, step = chain_locks(clip, video, pts_rel, args.device,
                                           args.weights, args.frame_step)
        order = sorted(locks)
        seq = [locks[f] for f in order]
        fires = 0
        for i, f in enumerate(order):
            p = locks[f]
            if p is None:
                continue
            fires += 1
            cxy = ("", "")
            ind = ""
            if H is not None:
                from swingvision import calibration, court
                cx, cy = calibration.image_to_court(H, [p])[0]
                cxy = (f"{cx:.1f}", f"{cy:.1f}")
                ind = "IN" if court.is_in_doubles(cx, cy, 3.0) else "OUT"
            # roam/runLen describe a lock's NEIGHBOURHOOD, so they only mean
            # anything when neighbouring entries are neighbouring frames. At
            # stage=raw the entries are gold labels ~116 source frames apart on
            # am_hard_utr, and "displacement over +/-8 of those" is a number
            # about the rally, not about the lock. Left blank rather than
            # printed as if it were evidence.
            roam, run = describe(seq, i) if args.stage == "chain" \
                else (None, None)
            coast = ctx.get(f, (None, None, None, None))[2]
            rows.append(dict(clip=clip, frame=f, x=round(p[0], 1),
                             y=round(p[1], 1),
                             court_x=None if not cxy[0] else float(cxy[0]),
                             court_y=None if not cxy[1] else float(cxy[1]),
                             in_court=(None if not ind else ind == "IN"),
                             roam_px=None if roam is None else round(roam, 1),
                             run_len=run, coasted=coast, klass=None))
            court_s = "" if not cxy[0] else f"({cxy[0]:>6},{cxy[1]:>6})"
            print(f"{clip:<12}{f:>7} ({p[0]:>6.0f},{p[1]:>4.0f}) {court_s:>15} "
                  f"{ind:>8} {'' if roam is None else f'{roam:.0f}':>6} "
                  f"{'' if run is None else run:>7} "
                  f"{'' if coast is None else ('yes' if coast else 'no'):>6}")
        n_nb = len(order)
        per_clip[clip] = dict(fires=fires, n_scored=n_nb,
                              false_fire=round(100 * fires / max(n_nb, 1), 1),
                              frame_step=step)
        print(f"{'':<12}{'--':>7} {clip}: {fires} locks on {n_nb} scoreable "
              f"no-ball frames ({100 * fires / max(n_nb, 1):.1f}%)")

    # Fold in the reviewer's classification, if one exists for these locks.
    klasses = {}
    cpath = REPO / args.classes if args.classes else None
    if cpath and cpath.exists():
        blob = json.loads(cpath.read_text(encoding="utf-8"))
        klasses = blob.get("labels", {})
        for r in rows:
            r["klass"] = klasses.get(r["clip"], {}).get(str(r["frame"]))

    tot_f = sum(v["fires"] for v in per_clip.values())
    tot_n = sum(v["n_scored"] for v in per_clip.values())
    print("-" * len(hdr))
    print(f"POOLED {tot_f} false locks on {tot_n} no-ball frames "
          f"({100 * tot_f / max(tot_n, 1):.1f}%), measured against human gold clicks")

    tally = {}
    if klasses:
        for r in rows:
            tally[r["klass"] or "UNCLASSIFIED"] = \
                tally.get(r["klass"] or "UNCLASSIFIED", 0) + 1
        # The split that decides Session F steps 4 and 5. Motion attention
        # (TrackNetV4) suppresses STATIC and low-motion confusers; a racquet head
        # or a limb moves with the player and is exactly what it cannot separate.
        moving = sum(tally.get(k, 0) for k in ("racquet", "player"))
        stat = sum(tally.get(k, 0) for k in ("fence", "net", "signage",
                                             "court_line", "court_surface",
                                             "background"))
        ball = tally.get("held_ball", 0)
        print(f"\n  what the detector fired at (reviewer classification, "
              f"{cpath.name}):")
        for k, c in sorted(tally.items(), key=lambda kv: -kv[1]):
            print(f"      {k:<16}{c:>4}  {100*c/max(tot_f,1):>5.1f}%")
        print(f"\n      MOVING WITH A PERSON (racquet+player) {moving:>4}  "
              f"{100*moving/max(tot_f,1):.1f}%")
        print(f"      STATIC SCENERY  (fence/net/signage/line/surface/bg) "
              f"{stat:>4}  {100*stat/max(tot_f,1):.1f}%")
        print(f"      REAL BALL, NOT IN PLAY  (held/basket)  {ball:>10}  "
              f"{100*ball/max(tot_f,1):.1f}%")
    if args.stage == "chain":
        print("roam = max displacement over +/-8 processed frames; runLen = "
              "frames the lock holds within 15 px. A real ball scores high roam "
              "and short run; a fixture the reverse.")
    else:
        print("roam/runLen are blank at stage=raw: consecutive gold labels are "
              "tens to hundreds of source frames apart, so a neighbourhood "
              "statistic over them would describe the rally, not the lock.")

    if args.contact_sheet:
        n = contact_sheet(rows, args.contact_sheet, args.crop_px, args.tile_px)
        print(f"wrote {args.contact_sheet} ({n} of {len(rows)} locks; the rest "
              f"had no extracted gold frame on disk)")
        if len(clips) > 1:
            stem = Path(args.contact_sheet)
            for clip in clips:
                sub = [r for r in rows if r["clip"] == clip]
                if not sub:
                    continue
                p = stem.with_name(f"{stem.stem}_{clip}{stem.suffix}")
                contact_sheet(sub, p, args.crop_px, args.tile_px)
                print(f"  wrote {p} ({len(sub)} locks)")

    if args.json_out:
        try:
            commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                    cwd=REPO, capture_output=True, text=True,
                                    timeout=10).stdout.strip()
        except Exception:
            commit = None
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps({
            "tool": "inspect_false_locks",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "commit": commit, "stage": args.stage, "weights": args.weights,
            "device": args.device,
            "measured_against":
                f"human gold clicks: every frame a human marked 'no ball' "
                f"(unsure excluded). {tot_f} locks on {tot_n} such frames across "
                f"{len(clips)} clip(s). `klass` is null until a human or a "
                f"reviewer fills it in from the contact sheet.",
            "pooled": {"fires": tot_f, "n_scored": tot_n,
                       "false_fire": round(100 * tot_f / max(tot_n, 1), 1)},
            "class_tally": tally, "classes_from": args.classes if klasses else None,
            "per_clip": per_clip, "locks": rows},
            indent=1), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
