"""backup_offmachine.py — copy the irreplaceable data to a drive you can unplug.

WHY THIS EXISTS
---------------
SCOREBOARD's Open table: `data/train_clips/` (20 videos, 2.73 GB) and
`data/ball_dataset/` (73,098 files, 3.45 GB) are gitignored and tracked by
nothing. The dataset is nominally regenerable from the videos, but re-processing
yields DIFFERENT pseudo-labels, so treat it as semi-irreplaceable too.

A second-disk copy already exists at C:\\SwingPath_Backup and retires single-disk
failure, which was the dominant risk. It does NOT cover fire, theft or
ransomware, because it is the same machine. That is what this closes, and it
needs a target you can physically unplug (or a remote you trust).

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It will not upload anywhere. Sending this data to a cloud service is a decision
about where a person's video of themselves and others is stored, and that belongs
to the user, not to a script that runs unattended. Point it at a path; if that
path happens to be a mounted cloud drive, that is the user's explicit choice.

THE GOTCHA THIS ALREADY COST SOMEONE
------------------------------------
`robocopy` exits **1 on a SUCCESSFUL copy** (and 0 only when nothing needed
copying). A wrapper that checks `returncode != 0` reports a false failure —
SCOREBOARD records that happening. Exit codes >= 8 are the real failures. This
uses Python's own copy instead, so the question does not arise, and verifies by
content rather than by trusting any exit code at all.

USAGE
-----
    py tools/backup_offmachine.py --dest F:/SwingPath_Backup
    py tools/backup_offmachine.py --dest F:/SwingPath_Backup --verify-only
    py tools/backup_offmachine.py --dest F:/SwingPath_Backup --quick

`--quick` verifies by size only (fast, ~seconds). The default hashes every file
(slow, minutes) — a size match is not a content match, and a silently corrupt
backup is worse than a missing one because it is trusted.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: What is irreplaceable AND not covered by git. Scope checked 2026-08-17:
#:   - data/train_clips  20 videos, 2.73 GB, gitignored -> needs this tool
#:   - data/ball_dataset 73,098 files, 3.45 GB, gitignored -> needs this tool
#:   - data/gold         DELIBERATELY NOT HERE. The part that matters - all 31
#:                       *.labels.json, the 2,159 human clicks that cannot be
#:                       regenerated at any price - IS tracked in git and pushed
#:                       to the private GitHub remote, so it is already
#:                       off-machine. The other ~3,185 files there are extracted
#:                       frame images, regenerable from the videos above.
#:                       Including it made this tool report 3,258 "missing" files
#:                       against a perfectly good backup.
TARGETS = ("data/train_clips", "data/ball_dataset")


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def walk(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file():
            yield p


def do_copy(src_root: Path, dst_root: Path, quick: bool) -> tuple[int, int]:
    copied = skipped = 0
    for src in walk(src_root):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            if quick or sha256(dst) == sha256(src):
                skipped += 1
                continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
        if copied % 500 == 0:
            print(f"    copied {copied}...", flush=True)
    return copied, skipped


def do_verify(src_root: Path, dst_root: Path, quick: bool) -> list[str]:
    problems = []
    n = 0
    for src in walk(src_root):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        n += 1
        if not dst.exists():
            problems.append(f"MISSING  {rel}")
            continue
        if dst.stat().st_size != src.stat().st_size:
            problems.append(f"SIZE     {rel}")
            continue
        if not quick and sha256(dst) != sha256(src):
            problems.append(f"CONTENT  {rel}")
    print(f"    checked {n} files")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dest", required=True,
                    help="a drive you can UNPLUG. Same-machine paths are "
                         "accepted but warned about - they do not close the risk "
                         "this tool exists for.")
    ap.add_argument("--quick", action="store_true",
                    help="verify by size only; default hashes every file")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()

    dest = Path(args.dest)
    if not dest.parent.exists() and not dest.exists():
        raise SystemExit(f"destination not reachable: {dest}\n"
                         "Plug the drive in, or pass a path that exists.")
    try:
        if str(dest.resolve()).lower().startswith(str(REPO.resolve()).lower()):
            raise SystemExit("destination is inside the repo - that is not a backup.")
    except OSError:
        pass
    if str(dest)[:1].upper() in ("C", "E"):
        print(f"WARNING: {dest} looks like an internal disk. This copy will not "
              f"survive fire, theft or ransomware, which is the whole point of "
              f"this tool. Continuing anyway.\n")

    total_problems = []
    for rel in TARGETS:
        src = REPO / rel
        if not src.exists():
            print(f"[skip] {rel} (not present)")
            continue
        # Match the layout the existing C:\SwingPath_Backup already uses:
        # basename at the destination root, NOT the repo-relative path. Got
        # this wrong first time and the tool reported a perfectly good
        # backup as 21 missing files - a backup checker that cries wolf is
        # worse than none, because the next real failure gets ignored.
        dst = dest / Path(rel).name
        print(f"[{rel}]")
        if not args.verify_only:
            dst.mkdir(parents=True, exist_ok=True)
            copied, skipped = do_copy(src, dst, args.quick)
            print(f"    copied {copied}, already-current {skipped}")
        problems = do_verify(src, dst, args.quick)
        if problems:
            print(f"    {len(problems)} PROBLEM(S):")
            for p in problems[:20]:
                print(f"      {p}")
            total_problems += problems
        else:
            print("    verified OK")
        print()

    if total_problems:
        print(f"FAILED: {len(total_problems)} file(s) did not verify. The backup "
              f"is NOT trustworthy - do not rely on it until this is clean.")
        sys.exit(1)
    mode = "size-only" if args.quick else "sha256"
    print(f"BACKUP VERIFIED ({mode}). Note what this does and does not cover: it "
          f"is only off-machine if {dest} is a drive you can physically remove.")


if __name__ == "__main__":
    main()
