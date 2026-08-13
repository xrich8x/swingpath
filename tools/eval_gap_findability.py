"""eval_gap_findability.py — can anything predict, BEFORE a human clicks, whether a
far-court gap contains a findable ball?

WHY
---
The far-court label queue offers the human a gap and asks them to find the ball in
it. Measured on the two labelled rounds, **41% of gaps contain nothing findable** —
the human clicks a wall mark or the identical pixel twice — and Session J's fix of
telling them so on the labelling page did NOT work (the round labelled 30 minutes
after that shipped is worse than the one before). So the control has to be
mechanical, and it has to run at SELECTION time, before the effort is spent.

That cannot be the anchor control: that compares the HUMAN's click on an anchor
against the tracker, so it needs a human by construction. It has to be something
computable from the queue itself.

WHAT IS ACTUALLY AVAILABLE, and one candidate is dead on arrival
----------------------------------------------------------------
The manifest carries, per queued frame: the tracker's prior, the source frame, the
clip and the resolution. From that: anchor displacement, gap duration, implied
speed, and where in the frame the gap sits.

NOT the midpoint's own prior. It looks like independent evidence and is not:
measured on all 49 cal1 gaps, it reproduces pure linear interpolation between the
anchors to **0 of 49** deviating by more than 0.5 px. Any "is the midpoint
consistent with the anchors" feature is identically zero. Ruled out before it cost
anything.

Local roam IS included, as a CONTROL: Session J measured it failing to separate on
12 gaps, and 12 is small enough that it deserves one honest retest on 79. It comes
free from the pseudo-label track already in the training dirs.

THE GATE, pre-registered before any feature was scored
------------------------------------------------------
A screen must **keep >= 70% of usable gaps while dropping >= 60% of unusable ones.**
Below that it either throws away the far-court data we are short of, or fails to
save the human any time.

Ground truth per gap is the adjudicator's verdict — anchor-confirmed AND
ball-like click motion — which is human-derived and independent of every feature
scored here.

  py tools/eval_gap_findability.py --json data/output/gap_findability.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import farcourt_labels_to_dataset as f2d   # noqa: E402

ROUNDS = ("farcourt_cal1", "farcourt_pilot2")
CATCH_GATE, DROP_GATE = 70.0, 60.0        # keep >=70% usable, drop >=60% unusable


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _track(clip: str) -> dict[int, tuple[float, float]]:
    """The tracker's own pseudo-label track for a clip, from the training dir.

    This is what the queue was built from, so roam around an anchor costs no
    video decode — the positions are already on disk.
    """
    p = REPO / "data" / "ball_dataset" / f"yt_{clip}" / "labels.json"
    if not p.is_file():
        return {}
    blob = json.loads(p.read_text(encoding="utf-8"))
    return {int(k): (float(v[0]), float(v[1])) for k, v in blob["labels"].items()}


def roam(track, frame, half=8) -> float | None:
    """Max displacement of the track within +/-`half` frames of `frame`.

    Session J's failed criterion, retested here on 79 gaps instead of 12.
    """
    pts = [track[f] for f in range(frame - half, frame + half + 1) if f in track]
    if len(pts) < 2:
        return None
    return max(_dist(a, b) for a in pts for b in pts)


def features(rs) -> dict | None:
    """Everything computable from the queue alone, for one gap."""
    anchors = sorted((r for r in rs if r["bucket"] == "anchor"),
                     key=lambda r: r["src_frame"])
    mids = [r for r in rs if r["bucket"] != "anchor"]
    if len(anchors) < 2 or not mids:
        return None
    a, b = anchors[0], anchors[-1]
    h = a.get("height", 720)
    s = 720.0 / h                     # normalise every pixel quantity to 720p
    span = max(b["src_frame"] - a["src_frame"], 1)
    disp = _dist((a["prior_x"], a["prior_y"]), (b["prior_x"], b["prior_y"])) * s
    tr = _track(a["src_dataset"].removeprefix("yt_"))
    ra, rb = roam(tr, a["src_frame"]), roam(tr, b["src_frame"])
    roams = [r for r in (ra, rb) if r is not None]
    return {
        "anchor_disp_px": round(disp, 1),
        "gap_frames": span,
        "speed_px_per_frame": round(disp / span, 2),
        "anchor_y_mean": round((a["prior_y"] + b["prior_y"]) * s / 2, 1),
        "anchor_y_drop": round(abs(b["prior_y"] - a["prior_y"]) * s, 1),
        "roam_min_px": None if not roams else round(min(roams) * s, 1),
        "roam_max_px": None if not roams else round(max(roams) * s, 1),
        "clip": a["src_dataset"],
    }


def collect() -> list[dict]:
    rows = []
    for q in ROUNDS:
        man = json.loads((REPO / f"data/labels/{q}.manifest.json").read_text(encoding="utf-8"))
        labs = json.loads((REPO / f"data/labels/{q}.labels.json").read_text(encoding="utf-8"))
        labs = labs.get("labels", labs)
        _, verdicts = f2d.adjudicate(man, labs)
        by_gap: dict = {}
        for gid, r in zip(f2d.gap_ids(man["frames"]), man["frames"]):
            by_gap.setdefault(gid, []).append(r)
        for v in verdicts:
            f = features(by_gap.get(v["gap"], []))
            if f is None:
                continue
            rows.append({"round": q, "gap": v["gap"], "usable": bool(v["accepted"]), **f})
    return rows


def sweep(rows, key, higher_is_better=True):
    """Best achievable (keep-usable, drop-unusable) over every threshold on `key`."""
    vals = sorted({r[key] for r in rows if r.get(key) is not None})
    use = [r for r in rows if r["usable"] and r.get(key) is not None]
    bad = [r for r in rows if not r["usable"] and r.get(key) is not None]
    if not use or not bad or len(vals) < 2:
        return None
    best = None
    for t in vals:
        keep = (lambda v: v >= t) if higher_is_better else (lambda v: v <= t)
        kept = 100.0 * sum(1 for r in use if keep(r[key])) / len(use)
        dropped = 100.0 * sum(1 for r in bad if not keep(r[key])) / len(bad)
        score = min(kept - CATCH_GATE, dropped - DROP_GATE)
        if best is None or score > best["score"]:
            best = {"threshold": t, "keep_usable_pct": round(kept, 1),
                    "drop_unusable_pct": round(dropped, 1), "score": score,
                    "direction": ">=" if higher_is_better else "<="}
    best["passes_gate"] = (best["keep_usable_pct"] >= CATCH_GATE
                           and best["drop_unusable_pct"] >= DROP_GATE)
    best.pop("score")
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    rows = collect()
    use = [r for r in rows if r["usable"]]
    print(f"{len(rows)} gaps with a human verdict: {len(use)} usable "
          f"({100*len(use)/len(rows):.0f}%), {len(rows)-len(use)} not\n")

    keys = ["anchor_disp_px", "gap_frames", "speed_px_per_frame",
            "anchor_y_mean", "anchor_y_drop", "roam_min_px", "roam_max_px"]
    print(f"{'feature':<22}{'usable median':>15}{'unusable median':>17}   best split")
    print("-" * 88)
    results = {}
    for k in keys:
        u = [r[k] for r in rows if r["usable"] and r.get(k) is not None]
        n = [r[k] for r in rows if not r["usable"] and r.get(k) is not None]
        if not u or not n:
            continue
        best = max((sweep(rows, k, d) for d in (True, False)),
                   key=lambda b: (b["keep_usable_pct"] + b["drop_unusable_pct"]) if b else -1)
        results[k] = {"usable_median": statistics.median(u),
                      "unusable_median": statistics.median(n), "best": best}
        tag = "  <== PASSES" if best and best["passes_gate"] else ""
        print(f"{k:<22}{statistics.median(u):>15.1f}{statistics.median(n):>17.1f}"
              f"   {best['direction']}{best['threshold']:<8} keep {best['keep_usable_pct']:>5.1f}% "
              f"drop {best['drop_unusable_pct']:>5.1f}%{tag}")

    winners = [k for k, v in results.items() if v["best"] and v["best"]["passes_gate"]]
    print("\n" + "=" * 88)
    if winners:
        print(f"GATE PASSED by: {', '.join(winners)}")
    else:
        print(f"GATE FAILED: nothing keeps >={CATCH_GATE:.0f}% of usable gaps while "
              f"dropping >={DROP_GATE:.0f}% of unusable ones.")
    print("=" * 88)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            "tool": "eval_gap_findability",
            "measured_against": (
                f"{len(rows)} far-court gaps from {', '.join(ROUNDS)}, each with a "
                f"human verdict (anchor-confirmed AND ball-like click motion). Every "
                f"feature is computable from the queue manifest or the pseudo-label "
                f"track, i.e. before any human sees the gap."),
            "gate": {"keep_usable_pct": CATCH_GATE, "drop_unusable_pct": DROP_GATE,
                     "passed": bool(winners)},
            "n_gaps": len(rows), "n_usable": len(use),
            "features": results, "rows": rows,
        }, indent=1), encoding="utf-8")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
