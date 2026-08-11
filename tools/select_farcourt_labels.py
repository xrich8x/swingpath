"""select_farcourt_labels.py — queue the far-court frames worth a human click.

WHY THIS EXISTS
---------------
Far-court recall has been "waiting on a few hundred human labels" for several
sessions and never started, because the real number was never counted. It is
**4,087 frames** across **1,267 distinct bracketed gaps** — 4-5 hours of clicking.
A task that size does not get done; a ranked few hundred does.
(Counts and method: data/output/farcourt_label_yield.md.)

Filling them automatically is a MEASURED NEGATIVE: 89% of those frames sit in
bridges of <=10 frames with a confident detection on both sides, but interpolating
between the anchors lands within 10 px of a human click only **63%** of the time,
flat across bridge length. A label that wrong is a Gaussian on empty court.

WHAT THIS SELECTS, AND THE ONE JUDGEMENT IN IT
----------------------------------------------
ONE FRAME PER GAP, the midpoint. Every frame inside a 10-frame gap is a
near-duplicate of its neighbours, so labelling all ten buys roughly one frame of
information for ten clicks. The midpoint is also the furthest from both anchors —
the hardest and most informative single frame in the gap.

Clips are sampled round-robin so no clip dominates: labelling 300 frames from one
rally teaches far less than 300 spread across lighting, courts and camera heights.

--with-anchors (default) also queues the two anchor frames either side of each
gap. They cost clicks but earn them three times over:
  * CONTEXT — arrow-keying anchor -> midpoint -> anchor shows where the ball came
    from and went to, which is most of how a human finds a 2 px ball;
  * A CONTROL — if the anchors are easy to click and the midpoints are not, the
    frames are unlabelable rather than the labeller being slow;
  * A CHECK ON THE PSEUDO-LABELS — the anchors ARE tracker output, so a human
    disagreeing with one is a mislabelled training positive.

LABEL AT SOURCE RESOLUTION, NOT AT 512x288
------------------------------------------
`data/ball_dataset/` holds 512x288 JPEGs — the network's input size — and a far
ball is ~1.6 px there, which is not clickable. The SOURCE videos survive in
`data/train_clips/` at 720p and 1080p, so this extracts from those instead: 2.5x
to 3.75x more linear resolution on the thing the labeller has to find.

Recovering the source frame is exact and pinned by a test. `relabel_train_clips`
builds each directory from `n_windows` windows of `window_len` processed frames,
sampling every `step`-th source frame, and records the processed index of each
seam in `window_starts`. The source starts are recomputed with the same
`np.linspace(0.15*total, 0.85*total - span, n)` and verified against the pixels:

    dataset index i, in window w  ->  source frame  starts[w] + (i - window_starts[w]) * step

Two directories (`amateur`, `highangle`) came from a different pipeline with no
recorded video; they fall back to the 512x288 JPEG and are flagged in the manifest.

BURNED-IN GRAPHICS ARE PAINTED OUT BEFORE THE HUMAN SEES THE FRAME
------------------------------------------------------------------
The first pilot put 5 of its 36 clicks inside a scoreboard graphic
(data/output/farcourt_anchor_audit.md). A label on a scoreboard teaches the
detector that a scoreboard is a ball, which is a confuser it already fires on,
so those clicks are worth less than none. `--hud-masks` (on by default when
data/hud_masks.json exists) paints every declared graphic flat before writing
the frame, and records the boxes in the manifest so any click can be audited
against the mask that was in force when it was made.

A gap whose prior lands INSIDE a mask is dropped rather than queued: the ball
there is behind a graphic in the source video too, so there is nothing for a
human to find and the click would land on grey.

THE PREMISE THIS PILOT TESTS, WHICH IS NOT YET ESTABLISHED
-----------------------------------------------------------
Spot checks show the interpolated point often landing on background the same
colour as the ball (white ball on white signage, dark ball on dark wall) —
plausibly why the detector missed it, and plausibly why a human will too. **Run a
small --gaps first and see whether the ball is visibly there before committing
hours.** If it is not even at source resolution, the fix is new footage.

The first pilot answered that question NO on 7 of 12 gaps, and the reason was
not resolution: the two ANCHORS bracketing those gaps were themselves false
locks on a wall, a tree or a spectator, so there was no ball anywhere near the
interpolated point. The anchors are the control this queue was built to provide
and `farcourt_labels_to_dataset.py` now enforces it — a midpoint is only
accepted as training data if the human confirmed an anchor beside it.

    py tools/select_farcourt_labels.py --gaps 10          # ~30 frames, a pilot
    py tools/lab_server.py                                # label them, Label tab

Writes into data/labels/ (the TRAIN pool). It refuses to touch data/gold/.
"""
from __future__ import annotations

import argparse
import bisect
import glob
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

IN_W, IN_H = 512, 288
FAR_FRAC = 0.36          # the project's resolution-comparable far_px band
MAX_GAP = 10             # 89% of far-court misses; beyond this there is no anchor
NET_Y_M = 11.885         # the real far/near boundary, in court metres


def far_test(dataset_dir: Path, clips_root: Path):
    """A predicate saying whether a 512x288 point is in the FAR COURT.

    Geometric when the clip has a calibration, frame-row otherwise.

    WHY THIS MATTERS, MEASURED: `FAR_FRAC` calls the top 36% of the FRAME "far
    court". That is a proxy for the far half of the COURT, and it only holds for
    the framing it was written against. On the clips added in this session it is
    wrong by 5-26x — `tc8CGFxyRE8` puts **3.2% of its labels in the top 36% of
    the frame and 84.0% past the net**, `e8T34KoJzOw_s2` 5.0% vs 46.1%. A camera
    that frames the court well puts the far baseline LOWER in the frame, so the
    proxy quietly declares a whole clip to have almost no far court and the queue
    skips it.

    Past the net (court-y > 11.885 m) is the real question, and it is answerable
    now that every new clip carries a homography — it was not before.
    """
    import numpy as np      # noqa: F401  (imported for the cv2/H path below)

    row_rule = (lambda x, y: y < FAR_FRAC * IN_H, "frame-row")
    kp = REPO / "data" / f"{dataset_dir.name.removeprefix('yt_')}_pts.json"
    try:
        sm = source_map(dataset_dir, clips_root)
    except (OSError, ValueError, KeyError):
        # A malformed or half-written dataset dir must not take the queue down,
        # and must not silently become "everything is far court" either. Choosing
        # the policy is not the place to fail; fall back to the proxy.
        return row_rule
    if not kp.is_file() or sm is None:
        return row_rule
    import cv2  # noqa: F401
    from swingvision import calibration, court

    _v, _ws, _st, _step, (W, H) = sm
    pts = {k: v for k, v in json.loads(kp.read_text(encoding="utf-8")).items()
           if not k.startswith("_")}
    names = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
    if not all(n in pts for n in names):
        return row_rule
    Hm = calibration.compute_homography([court.LANDMARKS[n] for n in names],
                                        [pts[n] for n in names])
    sx, sy = W / IN_W, H / IN_H

    def geo(x, y):
        cx, cy = calibration.image_to_court(Hm, [(x * sx, y * sy)])[0]
        return cy > NET_Y_M

    return geo, "court-metres"


def candidates(data_root: Path, max_gap: int = MAX_GAP, clips_root: Path = None):
    """One (dir, a, pa, mid, p_interp, b, pb) per bracketed far-court gap."""
    out = []
    for lp in sorted(glob.glob(str(data_root / "*" / "labels.json"))):
        is_far, _how = (far_test(Path(lp).parent, clips_root)
                        if clips_root else
                        (lambda x, y: y < FAR_FRAC * IN_H, "frame-row"))
        d = json.loads(Path(lp).read_text(encoding="utf-8"))
        L = d.get("labels") or {}
        neg = set(d.get("negatives") or [])
        # Windows are separate moments in the source video spliced into one
        # directory, so a gap spanning a boundary joins two unrelated positions.
        # Only ~1% do, but interpolating across one is meaningless.
        ws = sorted(d.get("window_starts") or [])
        ks = sorted(int(k) for k in L)
        for a, b in zip(ks, ks[1:]):
            g = b - a - 1
            if not (1 <= g <= max_gap):
                continue
            if ws and bisect.bisect_right(ws, a) != bisect.bisect_right(ws, b):
                continue
            xa, ya = L[str(a)]
            xb, yb = L[str(b)]
            m = (a + b) // 2
            if m in neg:
                continue
            t = (m - a) / (b - a)
            yi = ya + (yb - ya) * t
            xi = xa + (xb - xa) * t
            if not is_far(xi, yi):
                continue
            out.append((os.path.dirname(lp), a, (xa, ya), m,
                        (xa + (xb - xa) * t, yi), b, (xb, yb)))
    return out


def source_map(dataset_dir: Path, clips_root: Path):
    """(video_path, window_starts, source_starts, step, (W, H)) or None.

    Exact inverse of relabel_train_clips' window sampler. Verified against the
    pixels rather than trusted: see tests/test_farcourt_selection.py.
    """
    import cv2
    import numpy as np

    d = json.loads((dataset_dir / "labels.json").read_text(encoding="utf-8"))
    pv = d.get("provenance") or {}
    name, ws = pv.get("video"), d.get("window_starts") or []
    if not name or not ws:
        return None                       # a different pipeline; no video recorded
    vid = clips_root / name
    if not vid.is_file():
        return None
    step = int(pv.get("frame_step") or 1)
    window_len = ws[1] - ws[0] if len(ws) > 1 else d.get("n_frames", 0)
    cap = cv2.VideoCapture(str(vid))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    wh = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    cap.release()
    span = window_len * step
    starts = np.linspace(0.15 * total, max(0.15 * total, 0.85 * total - span),
                         len(ws)).astype(int).tolist()
    return str(vid), ws, starts, step, wh


def source_frame(idx: int, ws, starts, step) -> int:
    w = bisect.bisect_right(ws, idx) - 1
    return starts[w] + (idx - ws[w]) * step


def key_of(c):
    """(clip dir name, anchor, midpoint, anchor) — identifies a gap across queues."""
    return (os.path.basename(c[0]), c[1], c[3], c[5])


def gaps_in_manifest(path):
    """The set of gaps an earlier queue held, so a new one can REPEAT them.

    A repeat block is a controlled A/B — same gaps, one thing changed — and a
    fresh block measures a rate without the labeller's memory of the first pass
    in it. A queue that is only repeats can do the first and not the second.
    """
    man = json.loads(Path(path).read_text(encoding="utf-8"))
    by = {}
    for gid, r in zip(_manifest_gap_ids(man["frames"]), man["frames"]):
        by.setdefault(gid, []).append(r)
    out = set()
    for rs in by.values():
        rs = sorted(rs, key=lambda r: r["frame"])
        mids = [r for r in rs if r["bucket"] != "anchor"]
        anch = [r for r in rs if r["bucket"] == "anchor"]
        if len(mids) == 1 and len(anch) == 2:
            out.add((rs[0]["src_dataset"], anch[0]["src_frame"],
                     mids[0]["src_frame"], anch[1]["src_frame"]))
    return out


def _manifest_gap_ids(rows):
    if any("gap" in r for r in rows):
        return [r["gap"] for r in rows]
    out, gid, after_mid = [], 0, False
    for r in rows:
        is_mid = r["bucket"] != "anchor"
        if is_mid and after_mid:
            gid, after_mid = gid + 1, False
        out.append(gid)
        if is_mid:
            after_mid = True
        elif after_mid:
            gid, after_mid = gid + 1, False
    return out


def split_pools(cands, repeat_keys, exclude_keys):
    """(repeats, fresh) after removing already-labelled gaps.

    An explicit --repeat-from wins over an --exclude-from, because a session can
    legitimately name the same manifest in both (repeat this queue, skip that
    one) and the controlled half of the queue must not silently empty.
    """
    exclude_keys = set(exclude_keys) - set(repeat_keys)
    kept = [c for c in cands if key_of(c) not in exclude_keys]
    return ([c for c in kept if key_of(c) in repeat_keys],
            [c for c in kept if key_of(c) not in repeat_keys],
            len(cands) - len(kept))


def _interleave(a, b):
    """Spread `a` evenly through `b` rather than putting it in a block at the
    front. Deterministic — no RNG, so the queue is reproducible.

    Repeated gaps at the head of the queue would be labelled first, fresh ones
    last, so any drift in how the labeller works over a session lands entirely
    on one of the two groups being compared.
    """
    if not a or not b:
        return list(a) + list(b)
    out, ai, step = [], 0, len(b) / len(a)
    for i, x in enumerate(b):
        while ai < len(a) and ai * step <= i:
            out.append(a[ai])
            ai += 1
        out.append(x)
    return out + list(a[ai:])


def round_robin(cands, n):
    """Take from each clip in turn so no clip dominates the queue."""
    by = {}
    for c in cands:
        by.setdefault(c[0], []).append(c)
    for v in by.values():                      # spread within a clip too
        step = max(1, len(v) // max(1, n))
        v[:] = v[::step]
    picked, i = [], 0
    keys = sorted(by)
    while len(picked) < n and any(by[k] for k in keys):
        k = keys[i % len(keys)]
        if by[k]:
            picked.append(by[k].pop(0))
        i += 1
    return picked


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=str(REPO / "data/ball_dataset"))
    ap.add_argument("--clips", default=str(REPO / "data/train_clips"),
                    help="where the SOURCE videos live. Labelling a 1.6 px ball on "
                         "the 512x288 network-input JPEG is not possible; these are "
                         "720p/1080p")
    ap.add_argument("--out", default=str(REPO / "data/labels"))
    ap.add_argument("--clip", default="farcourt_pilot",
                    help="name of the queue; becomes <clip>.manifest.json")
    ap.add_argument("--gaps", type=int, default=10,
                    help="number of GAPS, not frames. With --with-anchors each "
                         "gap contributes 3 frames")
    ap.add_argument("--with-anchors", dest="anchors", action="store_true", default=True)
    ap.add_argument("--no-anchors", dest="anchors", action="store_false")
    ap.add_argument("--max-gap", type=int, default=MAX_GAP)
    ap.add_argument("--force", action="store_true",
                    help="overwrite a queue that already has human labels against "
                         "it. Renumbers frames, so the labels stop meaning what "
                         "they meant — archive them first")
    ap.add_argument("--allow-native", action="store_true",
                    help="also queue directories with no source video, at 512x288. "
                         "OFF by default: mixing a 1.6 px ball in with 720p frames "
                         "makes 'could you see it?' unanswerable")
    ap.add_argument("--repeat-from", default="",
                    help="a previous *.manifest.json whose gaps this queue should "
                         "REPEAT first, before topping up with fresh ones. The "
                         "repeats are a controlled A/B; the fresh ones measure a "
                         "rate the labeller's memory of the first pass cannot "
                         "reach. --gaps counts BOTH")
    ap.add_argument("--exclude-from", nargs="*", default=[],
                    help="manifests whose gaps this queue must NOT contain. A gap "
                         "already labelled teaches nothing a second time, and it "
                         "carries the labeller's memory of the first pass, so it "
                         "cannot be part of a clean rate")
    ap.add_argument("--hud-masks", default=str(REPO / "data/hud_masks.json"),
                    help="burned-in graphics to paint out (tools/mask_hud.py). "
                         "Pass '' to label unmasked footage — the first pilot did "
                         "and put 5 of 36 clicks inside a scoreboard")
    args = ap.parse_args()

    out = Path(args.out)
    if "gold" in out.parts:
        raise SystemExit("refusing to write into the gold (TEST) pool")
    # Second, independent check that the mining root holds no gold clip.
    from train_ballnet import assert_no_gold_leak
    assert_no_gold_leak(args.data, exclude=())

    # Rebuilding a manifest in place RENUMBERS its frames, so any clicks already
    # made against it silently come to mean a different frame. This happened once
    # and cost three human labels; they were recoverable only because the old
    # frame list was still in the session. Never again without an explicit --force.
    existing = out / f"{args.clip}.labels.json"
    if existing.is_file() and not args.force:
        n = len(json.loads(existing.read_text(encoding="utf-8")).get("labels") or {})
        raise SystemExit(
            f"{existing} already holds {n} human label(s) keyed to the CURRENT frame "
            f"numbering of {args.clip}. Rebuilding renumbers them and the labels "
            f"would silently point at different frames.\n"
            f"  Use --clip <another name> for a new queue, or --force to overwrite "
            f"after archiving those labels yourself.")

    cands = candidates(Path(args.data), args.max_gap, Path(args.clips))
    print(f"{len(cands)} bracketed far-court gaps in {args.data}")
    if not args.allow_native:
        keep = {d for d in {c[0] for c in cands}
                if source_map(Path(d), Path(args.clips)) is not None}
        dropped = sorted({os.path.basename(c[0]) for c in cands if c[0] not in keep})
        cands = [c for c in cands if c[0] in keep]
        if dropped:
            print(f"  skipped (no source video, would be 512x288): {dropped} "
                  f"-> {len(cands)} gaps from {len(keep)} clips")
    repeat_keys = gaps_in_manifest(args.repeat_from) if args.repeat_from else set()
    seen = set().union(*(gaps_in_manifest(p) for p in args.exclude_from)) \
        if args.exclude_from else set()
    repeats, fresh, n_excluded = split_pools(cands, repeat_keys, seen)
    if n_excluded:
        print(f"  excluding {n_excluded} already-labelled gap(s) -> "
              f"{len(repeats) + len(fresh)} left")
    if repeat_keys:
        print(f"  repeating {len(repeats)} of {len(repeat_keys)} gap(s) from "
              f"{os.path.basename(args.repeat_from)}")
    topup = round_robin(fresh, max(0, args.gaps - len(repeats)))
    picked = _interleave(repeats, topup)
    if not picked:
        raise SystemExit("no candidates")

    import cv2
    import mask_hud

    masks = mask_hud.load_masks(args.hud_masks) if args.hud_masks else {}
    if args.hud_masks and not masks:
        print(f"  NOTE: no HUD masks at {args.hud_masks} — every burned-in "
              f"graphic will be shown to the labeller as if it were footage")

    frames_dir = out / "frames" / args.clip
    frames_dir.mkdir(parents=True, exist_ok=True)
    maps, caps = {}, {}
    rows, idx, native, behind_mask = [], 0, 0, 0
    # Every frame must land at the SAME size or the labeller's canvas resizes
    # between frames and the click scaling differs per frame. Take the largest
    # source we are queueing and letterbox nothing — just record per-frame size.
    for gap_id, (d, a, pa, m, pm, b, pb) in enumerate(picked):
        if d not in maps:
            maps[d] = source_map(Path(d), Path(args.clips))
        trio = [(a, pa, "anchor"), (m, pm, "farcourt_gap"), (b, pb, "anchor")]
        # Build the whole trio before writing anything: whether to queue a gap is
        # a decision about the GAP, and an anchor without its midpoint (or the
        # reverse) is not a usable unit of work.
        staged = []
        for src, (px, py), bucket in (trio if args.anchors else trio[1:2]):
            sm = maps[d]
            img, boxes = None, []
            if sm is not None:
                vid, ws, starts, step, (W, H) = sm
                sf = source_frame(src, ws, starts, step)
                cap = caps.get(vid) or cv2.VideoCapture(vid)
                caps[vid] = cap
                cap.set(cv2.CAP_PROP_POS_FRAMES, sf)
                ok, fr = cap.read()
                if ok:
                    img = fr
                    sx, sy = W / IN_W, H / IN_H       # 512x288 prior -> source px
                    px, py, srcinfo = px * sx, py * sy, {"video": os.path.basename(vid),
                                                         "video_frame": sf}
                    boxes = masks.get(os.path.basename(vid), [])
            if img is None:                            # no video recorded for this dir
                img = cv2.imread(str(Path(d) / f"{src:05d}.jpg"))
                srcinfo = {"video": None, "video_frame": None}
                native += 1
                if img is None:
                    continue
            staged.append((img, boxes, src, px, py, bucket, srcinfo))

        # The ball is behind the graphic in the source video too, so there is
        # nothing here for a human to find and the click would land on flat grey.
        if any(mask_hud.covers(bx, px, py) for _i, bx, _s, px, py, _b, _si in staged):
            behind_mask += 1
            continue

        for img, boxes, src, px, py, bucket, srcinfo in staged:
            cv2.imwrite(str(frames_dir / f"f{idx:05d}.jpg"), mask_hud.apply_mask(img, boxes),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            rows.append({"frame": idx, "bucket": bucket,
                         # which gap this frame belongs to. The anchors are the
                         # control for their own midpoint, so the converter has
                         # to be able to find them; grouping by "consecutive
                         # threes" breaks the moment a frame fails to decode.
                         "gap": gap_id,
                         # provenance so a click can be traced back — these are
                         # renumbered, not source indices
                         # whether this gap is a REPEAT of an earlier queue.
                         # Recorded, never shown: telling the labeller would put
                         # their memory of the first pass into the measurement.
                         "repeat": key_of((d, a, pa, m, pm, b, pb)) in repeat_keys,
                         "src_dataset": os.path.basename(d), "src_frame": src,
                         "width": img.shape[1], "height": img.shape[0], **srcinfo,
                         # what the tracker/interpolation thinks, in THIS frame's
                         # pixels. The UI never shows it, so it cannot bias a click.
                         "prior_x": round(px, 1), "prior_y": round(py, 1),
                         # what was painted out on THIS frame, so a click can be
                         # audited against the mask that was in force when made
                         "hud_boxes": boxes})
            idx += 1
    for c in caps.values():
        c.release()
    if behind_mask:
        print(f"  dropped {behind_mask} gap(s): a prior sits behind a burned-in "
              f"graphic, so there is no ball there to find")

    sizes = sorted({(r["width"], r["height"]) for r in rows})
    man = {"clip": args.clip, "video": None,
           "source": "source videos in data/train_clips at native resolution; "
                     f"{native} frames fell back to the 512x288 dataset JPEG "
                     "(no video recorded for that directory)",
           "frame_sizes": [f"{w}x{h}" for w, h in sizes],
           "width": sizes[-1][0], "height": sizes[-1][1],
           "fps": None, "video_frames": idx,
           "created": time.strftime("%Y-%m-%d %H:%M:%S"),
           "params": {"tool": "select_farcourt_labels.py",
                      "gaps": len(picked) - behind_mask,
                      "max_gap": args.max_gap, "far_frac": FAR_FRAC,
                      "with_anchors": args.anchors,
                      "selection": "midpoint of each bracketed far-court gap, "
                                   "round-robin over clips",
                      "hud_masks": args.hud_masks or None,
                      "gaps_dropped_behind_mask": behind_mask},
           # The mask is part of what the labeller saw, so it belongs in the
           # manifest and not only in a separate file that can drift from it.
           "hud_masks": {v: masks[v] for v in
                         sorted({r["video"] for r in rows if r.get("video")})
                         if masks.get(v)},
           "bucket_counts": {b: sum(1 for r in rows if r["bucket"] == b)
                             for b in {r["bucket"] for r in rows}},
           "frames": rows}
    (out / f"{args.clip}.manifest.json").write_text(json.dumps(man, indent=1),
                                                    encoding="utf-8")
    clips = sorted({r["src_dataset"] for r in rows})
    print(f"wrote {out}/{args.clip}.manifest.json — {len(picked)} gaps, "
          f"{idx} frames, {len(clips)} clips")
    print(f"  {man['bucket_counts']}")
    print()
    print("Label them:  py tools/lab_server.py   (Label tab, TRAINING POOL)")
    print("THE QUESTION THIS ANSWERS: can you see the ball on the "
          "'farcourt_gap' frames at all? The 'anchor' frames are the control — "
          "the tracker found a ball on those, so if they are easy and the gaps "
          "are not, this data is unlabelable and the fix is new footage.")


if __name__ == "__main__":
    main()
