"""_goldset.py — the gold clip registry, in one place.

WHY THIS EXISTS
---------------
Seven tools under tools/ each hardcoded their own table of gold clips, in four
different shapes: a dict of name->video, a list of (name, video, calibration)
tuples, a dict of name->(video, calibration, labels), and a two-clip legacy
subset. They are all projections of ONE fact — six hand-labelled clips, three of
which have a calibration — and they drifted: adding a gold clip meant editing up
to seven literals, and a tool that missed the edit would silently score on fewer
clips than the one next to it while both printed "pooled".

Nothing here changes what any tool measures. The registry reproduces every
historical table exactly, including ORDER (which matters: pooled numbers are
accumulated in iteration order, and the committed evidence JSONs record per-clip
blocks in that order). tests/test_goldset_registry.py pins the derived tables
against the literals they replaced.

ALSO SHARED, because two evals written the same week duplicated them verbatim:
the gold-label readers, the "seek to these frames and cache the result" loop that
every criterion eval needs, and the pass/fail gate reporting.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The four court corners every homography in this project is solved from.
CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


@dataclass(frozen=True)
class GoldClip:
    name: str
    video: str
    calib: str | None      # None = no calibration, so no geometric far-court band
    labels: str

    @property
    def video_path(self) -> Path:
        return REPO / self.video

    @property
    def has_calibration(self) -> bool:
        return self.calib is not None


def _clip(name: str, calib: bool) -> GoldClip:
    return GoldClip(name=name,
                    video=f"data/{name}.mp4",
                    calib=f"data/{name}_pts.json" if calib else None,
                    labels=f"data/gold/{name}.labels.json")


def _trimmed(stem: str) -> GoldClip:
    """A clip promoted to gold from the trimmed training pool (2026-08-11).

    Different layout from the originals and deliberately not forced into
    `_clip`'s: the video lives in data/gold_clips (kept out of data/ so nothing
    picks it up as training footage), and the calibration is keyed on the CLIP
    stem while the gold set is keyed on `gold_<stem>`.
    """
    return GoldClip(name=f"gold_{stem}",
                    video=f"data/gold_clips/{stem}.mp4",
                    calib=f"data/{stem}_pts.json",
                    labels=f"data/gold/gold_{stem}.labels.json")


#: The six clips every number published before 2026-08-11 was measured against.
#: Kept as a named set so a historical figure can still be reproduced exactly
#: after the benchmark grew — see tests/test_goldset_registry.py.
LEGACY_SIX = ("am_hard_utr", "gold_shell", "gold_clay", "gold_am",
              "yt_rally2", "yt_match40")

# CANONICAL ORDER. Every historical table is a prefix-preserving subsequence of
# this, so deriving from it reproduces each tool's iteration order exactly.
# The four appended clips are NEW — every pooled number moves when they are
# included, and a figure quoted from before that date is not comparable to one
# quoted after it without saying which set it used.
GOLD: dict[str, GoldClip] = {c.name: c for c in (
    _clip("am_hard_utr", calib=True),    # 1080p, 1.74 m mount — the primary hard clip
    _clip("gold_shell", calib=False),    # broadcast wide; the only clip where pose finds both players
    _clip("gold_clay", calib=False),
    _clip("gold_am", calib=False),
    _clip("yt_rally2", calib=True),
    _clip("yt_match40", calib=True),
    # 2026-08-11: four venues at 2.88-3.35 m. The set previously had ONE clip
    # in that band (yt_rally2, 3.30 m) and could say almost nothing about the
    # height regime that measures best.
    _trimmed("UHf0LeMU2pg"),             # 3.35 m indoor, no overlay
    _trimmed("sAjkpeRq4P4"),             # 3.33 m outdoor clay
    _trimmed("uR5q2cSM6AY"),             # 3.32 m indoor, full SwingVision overlay
    _trimmed("L73ep7JHiJ4"),             # 2.88 m indoor
)}

#: The six-clip set as it stood before the 2026-08-11 additions.
LEGACY: dict[str, GoldClip] = {k: GOLD[k] for k in LEGACY_SIX}

#: the three clips with a calibration — the only ones with a geometric far band
CALIBRATED: dict[str, GoldClip] = {k: v for k, v in GOLD.items() if v.has_calibration}

#: BLIND HOLDOUT (2026-08-16, review finding P0-1). tune_smoother.py and
#: tune_suppress.py had been sweeping max_gap_s / suppression thresholds /
#: score_thresh directly against the same 1851 clicks that also produce every
#: headline recall/false-fire number — the gold set was a validation set wearing
#: a test set's reputation. These two clips are withdrawn from both tuning
#: tools' --clip choices from this commit forward, one indoor + one outdoor so
#: the eventual release-candidate check still spans surfaces. This choice is
#: ONE-WAY, same discipline as data/gold/court_split.json's TEST/TRAIN split:
#: do not add a clip back to the tunable pool once a sweep has looked at it.
#: They remain fully visible to eval_gold.py / eval_detector_gold.py /
#: eval_model_filters.py — the rule is about what CHOSE a parameter value, not
#: about what gets measured and reported.
HOLDOUT: frozenset[str] = frozenset({"gold_UHf0LeMU2pg", "gold_sAjkpeRq4P4"})


def videos() -> dict[str, str]:
    """name -> video. (eval_pose_proximity, eval_racquet_negation)"""
    return {k: v.video for k, v in GOLD.items()}


def name_video_calib() -> list[tuple[str, str, str | None]]:
    """[(name, video, calib_or_None)] over all six. (eval_detector_gold)"""
    return [(c.name, c.video, c.calib) for c in GOLD.values()]


def calibrated_triples() -> list[tuple[str, str, str]]:
    """[(name, video, calib)] over the three calibrated clips. (eval_court_gate)"""
    return [(c.name, c.video, c.calib) for c in CALIBRATED.values()]


def calibrated_map() -> dict[str, tuple[str, str, str]]:
    """name -> (video, calib, labels), calibrated only. (eval_model_filters, tune_suppress)"""
    return {c.name: (c.video, c.calib, c.labels) for c in CALIBRATED.values()}


def tunable_calibrated_map() -> dict[str, tuple[str, str, str]]:
    """calibrated_map() minus HOLDOUT. The only clip table a tune_*.py sweep may
    offer as a --clip choice — see HOLDOUT for why. Reporting tools
    (eval_model_filters, eval_gold, eval_detector_gold) keep using
    calibrated_map()/GOLD directly; they measure a fixed config, they don't pick one."""
    return {k: v for k, v in calibrated_map().items() if k not in HOLDOUT}


# --------------------------------------------------------------------------
# Gold labels. A frame is a BALL frame only when a human clicked a position on
# it; "unsure" is neither ball nor no-ball and is excluded from both populations,
# which is why these are two functions and not one with a flag.
# --------------------------------------------------------------------------

def _labels(clip: str) -> dict:
    return json.loads((REPO / GOLD[clip].labels).read_text(encoding="utf-8"))["labels"]


def ball_frames(clip: str) -> dict[int, tuple[float, float]]:
    """{frame: (x, y)} for every frame a human clicked a real ball on."""
    return {int(f): (float(v["x"]), float(v["y"]))
            for f, v in _labels(clip).items()
            if v.get("ball") is True and v.get("x") is not None}


def noball_frames(clip: str) -> list[int]:
    """Frames a human marked as having no ball. 'unsure' is excluded."""
    return sorted(int(f) for f, v in _labels(clip).items() if v.get("ball") is False)


def load_H(clip: str):
    """Homography from the clip's committed calibration, or None if uncalibrated."""
    c = GOLD[clip]
    if not c.calib or not (REPO / c.calib).is_file():
        return None
    import sys
    sys.path.insert(0, str(REPO / "backend"))
    from swingvision import calibration, court
    kp = json.loads((REPO / c.calib).read_text(encoding="utf-8"))
    return calibration.compute_homography([court.LANDMARKS[n] for n in CORNERS],
                                          [kp[n] for n in CORNERS])


# --------------------------------------------------------------------------
# Shared eval scaffolding
# --------------------------------------------------------------------------

def res_scale(frame_h: int) -> float:
    """Pixel thresholds in this repo are tuned at 720p and MUST scale — an
    unscaled constant silently deleted real balls at 1080p twice (CLAUDE.md,
    E6 part 2). Exact no-op at 720p."""
    return frame_h / 720.0


def frames_for(clip: str, extra_frames=()) -> set[int]:
    """Every frame an eval needs: the human ball clicks plus whatever else."""
    return set(ball_frames(clip)) | set(extra_frames)


def collect_over_frames(clip, frames, fn, cache_path=None, cache_key=None,
                        label="", progress_every=200):
    """Apply `fn(image) -> jsonable` to specific frames, with a cache.

    Seeks rather than decoding whole clips: the frames wanted are scattered over
    tens of thousands, so seeking is the cheap direction. Mirrors the pattern in
    inspect_false_locks.raw_locks. Returns (results_by_frame, (w, h)).

    The cache is keyed so a run under different settings cannot silently reuse
    another run's results — the stale-cache trap this repo has been bitten by.
    """
    import cv2

    if cache_path and Path(cache_path).is_file():
        blob = json.loads(Path(cache_path).read_text(encoding="utf-8"))
        if blob.get("clip") == clip and blob.get("key") == cache_key:
            return ({int(k): v for k, v in blob["data"].items()},
                    tuple(blob["frame_wh"]))

    cap = cv2.VideoCapture(str(GOLD[clip].video_path))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {GOLD[clip].video}")
    frame_wh = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    out = {}
    ordered = sorted(frames)
    for n, f in enumerate(ordered):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, im = cap.read()
        if not ok:
            continue
        out[f] = fn(im)
        if progress_every and n % progress_every == 0:
            print(f"    {label or clip}: {n}/{len(ordered)}", flush=True)
    cap.release()

    if cache_path:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(json.dumps(
            {"clip": clip, "key": cache_key, "frame_wh": list(frame_wh),
             "data": out}), encoding="utf-8")
    return out, frame_wh


def rate_at(values, threshold) -> float:
    """Percent of `values` at or under `threshold`. Empty -> 0.0."""
    return 100.0 * sum(1 for v in values if v <= threshold) / max(len(values), 1)


def report_gate(rows, catch_key, collateral_key, catch_gate, collateral_gate,
                label="") -> list:
    """Print the pass/fail verdict for a swept criterion and return the winners.

    Every criterion eval in this repo pre-registers a gate and reports against it
    rather than picking the best row after the fact — that ordering is what killed
    the score-threshold change in Session F, where the ghost-ball gate would have
    passed and only the recall gate caught it.
    """
    winners = [r for r in rows if r.get("passes_gate")]
    print("\n" + "=" * 76)
    if winners:
        best = max(winners, key=lambda r: r[catch_key])
        print(f"GATE PASSED by {len(winners)} configuration(s){label}. Best: "
              f"catch {best[catch_key]}% at collateral {best[collateral_key]}%")
    else:
        print(f"GATE FAILED{label}: nothing reaches catch >= {catch_gate}% "
              f"at collateral <= {collateral_gate}%.")
    print("=" * 76)
    return winners
