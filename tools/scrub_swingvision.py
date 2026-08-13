"""scrub_swingvision.py — keep SwingVision's rendered output out of training.

THE RULE (user instruction, 2026-08-13): do not train on SwingVision information.

Five clips in the training pool carry a burned-in SwingVision overlay — the
mini-court radar, the stroke + speed readout, the score panel and the watermark,
which is a literal yellow tennis ball. That is another system's OUTPUT sitting in
our INPUT, and it is 11,187 of 41,390 labels (27% of the pool).

Two distinct problems, and they need different fixes:

  1. 56 positive labels land INSIDE one of those graphics. Those are not "a ball
     the tracker found near an overlay" — they are the pseudo-labeller locking
     onto SwingVision's watermark ball and us teaching that it is a tennis ball.
     They are DROPPED.
  2. The other 11,131 labels are on real balls, on frames that happen to carry
     the overlay. Throwing those away would cost a quarter of the pool for no
     reason. The graphics are PAINTED OUT instead.

NON-DESTRUCTIVE BY DESIGN. This writes `swingvision_mask.json` into each affected
dataset directory; it never rewrites a frame. `train_ballnet.BallWindows` reads
that file, paints the boxes as it loads, and drops the in-box labels — so the
scrub is applied at every training run rather than baked once into JPEGs nobody
re-checks. `train_ballnet.assert_no_swingvision_leak` then REFUSES to start if a
directory's source clip is known to carry SwingVision graphics and has no mask
file, which is the same structural shape as the gold-leak guard: the rule is
enforced by the trainer, not remembered by the person running it.

Boxes come from data/hud_masks.json, which was verified by eye in Session J on
19 boxes x 4 real frames. Only clips whose boxes are SwingVision's are touched —
a broadcast score bug on col_hard_zheng is not SwingVision's output and is left
alone.

  py tools/scrub_swingvision.py                 # report only
  py tools/scrub_swingvision.py --write         # write the mask files
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MASKS = REPO / "data" / "hud_masks.json"
DATASET = REPO / "data" / "ball_dataset"

#: Substrings identifying a box as SwingVision's own rendered output. A generic
#: broadcast score panel is NOT SwingVision and is deliberately not matched.
SV_MARKERS = ("swingvision", "mini-court", "stroke + speed")

#: Same fill as tools/mask_hud.py, so a frame painted for training looks like a
#: frame painted for the far-court label queue. Two different greys would be two
#: different distributions for no reason.
FILL = (60, 60, 60)


def sv_clips() -> dict[str, dict]:
    """clip stem -> {src_wh, boxes} for clips carrying SwingVision graphics.

    A clip qualifies if ANY of its boxes is SwingVision's. Once it does, ALL of
    its recorded boxes are masked: on a SwingVision export the score panel is
    SwingVision's too, and the boxes were verified together.
    """
    blob = json.loads(MASKS.read_text(encoding="utf-8"))["clips"]
    out = {}
    for clip, v in blob.items():
        boxes = v.get("boxes") or []
        if any(any(m in (b.get("what") or "").lower() for m in SV_MARKERS)
               for b in boxes):
            out[clip[:-4] if clip.endswith(".mp4") else clip] = {
                "src_wh": v["src_wh"], "boxes": boxes}
    return out


def _in_any(x, y, boxes) -> bool:
    return any(b["x"] <= x <= b["x"] + b["w"] and b["y"] <= y <= b["y"] + b["h"]
               for b in boxes)


def scan(write: bool) -> int:
    clips = sv_clips()
    print(f"{len(clips)} clip(s) in data/hud_masks.json carry SwingVision graphics\n")
    hdr = f"{'dataset dir':<24}{'labels':>8}{'dropped':>9}{'negs hit':>10}{'boxes':>7}"
    print(hdr); print("-" * len(hdr))
    tot_lab = tot_drop = 0
    for stem, v in sorted(clips.items()):
        d = DATASET / f"yt_{stem}"
        if not d.is_dir():
            print(f"{'yt_'+stem:<24}   (no training directory — nothing to scrub)")
            continue
        lp = d / "labels.json"
        meta = json.loads(lp.read_text(encoding="utf-8"))
        labels = meta["labels"]
        sw, sh = v["src_wh"]
        # Labels are stored in NETWORK space (512x288), boxes in SOURCE space.
        mx = max(p[0] for p in labels.values()); my = max(p[1] for p in labels.values())
        lw, lh = (512, 288) if (mx <= 512 and my <= 288) else (sw, sh)
        drop = sorted(int(k) for k, (x, y) in labels.items()
                      if _in_any(x * sw / lw, y * sh / lh, v["boxes"]))
        # Negatives inside a painted box teach nothing — the region is flat grey
        # at train time, so a "there is no ball here" example there is a free
        # sample of a constant. Reported, and dropped alongside.
        negs = [int(i) for i in (meta.get("negatives") or [])]
        lneg = {}
        lp2 = d / "localised_negatives.json"
        if lp2.is_file():
            lneg = (json.loads(lp2.read_text(encoding="utf-8"))
                    .get("localised_negatives") or {})
        nhit = sum(1 for pts in lneg.values()
                   for (x, y) in pts if _in_any(x * sw / lw, y * sh / lh, v["boxes"]))
        tot_lab += len(labels); tot_drop += len(drop)
        print(f"{'yt_'+stem:<24}{len(labels):>8}{len(drop):>9}{nhit:>10}{len(v['boxes']):>7}")

        if write:
            # Boxes are written in NETWORK space too, so the loader paints without
            # needing to know the source resolution.
            boxes_px = [{"x": round(b["x"] * lw / sw), "y": round(b["y"] * lh / sh),
                         "w": round(b["w"] * lw / sw), "h": round(b["h"] * lh / sh),
                         "what": b.get("what", "")} for b in v["boxes"]]
            (d / "swingvision_mask.json").write_text(json.dumps({
                "tool": "scrub_swingvision.py",
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "why": "user instruction 2026-08-13: do not train on SwingVision "
                       "information. Boxes are painted at load; drop_labels are "
                       "positives that landed inside a graphic.",
                "source": "data/hud_masks.json",
                "frame_wh": [lw, lh], "src_wh": [sw, sh],
                "fill": list(FILL),
                "boxes": boxes_px,
                "drop_labels": drop,
                "n_labels": len(labels),
            }, indent=1), encoding="utf-8")
    print("-" * len(hdr))
    print(f"{'TOTAL':<24}{tot_lab:>8}{tot_drop:>9}")
    if write:
        print(f"\nwrote swingvision_mask.json into {len(clips)} directory(ies).")
        print("train_ballnet applies them at load and refuses to run without them.")
    else:
        print("\nreport only — pass --write to create the mask files.")
    return tot_drop


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    scan(args.write)


if __name__ == "__main__":
    main()
