"""Score a chain change against the pre-registered gate, on every gold clip that
has a perception cache.

The gate itself lives in docs/evidence/ball-chain-gate.md and is NOT restated
here (one number, one home). This tool reports the inputs each bar needs.

WHY IT EXISTS. The first run of that gate used the three clips that happened to
have caches - 74 of the gold set's 308 no-ball frames - and its separation ratio
came down to a denominator of two ghost frames. This runs the same comparison
over every cached clip instead.

Everything is INVOKED, not re-derived (T15): the chain comes from
tools/chain_cache.py (which calls pipeline's own stage functions) and the
scoring from tools/eval_gold.py. Resolution and fps are read from the video, not
defaulted - res_scale = height/720 scales every pixel threshold in the chain, so
a wrong default runs it silently too loose (T16).

  backend/.venv/Scripts/python.exe tools/eval_chain_gate.py --bounce-hypothesis
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import cv2  # noqa: E402
from _goldset import GOLD  # noqa: E402
from chain_cache import homography, run_chain  # noqa: E402
from eval_gold import load, score  # noqa: E402


def clips():
    return GOLD if isinstance(GOLD, (list, tuple)) else list(GOLD.values())


def cache_for(name: str) -> Path | None:
    exact = REPO / "data" / "output" / f"{name}.perception.json"
    if exact.exists():
        return exact
    hits = sorted(glob.glob(str(REPO / "data" / "output" / f"{name}*.perception.json")))
    return Path(hits[0]) if hits else None


def video_for(video: str) -> Path | None:
    hits = glob.glob(str(REPO / "data" / "**" / Path(video).name), recursive=True)
    return Path(hits[0]) if hits else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bounce-hypothesis", action="store_true",
                    help="the arm under test; off-arm is always the shipped path")
    ap.add_argument("--restitution-set", default=None,
                    help="v2 of the bounce hypothesis: comma-separated "
                         "restitution values, each tested at the UNMODIFIED S "
                         "(docs/evidence/bounce-hypothesis-v2-gate.md). Absent "
                         "= v1, a single restitution with restitution_band "
                         "inflating S[1,1].")
    ap.add_argument("--radius", type=float, default=10.0)
    ap.add_argument("--markdown", default=None)
    args = ap.parse_args()
    rset = ([float(v) for v in args.restitution_set.split(",")]
            if args.restitution_set else None)
    arm = ("OFF (shipped)" if not args.bounce_hypothesis
           else (f"v2 restitution_set={rset}, S UNMODIFIED" if rset
                 else "v1 single restitution + restitution_band on S[1,1]"))
    print(f"ON-arm: {arm}")

    rows = []
    tot = dict(ball=0, nb=0, h_off=0, h_on=0, w_off=0, w_on=0, f_off=0, f_on=0)

    for c in clips():
        cache_p = cache_for(c.name)
        vid = video_for(c.video)
        lab_p = REPO / c.labels
        if not (cache_p and vid and lab_p.exists()):
            print(f"skip {c.name}: cache={bool(cache_p)} video={bool(vid)} labels={lab_p.exists()}")
            continue

        cap = cv2.VideoCapture(str(vid))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()

        cache = json.loads(cache_p.read_text(encoding="utf-8"))
        step = int(cache.get("frame_step") or 1)
        fps_eff = fps / step
        H = homography(str(REPO / c.calib)) if c.calib and (REPO / c.calib).exists() else None

        g = load(str(lab_p))
        gold = {int(k): v for k, v in g["labels"].items()
                if not (v.get("unsure") or v.get("ball") is None)}

        res = {}
        for arm, flag in (("off", False), ("on", args.bounce_hypothesis)):
            track, coasted, _counts = run_chain(
                list(cache["ball_px"]), fps_eff=fps_eff, width=w, height=h,
                H=H, hfov=(cache.get("provenance") or {}).get("camera_hfov_deg"),
                bounce_hypothesis=flag,
                restitution_set=(rset if flag else None))
            seen = [None if coasted[i] else p for i, p in enumerate(track)]
            res[arm] = score({**cache, "ball_px": seen}, gold, {}, args.radius)

        o, n = res["off"], res["on"]
        rows.append((c.name, H is not None, o, n))
        tot['ball'] += o['n_ball']; tot['nb'] += o['n_noball']
        tot['h_off'] += o['hit']; tot['h_on'] += n['hit']
        tot['w_off'] += o['wrong']; tot['w_on'] += n['wrong']
        tot['f_off'] += o['fp']; tot['f_on'] += n['fp']

    hdr = (f"{'clip':<20}{'cal':>4}{'ball':>6}{'hit_off':>8}{'hit_on':>7}{'d':>5}"
           f"{'wrong':>7}{'d':>4}{'nb':>5}{'fp_off':>7}{'fp_on':>6}{'d':>4}")
    print("\n" + hdr)
    print("-" * len(hdr))
    for name, cal, o, n in rows:
        print(f"{name:<20}{'Y' if cal else 'n':>4}{o['n_ball']:>6}{o['hit']:>8}{n['hit']:>7}"
              f"{n['hit']-o['hit']:>+5}{o['wrong']:>7}{n['wrong']-o['wrong']:>+4}"
              f"{o['n_noball']:>5}{o['fp']:>7}{n['fp']:>6}{n['fp']-o['fp']:>+4}")
    dh = tot['h_on'] - tot['h_off']; dg = tot['f_on'] - tot['f_off']
    dw = tot['w_on'] - tot['w_off']
    print("-" * len(hdr))
    print(f"{'POOLED':<20}{'':>4}{tot['ball']:>6}{tot['h_off']:>8}{tot['h_on']:>7}{dh:>+5}"
          f"{tot['w_off']:>7}{dw:>+4}{tot['nb']:>5}{tot['f_off']:>7}{tot['f_on']:>6}{dg:>+4}")

    print(f"\nP1 recall     {tot['h_off']/tot['ball']*100:.1f}% -> "
          f"{tot['h_on']/tot['ball']*100:.1f}%   ({dh:+d} hits on {tot['ball']} clicks)")
    print(f"P2 ghosts     {tot['f_off']} -> {tot['f_on']} ({dg:+d}) pooled; "
          f"per-clip rises: {sum(1 for _,_,o,n in rows if n['fp'] > o['fp'])} of {len(rows)}")
    ratio = (dh / dg) if dg > 0 else float('inf')
    print(f"P4 separation {dh} real hits / {dg} ghosts = "
          f"{ratio:.2f} : 1      GATE REQUIRES > 7")
    print(f"P5 power      {tot['nb']} no-ball frames      GATE REQUIRES >= 74")

    # P6 replication: a pass on one clip and a collapse on another is a FAIL.
    # The gate's own per-clip recall floor is -2.0 pts.
    r_fail = [name for name, _, o, n in rows
              if o['n_ball'] and (n['hit'] - o['hit']) / o['n_ball'] * 100 < -2.0]
    print(f"P6 replication INPUT ONLY - clips below the -2.0 pt per-clip recall "
          f"floor: {len(r_fail)} of {len(rows)}"
          f"{(' ' + ', '.join(r_fail)) if r_fail else ''}")
    print("   P6 is a JUDGEMENT over the per-clip rows, not this one number: a "
          "pass on one clip")
    print("   and a collapse on another is a FAIL. Read it with P2 and P7's "
          "per-clip rises -")
    print("   v1 failed P6 at a recall delta INSIDE this floor.")

    # P7 (v2 gate only, docs/evidence/bounce-hypothesis-v2-gate.md). v1's real
    # defect was mislocalisation on BALL frames, which P1-P6 only saw indirectly:
    # recall can rise while the track gets less accurate. A ghost lands on a
    # no-ball frame and scores `fp`; a wrong position on a ball frame scores
    # `wrong`, and that is the column this bar reads.
    w_rise = [(name, n['wrong'] - o['wrong']) for name, _, o, n in rows
              if n['wrong'] > o['wrong']]
    print(f"P7 wrong      {tot['w_off']} -> {tot['w_on']} ({dw:+d}) pooled; "
          f"per-clip rises: {len(w_rise)} of {len(rows)}"
          f"      GATE REQUIRES 0 rises on any clip")
    for name, d in w_rise:
        print(f"   {name:<22}{d:+d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
