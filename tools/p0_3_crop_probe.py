"""P0-3 rebuilt: at a FAR-END ball contact, does a native-resolution crop find the
far player where a full 1280 frame does not?

This replaces `tools/probe_crop_pose.py`, whose 78.8% was withdrawn. Three defects
in that probe, all fixed here:

1. POPULATION. It selected contacts by `hit_xy[1] > court.NET_Y` — the ball's
   GROUND-projected contact. The ball is ~1 m up at contact and the camera sits
   behind the near baseline, so a near-player contact's ground ray lands past the
   net. On yt_match40 that called 193 of 196 contacts "far". Here the population
   comes from `p0_3_population.py`: a far-end hit is a local MINIMUM of the ball's
   raw IMAGE y-track. No homography anywhere in the selection.

2. NOT PERSON-SPECIFIC. It asked "does ANY person box overlap the 448 px region",
   which a 448 px box on a 1280x720 frame satisfies via the near player almost
   regardless. Here a detection only counts if its own box (expanded 25%) CONTAINS
   the contact point AND it is much smaller than the tallest person on court. The
   IDENTICAL test runs on control and on every crop arm.

3. NO SAME-RUN CONTROL. Here the full-frame control is one more arm of the same
   pass over the same frames, at the same pipeline stage.

WHY THE PRE-REGISTERED IDENTITY TEST WAS NOT USABLE AS WRITTEN. The brief asked
for "foot keypoint projects beyond NET_Y, plus a box height consistent with that
depth". That routes through the calibration, and `data/yt_match40_pts.json` is
MISCALIBRATED — all four clicked corners lie on blank asphalt, hedge or fence, not
on any court line (see `data/output/p0_3_calib_corners_yt_match40.png`). The
homography clause is therefore computed and reported as `secondary_*`, flagged,
and the headline number uses the calibration-free test instead. The calibration
file is human-supplied ground truth: it is recorded here, not edited.

STAGE. Raw pose detections, before `_reject_static_player` and before
`select_players_on_court`. That is the same stage the perception cache is written
at, but the denominator here is far-end CONTACT frames, not all pose frames, and
the acceptance test is different — so these numbers are NOT comparable with the
11.0% in `docs/evidence/pose-downscale-far-player.md`.

ON-DEVICE CAVEAT, stated in the evidence file too: a pass here proves the crop
FINDS the player, not that an A13 can afford it. Core ML wants one fixed input
shape, so the shippable form is one fixed-size crop per contact, batched — never a
variable-shape graph, or the ANE silently falls back to CPU and the saving is
gone. Proving affordability needs P0-0 and a device.

Run from the repo root:
  ./backend/.venv-train/Scripts/python.exe tools/p0_3_crop_probe.py \
      --match data/output/p0_1280_yt_match40.json \
      --video data/incoming/Hardcourt/yt_match40.mp4 \
      --keypoints data/yt_match40_pts.json \
      --out data/output/p0_3_probe_yt_match40.json \
      --sheet-prefix data/output/p0_3_sheet_yt_match40 --device cuda
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from swingvision import calibration, court, pose as pose_mod           # noqa: E402
from swingvision.pipeline import calibrate_video                       # noqa: E402
import p0_3_population as pop                                          # noqa: E402

# --- pre-registered arm grid -------------------------------------------------
CROP_SIZES = [192, 320, 448]      # native px, square, centred on the ball at contact
FULL_IMGSZ = 1280                 # control: the shipped `fast` preset's resolution
M_WEIGHTS = "yolo11m-pose.pt"     # the shipped pose model
X_WEIGHTS = "yolo11x-pose.pt"     # the `accurate` preset, used by the E3d far-court rescue

# --- identity test (calibration-free) ---------------------------------------
BOX_EXPAND = 0.25          # grow a detection's box by this fraction before asking
                           # whether it contains the contact point (the racquet head
                           # reaches roughly a body-width past the keypoint hull)
FAR_MAX_REL_H = 0.5        # a far-end striker must be at most half the height of the
                           # tallest person the control pass found in the same frame
FAR_MAX_ABS_H_FRAC = 0.25  # fallback when the control found nobody: at most this
                           # fraction of the frame height
NEAR_IOU_MAX = 0.2         # and it must not BE that person. A height test alone leaks:
                           # a 192 px crop TRUNCATES the near player's box to under
                           # 192 px, so the near player passes a relative-height gate
                           # in the crop arms and fails it in the control — which is
                           # not an A/B, it is the old defect in a new costume.
KP_CONF = 0.3              # keypoint confidence for the box hull

# --- secondary (pre-registered) homography clause ---------------------------
PERSON_H_M = 1.75
SIZE_LO, SIZE_HI = 0.4, 2.5
RUNOFF_M = 10.0
SIDE_MARGIN_M = 3.0


def _sha(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()[:12]
    except OSError:
        return None


def _git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True, timeout=20)
        return out.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")
    except Exception:
        return None


def _hull_box(p):
    """Box from the confident keypoints (the model's own box can include a
    low-confidence limb hallucinated outside the crop)."""
    pts = [(x, y) for x, y, c in p.keypoints if c > KP_CONF]
    if not pts:
        return None
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _contains(box, pt, expand=BOX_EXPAND):
    x1, y1, x2, y2 = box
    w, h = max(1.0, x2 - x1), max(1.0, y2 - y1)
    return (x1 - expand * w <= pt[0] <= x2 + expand * w
            and y1 - expand * h <= pt[1] <= y2 + expand * h)


def _iou(a, b):
    if a is None or b is None:
        return 0.0
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _centre_inside(box, outer):
    if box is None or outer is None:
        return False
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    return outer[0] <= cx <= outer[2] and outer[1] <= cy <= outer[3]


def _shift(poses, dx, dy):
    """Crop-local detections -> full-frame coordinates."""
    out = []
    for p in poses:
        out.append(pose_mod.PlayerPose(
            player=p.player,
            keypoints=[(x + dx, y + dy, c) for x, y, c in p.keypoints],
            box=(p.box[0] + dx, p.box[1] + dy, p.box[2] + dx, p.box[3] + dy),
            score=p.score))
    return out


def _secondary(p, H_t, img_wh, hfov):
    """The pre-registered homography clause. Returns (far_ok, size_ok, court_xy,
    expected_h_px). UNRELIABLE wherever the calibration is wrong — reported, not
    used for the headline."""
    try:
        Hinv = np.linalg.inv(np.asarray(H_t, float))
    except np.linalg.LinAlgError:
        return False, False, None, None
    fx, fy = p.feet()
    v = Hinv @ np.array([fx, fy, 1.0])
    if abs(v[2]) < 1e-9 or v[2] <= 0:          # at/behind the ground-plane horizon
        return False, False, None, None
    cx, cy = float(v[0] / v[2]), float(v[1] / v[2])
    far_ok = (cy >= court.NET_Y and cy <= court.LENGTH + RUNOFF_M
              and -SIDE_MARGIN_M <= cx <= court.DOUBLES_WIDTH + SIDE_MARGIN_M)
    exp_h = None
    size_ok = False
    if hfov:
        proj = calibration.project_court_3d(
            H_t, img_wh, [(cx, min(cy, court.LENGTH + 3.0), 0.0),
                          (cx, min(cy, court.LENGTH + 3.0), PERSON_H_M)], hfov)
        if proj is not None:
            exp_h = float(abs(proj[1][1] - proj[0][1]))
            box = _hull_box(p)
            if box is not None and exp_h > 1e-6:
                r = (box[3] - box[1]) / exp_h
                size_ok = SIZE_LO <= r <= SIZE_HI
    return bool(far_ok), bool(size_ok), (cx, cy), exp_h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", required=True)
    ap.add_argument("--perception", default=None)
    ap.add_argument("--video", required=True)
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet-prefix", default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--extra-imgsz", type=int, nargs="*", default=None,
                    help="EXPLORATORY follow-up, not part of the pre-registered grid: "
                         "add a crop{C}@{sz} arm for each crop size and each size given. "
                         "Used to separate 'crop' from 'upscale factor' as the variable.")
    args = ap.parse_args()

    np.random.seed(args.seed)
    match, perception = pop.load(args.match, args.perception)
    records = pop.classify_contacts(match, perception)
    far = [r for r in records if r["end"] == "far" and r.get("ball_px_at_contact")]
    if args.limit:
        far = far[: args.limit]
    print(f"[p0-3] far-end contacts in population: {len(far)}")
    if not far:
        print("[p0-3] nothing to measure")
        return

    frame_step = int(perception.get("frame_step", 1))
    cam_motion = perception.get("cam_motion") or []
    H, fit_err, src, _named, hfov, k1, _Hund = calibrate_video(args.video, args.keypoints, None)

    # Arm table. `key` -> (weights, imgsz, crop_size or None for the full frame).
    arms = {"control_full@1280": (M_WEIGHTS, FULL_IMGSZ, None)}
    for c in CROP_SIZES:
        arms[f"crop{c}@{c}_m"] = (M_WEIGHTS, c, c)       # native res, cheapest input
        arms[f"crop{c}@640_m"] = (M_WEIGHTS, 640, c)     # upsampled, fixed input cost
        arms[f"crop{c}@640_x"] = (X_WEIGHTS, 640, c)     # the E3d "accurate" model
    for sz in (args.extra_imgsz or []):
        for c in CROP_SIZES:
            arms[f"crop{c}@{sz}_x_EXPLORATORY"] = (X_WEIGHTS, sz, c)
    estimators = {}
    for key, (w, sz, _c) in arms.items():
        estimators[key] = pose_mod.PoseEstimator(weights=w, imgsz=sz, device=args.device)

    cap = cv2.VideoCapture(args.video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0

    wanted = {}
    for r in far:
        wanted.setdefault(r["source_frame"], r)
    per_contact = []
    tiles = {}          # source_frame -> the 448 native crop, for the contact sheets
    t0 = time.time()
    idx = 0
    remaining = set(wanted)
    while remaining:
        if not cap.grab():
            break
        if idx in remaining:
            ok, frame = cap.retrieve()
            remaining.discard(idx)
            if not ok:
                idx += 1
                continue
            r = wanted[idx]
            bx, by = r["ball_px_at_contact"]
            pi = r["processed_index"]
            H_t = H
            if pi < len(cam_motion) and cam_motion[pi]:
                H_t = np.asarray(cam_motion[pi], float).reshape(3, 3) @ np.asarray(H, float)

            # One inference per arm, on the SAME frame, in the SAME pass.
            dets = {}
            for key, (_w, _sz, c) in arms.items():
                if c is None:
                    poses = estimators[key].estimate(frame)
                else:
                    h = c // 2
                    x1, y1 = int(max(0, min(W - c, bx - h))), int(max(0, min(Hh - c, by - h)))
                    x2, y2 = min(W, x1 + c), min(Hh, y1 + c)
                    if x2 - x1 < 32 or y2 - y1 < 32:
                        dets[key] = []
                        continue
                    poses = _shift(estimators[key].estimate(frame[y1:y2, x1:x2]), x1, y1)
                dets[key] = poses

            # The near player is the tallest person the control pass found. Used
            # only as a SIZE reference, so the crop arms are judged by the same
            # yardstick and cannot be handed the near player as a far detection.
            ctrl_boxes = [b for b in (_hull_box(p) for p in dets["control_full@1280"]) if b]
            near_box = max(ctrl_boxes, key=lambda b: b[3] - b[1], default=None)
            tallest = (near_box[3] - near_box[1]) if near_box else 0.0
            max_far_h = (FAR_MAX_REL_H * tallest if tallest > 0
                         else FAR_MAX_ABS_H_FRAC * Hh)

            rec = {k: v for k, v in r.items()}
            rec["near_player_box_full_frame"] = (None if near_box is None
                                                 else [round(v, 1) for v in near_box])
            rec["tallest_control_box_h_px"] = round(tallest, 1)
            rec["max_far_box_h_px"] = round(max_far_h, 1)
            # POPULATION PURITY, reported not enforced. A low camera makes the ball's
            # trajectory APEX a local image-y minimum too, so the ball-derived
            # criterion admits some mid-flight and some near-player contacts. Flag the
            # ones where the contact point sits on the near player: those are near-end
            # hits, and every arm fails them alike, so they only dilute.
            rec["contact_on_near_player"] = bool(
                near_box is not None and _contains(near_box, (bx, by)))
            rec["arms"] = {}
            for key, poses in dets.items():
                acc, rej = [], []
                for p in poses:
                    box = _hull_box(p)
                    if box is None:
                        continue
                    bh = box[3] - box[1]
                    hits = _contains(box, (bx, by))
                    small = bh <= max_far_h
                    not_near = (near_box is None
                                or (_iou(box, near_box) < NEAR_IOU_MAX
                                    and not _centre_inside(box, near_box)))
                    f_ok, s_ok, cxy, exp_h = _secondary(p, H_t, (W, Hh), hfov)
                    entry = {
                        "box": [round(v, 1) for v in box],
                        "box_h_px": round(bh, 1),
                        "score": round(float(p.score), 3),
                        "contains_contact": bool(hits),
                        "small_enough": bool(small),
                        "not_the_near_player": bool(not_near),
                        "iou_with_near_player": round(_iou(box, near_box), 3),
                        "secondary_far_by_H": f_ok,
                        "secondary_size_ok": s_ok,
                        "secondary_court_xy": None if cxy is None else [round(cxy[0], 2), round(cxy[1], 2)],
                        "secondary_expected_h_px": None if exp_h is None else round(exp_h, 1),
                    }
                    (acc if (hits and small and not_near) else rej).append(entry)
                rec["arms"][key] = {
                    "n_detections": len(poses),
                    "accepted": acc,
                    "rejected": rej,
                    "found": bool(acc),
                    "found_secondary": any(e["secondary_far_by_H"] and e["secondary_size_ok"]
                                           and e["contains_contact"] for e in acc + rej),
                }
            per_contact.append(rec)

            h = CROP_SIZES[-1] // 2
            tx1 = int(max(0, min(W - CROP_SIZES[-1], bx - h)))
            ty1 = int(max(0, min(Hh - CROP_SIZES[-1], by - h)))
            tiles[idx] = (frame[ty1:ty1 + CROP_SIZES[-1], tx1:tx1 + CROP_SIZES[-1]].copy(),
                          tx1, ty1)
        idx += 1
    cap.release()

    n = len(per_contact)
    clean = [r for r in per_contact if not r["contact_on_near_player"]]
    nc = len(clean)
    rates, boxh = {}, {}
    for key in arms:
        k1_ = sum(1 for r in per_contact if r["arms"][key]["found"])
        k2_ = sum(1 for r in per_contact if r["arms"][key]["found_secondary"])
        k3_ = sum(1 for r in clean if r["arms"][key]["found"])
        hs = [e["box_h_px"] for r in per_contact for e in r["arms"][key]["accepted"]]
        rates[key] = {
            "found": k1_,
            "rate_pct": round(100.0 * k1_ / n, 1) if n else None,
            "found_not_on_near_player_subset": k3_,
            "rate_pct_subset": round(100.0 * k3_ / nc, 1) if nc else None,
            "found_secondary_homography": k2_,
            "rate_secondary_pct": round(100.0 * k2_ / n, 1) if n else None,
        }
        boxh[key] = {"n": len(hs),
                     "median_accepted_box_h_px": round(float(np.median(hs)), 1) if hs else None}

    result = {
        "probe": "P0-3 crop-around-contact, rebuilt",
        "measured_against": (
            "ball-derived far-end contacts (image-y local minimum) and a "
            "calibration-free person-specific test: a detection counts only if its "
            "own keypoint-hull box, expanded 25%, contains the ball contact point AND "
            "its height is at most half the tallest person the full-frame control "
            "found in the same frame. NOT scored against human pose labels."),
        "pipeline_stage": ("raw pose detections, BEFORE select_players_on_court and "
                           "BEFORE _reject_static_player — the same stage the perception "
                           "cache is written at, but on far-end contact frames only"),
        "not_comparable_to": ("the 11.0%/1.0% in docs/evidence/pose-downscale-far-player.md "
                              "— different denominator (all pose frames) and different "
                              "acceptance test"),
        "video": os.path.basename(args.video),
        "frame_wh": [W, Hh],
        "source_fps": round(src_fps, 3),
        "frame_step": frame_step,
        "population": {
            "criterion": ("far-end hit = local MINIMUM of the ball's raw IMAGE y-track; "
                          f"least-squares slope over +/-{pop.WINDOW} processed frames, "
                          f"min |slope| {pop.MIN_SLOPE_PX_720} px/frame scaled by height/720, "
                          f"min {pop.MIN_SAMPLES} detections per side"),
            "far_contacts_evaluated": n,
            "far_contacts_not_on_near_player": nc,
            "shots_total": len(match["shots"]),
            "class_counts": {c: sum(1 for r in records if r["end"] == c)
                             for c in ("far", "near", "undecided")},
            "alternation_check": pop.alternation_report(records),
            "pipeline_player_agreement": pop.pipeline_agreement(records),
        },
        "arms": {k: {"weights": v[0], "imgsz": v[1], "crop_px": v[2]} for k, v in arms.items()},
        "rates": rates,
        "accepted_box_heights": boxh,
        "calibration": {
            "keypoints_file": os.path.basename(args.keypoints),
            "keypoints_sha256": _sha(args.keypoints),
            "fit_residual_px": round(float(fit_err), 2),
            "source": src,
            "hfov_deg": hfov,
            "lens_k1": k1,
            "WARNING": ("the secondary_* fields route through this homography; verify it "
                        "lands on the real court lines before reading them"),
        },
        "provenance": {
            "device": args.device,
            "seed": args.seed,
            "git_commit": _git_commit(),
            "weights": {w: {"path": w, "sha256": _sha(os.path.join("backend", w))}
                        for w in (M_WEIGHTS, X_WEIGHTS)},
            "match_json": os.path.basename(args.match),
            "perception_pose_model": perception.get("provenance", {}).get("pose_model"),
            "elapsed_s": round(time.time() - t0, 1),
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "contacts": per_contact,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    brief = {k: v for k, v in result.items() if k != "contacts"}
    print(json.dumps(brief, indent=2))

    if args.sheet_prefix:
        _sheets(args.sheet_prefix, per_contact, tiles, arms)


TILE = 384
COLS = 5


def _sheets(prefix, per_contact, tiles, arms):
    """One contact sheet per crop arm: the 448 px native crop, upscaled, with the
    control arm and that crop arm drawn on the SAME tile."""
    for key in arms:
        if key == "control_full@1280":
            continue
        out = []
        for r in per_contact:
            t = tiles.get(r["source_frame"])
            if t is None:
                continue
            sub, tx, ty = t
            sub = sub.copy()
            bx, by = r["ball_px_at_contact"]
            crop_px = arms[key][2]
            h = crop_px // 2
            cx0, cy0 = int(bx - h - tx), int(by - h - ty)
            cv2.rectangle(sub, (cx0, cy0), (cx0 + crop_px, cy0 + crop_px), (255, 255, 255), 1)
            # Show the tile at THIS arm's crop scale, not always the 448 box — a
            # 25 px far player inside a 448 tile shrunk to fit is unreadable, and an
            # unreadable contact sheet is exactly how the first P0-3 number survived.
            pad = 24
            for arm, (ca, cr) in ((("control_full@1280"), ((0, 255, 0), (0, 140, 255))),
                                  ((key), ((255, 255, 0), (0, 0, 255)))):
                a = r["arms"][arm]
                for e in a["accepted"]:
                    x1, y1, x2, y2 = e["box"]
                    cv2.rectangle(sub, (int(x1 - tx), int(y1 - ty)),
                                  (int(x2 - tx), int(y2 - ty)), ca, 2)
                for e in a["rejected"]:
                    x1, y1, x2, y2 = e["box"]
                    cv2.rectangle(sub, (int(x1 - tx), int(y1 - ty)),
                                  (int(x2 - tx), int(y2 - ty)), cr, 1)
            cv2.drawMarker(sub, (int(bx - tx), int(by - ty)), (255, 0, 255),
                           cv2.MARKER_TILTED_CROSS, 18, 1)
            vx1, vy1 = max(0, cx0 - pad), max(0, cy0 - pad)
            vx2 = min(sub.shape[1], cx0 + crop_px + pad)
            vy2 = min(sub.shape[0], cy0 + crop_px + pad)
            if vx2 - vx1 > 16 and vy2 - vy1 > 16:
                sub = sub[vy1:vy2, vx1:vx2]
            # Letterbox to a fixed square: crops clipped at a frame edge are not
            # square, and rows of a contact sheet must stack.
            sc = TILE / float(max(sub.shape[0], sub.shape[1]))
            sub = cv2.resize(sub, (max(1, int(sub.shape[1] * sc)), max(1, int(sub.shape[0] * sc))),
                             interpolation=cv2.INTER_NEAREST)
            canvas = np.zeros((TILE, TILE, 3), np.uint8)
            canvas[:sub.shape[0], :sub.shape[1]] = sub
            sub = canvas
            cv2.putText(sub, f"#{r['shot_id']} f{r['source_frame']} "
                             f"C{'Y' if r['arms']['control_full@1280']['found'] else 'n'}"
                             f"/{'Y' if r['arms'][key]['found'] else 'n'}",
                        (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 0, 255), 1, cv2.LINE_AA)
            out.append(sub)
        if not out:
            continue
        rows = []
        for i in range(0, len(out), COLS):
            row = out[i:i + COLS]
            while len(row) < COLS:
                row.append(np.zeros_like(out[0]))
            rows.append(np.hstack(row))
        sheet = np.vstack(rows)
        legend = np.zeros((52, sheet.shape[1], 3), np.uint8)
        cv2.putText(legend, f"{key}   view = this arm's {arms[key][2]}px native crop +24px, "
                            f"upscaled x{TILE/(arms[key][2]+48.0):.2f}   "
                            "magentaX = ball at contact   white box = the crop region",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(legend, "green = CONTROL accepted, orange = control rejected   |   "
                            "cyan = CROP accepted, red = crop rejected   |   label: C<control>/<crop>",
                    (8, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)
        path = f"{prefix}_{key.replace('@', 'at').replace('/', '_')}.png"
        cv2.imwrite(path, np.vstack([legend, sheet]))
        print(f"[p0-3] sheet -> {path} ({len(out)} tiles)")


if __name__ == "__main__":
    main()
