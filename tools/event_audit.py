"""event_audit.py — do our EVENTS land where a human saw a ball? (Session F step 1)

Per-frame false-fire is not the product. MEASURED in E6 part 4: raising it from
19.2% to 23.1% on yt_rally2 produced ZERO extra phantom events — identical 14
hits, 8 bounces, 14 shots — because events.drop_events_without_ball and
smooth_forecast's segment logic absorb locks that never form a trajectory. So a
session can burn itself improving a number the user never sees. This tool is the
number the user does see: it adjudicates every hit and landing we emit against
the human gold clicks, and it is what experiments are picked on.

  backend/.venv/Scripts/python.exe tools/event_audit.py \
      --match data/output/rally2_base.json --clip yt_rally2 \
      --hud data/gold/hud_yt_rally2.json --arm baseline \
      --json data/output/rally2_base.eventaudit.json

WHY THIS RUNS ON ONE CLIP ONLY
------------------------------
The gold sets are a uniform frame grid, and only yt_rally2 is dense enough to
adjudicate an event that can land on any frame. MEASURED label spacing and the
resulting share of frames that have a decided label within +/-3:

    yt_rally2     6 frames   64.7%     <- the only viable clip
    gold_shell   22 frames   30.9%
    gold_am      22 frames   27.5%
    gold_clay    45 frames   15.1%
    yt_match40   34 frames   14.2%
    am_hard_utr 116 frames    5.5%     <- the WORST false-fire clip, unmeasurable

That is the structural limit of this instrument and it must be stated with every
result, not buried: am_hard_utr has the worst raw false-fire of any clip (45.3%)
and cannot be adjudicated this way at all, while yt_rally2 is one uninterrupted
37 s rally — the regime with the FEWEST dead-time frames for a phantom to appear
in. A win here does not demonstrate a win there. The ghost-ball count from
tools/eval_model_filters.py DOES run on all three calibrated clips, so that is
the wide half of the decision and this is the narrow half.

HITS AND LANDINGS OVERLAP, SO THE TWO NUMBERS ARE MADE INDEPENDENT
------------------------------------------------------------------
Every shot carries a `bounce_t_s` whether or not a bounce was DETECTED (the
pipeline reported 6 bounces on the clip that produced 12 shots), and the value is
often the next contact rather than a ground bounce — MEASURED, 5 of 12 landings
on yt_rally2 are also a later shot's `t_hit_s`. Auditing both lists naively
counts those frames twice, which reported the single t=26.6 phantom under both
headings and made one error look like two. A landing that coincides with a hit is
therefore verdicted `also_a_hit` and leaves the landing denominator.

WHAT `phantom_ball_under_hit` IS NOT
-----------------------------------
A gold `ball: true` click means A BALL WAS VISIBLE IN THAT FRAME. It does not
mean a stroke occurred. So this metric detects "we put a hit where there was no
ball" and is BLIND to the dominant historical phantom mode — a bounce read as a
racquet contact — which sits on a perfectly real ball and scores clean. It is
necessary, not sufficient. Never report a zero here as "no phantom strokes".

POWER
-----
~12 adjudicable hits. 2/12 has a 95% Wilson CI of [5%, 45%]. Do NOT claim a
phantom-rate improvement unless the raw COUNT moves by >= 3. If ghost fires fall
and recall holds while this term is flat, the honest verdict is "per-frame and
ghost-ball improved; phantom events unchanged - n=12 cannot resolve a change this
size". That is a shippable result, correctly qualified.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import cv2  # noqa: E402

# One definition of the gold-frame parity guard in this repo, not three. The
# `f % step == 0` check is the bug that understated the tracker through all of
# E6 part 2 (CLAUDE.md records the withdrawn numbers), so it is imported rather
# than re-typed. eval_model_filters is __main__-guarded, so this costs an import
# of cv2/numpy and runs nothing.
from eval_model_filters import CLIPS, build_calib, gold, index_of  # noqa: E402
from hud_compare import match_monotonic  # noqa: E402

HIT_RADIUS_PX = 10.0      # the same tolerance the gold ladder scores recall at


def wilson95(k, n):
    """95% CI for a proportion. Reported because n is ~12 and a reader who sees
    '16.7%' without it will believe the third significant figure."""
    if n == 0:
        return None
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(100 * (c - r) / d), round(100 * (c + r) / d)]


def post_chain(raw, H, wh, hfov, fps_eff):
    """Re-run the shipped post-tracking chain over a cached RAW track.

    The perception cache stores the tracker's raw output (pipeline.py writes it
    before the filter chain); the cleaned ball_px and the coasted mask that
    annotate.py actually draws from exist only in memory. Rather than change the
    cache format, recompute — it is five calls and about a second of CPU, and it
    keeps this tool from touching shipped code. The order MUST stay identical to
    pipeline.analyze_video: rectify -> suppress -> court gate -> smooth.
    """
    from swingvision import ball as B
    W, Hh = wh
    rs = Hh / 720.0
    tr = B.remove_outliers(list(raw), max_jump=max(W, Hh) * 0.06)
    tr = B.rectify_track(tr, max_speed_px=3000.0 * rs / fps_eff, resid_px=35.0 * rs)
    tr = B.suppress_false_locks(tr, fps_eff=fps_eff, res_scale=rs)
    if H is not None:
        tr = B.gate_ball_to_court(tr, H, (W, Hh), hfov_deg=hfov)
    tr, coasted, _conf = B.smooth_forecast(tr, fps_eff=fps_eff, res_scale=rs)
    return tr, coasted


def adjudicate(t_s, src_fps, decided, k, tr, at, click_ok=True):
    """One event -> a verdict against the nearest decided human label.

    Returns (verdict, src_frame, nearest_frame, delta, coasted). An event further
    than k frames from any decided label is UNKNOWN and leaves the denominator —
    counting it as either a pass or a phantom would be inventing evidence.
    """
    f = int(round(t_s * src_fps))
    near = min(decided, key=lambda g: abs(g - f))
    d = abs(near - f)
    if d > k:
        return "unknown", f, near, d, None
    pf = at(near)
    coasted = None
    if not decided[near]:
        return "phantom_ball", f, near, d, coasted
    if not click_ok or pf is None or tr is None or pf >= len(tr) or tr[pf] is None:
        return "ball_present", f, near, d, coasted
    v = decided[near]
    ok = math.dist(tr[pf], (v["x"], v["y"])) <= HIT_RADIUS_PX
    return ("localised" if ok else "ball_elsewhere"), f, near, d, coasted


def landing_verdict(verdict, coasted):
    """Collapse a landing's presence verdict into the three-way split.

    A landing legitimately falls on an interpolated frame — pipeline.py states
    the exact contact usually lands BETWEEN detections, and `ball_valid` is
    deliberately computed from a mask that includes coasted frames. Scoring a
    coasted landing as a phantom would blame the smoother for doing its job, so
    only a landing on a human "no ball" counts. `unknown` passes through
    untouched: it is out of the denominator either way.
    """
    if verdict in ("ball_present", "localised", "ball_elsewhere"):
        return "coasted" if coasted else "real_detection"
    return verdict


def coverage_at(decided_frames, n_frames, k):
    """Share of all source frames that an event could be adjudicated on at
    tolerance k. Printed at several k so nobody tunes k until they like the
    answer."""
    hit = 0
    for f in range(n_frames):
        near = min(decided_frames, key=lambda g: abs(g - f))
        hit += abs(near - f) <= k
    return 100.0 * hit / max(n_frames, 1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--match", required=True, help="our match.json")
    ap.add_argument("--clip", default="yt_rally2", choices=list(CLIPS))
    ap.add_argument("--perception", default=None,
                    help="the <match stem>.perception.json holding the RAW track; "
                         "defaults to that path. Without it the localised/coasted "
                         "columns are omitted rather than guessed.")
    ap.add_argument("--hud", default=None)
    ap.add_argument("--tolerance-frames", type=int, default=3, dest="k",
                    help="max |event frame - nearest decided gold label|. 3 source "
                         "frames is 50 ms at 60 fps, inside MIN_FLIGHT_S, and the "
                         "tightest k that keeps yt_rally2 adjudication above 60%%")
    ap.add_argument("--ghost", default=None,
                    help="an eval_model_filters --json payload; its FULL-row ghost "
                         "counts are folded into this envelope so one artifact "
                         "carries both the per-frame and the product number")
    ap.add_argument("--arm", default="", help="what this run is an arm OF")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    video_rel, pts_rel, labels_rel = CLIPS[args.clip]
    cap = cv2.VideoCapture(str(REPO / video_rel))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # The SOURCE fps. match["video"]["fps"] is fps_eff (30.0 on this 60 fps clip),
    # so using it would halve every frame index and silently misalign the audit.
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    ballg, noball = gold(labels_rel)
    # `decided` maps frame -> the click dict for a ball, or False for a no-ball.
    # `unsure` labels are excluded from BOTH sides: the human declined to call it,
    # so neither a pass nor a phantom can be read off them.
    decided = {f: v for f, v in ballg.items()}
    decided.update({f: False for f in noball})

    match = json.loads(Path(args.match).read_text(encoding="utf-8"))
    shots = match["shots"]

    perc_path = (Path(args.perception) if args.perception
                 else Path(str(Path(args.match).with_suffix("")) + ".perception.json"))
    tr = at = None
    step = None
    if perc_path.exists():
        cache = json.loads(perc_path.read_text(encoding="utf-8"))
        step = cache["frame_step"]
        H, hfov = build_calib(pts_rel, (W, Hh))
        raw = [None if p is None else list(p) for p in cache["ball_px"]]
        tr, coasted = post_chain(raw, H, (W, Hh), hfov, src_fps / step)
        at = index_of(step, len(tr))
    else:
        coasted = None
        print(f"NOTE no perception cache at {perc_path} - reporting phantom "
              f"verdicts only; localised/coasted columns omitted.")

    def coast_at(t_s):
        if coasted is None or step is None:
            return None
        pf = int(round(t_s * src_fps)) // step
        return bool(pf < len(coasted) and coasted[pf])

    print(f"arm: {args.arm or '(unnamed)'}   clip: {args.clip}   "
          f"{W}x{Hh} @ {src_fps:.2f}fps   k={args.k} source frames")
    dfr = sorted(decided)
    cov = {kk: round(coverage_at(dfr, n_frames, kk), 1) for kk in (2, args.k, 5)}
    print(f"  {len(decided)} decided gold labels ({len(ballg)} ball / "
          f"{len(noball)} no-ball); adjudicable share of frames at "
          f"k=2/{args.k}/5: {cov[2]}% / {cov[args.k]}% / {cov[5]}%")

    # A shot's `bounce_t_s` is the landing attached to it, and the pipeline
    # frequently fills that with the NEXT contact rather than a ground bounce —
    # on this clip 5 of 12 landings are also a later shot's t_hit_s. Auditing
    # both lists naively counts the same frame twice and would have reported the
    # t=26.6 phantom under both headings, making one error look like two.
    # Landings that coincide with a hit leave the landing denominator instead.
    hit_frames = {int(round(s["t_hit_s"] * src_fps)) for s in shots}

    out = {}
    for kind, times, want_click in (("hits", [s["t_hit_s"] for s in shots], True),
                                    ("landings", [s.get("bounce_t_s") for s in shots],
                                     False)):
        rows, tally = [], {}
        for i, t in enumerate(times):
            if t is None:
                continue
            if kind == "landings" and int(round(t * src_fps)) in hit_frames:
                rows.append(dict(id=i, t_s=round(t, 2),
                                 src_frame=int(round(t * src_fps)),
                                 nearest_label=None, d_frames=None,
                                 verdict="also_a_hit", coasted=None))
                tally["also_a_hit"] = tally.get("also_a_hit", 0) + 1
                continue
            verdict, f, near, d, _ = adjudicate(t, src_fps, decided, args.k, tr, at,
                                                click_ok=want_click)
            c = coast_at(t)
            if kind == "landings":
                verdict = landing_verdict(verdict, c)
            rows.append(dict(id=i, t_s=round(t, 2), src_frame=f,
                             nearest_label=near, d_frames=d, verdict=verdict,
                             coasted=c))
            tally[verdict] = tally.get(verdict, 0) + 1

        n = len(rows)
        adj = n - tally.get("unknown", 0) - tally.get("also_a_hit", 0)
        ph = tally.get("phantom_ball", 0)
        out[kind] = dict(n=n, adjudicable=adj, phantom_ball=ph,
                         phantom_pct=None if adj == 0 else round(100 * ph / adj, 1),
                         ci95_pct=wilson95(ph, adj), tally=tally, rows=rows)
        dup = tally.get("also_a_hit", 0)
        print(f"\n  {kind}: {n} emitted, {adj} adjudicable at k={args.k}, "
              f"{ph} phantom" + (f" ({dup} excluded as also a hit)" if dup else ""))
        for v, c in sorted(tally.items()):
            print(f"      {v:<16} {c}")
        for r in rows:
            if r["verdict"] in ("phantom_ball", "ball_elsewhere"):
                print(f"      -> {r['verdict']} at t={r['t_s']}s "
                      f"(frame {r['src_frame']}, label {r['nearest_label']} "
                      f"{r['d_frames']}f away)")

    hud_block = None
    if args.hud:
        readings = json.loads(Path(args.hud).read_text(encoding="utf-8"))["shots"]
        idx = match_monotonic(shots, readings, -0.25, 2.0)
        matched = {i for i, _, _ in idx}
        sur = [s for i, s in enumerate(shots) if i not in matched]
        hud_block = dict(n_hud=len(readings), n_ours=len(shots), matched=len(idx),
                         surplus_shots=len(sur),
                         surplus_confident_shots=sum(
                             1 for s in sur if s.get("speed_confident")),
                         coverage_pct=round(100 * len(idx) / max(len(readings), 1), 1),
                         matcher="monotonic-dp")
        print(f"\n  HUD (tie-break evidence only): matched {len(idx)}/"
              f"{len(readings)}, surplus {len(sur)} shots "
              f"({hud_block['surplus_confident_shots']} confident)")

    ghost_block = None
    if args.ghost:
        g = json.loads(Path(args.ghost).read_text(encoding="utf-8"))
        full = [r for r in g.get("rows", []) if r.get("fires_real") is not None]
        if full:
            r = full[-1]
            ghost_block = dict(source=Path(args.ghost).name, clip=g.get("clip"),
                               stage=r["stage"], fires=r["fires"],
                               fires_real=r["fires_real"],
                               fires_coasted=r["fires_coasted"],
                               n_noball=r["n_noball"],
                               false_fire_pct=r["false_fire"],
                               recall_pct=r["recall"])
            print(f"\n  ghost ball ({ghost_block['clip']}): {r['fires']}/"
                  f"{r['n_noball']} ({r['fires_real']} solid, "
                  f"{r['fires_coasted']} faded) at {r['recall']}% recall")

    h, b = out["hits"], out["landings"]
    summary = (f"{args.clip} | "
               + (f"per-frame FF {ghost_block['false_fire_pct']}% | ghost "
                  f"{ghost_block['fires']}/{ghost_block['n_noball']} "
                  f"({ghost_block['fires_real']} solid, "
                  f"{ghost_block['fires_coasted']} faded) | " if ghost_block else "")
               + f"phantom hits {h['phantom_ball']}/{h['adjudicable']} | "
               + f"phantom landings {b['phantom_ball']}/{b['adjudicable']}"
               + (f" | surplus shots {hud_block['surplus_shots']}/"
                  f"{hud_block['n_ours']} ({hud_block['surplus_confident_shots']} "
                  f"conf) | HUD {hud_block['matched']}/{hud_block['n_hud']}"
                  if hud_block else ""))
    print(f"\nSUMMARY  {summary}")

    if args.json_out:
        try:
            commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                    cwd=REPO, capture_output=True, text=True,
                                    timeout=10).stdout.strip()
        except Exception:
            commit = None
        payload = {
            "tool": "event_audit",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "commit": commit,
            "arm": args.arm,
            "match": Path(args.match).name,
            "clip": args.clip,
            "src_fps": round(src_fps, 2),
            "frame_step": step,
            "tolerance_frames": args.k,
            "adjudicable_share_pct": cov,
            "measured_against":
                f"human gold clicks on {args.clip}: {len(decided)} decided labels "
                f"({len(ballg)} ball, {len(noball)} no-ball; unsure excluded from "
                f"both sides). An event is adjudicated only if a decided label lies "
                f"within {args.k} source frames. A 'ball present' verdict means a "
                f"ball was VISIBLE in that frame, NOT that a stroke occurred.",
            "hits": h, "bounces": b, "hud": hud_block, "ghost_ball": ghost_block,
            "summary": summary,
            "caveats": [
                "Single clip. yt_rally2 is one continuous 37 s rally with almost no "
                "dead time - the regime with the FEWEST phantom opportunities. "
                "am_hard_utr, the clip with the worst false-fire, has a decided "
                "label only every ~116 frames and cannot be measured this way.",
                "phantom_ball_under_hit is blind to a bounce misread as a racquet "
                "contact: that phantom sits on a real ball and scores clean.",
                "speed_confident derives from the same ball_px mask a false-fire "
                "change modifies, so the confident subset is partially self-graded.",
                f"n={h['adjudicable']} adjudicable hits: a 1- or 2-event move is "
                f"inside the 95% CI. Require a count move of >=3.",
                "The HUD block is tie-break evidence only. The HUD misses strokes "
                "on its own terms, so an unmatched pair is a joint failure this "
                "tool cannot attribute.",
            ],
        }
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, indent=1),
                                       encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
