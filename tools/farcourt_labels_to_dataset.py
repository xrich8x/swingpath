"""farcourt_labels_to_dataset.py — turn far-court queue clicks into training data.

WHY A SECOND CONVERTER
----------------------
`labels_to_dataset.py` takes ONE `--video` and reads label keys as frame indices
into it. The far-court queue is deliberately the opposite shape: frames
renumbered 0..N drawn from TWELVE different videos, with the origin recorded per
frame (`video`, `video_frame`, `src_dataset`, `src_frame`). This splits the
queue's labels back into one label file per source clip and calls the existing
converter once per clip, so the audited single-video path is untouched and its
gold-leak refusal runs per clip rather than being re-implemented here.

THE ANCHOR CONTROL, WHICH IS THE REASON THIS IS NOT A PLAIN FORMAT SHIM
-----------------------------------------------------------------------
A queued gap is the midpoint between two tracker detections. MEASURED on the
first pilot (data/output/farcourt_anchor_audit.md): on 7 of 12 gaps BOTH of
those detections were false locks — on a wall, a hedge, a spectator, a parked
car — so there was no ball anywhere near the interpolated point, and the
labeller, finding nothing, clicked something: empty sky, flat court, foliage, a
scoreboard. Those are not noisy labels, they are a Gaussian on empty background,
which is the exact failure the far-court plan exists to avoid.

The queue already carries the control that detects this — it queues both anchors
precisely so a human verdict on them can be compared with the tracker — and
nothing had ever read it. So: a midpoint is accepted only when the human's click
on at least ONE of its anchors lands within `--anchor-px` of what the tracker
claimed there. On the pilot that rule keeps 5 of 5 usable midpoints and drops 7
of 7 unusable ones. n=12 gaps: a clean split, on a small sample. `--no-anchor-
control` turns it off and prints what it would have dropped.

Two kinematic alternatives were tried first and both FAILED (same file): local
roam does not separate confirmed anchors from false ones (14-220 px vs 13-239 px,
fully overlapping), and `ball.suppress_false_locks` drops 4 of the 5 confirmed
gaps. There is no model-side substitute for the human's verdict here.

    py tools/farcourt_labels_to_dataset.py --clip farcourt_pilot2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import labels_to_dataset as l2d        # noqa: E402  (path set above)

ANCHOR_PX = 15.0        # at 720p; scaled by frame height, like the rest of the stack
#: Minimum distance a human click may move across a gap, at 720p. Below this the
#: labeller was looking at something that does not move, which a ball in play
#: never is. Pre-registered in Session J from 12 gaps, then CONFIRMED on 49
#: independent ones (farcourt_cal1) where the distribution is bimodal with a
#: valley at 9-16 px and 17 clicks at EXACTLY zero. See data/output/farcourt_l2.md.
MIN_MOTION_PX = 9.0


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def click_motion(rs, labels):
    """(human click path length, tracker anchor-to-anchor displacement) in px.

    ENFORCED as of 2026-08-13; it was reported-only until then, and the reason
    for the change is that the threshold stopped being fitted to its own evidence.

    The anchor control asks whether the human AGREES with the tracker, and the
    masked re-run showed that is not the same as being right: on 2 of 12 repeat
    gaps the human clicked a static wall mark or a window, one of them the very
    mark the tracker had locked onto, agreeing to 2-5 px. A labeller who cannot
    find the ball clicks the most ball-like thing in the frame, which is what the
    detector locked onto for the same reasons.

    A ball in play is somewhere different on every frame, so these two numbers
    separate the cases: on that session the bad gaps had the human moving 1-8 px
    while the tracker's own prior moved 60-583 px. It is not a filter because the
    apparent threshold was found AFTER looking at those twelve gaps, and a cutoff
    fitted to twelve observations is a memory of them rather than a control. The
    labelling page carries the rule too — and MEASURED, the rule did NOT work:
    farcourt_cal1 was labelled 30 minutes after it shipped and is WORSE than the
    round before it (47% vs 60% ball-like motion). So the control has to be
    mechanical. Confirmed on those 49 independent gaps: bimodal, valley at
    9-16 px, 17 clicks at exactly zero. data/output/farcourt_l2.md.
    """
    pts = []
    for r in sorted(rs, key=lambda r: r["frame"]):
        v = labels.get(str(r["frame"])) or {}
        if v.get("x") is not None and not v.get("unsure"):
            pts.append((v["x"], v["y"]))
    human = sum(_dist(a, b) for a, b in zip(pts, pts[1:]))
    anchors = sorted((r for r in rs if r["bucket"] == "anchor"),
                     key=lambda r: r["frame"])
    tracker = _dist((anchors[0]["prior_x"], anchors[0]["prior_y"]),
                    (anchors[-1]["prior_x"], anchors[-1]["prior_y"])) \
        if len(anchors) >= 2 else None
    return (round(human, 1), None if tracker is None else round(tracker, 1))


def gap_ids(rows):
    """Which gap each queued frame belongs to.

    New manifests record it. The first pilot's does not, and it must still be
    adjudicable, because it is the evidence that the control is needed at all —
    so fall back to the writer's fixed per-gap order of anchor, midpoint,
    anchor. Falling back to "one gap per frame" instead would silently accept
    every midpoint, which is the failure this whole file exists to prevent.
    """
    if any("gap" in r for r in rows):
        return [r["gap"] for r in rows]
    out, gid, after_mid = [], 0, False
    for r in rows:
        is_mid = r["bucket"] != "anchor"
        if is_mid and after_mid:          # --no-anchors queue: one gap per frame
            gid, after_mid = gid + 1, False
        out.append(gid)
        if is_mid:
            after_mid = True
        elif after_mid:                   # the anchor that closes a gap
            gid, after_mid = gid + 1, False
    return out


def adjudicate(manifest: dict, labels: dict, *, anchor_px: float = ANCHOR_PX,
               enforce: bool = True, min_motion_px: float = MIN_MOTION_PX):
    """(accepted rows, per-gap verdicts). Pure — the tests drive it directly."""
    frames = manifest["frames"]
    gaps: dict = {}
    for gid, r in zip(gap_ids(frames), frames):
        gaps.setdefault(gid, []).append(r)

    verdicts, accepted = [], []
    for gid, rs in sorted(gaps.items()):
        anchors = [r for r in rs if r["bucket"] == "anchor"]
        mids = [r for r in rs if r["bucket"] != "anchor"]
        confirmed, checked = [], 0
        for a in anchors:
            v = labels.get(str(a["frame"])) or {}
            if v.get("unsure") or v.get("x") is None:
                continue
            checked += 1
            # Scale the tolerance the way every other pixel threshold in this
            # stack does: the same physical miss covers 1.5x the pixels at 1080p.
            tol = anchor_px * (a.get("height", 720) / 720.0)
            if _dist((v["x"], v["y"]), (a["prior_x"], a["prior_y"])) <= tol:
                confirmed.append(a["frame"])
        moved, tmoved = click_motion(rs, labels)
        # THE MOTION TEST, now ENFORCED (2026-08-13). Session J found the
        # separation post-hoc on 12 gaps and deliberately left it reported-only,
        # because a threshold fitted to the gaps that suggested it is not a
        # threshold. It has now reproduced on an INDEPENDENT round: farcourt_cal1,
        # 49 gaps labelled 30 minutes after the "a ball is somewhere different on
        # every frame" rule shipped. The distribution is cleanly bimodal —
        # 20 gaps at <=8 px (SEVENTEEN of them at exactly 0, the identical pixel
        # clicked twice), 23 at >=17 px, and only 6 in the 9-16 px valley between.
        # A ball in play cannot be in the same place two frames apart, so a
        # zero-motion click is a static object by definition, not a noisy label.
        moved_ok = (moved is None) or (moved >= min_motion_px *
                                       (rs[0].get("height", 720) / 720.0))
        ok = (bool(confirmed) or not anchors) and moved_ok
        verdicts.append({"gap": gid, "clip": rs[0]["src_dataset"],
                         "anchors_clicked": checked, "anchors_confirmed": confirmed,
                         "accepted": ok or not enforce,
                         # a repeat of an earlier queue carries the labeller's
                         # memory of that pass, so it cannot be pooled with the
                         # fresh gaps when estimating a confirmation RATE
                         "repeat": bool(rs[0].get("repeat")),
                         "click_motion_px": moved, "tracker_motion_px": tmoved,
                         "midpoints": [m["frame"] for m in mids]})
        if ok or not enforce:
            accepted += rs
    return accepted, verdicts


def split_by_clip(rows, labels):
    """{video filename -> {video_frame -> human verdict}} in source-video pixels.

    The queue frame IS the source frame (extracted at native resolution, never
    resized), so the click needs no rescaling — only its key does, from the
    queue's renumbering back to the source index.
    """
    out: dict = {}
    for r in rows:
        v = labels.get(str(r["frame"]))
        if not v or not r.get("video") or r.get("video_frame") is None:
            continue
        out.setdefault(r["video"], {})[str(r["video_frame"])] = v
    return out


def verify_round_trip(out_root: Path, clip: str, video: Path, per_frame: dict,
                      window: int = 3, min_margin: float = 0.02):
    """THE GATE: every produced sample must be the frame the human actually saw.

    A silent off-by-one here poisons training invisibly — the label says "ball at
    (x, y)" about a frame from a different moment — and nothing downstream would
    ever show it. So it is checked from the pixels, not from the arithmetic that
    produced them.

    NOT dHash, which is what this reached for first and what Session I used to
    verify the window mapping. That was a different question: a wrong window is
    ~1600 frames and a different scene away, so a 64-bit perceptual hash resolves
    it easily. The risk HERE is off by ONE, and on a 60 fps clip of a mostly
    static court, frames f-3..f+3 all hash within 2 bits of each other while JPEG
    and the 1080p -> 512x288 resize contribute 6-8 bits of their own. MEASURED on
    col_hard_zheng: raw dHash reads 14 bits at EVERY candidate frame. The test
    would have failed identically whether the mapping was right or wrong, which
    makes it worse than no test.

    What does resolve it is a straight mean absolute difference, taken as an
    ARGMIN over the neighbourhood rather than against a threshold: the sample
    must be closer to the frame it claims than to any frame beside it. The
    margin is reported, not just the verdict, because on a frozen scene the
    argmin is noise and a caller is entitled to see that it was.
    """
    import cv2
    import numpy as np

    meta = json.loads((out_root / clip / "labels.json").read_text(encoding="utf-8"))
    wanted = sorted({int(k) for k in per_frame})
    cap = cv2.VideoCapture(str(video))
    bad, flat, checked, margins = [], [], 0, []
    # build() writes each labelled source frame f as a triplet at 3k, 3k+1, 3k+2
    # and attaches the label to 3k+2, so index 3k+2 <-> wanted[k].
    for k, f in enumerate(wanted):
        p = out_root / clip / f"{3 * k + 2:05d}.jpg"
        if not p.is_file():
            continue                       # dropped at the clip end by build()
        got = cv2.imread(str(p)).astype(np.float32)
        d = {}
        for g in range(max(0, f - window), f + window + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, g)
            ok, src = cap.read()
            if ok:
                d[g] = float(np.abs(got - cv2.resize(
                    src, (got.shape[1], got.shape[0])).astype(np.float32)).mean())
        if not d:
            continue
        checked += 1
        best = min(d, key=d.get)
        others = [v for g, v in d.items() if g != f]
        margin = (min(others) - d[f]) / max(d[f], 1e-6) if others else 0.0
        margins.append(round(margin, 4))
        # A "miss" only means something if the winner is meaningfully better than
        # the claimed frame. On a static court neighbouring frames tie — measured
        # on TilAFMPc0yg:2787, frames 2786 and 2787 both score 2.575, so argmin
        # picks whichever it saw first and the verdict is decided by dict order,
        # not by pixels. That is the same "the argmin is noise" case this function
        # already reports as unresolved; it simply was not reached when the tie
        # happened to fall the wrong way. Judged on the SAME min_margin, so there
        # is one notion of "too close to call" rather than two.
        # Contrast RZ_wyJ9rI3Q:1231, which reads 3.01 -> 2.187 monotonically across
        # the window: the true frame is probably outside it. That stays a hard stop.
        lead = (d[f] - d[best]) / max(d[f], 1e-6)      # how much better `best` is
        if best != f and lead >= min_margin:
            bad.append({"source_frame": f, "sample": p.name, "closest_to": best,
                        "lead_over_claimed": round(lead, 4),
                        "mean_abs": {g: round(v, 3) for g, v in d.items()}})
        elif best != f or margin < min_margin:
            # Nothing moved in +/-3 frames, so "closest" carries no information.
            flat.append({"source_frame": f, "margin": round(margin, 4),
                         "tied_with": None if best == f else best})
    cap.release()
    return {"checked": checked, "mismatches": bad, "unresolved_static": flat,
            "median_margin": round(float(np.median(margins)), 4) if margins else None,
            "n_frames_written": meta.get("n_frames")}


def contact_sheet(manifest: dict, labels: dict, frames_dir: Path, out: Path,
                  radius: int = 44, zoom: int = 5) -> None:
    """One tile per queued frame, centred on where the human clicked.

    "The labeller clicked empty sky" is a claim about pixels, and the only
    honest way to make it is to look. A summary statistic — distance from the
    tracker's prior — cannot tell a human who found a real ball the tracker
    missed (yt_rz4T0-VALNw, 39-47 px out and RIGHT) from one who found nothing
    and clicked anyway.
    """
    import cv2
    import numpy as np

    tiles = []
    for r in sorted(manifest["frames"], key=lambda r: r["frame"]):
        k = r["frame"]
        v = labels.get(str(k)) or {}
        t = np.full((2 * radius * zoom, 2 * radius * zoom, 3), 25, np.uint8)
        im = cv2.imread(str(frames_dir / f"f{k:05d}.jpg"))
        if im is not None and v.get("x") is not None:
            x, y = int(v["x"]), int(v["y"])
            x0 = max(0, min(x - radius, im.shape[1] - 2 * radius))
            y0 = max(0, min(y - radius, im.shape[0] - 2 * radius))
            t = cv2.resize(im[y0:y0 + 2 * radius, x0:x0 + 2 * radius],
                           (2 * radius * zoom,) * 2, interpolation=cv2.INTER_NEAREST)
            cv2.drawMarker(t, ((x - x0) * zoom, (y - y0) * zoom), (0, 0, 255),
                           cv2.MARKER_CROSS, 52, 2)
        else:
            cv2.putText(t, "no ball" if v.get("ball") is False else
                        ("unsure" if v.get("unsure") else "unlabelled"),
                        (20, radius * zoom), 0, 0.9, (200, 200, 200), 2)
        cv2.putText(t, f"{k} {r['bucket'][:6]}", (5, 22), 0, 0.62, (0, 255, 255), 2)
        cv2.putText(t, r["src_dataset"][3:], (5, 2 * radius * zoom - 10), 0, 0.55,
                    (0, 255, 255), 2)
        tiles.append(t)
    per = 6
    while len(tiles) % per:
        tiles.append(np.zeros_like(tiles[0]))
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), np.vstack([np.hstack(tiles[i:i + per])
                                     for i in range(0, len(tiles), per)]),
                [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"wrote {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", default="farcourt_pilot",
                    help="queue name: reads data/labels/<clip>.{manifest,labels}.json")
    ap.add_argument("--labels-dir", default=str(REPO / "data/labels"))
    ap.add_argument("--out", default=str(REPO / "data/ball_dataset"))
    ap.add_argument("--prefix", default="",
                    help="dataset dir name per clip; defaults to <queue>_<video stem>")
    ap.add_argument("--anchor-px", type=float, default=ANCHOR_PX)
    ap.add_argument("--min-motion-px", type=float, default=MIN_MOTION_PX,
                    help="minimum human click travel across a gap, at 720p; "
                         "0 disables the test (it was reported-only before "
                         "2026-08-13)")
    ap.add_argument("--no-anchor-control", dest="anchor_control",
                    action="store_false", default=True)
    ap.add_argument("--no-verify", dest="verify", action="store_false", default=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="adjudicate and report; write nothing")
    ap.add_argument("--force", action="store_true",
                    help="build even from a manifest marked contaminated")
    ap.add_argument("--contact-sheet", default="",
                    help="every click at 5x, one tile per queued frame. This is "
                         "how the pilot's clicks were classified by eye; the "
                         "verdicts live in data/output/*_click_classes.json and "
                         "the sheet is regenerable, not committed")
    args = ap.parse_args()

    ld = Path(args.labels_dir)
    man_p, lab_p = ld / f"{args.clip}.manifest.json", ld / f"{args.clip}.labels.json"
    for p in (man_p, lab_p):
        if not p.is_file():
            raise SystemExit(f"no such file: {p}")
    manifest = json.loads(man_p.read_text(encoding="utf-8"))
    labels = json.loads(lab_p.read_text(encoding="utf-8")).get("labels") or {}

    if args.contact_sheet:
        contact_sheet(manifest, labels, ld / "frames" / args.clip,
                      Path(args.contact_sheet))

    l2d.refuse_if_contaminated(man_p, force=args.force)

    accepted, verdicts = adjudicate(manifest, labels, anchor_px=args.anchor_px,
                                    enforce=args.anchor_control,
                                    min_motion_px=args.min_motion_px)
    n_acc = sum(1 for v in verdicts if v["accepted"])
    print(f"{len(verdicts)} gap(s): {n_acc} accepted, {len(verdicts) - n_acc} "
          f"rejected by the anchor control"
          f"{'' if args.anchor_control else ' (control OFF, nothing dropped)'}")
    for v in verdicts:
        mark = "keep" if v["accepted"] else "DROP"
        tm = "" if v["tracker_motion_px"] is None else f"{v['tracker_motion_px']:>6.0f}"
        print(f"  {mark}  gap {v['gap']:>3} {v['clip']:<20} "
              f"{'repeat' if v['repeat'] else 'fresh ':<7} "
              f"anchors clicked {v['anchors_clicked']}, "
              f"confirmed {len(v['anchors_confirmed'])}   "
              f"moved: you {v['click_motion_px']:>6.0f} px / tracker {tm} px")
    # Sizing the next queue needs the rate on gaps the labeller had NOT already
    # seen; pooling the two would put their memory of the first pass into it.
    for tag, want in (("fresh", False), ("repeat", True)):
        sub = [v for v in verdicts if v["repeat"] is want]
        if sub:
            k = sum(1 for v in sub if v["anchors_confirmed"])
            print(f"  anchor-confirmation rate, {tag:<6} {k}/{len(sub)} "
                  f"= {100 * k / len(sub):.0f}%")

    by_clip = split_by_clip(accepted, labels)
    if not by_clip:
        raise SystemExit("nothing to build: no accepted frame carries a source video")

    gold = l2d.gold_videos()
    results = []
    for video_name, per_frame in sorted(by_clip.items()):
        if video_name.lower() in gold:
            raise SystemExit(f"REFUSING: {video_name} backs a gold clip")
        video = REPO / "data/train_clips" / video_name
        if not video.is_file():
            raise SystemExit(f"no such video: {video}")
        name = (args.prefix or f"{args.clip}_") + Path(video_name).stem
        n_pos = sum(1 for v in per_frame.values()
                    if v.get("ball") and not v.get("unsure"))
        n_neg = sum(1 for v in per_frame.values() if v.get("ball") is False)
        print(f"  {name:<34} {len(per_frame):>3} labelled frame(s)  "
              f"{n_pos} ball / {n_neg} no-ball")
        if args.dry_run:
            continue
        # Hand the existing converter exactly the file shape it already reads.
        tmp = ld / f".{name}.split.labels.json"
        tmp.write_text(json.dumps({"clip": name, "tool": "farcourt_labels_to_dataset.py",
                                   "source_queue": args.clip, "labels": per_frame}),
                       encoding="utf-8")
        try:
            res = l2d.build(name, video, tmp, Path(args.out))
        finally:
            tmp.unlink(missing_ok=True)
        if args.verify:
            rt = res["round_trip"] = verify_round_trip(Path(args.out), name,
                                                       video, per_frame)
            if rt["mismatches"]:
                # The gate runs AFTER build(), so a failure leaves an unverified
                # directory sitting in the training pool — the exact hazard this
                # check exists to prevent, arriving by a different door. A hard
                # stop that leaves the bad data behind is not a hard stop.
                import shutil
                shutil.rmtree(Path(args.out) / name, ignore_errors=True)
                raise SystemExit(
                    f"ROUND-TRIP FAILED for {name}: "
                    f"{rt['mismatches']}\nThe built samples are not "
                    f"the frames the human labelled. Nothing downstream would ever "
                    f"show this, so it is a hard stop.\n"
                    f"Removed {Path(args.out) / name} — an unverified dataset "
                    f"directory must not be left where the trainer will find it.")
            print(f"    round-trip: {rt['checked']} sample(s) closest to their own "
                  f"source frame, median margin {rt['median_margin']}"
                  + (f"; {len(rt['unresolved_static'])} too static to resolve"
                     if rt["unresolved_static"] else ""))
        results.append(res)

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return
    report = {"tool": "farcourt_labels_to_dataset.py", "queue": args.clip,
              "created": time.strftime("%Y-%m-%d %H:%M:%S"),
              "anchor_control": args.anchor_control, "anchor_px": args.anchor_px,
              "gaps": verdicts, "datasets": results}
    rp = REPO / "data/output" / f"farcourt_convert_{args.clip}.json"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=1), encoding="utf-8")
    tot = sum(r["positives"] for r in results)
    print(f"\n{tot} human ball label(s) across {len(results)} dataset dir(s); "
          f"round-trip verified on "
          f"{sum(r.get('round_trip', {}).get('checked', 0) for r in results)} sample(s)")
    print(f"report: {rp}")


if __name__ == "__main__":
    main()
