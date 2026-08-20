"""eval/run_eval.py - the court-detection feedback loop.

Runs the SHIPPED court path on every eval frame, prints one table, and writes a
diagnostic overlay per frame to eval/out/ so a failure can be SEEN and not just
counted.

Two frame sources, and they measure different things:

  gold  data/gold/<clip>.court.labels.json + the cached frames under
        data/gold/frames/<clip>/. 20 clips, ~315 human-clicked frames. This is
        the ONLY source with ground truth, so it is the only one that can report
        corner error or IoU. Numbers from here are measured against human clicks.
  drop  eval/frames/. Loose images, or one subdirectory per clip. NO ground
        truth, so the only honest columns are lock/refuse and the overlay. Use
        it to see behaviour on new surfaces (clay, shell, multi-sport overlay
        lines); do NOT quote a corner number from it, because there isn't one.

The path under test is the product path, not the raw detector:
`courtfit.auto_fit_frame` per frame -> `courtfit.consensus` across frames ->
`stacked_clay_fit` rescue, which is exactly what `pipeline.calibrate_video`
Tier 1 runs. ACCEPTED means what the pipeline means by it: a vote consensus with
>= 6 of 8 agreeing frames. A stacked-clay rescue produces a court but is NOT
auto-accepted, and is reported as `stk` so the distinction stays visible.

    backend/.venv/Scripts/python.exe eval/run_eval.py --gold --all
    backend/.venv/Scripts/python.exe eval/run_eval.py --drop
    backend/.venv/Scripts/python.exe eval/run_eval.py --gold am_wingfield_clay --k 8

Runtime is ~1.6 s/frame at 640x360, so the full 20-clip gold sweep is ~4 min.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))

from swingvision.courtfit import DBL   # the four doubles corners, in canonical order

GOLD = REPO / "data" / "gold"
DROP = REPO / "eval" / "frames"
OUT = REPO / "eval" / "out"

# A consensus court counts as WRONG above this. Not a taste call: on the gold set
# every court the pipeline accepts lands 3.4-13.9 px from the human clicks and every
# one it refuses lands 25.5-111.0 px away, with nothing in between
# (data/output/court_consensus_bar.md). 20 px sits in that empty gap. The precision
# record every later stage must not spend is "zero accepted courts above this line".
WRONG_PX = 20.0

# The pipeline auto-accepts a court at >= 6 agreeing frames out of 8 sampled
# (pipeline.calibrate_video Tier 1). Both numbers are load-bearing and were
# measured together at k=8 - the one 5-vote clip on the gold set is wrong by
# 68.7 px while every >=6-vote clip lands 3.4-13.9 px. The bar is NOT rescaled
# for a different k, because "6 of 8" is what the evidence covers and a fraction
# of some other k is a rule nobody measured.
ACCEPT_VOTES, ACCEPT_K = 6, 8


def _fmt(v, spec="6.1f"):
    return "-".rjust(int(spec.split(".")[0])) if v is None else format(v, spec)


# --- frame sources ----------------------------------------------------------

def gold_clips() -> list[str]:
    return sorted(p.name.replace(".court.labels.json", "")
                  for p in GOLD.glob("*.court.labels.json"))


def load_gold(clip: str, k: int):
    """(frames, gt) for a gold clip. frames = [(key, image)], gt = {key: keypoints}.

    Only frames the human marked `court: true` with all four doubles corners are
    usable; the rest are either unlabelled or a deliberate no-court frame."""
    import cv2

    lab_path = GOLD / f"{clip}.court.labels.json"
    if not lab_path.exists():
        return [], {}
    labs = json.loads(lab_path.read_text(encoding="utf-8"))["labels"]
    usable = {kk: v for kk, v in labs.items()
              if v.get("court") is True
              and all(n in v.get("keypoints", {}) for n in DBL)}
    if not usable:
        return [], {}
    keys = sorted(usable, key=lambda x: int(x))
    pick = keys[:: max(1, len(keys) // k)][:k]
    frames = []
    for kk in pick:
        im = cv2.imread(str(GOLD / "frames" / clip / f"f{int(kk):05d}.jpg"))
        if im is not None:
            frames.append((f"{int(kk):05d}", im))
    return frames, {f"{int(kk):05d}": usable[kk]["keypoints"] for kk in pick}


def drop_clips() -> list[tuple[str, list[Path]]]:
    """eval/frames/ -> [(clip, [paths])]. A subdirectory is one clip (so its frames
    can vote); loose files at the top level are graded one frame at a time under
    the clip name "_loose"."""
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if not DROP.exists():
        return []
    out = []
    loose = sorted(p for p in DROP.iterdir() if p.is_file() and p.suffix.lower() in exts)
    if loose:
        out.append(("_loose", loose))
    for d in sorted(p for p in DROP.iterdir() if p.is_dir()):
        fs = sorted(p for p in d.iterdir() if p.suffix.lower() in exts)
        if fs:
            out.append((d.name, fs))
    return out


def load_drop(paths: list[Path], k: int):
    import cv2

    frames = []
    for p in paths[:k]:
        im = cv2.imread(str(p))
        if im is not None:
            frames.append((p.stem, im))
    return frames, {}


# --- overlay ----------------------------------------------------------------

def _clip_infinite_line(n, rho, w, h):
    """A merged line from courtfit._detect_lines is (theta_normal, rho) - an
    INFINITE line, which is the point of the merge. Clip it to the frame to draw."""
    import cv2

    p0 = np.array([rho * np.cos(n), rho * np.sin(n)])
    d = np.array([-np.sin(n), np.cos(n)])
    a, b = p0 - 1e5 * d, p0 + 1e5 * d
    ok, q1, q2 = cv2.clipLine((0, 0, w, h),
                              (int(a[0]), int(a[1])), (int(b[0]), int(b[1])))
    return (q1, q2) if ok else None


def _mask_panel(frame, mask_fn, calibration, label):
    """Mask as grey, with the distinct merged lines the fit reasons over in red."""
    import cv2
    from swingvision import courtfit as cf

    mask = mask_fn(frame)
    h, w = mask.shape[:2]
    panel = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    panel[mask > 0] = (170, 170, 170)
    lines = cf._detect_lines(mask, w)
    for n, rho, _wt in lines:
        seg = _clip_infinite_line(n, rho, w, h)
        if seg:
            cv2.line(panel, seg[0], seg[1], (60, 60, 235), 1, cv2.LINE_AA)
    cv2.putText(panel, f"{label}  px={int((mask > 0).sum())}  lines={len(lines)}",
                (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    return panel


def write_overlay(path: Path, frame, calibration, court, H=None, gt=None, note=""):
    """frame + fitted model (green) + human GT (blue) | white mask | clay mask.

    Three panels because the Stage 2 question is "which channel carries the
    signal on this surface" - a clip that refuses with an empty white mask and a
    populated clay mask is a different bug from one where both are populated."""
    import cv2
    from swingvision import courtfit as cf

    left = frame.copy()
    if gt:
        # the human labelled points, not lines - so GT draws as the corner quad
        quad = np.array([gt[n] for n in DBL if n in gt], np.int32)
        if len(quad) == 4:
            cv2.polylines(left, [quad.reshape(-1, 1, 2)], True, (235, 170, 60), 2, cv2.LINE_AA)
    if H is not None:
        for a, b in court.LINES:
            pa = calibration.court_to_image(H, [a])[0]
            pb = calibration.court_to_image(H, [b])[0]
            if np.all(np.isfinite([pa, pb])) and np.max(np.abs([pa, pb])) < 1e5:
                cv2.line(left, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])),
                         (90, 235, 120), 2, cv2.LINE_AA)
    cv2.putText(left, note, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (255, 255, 255), 1, cv2.LINE_AA)

    panels = [left,
              _mask_panel(frame, calibration.line_ridge_mask, calibration, "white ridge"),
              _mask_panel(frame, lambda f: cf._clay_mask(f, calibration), calibration, "clay/shell")]
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.hstack(panels))


# --- scoring ----------------------------------------------------------------

def score_clip(clip, frames, gt, overlays=True, out_root=OUT):
    """Run the product path on one clip's frames. Returns (rows, summary)."""
    from swingvision import calibration, court, courtfit

    rows, fits = [], []
    for key, im in frames:
        t0 = time.time()
        corners, sc = courtfit.auto_fit_frame(im, calibration, court, with_score=True)
        dt = time.time() - t0
        fits.append(corners)
        err = None
        H = None
        if corners is not None:
            H = calibration.compute_homography([court.LANDMARKS[n] for n in DBL],
                                               [corners[n] for n in DBL])
            if key in gt:
                err = float(np.mean([
                    np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                               - np.asarray(gt[key][n]))) for n in DBL]))
        rows.append({"clip": clip, "frame": key, "fit": corners is not None,
                     "score": sc, "err": err, "secs": dt})
        if overlays:
            note = (f"{clip} f{key}  " +
                    ("REFUSED" if corners is None
                     else f"fit score={sc:.3f}" + (f"  err={err:.1f}px" if err is not None else "")))
            write_overlay(out_root / clip / f"f{key}.png", im, calibration, court,
                          H=H, gt=gt.get(key), note=note)

    pts, votes = courtfit.consensus(fits)
    tag = "vote" if pts is not None else None
    if pts is None and len(frames) >= 6:
        pts = courtfit.stacked_clay_fit(frames, calibration, court)
        tag = "stack" if pts is not None else None

    # The pipeline's own accept rule (pipeline.calibrate_video Tier 1), reproduced
    # rather than re-invented: vote consensus only, >= 6 agreeing frames.
    accepted = pts is not None and tag == "vote" and votes >= ACCEPT_VOTES
    cerr = None
    if pts is not None and gt:
        H = calibration.compute_homography([court.LANDMARKS[n] for n in DBL],
                                           [pts[n] for n in DBL])
        cerr = float(np.median([
            float(np.mean([np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                                      - np.asarray(g[n]))) for n in DBL]))
            for g in gt.values()]))
    return rows, {"clip": clip, "frames": len(frames),
                  "locked": sum(1 for f in fits if f), "votes": votes,
                  "tag": tag, "accepted": accepted, "err": cerr}


# --- report -----------------------------------------------------------------

def report(rows, summaries, source):
    print(f"\n=== PER FRAME ({source}) ===")
    print(f"{'clip':24s} {'frame':>7s} {'fit':>5s} {'score':>7s} {'corner_px':>10s} {'secs':>6s}")
    print("-" * 64)
    for r in rows:
        print(f"{r['clip']:24s} {r['frame']:>7s} {'ok' if r['fit'] else 'NO':>5s} "
              f"{_fmt(r['score'], '7.3f')} {_fmt(r['err'], '10.1f')} {r['secs']:6.2f}")

    print(f"\n=== PER CLIP ({source}) ===")
    print(f"{'clip':24s} {'frames':>6s} {'locked':>6s} {'votes':>6s} {'result':>9s} "
          f"{'consensus_px':>12s}")
    print("-" * 70)
    n_acc = n_wrong = 0
    errs = []
    for s in summaries:
        if s["accepted"]:
            n_acc += 1
            if s["err"] is not None:
                errs.append(s["err"])
                if s["err"] > WRONG_PX:
                    n_wrong += 1
        res = ("ACCEPTED" if s["accepted"]
               else "stk" if s["tag"] == "stack"
               else f"vote<{ACCEPT_VOTES}" if s["tag"] == "vote"
               else "refused")
        flag = "  <- WRONG" if (s["accepted"] and s["err"] is not None
                                and s["err"] > WRONG_PX) else ""
        print(f"{s['clip']:24s} {s['frames']:6d} {s['locked']:6d} {s['votes']:6d} "
              f"{res:>9s} {_fmt(s['err'], '12.1f')}{flag}")

    print("-" * 70)
    n = len(summaries)
    line = f"ACCEPTED {n_acc}/{n} clips"
    if errs:
        line += f"   median consensus err {np.median(errs):.1f} px (range {min(errs):.1f}-{max(errs):.1f})"
    line += f"   WRONG (>{WRONG_PX:.0f}px) {n_wrong}"
    print(line)
    if summaries and summaries[0]["frames"] != ACCEPT_K:
        print(f"NOTE: k={summaries[0]['frames']}, not {ACCEPT_K}. The >={ACCEPT_VOTES}-vote "
              f"accept bar was measured at k={ACCEPT_K}; the ACCEPTED column is not the "
              f"pipeline's rule at this k. Use --k {ACCEPT_K} for a comparable number.")
    if not errs and source == "drop":
        print("no ground truth in eval/frames/ - lock/refuse and the overlays are the "
              "only honest signal here; corner error is genuinely unavailable.")
    return {"accepted": n_acc, "clips": n, "wrong": n_wrong,
            "median_err": float(np.median(errs)) if errs else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="*", help="clip names to run (default: all in the source)")
    ap.add_argument("--gold", action="store_true", help="run the hand-labelled gold clips")
    ap.add_argument("--drop", action="store_true", help="run eval/frames/")
    ap.add_argument("--all", action="store_true", help="with --gold: every gold clip")
    ap.add_argument("--k", type=int, default=8, help="frames per clip (default 8, the pipeline's own sample)")
    ap.add_argument("--no-overlays", action="store_true", help="skip writing eval/out/")
    ap.add_argument("--out", default=None, help="overlay root (default eval/out)")
    ap.add_argument("--json", default=None, help="also write the summary as JSON here")
    a = ap.parse_args()
    if not (a.gold or a.drop):
        a.gold = True

    out_root = Path(a.out) if a.out else OUT
    overlays = not a.no_overlays
    result = {}

    if a.gold:
        names = a.clips or gold_clips()
        rows, sums = [], []
        for c in names:
            frames, gt = load_gold(c, a.k)
            if not frames:
                print(f"[skip] {c}: no usable labelled frames cached")
                continue
            r, s = score_clip(c, frames, gt, overlays, out_root)
            rows += r
            sums.append(s)
            print(f"[done] {s['clip']:24s} {s['locked']}/{s['frames']} locked, "
                  f"{s['votes']} votes, {'ACCEPTED' if s['accepted'] else (s['tag'] or 'refused')}")
        result["gold"] = report(rows, sums, "gold")

    if a.drop:
        groups = drop_clips()
        if not groups:
            print(f"\nnothing in {DROP} - drop frames there (loose files, or one "
                  f"subdirectory per clip so its frames can vote).")
        else:
            rows, sums = [], []
            for c, paths in groups:
                frames, gt = load_drop(paths, a.k)
                if not frames:
                    continue
                r, s = score_clip(c, frames, gt, overlays, out_root)
                rows += r
                sums.append(s)
            result["drop"] = report(rows, sums, "drop")

    if overlays:
        print(f"\noverlays -> {out_root}")
    if a.json:
        Path(a.json).write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
