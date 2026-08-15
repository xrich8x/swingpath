#!/usr/bin/env python
"""score_truth.py - build POINT-BOUNDARY ground truth from a burned-in scoreboard.

WHY THIS EXISTS
---------------
Rally segmentation and scoring are the only layers in this product with NO
ground truth. Ball detection has 1851 human clicks, court has 20 hand-labelled
clips, speed has the HUD and synth_truth. No point boundary has ever been
labelled, so "63 rallies is wrong" has been an ASSERTION, not a measurement
(data/output/rally_scoring_research.md).

Three gold clips carry a burned-in, point-by-point score. That is exact truth
for point boundaries, per-point winner, the score state machine and who is
serving - and it costs no annotation.

WHAT IT IS MEASURED AGAINST (rule 2)
------------------------------------
The clip's own broadcast scoreboard, which is produced by the recording system
and is completely independent of anything this project computes. Nothing here
reads our own pipeline, so this cannot self-grade.

HOW IT WORKS, AND WHY NOT OCR
-----------------------------
`hud_ocr.py` segments glyphs and NCC-matches them. That is the right tool for
the speed readout, where the value is an arbitrary 2-3 digit number. A tennis
score is not arbitrary: the points field takes 5 values (0/15/30/40/AD) and
games 0-7. So instead of recognising characters we CLUSTER each field's crop
into distinct visual states and label each cluster ONCE, by eye.

That matters for correctness, not just effort. The research counted distinct
states of the WHOLE PANEL and got "40 states, so ~35-40 points" - a +-5
uncertainty, because a server-dot move also changes the panel. Clustering
PER FIELD separates them exactly: a point change moves the points field, a
game change moves games, a serve change moves the dot.

Sub-commands
------------
  probe  - dump the panel and its field boxes as an image, to check geometry
  scan   - read every field across the clip, cluster states, write the series
  sheet  - render one tile per distinct state, for a human to label
  build  - apply labels, validate against tennis rules, write the truth file

Panel geometry lives in PANELS below. It is RECORDED here on purpose: the
2026-08-13 research located these boxes, produced evidence images, and kept no
code, so the coordinates were lost and had to be found again.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np

# --- Panel geometry, per clip -------------------------------------------------
# Boxes are (x0, y0, x1, y1) in SOURCE pixels, verified by eye against a drawn
# overlay (see `probe`). Rows are top/bottom player as the panel shows them.
PANELS = {
    "am_hard_utr": {
        "video": "data/am_hard_utr.mp4",
        "size": (1920, 1080),
        "panel": (20, 8, 600, 180),
        "fields": {
            "pts_top": (487, 26, 590, 88),
            "pts_bot": (487, 98, 590, 162),
            "gm_top": (440, 28, 487, 88),
            "gm_bot": (440, 100, 487, 162),
            "dot_top": (408, 40, 442, 78),
            "dot_bot": (408, 112, 442, 150),
        },
        "players": ["ANIRUDH", "JACK"],
        "sig": "adaptive",
    },
    # yt_match40 is the HARD panel and the one that matters for the 63-rally
    # figure: a semi-transparent dark card over a MOVING hedge, with no white
    # box behind the digits. An adaptive threshold tracks that moving
    # background and shatters one digit into many states, so this clip
    # thresholds on absolute brightness instead - the glyphs are near-white and
    # everything behind the card is far darker.
    "yt_match40": {
        "video": "data/yt_match40.mp4",
        "size": (1280, 720),
        "panel": (18, 15, 305, 115),
        "fields": {
            "pts_top": (250, 36, 288, 60),
            "pts_bot": (250, 86, 288, 110),
            "gm_top": (203, 36, 226, 60),
            "gm_bot": (203, 86, 226, 110),
            "dot_top": (150, 40, 172, 58),
            "dot_bot": (150, 90, 172, 108),
        },
        "players": ["D. Tan", "Opponent"],
        "sig": "bright",
    },
}

SIG_WH = (24, 16)          # field crop is reduced to this before hashing
HAMMING_SAME = 12          # <= this many differing bits -> same visual state


def _sig(crop, mode="adaptive") -> np.ndarray:
    """A compression-tolerant signature of a field crop.

    'adaptive' thresholds at the crop's own midpoint. That suits an opaque
    panel with strong local contrast (am_hard_utr), and copes with both colour
    schemes there - white-on-navy games, black-on-white points.

    'bright' thresholds at a fixed high level. Required when the panel is
    SEMI-TRANSPARENT over moving scenery (yt_match40, a dark card over a hedge):
    an adaptive threshold follows the background and shatters one digit into
    many states, while the glyphs themselves stay near-white throughout.
    """
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, SIG_WH, interpolation=cv2.INTER_AREA)
    if mode == "bright":
        return (g > 170).astype(np.uint8).ravel()
    lo, hi = float(g.min()), float(g.max())
    if hi - lo < 12:                     # flat crop (e.g. empty dot box)
        return np.zeros(SIG_WH[0] * SIG_WH[1], dtype=np.uint8)
    return (g > (lo + hi) / 2.0).astype(np.uint8).ravel()


def _ham(a, b) -> int:
    return int(np.count_nonzero(a != b))


def _fields(frame, spec):
    return {k: frame[y0:y1, x0:x1] for k, (x0, y0, x1, y1) in spec["fields"].items()}


def _clip_spec(clip):
    if clip not in PANELS:
        sys.exit(f"no panel geometry recorded for {clip!r}. Known: {list(PANELS)}")
    return PANELS[clip]


def _open(spec, root):
    path = os.path.join(root, spec["video"])
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        sys.exit(f"cannot open {path}")
    return cap


# ------------------------------------------------------------------ probe

def cmd_probe(args):
    spec = _clip_spec(args.clip)
    cap = _open(spec, args.root)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(args.at * fps))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        sys.exit(f"could not read frame at t={args.at}s")

    h, w = frame.shape[:2]
    if (w, h) != tuple(spec["size"]):
        print(f"WARNING: {args.clip} is {w}x{h} but geometry was recorded for "
              f"{spec['size']} - boxes will be wrong")

    px0, py0, px1, py1 = spec["panel"]
    vis = frame[max(0, py0 - 10):py1 + 10, max(0, px0 - 10):px1 + 10].copy()
    off = (max(0, px0 - 10), max(0, py0 - 10))
    colour = {"pts": (0, 0, 255), "gm": (0, 255, 0), "dot": (0, 255, 255)}
    for name, (x0, y0, x1, y1) in spec["fields"].items():
        c = colour[name.split("_")[0]]
        cv2.rectangle(vis, (x0 - off[0], y0 - off[1]), (x1 - off[0], y1 - off[1]), c, 2)
    vis = cv2.resize(vis, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(args.out, vis)
    print(f"wrote {args.out}  (red=points, green=games, yellow=server dot)")


# ------------------------------------------------------------------- scan

def cmd_scan(args):
    spec = _clip_spec(args.clip)
    cap = _open(spec, args.root)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(args.every * fps)))

    states = {k: [] for k in spec["fields"]}      # per field: list of signatures
    series = []                                   # (frame_idx, {field: state_id})

    idx = 0
    while idx < total:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            break
        row = {}
        for name, crop in _fields(frame, spec).items():
            s = _sig(crop, spec.get("sig", "adaptive"))
            hit = None
            for i, known in enumerate(states[name]):
                if _ham(s, known) <= HAMMING_SAME:
                    hit = i
                    break
            if hit is None:
                states[name].append(s)
                hit = len(states[name]) - 1
            row[name] = hit
        series.append((idx, row))
        idx += step
    cap.release()

    out = {
        "clip": args.clip,
        "measured_against": "the clip's own burned-in broadcast scoreboard "
                            "(independent of anything this project computes)",
        "fps": fps, "total_frames": total, "sample_every_s": args.every,
        "n_samples": len(series),
        "distinct_states": {k: len(v) for k, v in states.items()},
        "series": [{"frame": f, **r} for f, r in series],
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    np.save(args.out + ".sigs.npy",
            np.array([np.stack(states[k]) if states[k] else np.zeros((0, 384))
                      for k in sorted(states)], dtype=object), allow_pickle=True)
    print(f"{args.clip}: {len(series)} samples every {args.every}s")
    for k in sorted(states):
        print(f"  {k:9s} {len(states[k]):3d} distinct states")
    print(f"-> {args.out}")


# ------------------------------------------------------------------- sheet

def cmd_sheet(args):
    """One tile per distinct state of one field, so a human can label them."""
    spec = _clip_spec(args.clip)
    with open(args.scan, "r", encoding="utf-8") as fh:
        scan = json.load(fh)
    cap = _open(spec, args.root)

    field = args.field
    first = {}
    for row in scan["series"]:
        sid = row[field]
        if sid not in first:
            first[sid] = row["frame"]
    box = spec["fields"][field]

    tiles = []
    for sid in sorted(first):
        cap.set(cv2.CAP_PROP_POS_FRAMES, first[sid])
        ok, frame = cap.read()
        if not ok:
            continue
        x0, y0, x1, y1 = box
        crop = cv2.resize(frame[y0:y1, x0:x1], None, fx=3, fy=3,
                          interpolation=cv2.INTER_NEAREST)
        cv2.putText(crop, f"#{sid}", (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 0, 255), 2)
        tiles.append(crop)
    cap.release()

    hgt = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, hgt - t.shape[0], 0, 8, cv2.BORDER_CONSTANT,
                                value=(30, 30, 30)) for t in tiles]
    cv2.imwrite(args.out, np.hstack(tiles))
    print(f"{field}: {len(tiles)} distinct states -> {args.out}")
    print("label them with:  --labels '" +
          ",".join(f"{s}=?" for s in sorted(first)) + "'")


# ------------------------------------------------------------------- build

# Cluster-id -> value, READ BY EYE off `sheet` output (data/output/score_states_*.png).
# This is the human step and it is deliberately not automated: on dot_bot the
# clustering FALSE-SPLIT the empty box into two states on a background gradient,
# so trusting cluster identity to be semantic would have invented a serve change.
LABELS = {
    "am_hard_utr": {
        "pts_top": {0: "0", 1: "15", 2: "30", 3: "DU", 4: "AD", 5: "40"},
        "pts_bot": {0: "0", 1: "15", 2: "30", 3: "40", 4: "DU"},
        "gm_top": {0: 0, 1: 1, 2: 2},
        "gm_bot": {0: 0, 1: 1, 2: 2, 3: 3, 4: 4},
        "dot_top": {0: False, 1: True},
        "dot_bot": {0: True, 1: False, 2: False},   # 1 and 2 are both EMPTY
    },
    # None = the scoreboard is NOT DISPLAYED on that frame. yt_match40 opens
    # before the graphic appears. These samples must be dropped, not read as a
    # score: entering and leaving the state would otherwise invent two points.
    "yt_match40": {
        "pts_top": {0: None, 1: "0", 2: "15", 3: "30", 4: "40", 5: "AD"},
        "pts_bot": {0: None, 1: "0", 2: "15", 3: "30", 4: "40", 5: "AD"},
        "gm_top": {0: None, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5},
        "gm_bot": {0: None, 1: 0, 2: 1},
        "dot_top": {0: False, 1: True},
        "dot_bot": {0: False, 1: True},
    },
}

# Legal successor points within a game. Covers BOTH vocabularies seen so far:
# am_hard_utr writes deuce as "DU" and advantage as "AD"; yt_match40 leaves
# deuce as 40-40 and only writes "AD". So 40 may advance to either.
_NEXT = {"0": {"15"}, "15": {"30"}, "30": {"40", "DU"},
         "40": {"DU", "AD", "40"}, "DU": {"AD"}, "AD": {"DU", "40"}}


def _runs(series, keys):
    """Collapse the sample series into runs of a constant labelled state."""
    out = []
    for row in series:
        st = tuple(row[k] for k in keys)
        if not out or out[-1][0] != st:
            out.append([st, row["frame"], row["frame"]])
        else:
            out[-1][2] = row["frame"]
    return out


def cmd_build(args):
    spec = _clip_spec(args.clip)
    lab = LABELS[args.clip]
    with open(args.scan, "r", encoding="utf-8") as fh:
        scan = json.load(fh)
    fps = scan["fps"]

    # Apply the eye labels, DROPPING samples where the board is not displayed.
    series, n_absent = [], 0
    for row in scan["series"]:
        vals = {k: lab[k][row[k]] for k in lab}
        if any(vals[k] is None for k in ("pts_top", "pts_bot", "gm_top", "gm_bot")):
            n_absent += 1
            continue
        series.append({"frame": row["frame"], **vals})
    if not series:
        sys.exit("every sample has the scoreboard absent - check the labels")

    keys = ["pts_top", "pts_bot", "gm_top", "gm_bot", "dot_top", "dot_bot"]
    runs = _runs(series, keys)

    # A POINT ends whenever the points pair changes, or a game is won (points
    # reset and a games digit ticks). Server-dot moves alone are NOT points -
    # separating those is the whole reason for reading fields independently.
    points, issues = [], []
    for i in range(1, len(runs)):
        (p0, q0, g0, h0, d0, e0), s0, _ = runs[i - 1]
        (p1, q1, g1, h1, d1, e1), s1, _ = runs[i]
        pts_changed = (p0, q0) != (p1, q1)
        games_changed = (g0, h0) != (g1, h1)
        if not (pts_changed or games_changed):
            continue                              # serve dot only -> not a point
        winner = None
        if games_changed:
            winner = "top" if g1 > g0 else ("bot" if h1 > h0 else None)
        elif p1 != p0 and q1 == q0:
            winner = "top"
        elif q1 != q0 and p1 == p0:
            winner = "bot"
        elif p1 != p0 and q1 != q0:
            winner = "top" if p1 in ("AD", "DU") and p0 == "40" else None
        points.append({
            "t_s": round(s1 / fps, 3), "frame": s1,
            "from": f"{p0}-{q0} ({g0}-{h0})", "to": f"{p1}-{q1} ({g1}-{h1})",
            "winner": winner,
            "server": "top" if d1 else ("bot" if e1 else None),
        })
        # Validation: within a game, the winner's points must advance legally.
        if not games_changed:
            if winner == "top" and p1 not in _NEXT.get(p0, set()):
                issues.append(f"t={s1/fps:.1f}s illegal top {p0}->{p1}")
            if winner == "bot" and q1 not in _NEXT.get(q0, set()):
                issues.append(f"t={s1/fps:.1f}s illegal bot {q0}->{q1}")

    games = [r for i, r in enumerate(runs)
             if i and (runs[i - 1][0][2], runs[i - 1][0][3]) != (r[0][2], r[0][3])]

    out = {
        "clip": args.clip,
        "measured_against": "the clip's own burned-in broadcast scoreboard, read by "
                            "per-field state clustering with every state labelled by "
                            "eye; independent of anything this project computes",
        "evidence_tag": "MEASURED",
        "players": spec["players"],
        "fps": fps, "duration_s": round(scan["total_frames"] / fps, 1),
        "sample_every_s": scan["sample_every_s"],
        "samples_board_absent": n_absent,
        "n_points": len(points),
        "n_games": len(games),
        "final_score": f"{runs[-1][0][2]}-{runs[-1][0][3]}",
        "validation_issues": issues,
        "points": points,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    print(f"{args.clip}: {len(points)} POINTS, {len(games)} game changes, "
          f"final games {out['final_score']}")
    print(f"  boundary resolution: +-{scan['sample_every_s']}s (sample interval)")
    if issues:
        print(f"  {len(issues)} VALIDATION ISSUES (illegal point transitions):")
        for m in issues[:12]:
            print(f"    {m}")
    else:
        print("  validation: every point transition is legal tennis")
    print(f"-> {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="repo root")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="draw the field boxes on one frame")
    p.add_argument("--clip", required=True)
    p.add_argument("--at", type=float, default=40.0, help="timestamp (s)")
    p.add_argument("--out", default="panel_probe.png")
    p.set_defaults(func=cmd_probe)

    s = sub.add_parser("scan", help="read every field across the clip")
    s.add_argument("--clip", required=True)
    s.add_argument("--every", type=float, default=0.5, help="sample interval (s)")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_scan)

    t = sub.add_parser("sheet", help="render distinct states of one field to label")
    t.add_argument("--clip", required=True)
    t.add_argument("--scan", required=True)
    t.add_argument("--field", required=True, choices=sorted(
        PANELS["am_hard_utr"]["fields"]))
    t.add_argument("--out", default="states.png")
    t.set_defaults(func=cmd_sheet)

    b = sub.add_parser("build", help="apply eye labels, validate, write truth")
    b.add_argument("--clip", required=True)
    b.add_argument("--scan", required=True)
    b.add_argument("--out", required=True)
    b.set_defaults(func=cmd_build)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
