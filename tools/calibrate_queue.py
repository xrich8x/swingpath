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
the setup tool on a fixed port, waits for the file to appear, then moves on.
You Snap, Save, and it advances by itself.

ONE TAB, NOT ONE PER CLIP. Everything is served on the same port, so the tab
already points at the right URL and a RELOAD picks up the next clip. The
browser is opened for the first clip only — a first version opened it every
time and left ten windows behind on a ten-clip queue.

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


def wait_until_listening(port: int, proc, timeout_s: float = 240.0) -> bool:
    """Block until the setup tool is actually accepting connections.

    NOT a fixed sleep. The tool builds a temporal clean plate before it serves
    anything — decoding ~80 frames from a 60 s window — which is MEASURED at
    15.3 s on a 13-minute clip and 22.2 s on a 29-minute one. A first version
    slept 3 s and opened the browser into a dead port, which presents as "the
    server isn't connecting" rather than "it is still starting". Poll the
    socket, and say what is being waited for.
    """
    import socket

    deadline = time.time() + timeout_s
    told = False
    while time.time() < deadline:
        if proc.poll() is not None:
            return False                     # it exited; nothing to connect to
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        if not told and time.time() > deadline - timeout_s + 4:
            print("    building the clean plate (players removed) — "
                  "15-25 s. Do NOT reload until it says ready.")
            told = True
        time.sleep(1.0)
    return False


def wait_until_free(port: int, timeout_s: float = 20.0) -> bool:
    """Block until nothing is bound to `port` any more."""
    import socket

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return True
        time.sleep(0.5)
    return False


def serve(video: Path, out: Path, port: int, timeout_s: float,
          open_browser: bool = True):
    """Run the setup tool until `out` appears. Returns True if it was saved.

    `open_browser` is False for every clip after the first. The queue serves
    them all on ONE port, so the tab is already pointing at the right URL and a
    reload picks up the next clip; opening it per clip left ten tabs behind.
    """
    before = out.stat().st_mtime if out.is_file() else None
    # Keep the server's output. Sending it to DEVNULL made a failure to bind
    # the port indistinguishable from a slow start: both present as "nothing
    # is listening", and the reason was being thrown away.
    log_dir = REPO / "data" / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"court_setup_{out.stem}.log"
    fh = log.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        [str(PY), str(REPO / "tools/court_setup_server.py"),
         "--video", str(video), "--out", str(out),
         "--port", str(port), "--no-browser"],
        stdout=fh, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/"
    try:
        if not wait_until_listening(port, proc):
            tail = ""
            try:
                fh.flush()
                tail = log.read_text(encoding="utf-8",
                                     errors="replace").strip().splitlines()[-1:]
                tail = tail[0] if tail else ""
            except OSError:
                pass
            print(f"    could not start the setup tool — skipping. {tail}")
            print(f"    full log: {log}")
            return False
        if open_browser:
            webbrowser.open(url)
            print(f"    {url}  — auto-seed, Snap, Save. Ctrl+C here to skip.")
        else:
            print("    ready — RELOAD the browser tab. "
                  "Snap, Save. Ctrl+C here to skip.")
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
            proc.wait(timeout=5)
        fh.close()
        # The next clip reuses this port. Give the socket time to release,
        # or the next server dies on bind and the queue silently skips the
        # rest of the list.
        wait_until_free(port)


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
    ap.add_argument("--no-browser", dest="browser", action="store_false",
                    default=True,
                    help="never open a tab. For checking the queue without "
                         "leaving a browser window per clip behind")
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

    done, skipped, opened = [], [], False
    for i, (n, vid, pts) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {n}")
        want_tab = args.browser and not opened
        if want_tab:
            opened = True
        if serve(vid, pts, args.port, args.timeout, open_browser=want_tab):
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
