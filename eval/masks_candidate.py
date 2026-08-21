"""eval/masks_candidate.py - CANDIDATE line masks. NOTHING HERE SHIPS.

Lives in eval/ deliberately: `backend/swingvision/` is the product, and a mask
variant does not belong there until it has cleared a gate on
eval/score_truth.py. Import path for experiments only.

The problem these address, measured (data/output/court_truth_margin_*.json):

  * the shipped white mask `line_ridge_mask` scores the HUMAN's own court at
    g = 0.000 on am_lk35 and am_rally32short and 0.066 on am_wingfield_clay -
    all clay. Not "low": zero. Its `sat < 90` test throws clay's whitish-on-
    orange paint away, and its luminance ridge fires on foliage instead.
  * the hue-agnostic `_clay_mask` rescues exactly those (0.000 -> 0.212, 0.000
    -> 0.199, 0.066 -> 0.201) and COSTS elsewhere: am_classB 0.346 -> 0.164 and
    its margin flips to negative, am_beginner 0.536 -> 0.404, am_grass1 0.491
    -> 0.367.

Neither dominates, so the answer is to FUSE the channels rather than pick one -
luminance structure where luminance carries the line, chroma where it does not.
"""

from __future__ import annotations

import numpy as np


def _ridge(chan, tau, d):
    """Structure filter: brighter than BOTH neighbours at +-d, horizontally OR
    vertically. The same test line_ridge_mask uses, lifted so it can run on any
    single channel rather than only on grey."""
    import cv2

    c = chan.astype(np.int16)
    out = np.zeros(c.shape, np.uint8)
    for ax in (0, 1):
        a = np.roll(c, d, axis=ax)
        b = np.roll(c, -d, axis=ax)
        hit = (c - a >= tau) & (c - b >= tau)
        if ax == 0:
            hit[:d] = hit[-d:] = False
        else:
            hit[:, :d] = hit[:, -d:] = False
        out |= hit.astype(np.uint8)
    return out * 255


def fused_mask(frame, calibration=None, *, tau_l=10, tau_c=6, clahe=True,
               use_chroma=True, structure_clean=True):
    """Local-contrast luminance ridge OR chroma ridge, then structure-cleaned.

    L*  after CLAHE  - local contrast normalisation, so a low-contrast pale
                       (shell) surface is judged against its own neighbourhood
                       rather than a global constant.
    chroma           - distance in the a*/b* plane from a heavily blurred version
                       of itself, i.e. "how much does this pixel's colour differ
                       from the surface around it". On clay the line is a chroma
                       edge even when it is barely a luminance edge; on a hard
                       court this channel is near-silent and contributes nothing.
    OR, not AND      - a line only has to be visible in ONE channel. Requiring
                       both would fail exactly the surfaces this exists for.

    structure_clean keeps only pixels lying on a long straight segment, which is
    what makes a permissive mask usable on speckled clay (the trick `_clay_mask`
    already uses)."""
    import cv2

    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    L, A, B = lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]
    if clahe:
        L = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(L)

    w = frame.shape[1]
    d = max(2, int(round(w * 0.006)))
    m = _ridge(L, tau_l, d)

    if use_chroma:
        k = max(3, (d * 8) | 1)
        ab = np.stack([A, B], axis=2).astype(np.float32)
        bg = cv2.GaussianBlur(ab, (k, k), 0)
        chroma = np.linalg.norm(ab - bg, axis=2)
        chroma = cv2.normalize(chroma, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        m = m | _ridge(chroma, tau_c, d)

    if structure_clean:
        segs = cv2.HoughLinesP(m, 1, np.pi / 180, threshold=50,
                               minLineLength=max(40, int(w * 0.08)), maxLineGap=14)
        clean = np.zeros_like(m)
        if segs is not None:
            for x1, y1, x2, y2 in segs[:, 0]:
                cv2.line(clean, (int(x1), int(y1)), (int(x2), int(y2)), 255, 2)
        m = clean
    return m


VARIANTS = {
    "fused":        dict(),
    # Ablation showed neither chroma nor CLAHE is the active ingredient, so strip
    # BOTH: a plain L* ridge with no saturation gate, structure-cleaned. If this
    # matches the full fusion then the win was never chroma - it is dropping
    # line_ridge_mask's `sat < 90` test and keeping only long straight segments.
    "plain_L":      dict(use_chroma=False, clahe=False),
    "plain_L_raw":  dict(use_chroma=False, clahe=False, structure_clean=False),
    "fused_nochroma": dict(use_chroma=False),
    "fused_noclahe":  dict(clahe=False),
    "fused_raw":      dict(structure_clean=False),
}


# --- surface routing -------------------------------------------------------
# The user's proposal, and the measurements back it: judge the SURFACE from
# colour and texture, then use the mask built for it. Independent of detection,
# so unlike "pick whichever mask detects best" it cannot grade its own homework.
#
# Measured on 31 recordings against eyeball surface labels (eval/clip_classes.json):
#     clay   a* 148.0-163.5     everything else tops out at 132.0   -> 16 units clear
#     shell  L* 170.0-176.5     hard courts top out at 163.0        ->  7 units clear
#     hard   a* 112.5-131.5
# a* is OpenCV Lab where 128 is neutral; clay's red/orange pushes it up hard.
CLAY_A = 140.0      # midpoint of a 16-unit gap
SHELL_L = 166.0     # midpoint of a 7-unit gap - thinner, watch it


def surface_of(frame):
    """'clay' | 'shell' | 'hard', from the lower-middle of the frame."""
    import cv2

    h, w = frame.shape[:2]
    roi = frame[int(h * 0.45):int(h * 0.95), int(w * 0.15):int(w * 0.85)]
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    a = float(np.median(lab[:, :, 1]))
    L = float(np.median(lab[:, :, 0]))
    if a >= CLAY_A:
        return "clay"
    return "shell" if L >= SHELL_L else "hard"


def routed_mask(frame, calibration, base):
    """Shipped mask everywhere it already works; the hue-agnostic one on clay.

    `base` is passed in rather than read off the module because installing this
    as calibration.line_ridge_mask would otherwise recurse - _clay_mask calls
    line_ridge_mask(tau=12, sat_max=255) internally.

    Shell deliberately routes to the SHIPPED mask: it was measured at 2 of 4
    auto-calibrating with gold_shell at 8/8 votes, so a pale surface still gives
    a luminance ridge and needs no special case. Only clay does."""
    import cv2

    if surface_of(frame) != "clay":
        return base(frame)
    # _clay_mask inlined against `base` for the same reason
    raw = base(frame, tau=12, sat_max=255)
    segs = cv2.HoughLinesP(raw, 1, np.pi / 180, threshold=50,
                           minLineLength=max(40, int(frame.shape[1] * 0.08)), maxLineGap=14)
    clean = np.zeros_like(raw)
    if segs is not None:
        for x1, y1, x2, y2 in segs[:, 0]:
            cv2.line(clean, (int(x1), int(y1)), (int(x2), int(y2)), 255, 2)
    return clean
