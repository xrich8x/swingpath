"""Measure a change to courtfit.COARSE_GRID against the court gold set.

PRE-REGISTERED GATE, fixed before the first run:
  * REGRESSION BAR - accepted must stay >= 11 of 20, and ZERO accepted court may
    exceed 20 px from the human clicks. Buying recall with a wrong court FAILS.
  * WIN - accepted > 11 with that precision intact.

Motivation (data/output/court_why_it_fails.md): the shipped grid searches
far-half-width 0.20-0.42 of frame width and near-half-width 0.40-0.72, while all
30 human-measured courts sit at wf 0.09-0.22 and wn 0.40-0.85. The grid is
searching poses that do not occur and cannot reach ones that do.
"""
import sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend")); sys.path.insert(0, str(REPO / "eval"))
import numpy as np
from swingvision import courtfit as cf
from run_eval import load_gold, score_clip, gold_clips, WRONG_PX

SHIPPED = cf.COARSE_GRID
ARMS = {
 "baseline": SHIPPED,
 "A_wf":  (SHIPPED[0], SHIPPED[1], SHIPPED[2], SHIPPED[3], [0.08,0.13,0.18,0.23]),
 "B_wn":  (SHIPPED[0], SHIPPED[1], SHIPPED[2], [0.40,0.55,0.70,0.86], SHIPPED[4]),
 "C_both":(SHIPPED[0], SHIPPED[1], SHIPPED[2], [0.40,0.55,0.70,0.86], [0.08,0.13,0.18,0.23]),
}
out={}
for name, grid in ARMS.items():
    cf.COARSE_GRID = grid
    acc=[]; errs=[]; wrong=[]; per={}
    for c in gold_clips():
        frames, gt = load_gold(c, 8)
        if not frames: continue
        _r, s = score_clip(c, frames, gt, overlays=False)
        per[c] = {"votes": s["votes"], "accepted": s["accepted"], "err": s["err"]}
        if s["accepted"]:
            acc.append(c)
            if s["err"] is not None:
                errs.append(s["err"])
                if s["err"] > WRONG_PX: wrong.append((c, round(s["err"],1)))
    ok = len(acc) >= 11 and not wrong
    print(f"{name:9s} accepted {len(acc):2d}/20  median {np.median(errs):5.1f} px  "
          f"range {min(errs):.1f}-{max(errs):.1f}  WRONG {wrong if wrong else 0}  "
          f"-> {'PASS' if ok else 'FAILS GATE'}", flush=True)
    out[name]={"accepted":sorted(acc),"n":len(acc),"median":float(np.median(errs)),
               "wrong":wrong,"gate_pass":bool(ok),"per_clip":per}
cf.COARSE_GRID = SHIPPED
Path("data/output/court_grid_sweep.json").write_text(json.dumps(out,indent=1),encoding="utf-8")
b=set(out["baseline"]["accepted"])
for n in ("A_wf","B_wn","C_both"):
    a=set(out[n]["accepted"])
    print(f"\n{n}: gained {sorted(a-b) or 'none'}   lost {sorted(b-a) or 'none'}")
