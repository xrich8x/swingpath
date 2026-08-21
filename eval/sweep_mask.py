"""THE GATE for a candidate line mask: the full 20-clip court eval.

eval/score_truth.py is a proxy - it asks whether the criteria RECOGNISE a court
a human placed. This asks the product question: with the mask actually driving
the pipeline, how many clips auto-calibrate and is any accepted court wrong?
The seed-grid sweep is why both are needed: it improved on every mechanical
prediction and still failed here by accepting wrong courts.

The candidate replaces `calibration.line_ridge_mask` wholesale, which is what
shipping it would mean - so _precompute, _clay_mask, snap_to_lines, verify_court
and line_distance_map all see it, not just the scorer.

PRE-REGISTERED GATE (unchanged from the grid sweep):
  accepted >= 11 of 20 AND zero accepted court over 20 px from the human clicks.
"""
import sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend")); sys.path.insert(0, str(REPO / "eval"))
import numpy as np
from swingvision import calibration
import masks_candidate as mc
from run_eval import load_gold, score_clip, gold_clips, WRONG_PX

SHIPPED = calibration.line_ridge_mask

def wrap(**kw):
    """Signature-compatible with line_ridge_mask(frame, tau=, sat_max=) so the
    callers that pass those kwargs (notably _clay_mask) keep working."""
    def f(frame, tau=None, sat_max=None):
        return mc.fused_mask(frame, calibration, **kw)
    return f

def routed():
    """Surface-routed: clay gets the hue-agnostic mask, everything else is
    UNTOUCHED. The previous arms swapped the mask globally, which is why each
    bought clay and paid for it on hard courts."""
    def f(frame, tau=None, sat_max=None):
        if tau is not None or sat_max is not None:      # an internal call
            return SHIPPED(frame, tau=tau or 9, sat_max=sat_max or 90)
        return mc.routed_mask(frame, calibration, SHIPPED)
    return f

def routed_fused(**kw):
    """Surface-routed with the FUSED mask on clay. Routing to the EXISTING
    _clay_mask was measured identical to baseline (gained none, lost none) -
    the pipeline already falls back to it, so routing adds nothing there. The
    fused mask is what actually rescued clay in the global arms; this gives it
    to clay ONLY, leaving every other surface untouched."""
    def f(frame, tau=None, sat_max=None):
        if tau is not None or sat_max is not None:
            return SHIPPED(frame, tau=tau or 9, sat_max=sat_max or 90)
        if mc.surface_of(frame) == "clay":
            return mc.fused_mask(frame, calibration, **kw)
        return SHIPPED(frame)
    return f

ARMS = {"baseline": None,
        "routed_clay_chroma": routed_fused(clahe=False),
        "routed_clay_clahe":  routed_fused(use_chroma=False),
        }
out = {}
for name, fn in ARMS.items():
    calibration.line_ridge_mask = SHIPPED if fn is None else fn
    acc, errs, wrong = [], [], []
    for c in gold_clips():
        frames, gt = load_gold(c, 8)
        if not frames:
            continue
        _r, s = score_clip(c, frames, gt, overlays=False)
        if s["accepted"]:
            acc.append(c)
            if s["err"] is not None:
                errs.append(s["err"])
                if s["err"] > WRONG_PX:
                    wrong.append((c, round(s["err"], 1)))
    ok = len(acc) >= 11 and not wrong
    print(f"{name:12s} accepted {len(acc):2d}/20  median {np.median(errs):5.1f} px  "
          f"range {min(errs):.1f}-{max(errs):.1f}  WRONG {wrong if wrong else 0}  "
          f"-> {'PASS' if ok else 'FAILS GATE'}", flush=True)
    out[name] = {"n": len(acc), "accepted": sorted(acc), "median": float(np.median(errs)),
                 "wrong": wrong, "gate_pass": bool(ok)}
calibration.line_ridge_mask = SHIPPED
Path("data/output/court_mask_sweep.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
b = set(out["baseline"]["accepted"])
for n in ARMS:
    if n == "baseline":
        continue
    a = set(out[n]["accepted"])
    print(f"\n{n}: gained {sorted(a-b) or 'none'}   lost {sorted(b-a) or 'none'}")
