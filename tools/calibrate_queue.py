"""calibrate_queue.py — hand-calibrate a list of clips, one after another.

WHY THIS EXISTS
---------------
Auto-calibration refuses on roughly half of amateur footage, by design: it has
never once accepted a wrong court, and that record is the reason any number
downstream of the homography can be trusted. A refusal costs about 30 seconds in
`court_setup_server.py` — but that tool takes ONE clip, so ten refusals means ten
rounds of remembering the command, inventing an output filename, and stopping the
server before starting the next one. That friction is why calibrations do not get
done, and an uncalibrated clip cannot contribute a speed, a line call, or a
far-court gate.

So this serves the queue: for each clip that has no calibration yet, it starts
the setup tool on a fixed port, opens the browser, waits for the file to appear,
then moves on. You Snap, Save, and it advances by itself.

    py tools/calibrate_queue.py --refused        # everything the audit refused
    py tools/calibrate_queue.py --clips data/train_clips/foo.mp4

Each save is written to `data/<clip>_pts.json` and audited immediately, so a
degenerate result is caught while the tool is still open rather than three
sessions later. `--skip-existing` (default) leaves finished clips alone, so
stopping half way and resuming later costs nothing.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = REPO / "backend" / ".venv" / "Scripts" / "python.exe"
PORT = 8790


def refused_clips(audit_path: Path):
    """Clips the audit could not auto-calibrate, worst agreement last."""
    if not audit_path.is_file():
        raise SystemExit(f"no audit at {audit_path} — run tools/audit_new_clips.py --new")
    rows = json.loads(audit_path.read_text(encoding="utf-8"))["clips"]
    out = [r for r in rows if not r.get("calibrated")]
    # Best-agreement first: those are the ones where auto-detect will seed the
    # overlay closest to right, so the click job gets harder as you go rather
    # than starting with the worst one.
    return [r["clip"] for r in sorted(out, key=lambda r: -r.get("votes", 0))]


def serve(video: Path, out: Path, port: int, timeout_s: float):
    """Run the setup tool until `out` appears. Returns True if it was saved."""
    before = out.stat().st_mtime if out.is_file() else None
    proc = subprocess.Popen(
        [str(PY), str(REPO / "tools/court_setup_server.py"),
         "--video", str(video), "--out", str(out),
         "--port", str(port), "--no-browser"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/"
    try:
        time.sleep(3.0)                      # the clean plate takes a few seconds
        webbrowser.open(url)
        print(f"    {url}  — auto-seed, Snap, Save. Ctrl+C here to skip.")
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if proc.poll() is not None:
                return out.is_file() and out.stat().st_mtime != before
            if out.is_file() and out.stat().st_mtime != before:
                time.sleep(1.0)              # let the write finish
                return True
            time.sleep(1.0)
        return False
    except KeyboardInterrupt:
        return False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def audit(pts: Path) -> str:
    """One-line verdict from the same auditor the pipeline warns on."""
    r = subprocess.run(
        [str(PY), str(REPO / "tools/validate_new_clip.py"), "--audit", str(pts),
         "--stamp"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "residual" in line.lower() or "verdict" in line.lower():
            return line.strip()
    return (r.stdout or r.stderr or "").strip().splitlines()[-1:] and \
        (r.stdout or r.stderr).strip().splitlines()[-1] or "no verdict"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clips", nargs="*", default=[])
    ap.add_argument("--refused", action="store_true",
                    help="every clip data/output/new_clip_audit.json refused")
    ap.add_argument("--audit-json",
                    default=str(REPO / "data/output/new_clip_audit.json"))
    ap.add_argument("--clip-dir", default=str(REPO / "data/train_clips"))
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--timeout", type=float, default=900.0,
                    help="seconds to wait for a save before moving on")
    ap.add_argument("--redo", dest="skip_existing", action="store_false",
                    default=True, help="re-calibrate clips that already have a file")
    args = ap.parse_args()

    names = [Path(c).stem for c in args.clips]
    if args.refused:
        names += refused_clips(Path(args.audit_json))
    if not names:
        raise SystemExit("nothing to do: pass --clips or --refused")

    todo = []
    for n in names:
        vid = Path(args.clip_dir) / f"{n}.mp4"
        pts = REPO / "data" / f"{n}_pts.json"
        if not vid.is_file():
            print(f"  skip {n}: no video at {vid}")
            continue
        if args.skip_existing and pts.is_file():
            print(f"  skip {n}: already calibrated ({pts.name})")
            continue
        todo.append((n, vid, pts))

    if not todo:
        print("\nnothing left to calibrate.")
        return
    print(f"\n{len(todo)} clip(s) to calibrate, ~30 s each. "
          f"Close the browser tab and it moves on when you Save.\n")

    done, skipped = [], []
    for i, (n, vid, pts) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {n}")
        if serve(vid, pts, args.port, args.timeout):
            print(f"    saved {pts.name} — {audit(pts)}")
            done.append(n)
        else:
            print("    skipped (no save)")
            skipped.append(n)

    print(f"\ncalibrated {len(done)}, skipped {len(skipped)}")
    if skipped:
        print("  still uncalibrated: " + ", ".join(skipped))
    if done:
        print("\nRe-run tools/audit_new_clips.py --new to pick up the new heights.")


if __name__ == "__main__":
    main()
