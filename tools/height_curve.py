"""height_curve.py — what does camera height actually COST? Measured, not asserted.

WHY THIS EXISTS
---------------
The setup tool tells a user their mount is low, and quantifies it as MEASURABLE
DEPTH: "low camera 1.38 m — measurable to court-y 5.2 m of 23.8 (22% of depth)"
(`calibration.reliable_court_span`). That is a GEOMETRIC BOUND — the depth at
which one pixel of error stops being worth less than RELIABLE_SCALE_M_PER_PX. It
is not an error. Nobody has ever measured what a low camera does to the numbers
the user actually reads: the line call and the bounce position.

`synth_truth.py` made that measurable for the first time — it manufactures exact
truth (drag+gravity+Magnus), projects it through a REAL calibration, adds our
detector's real noise and dropout, and runs the shipped measurement code. It
takes ANY calibration. So point it at a ladder of camera heights and the bound
becomes a curve.

TWO HALVES, AND THEY ANSWER DIFFERENT QUESTIONS
-----------------------------------------------
A. CONTROLLED SWEEP — synthetic cameras, everything fixed except height.
   Setback, lens, resolution, noise and dropout are held constant, and the pitch
   is re-solved at each height to keep the court framed (which is what a user
   does: they tilt the phone, they cannot move the fence). This is the only half
   that isolates HEIGHT, because it is the only half where nothing else moves.

B. REAL CALIBRATIONS — the committed, audited court files, 1.38 m to 12.28 m.
   These are cameras that actually exist, so they anchor the curve in reality —
   but they scatter around it rather than lying on it, because each has its own
   lens, setback and resolution. Read them as anchors, NOT as curve points.

Reported per setup: measurable depth (the existing bound, for comparison), line
call agreement with truth, bounce position error, and the low-ball speed error.
The unrestricted speed error is deliberately NOT a column — synth_truth showed
its p90 is +25,000%, because a near-grazing ray meets z=0 at infinity, so it
measures the tail rather than the camera.

    cd backend && .venv-train/Scripts/python.exe ../tools/height_curve.py \
        --n 600 --markdown ../data/output/height_curve.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

from synth_truth import CORNERS, measure, summarize  # noqa: E402

# A phone at the back fence. The regulation runback is 6.4 m, and an ultrawide
# lens is not a luxury here: a 70 deg lens needs ~7.8 m of setback before the
# near doubles corners fit in frame at all, which is why the two amateur clips
# in this repo self-calibrate to 86 and 104 deg.
SETBACK_M = 6.0
HFOV_DEG = 100.0
HEIGHTS_M = (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 12.0)

# Every committed calibration the audit does not call DEGENERATE. Each carries
# its verdict and fitted camera height in the `_audit` key that
# validate_new_clip.py --stamp wrote (Session G part 2).
REAL = ("demo30_pts", "am_hard_utr_pts", "yt_court_pts", "yt_rally2_pts",
        "eala_pts_auto", "yt_match40_pts", "court_pts_refined")


def frame_the_court(height_m, setback_m, hfov_deg, w, h):
    """Corner pixels for a centre-line camera at `height_m`, tilted to frame the
    court — or None if this setup cannot see all four corners.

    The pitch is SOLVED, not assumed: bisect until the court's vertical midpoint
    sits at the frame centre. Holding pitch fixed instead would confound the
    thing being measured, since the same tilt frames a 1 m camera and a 12 m one
    completely differently.
    """
    from swingvision import court, courtfit

    f = (w / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)

    def corners_at(pitch):
        p = (court.DOUBLES_WIDTH / 2.0, -setback_m, height_m, 0.0, pitch, f)
        return courtfit._cam_corners(p, w, h, court)

    def offset(pitch):
        """Court's vertical centre minus the frame's. Monotone decreasing in
        pitch (tilting down moves the court up), so bisection is safe."""
        c = corners_at(pitch)
        if c is None:
            return None
        near = (c["near_bl_doubles"][1] + c["near_br_doubles"][1]) / 2.0
        far = (c["far_bl_doubles"][1] + c["far_br_doubles"][1]) / 2.0
        return (near + far) / 2.0 - h / 2.0

    lo, hi = 0.0, math.radians(85.0)
    if (o := offset(lo)) is None or o < 0:
        return None                       # court already above centre at zero tilt
    for _ in range(60):
        mid = (lo + hi) / 2.0
        o = offset(mid)
        if o is None or o < 0:
            hi = mid
        else:
            lo = mid
    c = corners_at(lo)
    if c is None:
        return None
    if not all(0 <= c[n][0] < w and 0 <= c[n][1] < h for n in CORNERS):
        return None                       # a corner off-frame: not a usable setup
    return {n: [float(c[n][0]), float(c[n][1])] for n in CORNERS}, math.degrees(lo)


def camera_height_of(kp, hfov_deg, w, h):
    """The height the MEASUREMENT chain actually believes this camera is at.

    Round-tripping the corners back through the same PnP that synth_truth uses
    is not a formality: if the generator and the chain disagreed about the
    camera, every number below would be junk in a way no output could reveal.
    """
    from tennis_tracker.bridge import camera_from_court_corners
    cam, _ = camera_from_court_corners({c: kp[c] for c in CORNERS}, (w, h),
                                       hfov_deg=hfov_deg)
    return float((-np.asarray(cam.R).T @ np.asarray(cam.t))[2])


def hfov_of(kp, H, w, h):
    """This clip's actual horizontal FOV, or None. Never assumed — speed scales
    with it and these files span a phone ultrawide to a broadcast telephoto.

    PRIMARY is `courtfit.cam_fit_quad`, the same physical-camera fit that
    produced each file's audited height, so the lens and the height quoted here
    come from one solve. `focal_from_homography` is the fallback: it is the
    cheaper self-calibration but it REFUSES outside 25-110 deg, which rejects
    exactly the broadcast and high-mount files this sweep needs at the top end.
    """
    from swingvision import calibration, court, courtfit
    try:
        fit = courtfit.cam_fit_quad({n: kp[n] for n in CORNERS}, calibration,
                                    court, w, h, allow_roll=True)
        if fit is not None:
            f = float(fit[3][5])
            if f > 1.0:
                return math.degrees(2.0 * math.atan((w / 2.0) / f))
    except Exception:
        pass
    f = calibration.focal_from_homography(H, (w, h))
    return None if f is None else math.degrees(2.0 * math.atan((w / 2.0) / f))


CONTROL_HEIGHTS = (1.0, 3.0, 12.0)
CONTROL_RATES = (("shipped 30fps / 30% dropout", 30.0, 0.30),
                 ("60fps / no dropout", 60.0, 0.0),
                 ("240fps / no dropout", 240.0, 0.0))


def control(args):
    """Is the curve HEIGHT, or is it just the frame rate?

    A plausible alternative explanation for everything above: our bounce estimate
    is the last tracked point, so at 30 fps with 30% dropout the last detection
    can be a frame or two before the ball actually lands, and the ball is still
    moving. That would depress every row — and it would be a sampling result
    wearing a geometry result's clothes.

    So re-run three heights with the sampling handicap removed. If the spread
    between 1 m and 12 m survives, it is the camera.
    """
    lines = []
    for hm in CONTROL_HEIGHTS:
        got = frame_the_court(hm, args.setback, args.hfov, args.width, args.height)
        if got is None:
            continue
        kp, _ = got
        for tag, fps, drop in CONTROL_RATES:
            s = summarize(measure(kp, hfov=args.hfov, width=args.width,
                                  height=args.height, n=args.n, fps=fps,
                                  pixel_noise=args.pixel_noise, dropout=drop,
                                  seed=args.seed))
            lines.append(f"| {hm:.1f} m | {tag} | {s['call_agree_near_pct']:.1f}% "
                         f"({s['n_near']}) | {s['bounce_err_median_m']:.2f} m |")
    return lines


def score(kp, *, hfov, w, h, n, seed, fps, dropout, noise720):
    """One setup, measured end to end. Returns a row or None."""
    from swingvision import calibration

    H = calibration.homography_from_landmarks({c: kp[c] for c in CORNERS})
    frac, until = calibration.reliable_court_span(H)
    # `noise720` is quoted at 720p (synth_truth's convention); the same physical
    # jitter covers proportionally more pixels on a taller frame, so scale it.
    rows = measure(kp, hfov=hfov, width=w, height=h, n=n, fps=fps,
                   pixel_noise=noise720 * (h / 720.0), dropout=dropout, seed=seed)
    if not rows:
        return None
    s = summarize(rows)
    s["depth_frac"] = 100.0 * frac
    s["depth_until_m"] = until
    s["hfov_deg"] = hfov
    s["img_wh"] = [w, h]
    return s


def skip_row(label, why, cam="—"):
    """A placeholder with the SAME column count as a real row, so a setup that
    could not be measured stays visible in the table instead of quietly vanishing."""
    return f"| {label} | {cam} | — | {why} |" + " |" * 7


def fmt_row(label, cam_m, s, extra=""):
    return (f"| {label} | {cam_m:.2f} | {s['hfov_deg']:.0f} | "
            f"{s['depth_frac']:.0f}% ({s['depth_until_m']:.1f} m) | {s['n']} | "
            f"{s['call_agree_pct']:.1f}% | "
            f"{s['call_agree_near_pct']:.1f}% ({s['n_near']}) | "
            f"{s['bounce_err_median_m']:.2f} | "
            f"{s['bounce_err_p90_m']:.2f} | {s['low_abs_err_median']:.1f}%"
            f" |{extra} |")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=600, help="flights simulated per setup")
    ap.add_argument("--fps", type=float, default=30.0, help="the SHIPPED effective rate")
    ap.add_argument("--dropout", type=float, default=0.30)
    ap.add_argument("--pixel-noise", type=float, default=2.0, help="px @720p")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--setback", type=float, default=SETBACK_M)
    ap.add_argument("--hfov", type=float, default=HFOV_DEG)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-real", action="store_true")
    ap.add_argument("--control", action="store_true",
                    help="also run the frame-rate control (see control())")
    ap.add_argument("--markdown")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    sweep, anchors = [], []
    head = ("| setup | camera m | hfov | measurable depth | flights | line call (all) | "
            "line call NEAR A LINE | bounce med m | bounce p90 m | speed err (low ball) "
            "| notes |")
    rule = "|---|---|---|---|---|---|---|---|---|---|---|"

    def baseline_note(rows_):
        """Every camera judges the SAME true bounces, so the near-line population
        and its majority-class floor are identical down a column — a paired
        comparison. Say the floor once; a call rate at or below it is worthless."""
        if not rows_:
            return ""
        b = rows_[0]
        return (f"   Near-line population: {b['n_near']} bounces within "
                f"{b['near_m']:g} m of a line (the SAME ones for every camera). "
                f"Answering with the majority class alone scores "
                f"{b['call_near_majority_pct']:.1f}% — that is the floor to beat.")

    print(f"A. CONTROLLED SWEEP — setback {args.setback:g} m, hfov {args.hfov:g} deg, "
          f"{args.width}x{args.height}, noise {args.pixel_noise:g}px, "
          f"dropout {args.dropout:g}, fps {args.fps:g}")
    print("   Only the camera HEIGHT changes; pitch is re-solved to keep the court framed.")
    print(head)
    print(rule)
    for hm in HEIGHTS_M:
        got = frame_the_court(hm, args.setback, args.hfov, args.width, args.height)
        if got is None:
            print(skip_row(f"{hm:.2f} m",
                           "court will not fit in frame at this height and setback"))
            continue
        kp, pitch = got
        rec = camera_height_of(kp, args.hfov, args.width, args.height)
        # The generator and the measurement chain must agree about the camera.
        assert abs(rec - hm) < 0.02 * max(hm, 1.0), \
            f"round-trip disagrees: commanded {hm:.2f} m, PnP recovered {rec:.2f} m"
        s = score(kp, hfov=args.hfov, w=args.width, h=args.height, n=args.n,
                  seed=args.seed, fps=args.fps, dropout=args.dropout,
                  noise720=args.pixel_noise)
        if s is None:
            print(skip_row(f"{hm:.2f} m", "no usable flights", cam=f"{rec:.2f}"))
            continue
        s["commanded_m"] = hm
        s["recovered_m"] = rec
        s["pitch_deg"] = pitch
        sweep.append(s)
        print(fmt_row(f"{hm:.2f} m", rec, s, f" pitch {pitch:.0f}°"))
    print(baseline_note(sweep))

    if not args.skip_real:
        print()
        print("B. REAL COMMITTED CALIBRATIONS — anchors, not curve points: each has its "
              "own lens, setback and resolution.")
        print(head)
        print(rule)
        from swingvision import calibration
        for name in REAL:
            p = REPO / "data" / f"{name}.json"
            kp = json.loads(p.read_text(encoding="utf-8"))
            aud = kp.get("_audit", {})
            if aud.get("verdict") == "DEGENERATE":
                print(skip_row(name, "SKIPPED: audit says DEGENERATE"))
                continue
            w, h = aud.get("img_wh", [1280, 720])
            H = calibration.homography_from_landmarks({c: kp[c] for c in CORNERS})
            hf = hfov_of(kp, H, w, h)
            if hf is None:
                print(skip_row(name, "SKIPPED: lens would not solve"))
                continue
            try:
                rec = camera_height_of(kp, hf, w, h)
            except Exception as e:
                print(skip_row(name, f"SKIPPED: {e}"))
                continue
            s = score(kp, hfov=hf, w=w, h=h, n=args.n, seed=args.seed, fps=args.fps,
                      dropout=args.dropout, noise720=args.pixel_noise)
            if s is None:
                print(skip_row(name, "no usable flights", cam=f"{rec:.2f}"))
                continue
            s["clip"] = name
            s["recovered_m"] = rec
            s["audit_height_m"] = aud.get("camera_height_m")
            s["verdict"] = aud.get("verdict")
            anchors.append(s)
            print(fmt_row(name, rec, s, f" {aud.get('verdict', '?')}"))
        print(baseline_note(anchors))

    ctrl = []
    if args.control:
        print()
        print("C. CONTROL — is this HEIGHT, or is it the frame rate?")
        print("| camera | sampling | line call NEAR A LINE | bounce med |")
        print("|---|---|---|---|")
        ctrl = control(args)
        for ln in ctrl:
            print(ln)

    if args.markdown:
        out = Path(args.markdown)
        out.parent.mkdir(parents=True, exist_ok=True)
        L = [
            "# What camera height costs — measured against exact truth",
            "",
            "Generated by `tools/height_curve.py`, which drives `tools/synth_truth.py`.",
            "",
            "**Measured against:** EXACT simulated truth. Flights are integrated through "
            "the real drag+gravity+Magnus model, projected through each camera, then "
            "given our detector's actual pixel noise and dropout; the SHIPPED "
            "`analytics.line_call` / `analytics.shot_speed_kmh` are run on the result "
            "and compared with the number the simulation started from. No human labels, "
            "no HUD.",
            "",
            "`measurable depth` is the EXISTING geometric bound "
            "(`calibration.reliable_court_span`) — the fraction of court depth where one "
            "pixel of error is still worth less than `RELIABLE_SCALE_M_PER_PX`. It is "
            "shown next to the measured errors so the two can finally be compared.",
            "",
            "`line call (all)` is agreement pooled over every flight, and it is "
            "NOT the number to read: with any realistic launch distribution most "
            "bounces land well inside the court, so metres of positional error still "
            "call them correctly and the figure saturates for cameras that are "
            "visibly bad. `line call NEAR A LINE` restricts to bounces whose TRUE "
            "position is within 0.5 m of a line — where a call is a call. Every "
            "camera judges the SAME bounces, so that column is a paired comparison.",
            "",
            "`speed err (low ball)` is median |error| for a ball under 1 m. The "
            "unrestricted figure is not tabulated on purpose: its p90 is ~+25,000%, "
            "because a near-grazing ray meets the court plane at infinity — it measures "
            "that tail, not the camera. It also exercises the `approx` fallback, NOT "
            "`speedspin`'s physics fit, so treat it as a floor.",
            "",
            f"Settings: {args.n} flights/setup, fps {args.fps:g}, "
            f"{args.pixel_noise:g}px noise @720p, {args.dropout:g} dropout, seed {args.seed}.",
            "",
            "## A. Controlled sweep — only the height changes",
            "",
            f"Camera on the centre line, {args.setback:g} m behind the near baseline "
            f"(regulation runback is 6.4 m), {args.hfov:g}° lens, "
            f"{args.width}x{args.height}. The pitch is re-solved at every height to keep "
            "the court framed, because that is the freedom a user actually has — they "
            "tilt the phone, they cannot move the fence. Every generated camera is "
            "round-tripped back through the same PnP the measurement uses, and the run "
            "aborts if the recovered height disagrees by more than 2%.",
            "",
            head, rule,
        ]
        L += [fmt_row(f"{s['commanded_m']:.2f} m", s["recovered_m"], s,
                      f" pitch {s['pitch_deg']:.0f}°") for s in sweep]
        L += ["", baseline_note(sweep).strip()]
        L += [
            "",
            "## B. Real committed calibrations — anchors, not curve points",
            "",
            "Every non-DEGENERATE calibration in `data/`, at its own audited resolution, "
            "with its lens solved by `courtfit.cam_fit_quad` — the same physical-camera "
            "fit that produced each file's audited height, so lens and height come from "
            "one solve. (`calibration.focal_from_homography` is only the fallback: it "
            "refuses outside 25-110 deg, which rejects the three high-mount and "
            "broadcast files outright.) These scatter around the sweep rather than lying "
            "on it — setback, lens and resolution all differ. `camera m` is re-derived "
            "here by PnP under that lens, so it can differ slightly from the `_audit` "
            "stamp.",
            "",
            head, rule,
        ]
        L += [fmt_row(s["clip"], s["recovered_m"], s, f" {s['verdict']}") for s in anchors]
        L += ["", baseline_note(anchors).strip()]
        if ctrl:
            L += [
                "",
                "## C. Control — is this height, or is it the frame rate?",
                "",
                "Our bounce estimate is the last TRACKED point, so at 30 fps with 30% "
                "dropout the last detection can land a frame or two before the ball "
                "actually does. That would depress every row above, and the curve would "
                "be a sampling result wearing a geometry result's clothes. Re-running "
                "three heights with the sampling handicap removed settles it.",
                "",
                "| camera | sampling | line call NEAR A LINE | bounce med |",
                "|---|---|---|---|",
                *ctrl,
            ]
        out.write_text("\n".join(L) + "\n", encoding="utf-8")
        print(f"\nwrote {out}")

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps({
            "tool": "height_curve",
            "measured_against":
                "EXACT simulated truth (drag+gravity+Magnus) through each camera. "
                "No human labels.",
            "settings": {"n": args.n, "fps": args.fps, "dropout": args.dropout,
                         "pixel_noise_720": args.pixel_noise,
                         "setback_m": args.setback, "hfov_deg": args.hfov,
                         "img_wh": [args.width, args.height], "seed": args.seed},
            "sweep": sweep, "anchors": anchors,
        }, indent=1), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
