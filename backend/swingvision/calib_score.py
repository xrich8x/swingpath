"""Composite calibration score - a MIX of every check this project built, not a gate.

Motivation, in one paragraph. Five autonomous accept/reject gates have failed here
(`verify_court` coverage, the camera-height screen, fit residual, the net-post height
reference, the fitted-hfov window). Each failed for a DIFFERENT reason: coverage fails on
line CONTRAST, hfov false-rejects BROADCAST footage, camera height is a mount-TYPE test,
residual is fooled by a self-consistent wrong court (trap T23). Decorrelated failure modes
are exactly the condition under which a mix beats its members - a wrong court has to fool
all of them at once.

Two design rules this module is built on, both load-bearing:

1. **Coherence, not thresholds.** The single most useful indicator here is not "the lens is
   narrow" - a real broadcast telephoto is narrow and correct. It is "the lens is narrow AND
   the camera is on a low amateur mount", which no real camera does. Depth-anisotropic
   compression - the corruption every shipped gate is blind to - produces exactly that
   contradiction, and broadcast footage does not. Same shape for the net tape: a
   tower-sized far-baseline/net-tape clearance next to a 1.6 m fitted height is a
   contradiction, not a reading.

2. **Almost every threshold comes from somewhere else**, and the one that does not is
   flagged as such. `HFOV_AMATEUR_FLOOR` is the repo's stated
   60-90 deg amateur-lens prior. `MOUNT_CEILING_M` / `MOUNT_FLOOR_M` are the plausible
   amateur-mount band. `TAPE_DISAGREE_PCT` is the pre-registered 10% bar from the net-tape
   height work. `CLEARANCE_TOWER_PX720` is read off the derivation table in
   `docs/evidence/live-setup-criterion.md` (4.00 m mount -> +43 px at 720p). `verify_court`'s
   bar is `verify_court`'s. The exceptions - `RESIDUAL_REFUSE_PX`, `WEIGHTS` and `FLAG_AT` -
   were chosen on a TRAIN split of clips and are labelled that way at their definition; the
   numbers reported in the evidence file come from a HELD-OUT split the rule never saw.

THIS IS NOT A GATE. It returns a score and a list of human-readable reasons for the person
confirming their setup. Whether it ever refuses anybody's footage is a product decision that
this module deliberately does not make.

Evidence: `docs/evidence/composite-calibration-score.md`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

# --- constants, each imported from an existing decision (see module docstring) ---
RESIDUAL_REFUSE_PX = 25.0
"""Px between the clicked quad and the nearest physically possible camera view.
CHOSEN ON THE TRAIN SPLIT (max believed-correct TRAIN baseline residual was 19.1 px);
`courtfit._cam_refine`'s own pre-existing REFUSE bound is 40 px and is reported as a
sensitivity variant in the evidence file. This is the ONE constant here fitted to data,
and it is fitted to TRAIN only."""

HFOV_AMATEUR_FLOOR = 60.0
"""Floor of this repo's stated 60-90 deg amateur-lens prior."""

MOUNT_FLOOR_M = 1.0
MOUNT_CEILING_M = 4.0
"""Plausible amateur mount band: a phone tripod starts near 1 m; a fence clamp tops out
near 4 m. ABOVE the ceiling is not an error - it is broadcast, which is a different and
valid mount type, so height alone never flags on its own."""

MOUNT_ABSURD_M = 15.0
"""Above any real tennis camera gantry. Below MOUNT_FLOOR_M or above this, the FIT has
failed, not the mount."""

TAPE_DISAGREE_PCT = 10.0
"""Pre-registered agreement bar from the net-tape-height work (`net-tape-height...` row in
docs/STATE.md): the tape-implied camera height must land within 10% of the fitted height."""

CLEARANCE_TOWER_PX720 = 43.0
"""Net-tape clearance at 720p implied by a 4.00 m mount, read off the derivation table in
docs/evidence/live-setup-criterion.md (1.40 -> -15, 2.50 -> +10, 3.00 -> +21, 4.00 -> +43)."""

WEIGHTS = {"lines": 0.5, "tape_height": 0.5}
"""Per-indicator weight; anything not listed weighs 1.0. The two half-weight members are
exactly the two that false-flag believed-correct calibrations on their own: `lines`
(`verify_court`) reads line CONTRAST and three real clips here have paint too faint for it,
and `tape_height` already scored 13/15 - two known disagreements - in the net-tape-height
work. Half a vote each means neither can flag alone, but either can confirm another.
CHOSEN ON THE TRAIN SPLIT."""

FLAG_AT = 1.0
"""Composite weight at which the score reads FLAG. CHOSEN ON THE TRAIN SPLIT by a
criterion declared before the held-out split was looked at: maximise pooled TRAIN
detection subject to ZERO TRAIN false flags, tie-break toward the simpler rule."""


@dataclass
class Indicator:
    name: str
    fired: bool
    weight: float
    reason: str = ""


@dataclass
class CalibScore:
    """`score` is the summed weight of the indicators that fired. `flag` is
    `score >= FLAG_AT`. `reasons` is what to show a human."""
    score: float
    flag: bool
    indicators: list = field(default_factory=list)
    reasons: list = field(default_factory=list)

    @property
    def fired(self) -> list:
        return [i.name for i in self.indicators if i.fired]


def _get(sig, key) -> Optional[float]:
    v = sig.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def composite_score(sig: dict, *, flag_at: float = FLAG_AT) -> CalibScore:
    """Score one calibration from an already-computed signal dict.

    Expected keys (all optional - a missing signal simply cannot fire, which is the
    honest behaviour when e.g. the net tape refuses or no player is standing on court):

      coverage, visible_frac, centrality  - `calibration.court_line_coverage` / `court_centrality`
      residual_px, cam_h_m, hfov_deg      - `courtfit.cam_fit_quad`
      clear_px720                         - `calibration.net_tape_clearance().margin_px_720`
      tape_delta_pct                      - `tools/net_tape_height.measure_tape_height`
      feet_max_y_m                        - deepest player-foot court-y, metres (see docs)
    """
    ind: list = []

    # I1 LINES - the shipped ground-plane gate, verbatim. Catches isotropic scale and
    # gross shift. Fails on low-contrast paint, which is why it is one vote, not the vote.
    cov, vis, cen = _get(sig, "coverage"), _get(sig, "visible_frac"), _get(sig, "centrality")
    if cov is not None and vis is not None and cen is not None:
        bad = cov < 0.40 or vis < 0.30 or cen < 0.70
        why = []
        if cov < 0.40:
            why.append(f"only {cov:.0%} of the projected court lines land on real paint")
        if vis < 0.30:
            why.append(f"only {vis:.0%} of the court is inside the frame")
        if cen < 0.70:
            why.append("the court is off to one side of the frame")
        ind.append(Indicator("lines", bad, 1.0,
                             "; ".join(why) if bad else ""))

    # I2 SELF-CONSISTENCY - the corners are not a shape any real camera makes.
    res = _get(sig, "residual_px")
    if res is not None:
        ind.append(Indicator("residual", res > RESIDUAL_REFUSE_PX, 1.0,
                             f"the four corners are {res:.0f} px from any physically "
                             f"possible camera view of a tennis court"
                             if res > RESIDUAL_REFUSE_PX else ""))

    # I3 INCOHERENT LENS - the depth-compression signature, and the reason the fitted-hfov
    # window failed alone. Narrow lens + HIGH mount is a broadcast camera and is correct;
    # narrow lens + LOW mount is a court that has been squashed in depth.
    hf, ch = _get(sig, "hfov_deg"), _get(sig, "cam_h_m")
    if hf is not None and ch is not None:
        bad = hf < HFOV_AMATEUR_FLOOR and ch < MOUNT_CEILING_M
        ind.append(Indicator("lens_coherence", bad, 1.0,
                             f"fitted lens is implausibly narrow ({hf:.0f} deg) for a "
                             f"{ch:.1f} m mount - the far half of the court looks "
                             f"compressed toward the net"
                             if bad else ""))

    # I4 FIT FAILURE - a height no camera is at. Deliberately NOT a mount-plausibility
    # test: high mounts are broadcast, which is valid.
    if ch is not None:
        bad = ch < MOUNT_FLOOR_M or ch > MOUNT_ABSURD_M
        ind.append(Indicator("camera_height", bad, 1.0,
                             f"fitted camera height {ch:.1f} m is not a place a camera can be"
                             if bad else ""))

    # I5 NET GEOMETRY vs FITTED HEIGHT - two readings of the same mount that must agree.
    clr = _get(sig, "clear_px720")
    if clr is not None and ch is not None:
        bad = clr > CLEARANCE_TOWER_PX720 and ch < MOUNT_CEILING_M
        ind.append(Indicator("net_coherence", bad, 1.0,
                             f"the far baseline sits {clr:.0f} px above the net tape, which "
                             f"needs a mount well above 4 m, but the corners fit a "
                             f"{ch:.1f} m camera"
                             if bad else ""))

    # I6 OFF-PLANE TAPE - the one reading that leaves the ground plane. Absent (refused)
    # far more often than it fires; absence is not evidence either way.
    td = _get(sig, "tape_delta_pct")
    if td is not None:
        bad = abs(td) > TAPE_DISAGREE_PCT
        ind.append(Indicator("tape_height", bad, 1.0,
                             f"the net tape puts the camera {td:+.0f}% away from the height "
                             f"the court corners give"
                             if bad else ""))

    # I7 PLAYER FEET - an object standing ON the court. A player whose feet map well beyond
    # the far baseline means the court model is shorter than the real court.
    fy = _get(sig, "feet_max_y_m")
    if fy is not None:
        bad = fy > 27.0 or fy < -3.5
        ind.append(Indicator("player_feet", bad, 1.0,
                             f"a player's feet land at court-y {fy:.1f} m, off the "
                             f"23.77 m court by more than any run-back"
                             if bad else ""))

    for i in ind:
        i.weight = WEIGHTS.get(i.name, 1.0)
    score = sum(i.weight for i in ind if i.fired)
    reasons = [i.reason for i in ind if i.fired and i.reason]
    return CalibScore(score=score, flag=score >= flag_at, indicators=ind, reasons=reasons)


def explain(sc: CalibScore) -> str:
    """One human sentence, for the setup screen."""
    if not sc.reasons:
        return "Every check agrees on this court."
    return "This court may be wrong: " + "; ".join(sc.reasons) + "."
