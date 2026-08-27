"""pose.py — player pose estimation (ML, REAL via ultralytics YOLO-pose).

Pose is perception. PoseEstimator wraps a YOLO pose model and returns per-person
17-keypoint COCO poses. A tennis broadcast frame contains far more people than the
two players (crowd, ball kids, line judges), so callers filter detections to the
court — see keep_players(), which keeps the largest people whose feet fall inside
a court region.

Weights (yolo11n-pose.pt) download automatically on first use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

# COCO-17 skeleton edges, for drawing.
COCO_SKELETON = [
    (5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16), (0, 1), (0, 2), (1, 3), (2, 4),
    (0, 5), (0, 6),
]


@dataclass
class PlayerPose:
    """One person's pose in one frame: 17 COCO keypoints as (x_px, y_px, conf),
    a bounding box (x1, y1, x2, y2), and detection confidence."""
    player: str
    keypoints: list[tuple[float, float, float]]
    box: tuple[float, float, float, float]
    score: float

    def feet(self) -> tuple[float, float]:
        """Mid-point between the two ankles (kpts 15, 16) — the player's court
        contact point. Falls back to the box-bottom centre if ankles are unseen."""
        la, ra = self.keypoints[15], self.keypoints[16]
        pts = [(x, y) for x, y, c in (la, ra) if c > 0.2]
        if pts:
            return float(np.mean([p[0] for p in pts])), float(np.mean([p[1] for p in pts]))
        x1, y1, x2, y2 = self.box
        return (x1 + x2) / 2.0, y2

    def box_area(self) -> float:
        x1, y1, x2, y2 = self.box
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)


# Speed/accuracy presets. The cost is dominated by resolving the *far* player
# (the near player is large and trivial). "fast" handles the near player and a
# moderately distant far player on CPU in ~0.4s/frame; "accurate" is ~6x slower
# but resolves a small far player on broadcast-style footage.
QUALITY_PRESETS = {
    "fast": ("yolo11m-pose.pt", 1280),
    "balanced": ("yolo11m-pose.pt", 1600),
    "accurate": ("yolo11x-pose.pt", 1920),
}


def _use_all_cpu_threads() -> None:
    import os

    import torch

    torch.set_num_threads(os.cpu_count() or torch.get_num_threads())


class PoseEstimator:
    """Wraps a YOLO pose model. Real inference; weights auto-download.

    `quality` picks a speed/accuracy preset (see QUALITY_PRESETS); pass explicit
    `weights`/`imgsz` to override it. Default is "fast" — analysis throughput
    matters, and most footage doesn't have a resolvable far player anyway.
    """

    def __init__(
        self,
        weights: Optional[str] = None,
        conf: float = 0.2,
        device: str = "cpu",
        imgsz=None,
        quality: str = "fast",
    ) -> None:
        preset_weights, preset_imgsz = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["fast"])
        self.weights = weights or preset_weights
        # Same env-hook pattern as BALLNET_INPUT (ball.py): points a benchmark at
        # a resolution no named preset covers (P0-2's 640/384 sweep) without
        # threading a CLI flag through every construction site. Stamped into the
        # perception-cache provenance via pose_model = f"{pose_w}@{pose_imgsz}"
        # (pipeline.py), so a cache built at one size is not a cache for another.
        import os
        env_imgsz = os.environ.get("POSE_IMGSZ")
        self.imgsz = int(env_imgsz) if env_imgsz else (imgsz or preset_imgsz)
        self.conf = conf
        self.device = device
        self._model = None

    def _load(self):
        from ultralytics import YOLO

        _use_all_cpu_threads()
        self._model = YOLO(self.weights)

    def estimate(self, frame: np.ndarray) -> list[PlayerPose]:
        """Return a PlayerPose for every person detected in the frame."""
        if self._model is None:
            self._load()
        res = self._model.predict(
            frame, conf=self.conf, device=self.device, imgsz=self.imgsz, verbose=False
        )[0]
        if res.keypoints is None or res.boxes is None:
            return []
        kpts = res.keypoints.data.cpu().numpy()          # (n, 17, 3)
        boxes = res.boxes.xyxy.cpu().numpy()             # (n, 4)
        scores = res.boxes.conf.cpu().numpy()            # (n,)
        out: list[PlayerPose] = []
        for i in range(len(kpts)):
            out.append(
                PlayerPose(
                    player=str(i),
                    keypoints=[(float(x), float(y), float(c)) for x, y, c in kpts[i]],
                    box=tuple(float(v) for v in boxes[i]),
                    score=float(scores[i]),
                )
            )
        return out

    def estimate_tiled(self, frame: np.ndarray, tile,
                       min_score: float = 0.0) -> list[PlayerPose]:
        """Run pose on one native-resolution crop, returning FULL-FRAME coordinates.

        The far player is the same small-object problem as the far ball: on
        yt_rally2 they stand ~45 px tall, and whole-frame inference finds them in
        0 of 2215 frames even at the `accurate` preset. Measured on 4 sampled
        frames (Session E3d): full frame finds 0 far players at both `fast` and
        `accurate`; a native-resolution far-court crop finds 0 at `fast` and 7 at
        `accurate`. Both the crop AND the larger model are required — neither
        alone recovers them.

        `tile` is (x0, y0, x1, y1) in frame pixels. Detections are shifted back to
        frame coordinates so callers cannot tell the difference.
        """
        x0, y0, x1, y1 = (int(v) for v in tile)
        h, w = frame.shape[:2]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 - x0 < 32 or y1 - y0 < 32:
            return []
        found = self.estimate(frame[y0:y1, x0:x1])
        out: list[PlayerPose] = []
        for p in found:
            if p.score < min_score:
                continue
            out.append(PlayerPose(
                player=p.player,
                keypoints=[(x + x0, y + y0, c) for x, y, c in p.keypoints],
                box=(p.box[0] + x0, p.box[1] + y0, p.box[2] + x0, p.box[3] + y0),
                score=p.score,
            ))
        return out


def far_court_tile(homography, img_wh, *, runoff_m: float = 5.0,
                   head_room: float = 1.6, pad_px: float = 40.0):
    """Image-space crop covering the FAR half of the court, for `estimate_tiled`.

    Derived from the homography rather than hardcoded, so it follows the camera:
    project the far half's ground corners (plus a behind-baseline runoff, since
    players receive from well back), then extend the box UPWARD by `head_room`
    times its own height — the projection covers the players' FEET, and their
    heads are above that in the image.

    Returns (x0, y0, x1, y1) clipped to the frame, or None if the projection is
    degenerate (bad calibration, court off-screen).
    """
    from . import calibration, court

    W, H = img_wh
    ground = [
        (-runoff_m, court.NET_Y), (court.DOUBLES_WIDTH + runoff_m, court.NET_Y),
        (-runoff_m, court.LENGTH + runoff_m),
        (court.DOUBLES_WIDTH + runoff_m, court.LENGTH + runoff_m),
    ]
    try:
        pts = np.asarray(calibration.court_to_image(homography, ground), float)
    except Exception:
        return None
    if not np.isfinite(pts).all():
        return None
    x0, y0 = pts[:, 0].min(), pts[:, 1].min()
    x1, y1 = pts[:, 0].max(), pts[:, 1].max()
    if not (x1 > x0 and y1 > y0):
        return None
    y0 -= head_room * (y1 - y0)          # room for standing players above their feet
    x0, y0 = max(0.0, x0 - pad_px), max(0.0, y0 - pad_px)
    x1, y1 = min(float(W), x1 + pad_px), min(float(H), y1 + pad_px)
    if x1 - x0 < 32 or y1 - y0 < 32:
        return None
    return int(x0), int(y0), int(x1), int(y1)


def _point_in_poly(x: float, y: float, poly: np.ndarray) -> bool:
    """Ray-casting point-in-polygon for an (N, 2) polygon."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def keep_players(
    poses: Sequence[PlayerPose],
    court_poly: Optional[Sequence[Sequence[float]]] = None,
    max_players: int = 2,
) -> list[PlayerPose]:
    """Filter raw detections down to the players on court.

    If a court polygon (image pixels) is given, keep only people whose feet fall
    inside it (drops the crowd); then keep the `max_players` largest. Without a
    polygon, just keep the largest people by box area (players are nearest the
    camera-facing court, hence biggest).
    """
    candidates = list(poses)
    if court_poly is not None:
        poly = np.asarray(court_poly, dtype=np.float64)
        candidates = [p for p in candidates if _point_in_poly(*p.feet(), poly)]
    candidates.sort(key=lambda p: p.box_area(), reverse=True)
    return candidates[:max_players]


def select_two_players(
    poses: Sequence[PlayerPose],
    split_y: float,
    center_x: float,
    court_poly: Optional[Sequence[Sequence[float]]] = None,
) -> list[PlayerPose]:
    """Pick exactly the two players from a crowd of detections.

    Area alone fails — the far player is smaller than near-court ball kids and
    line judges. Instead use the court structure: split the frame at the net
    (`split_y`); the NEAR player is the largest person below it; the FAR player is
    the person above it closest to the court centre line (`center_x`) — players
    rally down the middle, while ball kids and judges hug the posts and sidelines.
    """
    cands = list(poses)
    if court_poly is not None:
        poly = np.asarray(court_poly, dtype=np.float64)
        cands = [p for p in cands if _point_in_poly(*p.feet(), poly)]

    below = [p for p in cands if p.feet()[1] >= split_y]
    above = [p for p in cands if p.feet()[1] < split_y]
    chosen: list[PlayerPose] = []
    if below:
        chosen.append(max(below, key=lambda p: p.box_area()))
    if above:
        chosen.append(min(above, key=lambda p: abs(p.feet()[0] - center_x)))
    return chosen


def count_on_court(poses, homography, court_margin_m: float = 1.5,
                   runoff_m: float = 7.0) -> tuple[int, int]:
    """(near, far): how many people have feet on the court, per half. Used to tell
    singles (1 each side) from doubles (2 each side) for the line-call boundary."""
    from . import calibration, court

    nn = nf = 0
    for p in poses:
        cx, cy = calibration.image_to_court(homography, [p.feet()])[0]
        if (-court_margin_m <= cx <= court.DOUBLES_WIDTH + court_margin_m
                and -runoff_m <= cy <= court.LENGTH + runoff_m):
            if cy < court.NET_Y:
                nn += 1
            else:
                nf += 1
    return nn, nf


def infer_doubles(counts, min_frac: float = 0.35) -> bool:
    """Given per-frame (near, far) on-court counts, decide doubles vs singles.
    Doubles when a meaningful fraction of sampled frames show >=2 players on BOTH
    halves (a lone extra detection or a briefly-occluded partner won't flip it)."""
    counts = [c for c in counts if c is not None]
    if not counts:
        return False
    both_two = sum(1 for nn, nf in counts if nn >= 2 and nf >= 2)
    return both_two >= max(1, int(min_frac * len(counts)))


def select_players_on_court(
    poses: Sequence[PlayerPose],
    homography: np.ndarray,
    court_margin_m: float = 1.5,
    runoff_m: float = 7.0,
):
    """Angle-robust two-player selection, working in court metres via the
    homography instead of hardcoded image pixels.

    This adapts to any camera placement (a phone mounted a little above and behind
    a baseline, not just a TV camera): each person's feet are back-projected to the
    court plane; we keep those that land on the court (plus a sideline margin and a
    behind-baseline runoff, since players stand back to receive), split them by the
    net (court y < / > NET_Y), and take the most central person on each half — the
    rally happens down the middle while ball kids/judges hug the posts and edges.

    Returns up to two (PlayerPose, court_xy) pairs, near half first.
    """
    from . import calibration, court

    annotated = []
    for p in poses:
        cx, cy = calibration.image_to_court(homography, [p.feet()])[0]
        annotated.append((p, (float(cx), float(cy))))

    on_court = [
        t for t in annotated
        if -court_margin_m <= t[1][0] <= court.DOUBLES_WIDTH + court_margin_m
        and -runoff_m <= t[1][1] <= court.LENGTH + runoff_m
    ]
    # Fallback for rough calibration / amateur footage: if back-projection drops
    # too many (a skewed phone angle, an occluded corner), keep the two biggest
    # detections so we don't lose the players to a noisy homography.
    pool = on_court if len(on_court) >= 2 else sorted(annotated, key=lambda t: -t[0].box_area())[:2]

    near = [t for t in pool if t[1][1] < court.NET_Y]
    far = [t for t in pool if t[1][1] >= court.NET_Y]
    center = court.DOUBLES_WIDTH / 2.0
    chosen = []
    for half in (near, far):
        if half:
            # Most central in court x; tiebreak on the larger (closer) detection.
            half.sort(key=lambda t: (abs(t[1][0] - center), -t[0].box_area()))
            chosen.append(half[0])
    return chosen
