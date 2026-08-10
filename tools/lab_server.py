"""SwingVision Lab — add a clip, label it, train on it, score it. In a browser.

WHY THIS EXISTS
---------------
Labelling and training only ever happened when someone ran a script by hand,
so the data that would fix far-court ball recall never accumulated.
docs/sessions/SESSION_E_ball_push.md §E3j is explicit that the last ~20% of the
ball — the 2 px far/blurred one — cannot be taught by pseudo-labels, because the
teacher cannot see it either, and that the only way past ~80% far court is
synthetic blur or a few hundred HUMAN far-court labels. This is the tool that
makes collecting them a browser session instead of a Claude session.

WHAT IT IS NOT
--------------
It is not part of the analyzer. It never imports swingvision, never writes
match.json, and cannot change what the dashboard renders. It shells out to the
scripts that already exist. Delete this file and the product is unaffected.

THE RULE IT ENFORCES STRUCTURALLY
---------------------------------
ML_PRACTICES: never let a model grade its own homework. A clip is declared
"gold" (a TEST clip, hand-labelled, never trained on) or "train" at intake, and
that choice is ONE-WAY. The server refuses to build a training dataset from a
gold clip and refuses to cut gold frames from a train clip. train_ballnet.py's
own assert_no_gold_leak() stays as the second, independent line of defence —
CLAUDE.md records that the previous guard (`--exclude indoor_elev`) matched no
directory at all and "had been protecting nothing", which is exactly why this
one is enforced by the registry rather than by a flag someone has to remember.

RUNNING IT
----------
    py tools/lab_server.py

stdlib only, so it starts with no venv. It discovers backend/.venv (OpenCV, for
reading videos) and backend/.venv-train (torch + CUDA, for training) and uses
them for the subprocesses that need them. The labelling pages are the existing,
proven ones from gold_label_server.py, imported and served verbatim — no fork,
no restyle, and no risk of quietly changing labelling behaviour that every
number in this project depends on.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from gold_label_server import PAGE, PAGE_COURT, GoldStore   # noqa: E402
from lab_jobs import JobRunner                              # noqa: E402

GOLD_DIR = REPO / "data" / "gold"
# The second human-label pool. Same UI, same file format, opposite purpose:
# data/gold is the exam and is never trained on; data/labels is hand-clicked
# TRAINING material and is what labels_to_dataset.py converts. Keeping them in
# separate directories is what makes the train/test line a property of the
# filesystem rather than of somebody remembering.
LABELS_DIR = REPO / "data" / "labels"
CLIPS_DIR = REPO / "data" / "clips"
RUNS_DIR = REPO / "data" / "runs"
INCOMING = REPO / "data" / "incoming"
BALL_DATASET = REPO / "data" / "ball_dataset"
COURT_DATASET = REPO / "data" / "court_dataset"
WEIGHTS = REPO / "backend" / "weights"

VIDEO_DIRS = [REPO / "data", REPO / "data" / "train_clips",
              REPO / "data" / "amateur_clips", INCOMING]

ROLES = ("gold", "train")


# --------------------------------------------------------------------------
# interpreters
# --------------------------------------------------------------------------

def _venv_python(name: str) -> Path | None:
    base = REPO / "backend" / name
    for rel in ("Scripts/python.exe", "bin/python"):
        cand = base / rel
        if cand.exists():
            return cand
    return None


PY_CPU = _venv_python(".venv")            # OpenCV: probing, frame extraction
PY_TRAIN = _venv_python(".venv-train")    # torch + CUDA: training, model evals
PY_SELF = Path(sys.executable)


def interpreters() -> dict:
    return {
        "cpu": str(PY_CPU) if PY_CPU else None,
        "train": str(PY_TRAIN) if PY_TRAIN else None,
        "self": str(PY_SELF),
    }


def _run_sync(argv: list[str], timeout: int = 300) -> dict:
    """Run a short helper and parse its single JSON line. Never raises."""
    try:
        proc = subprocess.run([str(a) for a in argv], cwd=str(REPO),
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    out = (proc.stdout or "").strip()
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"error": (proc.stderr or out or "no output").strip()[-800:]}


# --------------------------------------------------------------------------
# clip registry — the train/gold boundary lives here
# --------------------------------------------------------------------------

class Registry:
    """data/clips/<id>.json, one file per clip. role is write-once."""

    def __init__(self, root: Path = CLIPS_DIR):
        self.root = root
        self._lock = threading.Lock()

    def path(self, clip_id: str) -> Path:
        return self.root / f"{clip_id}.json"

    def all(self) -> list[dict]:
        self.root.mkdir(parents=True, exist_ok=True)
        out = []
        for p in sorted(self.root.glob("*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        return out

    def get(self, clip_id: str) -> dict | None:
        p = self.path(clip_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def add(self, clip_id: str, video: Path, role: str, info: dict) -> dict:
        if role not in ROLES:
            return {"error": f"role must be one of {ROLES}, got {role!r}"}
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", clip_id):
            return {"error": "clip id must be 1-64 chars of [A-Za-z0-9._-]"}
        with self._lock:
            existing = self.get(clip_id)
            if existing is not None:
                # One-way role. Re-adding the same clip with the same role is a
                # harmless refresh; flipping it is the thing that would poison
                # every benchmark number, so it is refused outright.
                if existing.get("role") != role:
                    return {"error":
                            f"{clip_id!r} is already registered as "
                            f"{existing.get('role')!r}. Roles are one-way — a "
                            f"clip cannot move between train and gold. Register "
                            f"it under a new id if you really mean to."}
            self.root.mkdir(parents=True, exist_ok=True)
            rec = {
                "id": clip_id,
                "role": role,
                "video": _rel(video),
                "created": (existing or {}).get(
                    "created", time.strftime("%Y-%m-%d %H:%M:%S")),
                "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "pts_file": (existing or {}).get("pts_file"),
            }
            for key in ("width", "height", "fps", "video_frames", "video_sha1",
                        "duration_s", "size_mb"):
                if key in info:
                    rec[key] = info[key]
            tmp = self.path(clip_id).with_suffix(".json.tmp")
            tmp.write_text(json.dumps(rec, indent=1), encoding="utf-8")
            os.replace(tmp, self.path(clip_id))
            return rec

    def set_pts(self, clip_id: str, pts: str) -> dict | None:
        with self._lock:
            rec = self.get(clip_id)
            if rec is None:
                return None
            rec["pts_file"] = pts
            rec["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tmp = self.path(clip_id).with_suffix(".json.tmp")
            tmp.write_text(json.dumps(rec, indent=1), encoding="utf-8")
            os.replace(tmp, self.path(clip_id))
            return rec


def _rel(p: Path) -> str:
    p = Path(p).resolve()
    try:
        return p.relative_to(REPO).as_posix()
    except ValueError:
        return p.as_posix()


# --------------------------------------------------------------------------
# gold protection — derived, never hand-maintained
# --------------------------------------------------------------------------

def protected_sources() -> dict:
    """Videos a human has hand-labelled, split by which benchmark they belong to.

    Ball and court gold are kept apart on purpose: train_ballnet's own
    gold_source_videos() skips *.court.manifest.json, because court-corner
    labels are not a ball benchmark. Mirroring that split exactly is what lets
    the Lab claim it agrees with the trainer — if it used one merged set it
    would disagree, and a guard that disagrees with the thing it is guarding is
    worse than no guard.

    Basenames are lower-cased to match the trainer's comparison.
    """
    ball_v: set[str] = set()
    court_v: set[str] = set()
    sha1s: set[str] = set()
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    for man_path in GOLD_DIR.glob("*.manifest.json"):
        try:
            man = json.loads(man_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        target = court_v if ".court." in man_path.name else ball_v
        if man.get("video"):
            target.add(Path(man["video"]).name.lower())
        if man.get("video_sha1"):
            sha1s.add(man["video_sha1"])
    return {"ball": sorted(ball_v), "court": sorted(court_v),
            "sha1s": sorted(sha1s)}


def dataset_rows() -> list[dict]:
    """Every ball-dataset dir, with the gold-leak verdict spelled out.

    Three states, and the third one matters:
      protected  — provenance names a gold video. Never train on it.
      ok         — provenance names a video that is not gold. Checked, clean.
      unverified — labels.json records NO source video, so the guard cannot say
                   either way. train_ballnet passes these silently (its check is
                   `if vid and ...`), which reads as approval in the log. It is
                   shown here as its own state so an unverifiable dir is a
                   decision rather than an omission.
    """
    prot = protected_sources()
    rows = []
    if not BALL_DATASET.exists():
        return rows
    for d in sorted(p for p in BALL_DATASET.iterdir() if p.is_dir()):
        labels = d / "labels.json"
        if not labels.exists():
            continue        # the trainer skips dirs without labels.json too
        try:
            data = json.loads(labels.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        prov = data.get("provenance") or {}
        src = prov.get("video")
        protected = bool(src) and Path(src).name.lower() in prot["ball"]
        # A dataset with no recorded source video is not necessarily unverifiable.
        # tools/verify_dataset_not_gold.py answers the question from the PIXELS —
        # dHash every frame against every gold clip — and records the verdict
        # here. "unverified" is then reserved for dirs nobody has checked at all,
        # rather than covering ones that were checked a harder way.
        gchk = prov.get("gold_check") or {}
        hash_clean = gchk.get("verdict") == "not gold"
        # TWO DIFFERENT NUMBERS, and conflating them inverted this table.
        #   negatives      — labels.json's no-ball top-up frames (extend_noball_frames)
        #   hard_negatives — hard_negatives.json, MINED confuser frames
        #                    (mine_hard_negatives.py)
        # This column used to show only the first while the row's pill said "hard
        # negs", so the dataset Session F identified as the WORST-mined
        # (yt_am_dbl_classb, 52 mined = 2.5% of labels) read as the BEST-covered
        # here at 426. The mined fraction is the number three sessions of
        # false-fire work turned on, so it is now shown as its own column with the
        # percentage that makes under-mining visible.
        n_labels = len(data.get("labels", {}) or {})
        hard = 0
        hn = d / "hard_negatives.json"
        if hn.exists():
            try:
                hard = len(json.loads(hn.read_text(encoding="utf-8"))
                           .get("hard_negatives", []) or [])
            except (json.JSONDecodeError, OSError):
                hard = 0
        rows.append({
            "name": d.name,
            "path": _rel(d),
            "frames": data.get("n_frames", 0),
            "labels": n_labels,
            "negatives": len(data.get("negatives", []) or []),
            "hard_count": hard,
            "hard_pct": round(100.0 * hard / n_labels, 1) if n_labels else 0.0,
            "source": src,
            "protected": protected,
            "verified": bool(src) or hash_clean,
            "state": ("protected" if protected else
                      "ok" if src else
                      "hash-checked" if hash_clean else "unverified"),
            "gold_check": ({"min_hamming": gchk.get("min_hamming"),
                            "n_clips": len(gchk.get("checked_against") or []),
                            "date": gchk.get("date")} if gchk else None),
            "hard_negatives": hn.exists(),
        })
    return rows


def court_dataset_rows() -> list[dict]:
    rows = []
    if not COURT_DATASET.exists():
        return rows
    for d in sorted(p for p in COURT_DATASET.iterdir() if p.is_dir()):
        labels = d / "labels.json"
        row = {"name": d.name, "path": _rel(d), "frames": 0, "labels": 0,
               "source": None}
        if labels.exists():
            try:
                data = json.loads(labels.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
            row["frames"] = data.get("n_frames", 0)
            row["labels"] = len(data.get("labels", {}) or {})
            row["source"] = data.get("source")
        rows.append(row)
    return rows


def weight_rows() -> list[dict]:
    rows = []
    if not WEIGHTS.exists():
        return rows
    for p in sorted(WEIGHTS.glob("*.pt")) + sorted(WEIGHTS.glob("*.pth.tar")):
        stat = p.stat()
        rows.append({
            "name": p.name,
            "path": _rel(p),
            "size_mb": round(stat.st_size / 1e6, 1),
            "modified": time.strftime("%Y-%m-%d %H:%M",
                                      time.localtime(stat.st_mtime)),
        })
    return rows


def suggest_weight_name(prefix: str) -> str:
    """First free <prefix>_v<N>.pt. Never proposes overwriting a weights file."""
    for n in range(2, 100):
        cand = WEIGHTS / f"{prefix}_v{n}.pt"
        if not cand.exists():
            return cand.name
    return f"{prefix}_v{int(time.time())}.pt"


def discover_videos(registry: Registry) -> list[dict]:
    known = {r.get("video") for r in registry.all()}
    out = []
    for d in VIDEO_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.mp4")):
            rel = _rel(p)
            out.append({
                "video": rel,
                "name": p.stem,
                "size_mb": round(p.stat().st_size / 1e6, 1),
                "registered": rel in known,
                "dir": _rel(d),
            })
    return out


def chain_clips(store: GoldStore) -> list[str]:
    """Gold ball clips the full-chain evaluator can actually run on.

    eval_model_filters walks the shipped post-chain, which includes the court
    gate — so it needs a calibration, and its own CLIPS table lists exactly the
    three gold clips that have one. Deriving the same set from what is on disk
    rather than copying that table means a newly calibrated gold clip shows up
    here on its own, instead of the dropdown silently offering a clip the
    evaluator will reject.
    """
    out = []
    for c in store.clips():
        if (REPO / "data" / f"{c['clip']}_pts.json").exists():
            out.append(c["clip"])
    return out


def calibration_files() -> list[str]:
    out = []
    for p in sorted(REPO.glob("data/*_pts*.json")):
        out.append(_rel(p))
    for p in sorted(REPO.glob("data/amateur_clips/*_pts*.json")):
        out.append(_rel(p))
    return out


# --------------------------------------------------------------------------
# labelling session filter
# --------------------------------------------------------------------------

class SessionFilter:
    """Restrict a labelling session to certain manifest buckets.

    §E3j says the far-court labels are the valuable ones, so it must be possible
    to spend 300 clicks there rather than uniformly. This filters WHICH frames
    the labeller is shown; it does not tell them anything about the frame in
    front of them, so per-frame blindness is intact. Session-level knowledge
    ("everything today is far court") is the honest cost, and it is stated in
    the UI rather than hidden.
    """

    def __init__(self):
        self.clip: str | None = None
        self.buckets: list[str] = []

    def set(self, clip: str | None, buckets: list[str]) -> None:
        self.clip = clip or None
        self.buckets = [b for b in buckets if b]

    def active_for(self, clip: str) -> bool:
        return bool(self.buckets) and self.clip == clip

    def apply(self, manifest: dict) -> dict:
        clip = manifest.get("clip", "")
        if not self.active_for(clip):
            return manifest
        keep = [f for f in manifest.get("frames", [])
                if f.get("bucket") in self.buckets]
        out = dict(manifest)
        out["frames"] = keep
        out["_lab_filter"] = {"buckets": self.buckets, "kept": len(keep),
                              "of": len(manifest.get("frames", []))}
        return out

    def to_dict(self) -> dict:
        return {"clip": self.clip, "buckets": self.buckets}


def manifest_buckets(store: GoldStore, clip: str) -> dict:
    try:
        man = store.manifest(clip)
    except (FileNotFoundError, OSError):
        return {}
    counts: dict[str, int] = {}
    for f in man.get("frames", []):
        counts[f.get("bucket", "?")] = counts.get(f.get("bucket", "?"), 0) + 1
    return counts


# --------------------------------------------------------------------------
# eval results
# --------------------------------------------------------------------------

def eval_results(limit: int = 40) -> list[dict]:
    """Every eval JSON the Lab has produced, newest first."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(RUNS_DIR.glob("*.eval.json"), reverse=True)[:limit]:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        data["_file"] = _rel(p)
        out.append(data)
    return out


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    store: GoldStore          # data/gold  — the TEST pool
    train_store: GoldStore    # data/labels — the human TRAINING pool
    registry: Registry
    jobs: JobRunner
    session: SessionFilter
    device: str = "cuda"

    def log_message(self, *a):
        pass

    # -- plumbing ---------------------------------------------------------

    def _send(self, code: int, body: bytes, ctype: str, cache: bool = False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if cache:
            self.send_header("Cache-Control", "max-age=86400, immutable")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass    # the page navigated away mid-poll; not an error

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def _html(self, text: str):
        self._send(200, text.encode("utf-8"), "text/html; charset=utf-8")

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    # -- GET --------------------------------------------------------------

    def do_GET(self):
        url = urlparse(self.path)
        path, query = url.path, parse_qs(url.query)

        if path == "/":
            return self._html(LAB_PAGE)
        if path == "/label":
            return self._html(_labeller_page(PAGE))
        if path in ("/label/court", "/court"):
            return self._html(_court_page(PAGE_COURT))
        # The same two pages again, re-pointed at the training pool. Two mounted
        # copies rather than one page with a mode switch: a stale tab then
        # cannot write labels into the wrong pool, because the pool is baked
        # into the URLs the page fetches.
        if path == "/train/label":
            return self._html(_train_page(_labeller_page(PAGE)))
        if path == "/train/label/court":
            return self._html(_train_page(_court_page(PAGE_COURT)))
        if path.startswith("/train/"):
            return self._get_pool(self.train_store, path[len("/train"):], query)

        # --- the Lab's own API (checked before the pool routes) ---------
        if path == "/api/lab/overview":
            return self._json(self._overview())
        if path == "/api/lab/videos":
            return self._json(discover_videos(self.registry))
        if path == "/api/lab/jobs":
            return self._json({"jobs": self.jobs.list(),
                               "busy": self.jobs.busy()})
        if path == "/api/lab/job":
            job_id = query.get("id", [""])[0]
            offset = int(query.get("offset", ["0"])[0] or 0)
            out = self.jobs.tail(job_id, offset)
            out["progress"] = self.jobs.progress(job_id)
            return self._json(out)
        if path == "/api/lab/results":
            return self._json(eval_results())
        if path == "/api/lab/buckets":
            clip = query.get("clip", [""])[0]
            pool = query.get("pool", ["gold"])[0]
            store = self.train_store if pool == "train" else self.store
            return self._json(manifest_buckets(store, clip))

        # --- the labeller's own API, served unchanged, for the gold pool
        return self._get_pool(self.store, path, query)

    def _get_pool(self, store: GoldStore, path: str, query: dict):
        """Serve the labeller API against whichever pool `store` points at."""
        if path == "/api/clips":
            return self._json(store.clips())
        if path == "/api/court_clips":
            return self._json(store.court_clips())
        if path == "/api/state":
            clip = query.get("clip", [""])[0]
            try:
                return self._json({
                    "manifest": self.session.apply(store.manifest(clip)),
                    "labels": store.load_labels(clip)["labels"]})
            except FileNotFoundError:
                return self._json({"error": f"no manifest for clip {clip!r}"}, 404)
        if path == "/api/court_state":
            clip = query.get("clip", [""])[0]
            try:
                return self._json({
                    "manifest": store.court_manifest(clip),
                    "labels": store.load_court_labels(clip)["labels"]})
            except FileNotFoundError:
                return self._json(
                    {"error": f"no court manifest for clip {clip!r}"}, 404)
        if path.startswith("/frames/"):
            return self._serve_frame(store, path[len("/frames/"):])
        return self._send(404, b"not found", "text/plain")

    def _serve_frame(self, store: GoldStore, rel: str):
        base = (store.gold_dir / "frames").resolve()
        target = (base / rel).resolve()
        if base not in target.parents:
            return self._send(403, b"forbidden", "text/plain")
        if target.is_file():
            return self._send(200, target.read_bytes(), "image/jpeg", cache=True)
        return self._send(404, b"missing frame (re-run frame selection?)",
                          "text/plain")

    def _overview(self) -> dict:
        return {
            "registry": self.registry.all(),
            "gold_ball": self.store.clips(),
            "gold_court": self.store.court_clips(),
            "train_ball": self.train_store.clips(),
            "train_court": self.train_store.court_clips(),
            "datasets": dataset_rows(),
            "court_datasets": court_dataset_rows(),
            "weights": weight_rows(),
            "protected": protected_sources(),
            "interpreters": interpreters(),
            "suggest": {"ballnet": suggest_weight_name("ballnet"),
                        "courtnet": suggest_weight_name("courtnet")},
            "session": self.session.to_dict(),
            "busy": self.jobs.busy(),
            "device": self.device,
            "calibrations": calibration_files(),
            "chain_clips": chain_clips(self.store),
        }

    # -- POST -------------------------------------------------------------

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()

        # the labeller's writes. The /train/ prefix picks the pool, so a page
        # can only ever write into the pool whose URLs it was served with.
        store = self.store
        if path.startswith("/train/"):
            store, path = self.train_store, path[len("/train"):]
        if path == "/api/label":
            n = store.set_label(body["clip"], int(body["frame"]),
                                body.get("label"))
            return self._json({"ok": True, "labeled": n})
        if path == "/api/court_label":
            n = store.set_court_label(body["clip"], int(body["frame"]),
                                      body.get("label"))
            return self._json({"ok": True, "labeled": n})

        handlers = {
            "/api/lab/trim": self._post_trim,
            "/api/lab/intake": self._post_intake,
            "/api/lab/frames": self._post_frames,
            "/api/lab/calibrate": self._post_calibrate,
            "/api/lab/dataset": self._post_dataset,
            "/api/lab/human_dataset": self._post_human_dataset,
            "/api/lab/train": self._post_train,
            "/api/lab/eval": self._post_eval,
            "/api/lab/cancel": self._post_cancel,
            "/api/lab/session": self._post_session,
        }
        fn = handlers.get(path)
        if fn is None:
            return self._send(404, b"not found", "text/plain")
        try:
            return self._json(fn(body))
        except Exception as exc:                       # noqa: BLE001
            return self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    # -- POST handlers ----------------------------------------------------

    def _post_trim(self, body: dict) -> dict:
        """Cut a long recording down before anything else touches it.

        Deliberately does NOT register the result: trimming and declaring
        gold-vs-train are separate decisions, and the second one is irreversible.
        The trimmed file lands beside the source, so it appears in the video list
        for the next step.
        """
        video_rel = (body.get("video") or "").strip()
        start, end = (body.get("start") or "0").strip(), (body.get("end") or "").strip()
        if not video_rel or not end:
            return {"error": "video and end time are required"}
        src = (REPO / video_rel).resolve()
        if not src.is_file():
            return {"error": f"no such video: {video_rel}"}
        if PY_CPU is None:
            return {"error": "backend/.venv not found - it provides ffmpeg"}

        name = (body.get("name") or "").strip()
        dst = src.with_name((name or (src.stem + "_trim")) + ".mp4")
        if dst.resolve() == src:
            return {"error": "the trimmed name matches the source video"}
        if dst.exists():
            return {"error": f"{dst.name} already exists - pick another name"}

        cmd = [str(PY_CPU), str(REPO / "tools" / "trim_clip.py"), str(src),
               "--start", start, "--end", end, "--out", str(dst)]
        if body.get("fast"):
            cmd.append("--fast")
        job = self.jobs.submit("trim", cmd, REPO, meta={"out": dst.name},
                               label=f"trim {src.name} -> {dst.name}")
        return {"ok": True, "job": job.id, "out": str(dst.relative_to(REPO))}

    def _post_intake(self, body: dict) -> dict:
        video_rel = (body.get("video") or "").strip()
        clip_id = (body.get("id") or "").strip()
        role = (body.get("role") or "").strip()
        if not video_rel or not clip_id or not role:
            return {"error": "video, id and role are all required"}
        video = (REPO / video_rel).resolve()
        if not video.is_file():
            return {"error": f"no such video: {video_rel}"}
        if PY_CPU is None:
            return {"error": "backend/.venv not found — it provides OpenCV, "
                             "which is needed to read the video"}

        info = _run_sync([PY_CPU, REPO / "tools" / "lab_probe.py",
                          "probe", video])
        if "error" in info:
            return {"error": f"probe failed: {info['error']}"}

        rec = self.registry.add(clip_id, video, role, info)
        if "error" in rec:
            return rec

        # The resolution gate + calibration audit, as its own job so its full
        # output is readable rather than summarised away.
        job = self.jobs.submit(
            "intake",
            [str(PY_CPU), str(REPO / "tools" / "validate_new_clip.py"),
             str(video)],
            REPO, meta={"clip": clip_id}, label=f"validate {clip_id}")
        return {"ok": True, "clip": rec, "probe": info, "job": job.id}

    def _post_calibrate(self, body: dict) -> dict:
        clip_id = (body.get("id") or "").strip()
        rec = self.registry.get(clip_id)
        if rec is None:
            return {"error": f"unknown clip {clip_id!r}"}
        if PY_CPU is None:
            return {"error": "backend/.venv not found (OpenCV needed)"}
        port = int(body.get("port") or 8770)
        out = REPO / "data" / f"{clip_id}_pts.json"
        argv = [str(PY_CPU), str(REPO / "tools" / "court_setup_server.py"),
                "--video", str(REPO / rec["video"]),
                "--out", str(out), "--port", str(port), "--no-browser"]
        try:
            subprocess.Popen(argv, cwd=str(REPO))
        except OSError as exc:
            return {"error": f"could not start the court tool: {exc}"}
        self.registry.set_pts(clip_id, _rel(out))
        return {"ok": True, "url": f"http://127.0.0.1:{port}/",
                "out": _rel(out),
                "note": "Drag the four corners, then Save in that tab."}

    def _post_frames(self, body: dict) -> dict:
        clip_id = (body.get("id") or "").strip()
        kind = (body.get("kind") or "ball").strip()
        count = int(body.get("count") or 250)
        segments = (body.get("segments") or "").strip()
        if segments and kind != "ball":
            return {"error": f"Segments only apply to ball frames; the "
                             f"{kind!r} selector samples its own way. Clear the "
                             f"Segments box, or choose 'ball'."}
        rec = self.registry.get(clip_id)
        if rec is None:
            return {"error": f"unknown clip {clip_id!r}"}
        if PY_CPU is None:
            return {"error": "backend/.venv not found (OpenCV needed)"}
        video = REPO / rec["video"]

        # The clip's role decides which pool the frames land in. Both pools are
        # hand-labelled in the same UI; only their destination differs, and the
        # role was fixed one-way at intake.
        role = rec.get("role")
        out_dir = LABELS_DIR if role == "train" else GOLD_DIR
        out_rel = _rel(out_dir)

        if kind == "court":
            argv = [str(PY_CPU), str(REPO / "tools" / "court_gold_frames.py"),
                    str(video), "--clip", clip_id, "--n", str(count),
                    "--out", out_rel]
        elif kind == "noball":
            argv = [str(PY_CPU), str(REPO / "tools" / "extend_noball_frames.py"),
                    "--clip", clip_id, "--count", str(count),
                    "--gold-dir", out_rel]
        else:
            argv = [str(PY_CPU), str(REPO / "tools" / "select_gold_frames.py"),
                    "--video", _rel(video), "--clip", clip_id,
                    "--target", str(count), "--match", "", "--caches",
                    "--out", out_rel]
            pts = rec.get("pts_file")
            argv += ["--keypoints", pts] if pts else ["--keypoints", ""]
            # Only the ball selector understands time windows; the court and
            # no-ball tools sample their own way, so silently passing it there
            # would be a flag that does nothing.
            if segments:
                argv += ["--segments", segments]

        job = self.jobs.submit("frames", argv, REPO,
                               meta={"clip": clip_id, "kind": kind,
                                     "pool": role, "out": out_rel},
                               label=f"{kind} frames: {clip_id} -> {out_rel}")
        return {"ok": True, "job": job.id, "pool": role, "out": out_rel}

    def _post_human_dataset(self, body: dict) -> dict:
        """Human labels (data/labels) -> a BallNet training dataset dir.

        This is the loop the project did not have: until now the training set
        was entirely tracker pseudo-labels, which cannot teach the far-court
        ball because the tracker cannot see it either.
        """
        clip_id = (body.get("id") or "").strip()
        rec = self.registry.get(clip_id)
        if rec is None:
            return {"error": f"unknown clip {clip_id!r}"}
        if rec.get("role") != "train":
            return {"error":
                    f"{clip_id!r} is registered as {rec.get('role')!r}. Only a "
                    f"'train' clip's labels may become training data."}
        labels = LABELS_DIR / f"{clip_id}.labels.json"
        if not labels.exists():
            return {"error": f"no labels yet at {_rel(labels)} — cut frames and "
                             f"label some first."}
        if PY_CPU is None:
            return {"error": "backend/.venv not found (OpenCV needed)"}
        argv = [str(PY_CPU), str(REPO / "tools" / "labels_to_dataset.py"),
                "--clip", f"{clip_id}_human", "--video", rec["video"],
                "--labels", _rel(labels)]
        job = self.jobs.submit("dataset", argv, REPO,
                               meta={"clip": clip_id, "source": "human"},
                               label=f"human labels -> dataset: {clip_id}")
        return {"ok": True, "job": job.id}

    def _post_dataset(self, body: dict) -> dict:
        clip_id = (body.get("id") or "").strip()
        rec = self.registry.get(clip_id)
        if rec is None:
            return {"error": f"unknown clip {clip_id!r}"}
        if rec.get("role") != "train":
            return {"error":
                    f"{clip_id!r} is registered as {rec.get('role')!r}. Only a "
                    f"'train' clip can be turned into a training dataset."}
        prot = protected_sources()
        if Path(rec["video"]).name.lower() in prot["ball"]:
            return {"error":
                    f"{rec['video']} has hand-labelled gold frames. Refusing "
                    f"to build training data from a benchmark clip."}
        if PY_TRAIN is None:
            return {"error": "backend/.venv-train not found (torch needed)"}
        argv = [str(PY_TRAIN), str(REPO / "backend" / "relabel_train_clips.py"),
                "--only", Path(rec["video"]).stem, "--device", self.device]
        job = self.jobs.submit("dataset", argv, REPO / "backend",
                               meta={"clip": clip_id},
                               label=f"dataset: {clip_id}")
        return {"ok": True, "job": job.id}

    def _post_train(self, body: dict) -> dict:
        model = (body.get("model") or "ballnet").strip()
        epochs = int(body.get("epochs") or 40)
        out_name = (body.get("out") or "").strip()
        exclude = [str(x) for x in (body.get("exclude") or []) if x]
        if PY_TRAIN is None:
            return {"error": "backend/.venv-train not found — training needs "
                             "torch with CUDA"}
        if not out_name.endswith(".pt"):
            return {"error": "the output weights name must end in .pt"}
        if "/" in out_name or "\\" in out_name:
            return {"error": "give a bare filename, not a path"}
        if (WEIGHTS / out_name).exists():
            return {"error":
                    f"{out_name} already exists. ML_PRACTICES: always save to a "
                    f"NEW filename — a lost working model is expensive and "
                    f"weights are cheap."}

        if model == "courtnet":
            script, prefix = "train_courtnet.py", "courtnet"
        else:
            script, prefix = "train_ballnet.py", "ballnet"
        argv = [str(PY_TRAIN), script, "--epochs", str(epochs),
                "--out", f"weights/{out_name}", "--device", self.device]

        if model != "courtnet":
            # Whatever the page sent, every protected dir is excluded here as
            # well. The browser is a convenience, not the guard — a stale tab or
            # a hand-made POST must not be able to train on the benchmark.
            rows = dataset_rows()
            names = {r["name"] for r in rows}
            forced = {r["name"] for r in rows if r["protected"]}
            bad = [x for x in exclude if x not in names]
            if bad:
                return {"error": f"--exclude names no dataset dir: {bad}"}
            exclude = sorted(set(exclude) | forced)
            if exclude:
                argv += ["--exclude", *exclude]
        job = self.jobs.submit("train", argv, REPO / "backend",
                               meta={"model": model, "out": out_name,
                                     "epochs": epochs, "exclude": exclude,
                                     "prefix": prefix},
                               label=f"train {model} -> {out_name}")
        return {"ok": True, "job": job.id}

    def _post_eval(self, body: dict) -> dict:
        kind = (body.get("kind") or "detector").strip()
        weights = [str(w) for w in (body.get("weights") or []) if w]
        clip = (body.get("clip") or "").strip()
        if PY_TRAIN is None:
            return {"error": "backend/.venv-train not found (torch needed)"}

        stamp = time.strftime("%Y%m%d-%H%M%S")
        out_json = RUNS_DIR / f"{stamp}.{kind}.eval.json"
        RUNS_DIR.mkdir(parents=True, exist_ok=True)

        if kind in ("court", "court_learned"):
            argv = [str(PY_TRAIN), str(REPO / "tools" / "eval_court.py"),
                    "--all", "--json", str(out_json)]
            if kind == "court_learned":
                argv.append("--learned")
        elif kind == "chain":
            if not weights:
                return {"error": "pick at least one weights file"}
            argv = [str(PY_TRAIN), str(REPO / "tools" / "eval_model_filters.py"),
                    "--weights", *weights, "--device", self.device,
                    "--json", str(out_json)]
            if clip:
                argv += ["--clip", clip]
        else:
            if not weights:
                return {"error": "pick at least one weights file"}
            argv = [str(PY_TRAIN), str(REPO / "tools" / "eval_detector_gold.py"),
                    "--weights", *weights, "--device", self.device,
                    "--json", str(out_json)]

        job = self.jobs.submit("eval", argv, REPO,
                               meta={"kind": kind, "weights": weights,
                                     "clip": clip, "json": _rel(out_json)},
                               label=f"eval {kind}: {', '.join(
                                   Path(w).name for w in weights) or 'all'}")
        return {"ok": True, "job": job.id, "json": _rel(out_json)}

    def _post_cancel(self, body: dict) -> dict:
        job_id = (body.get("id") or "").strip()
        return {"ok": self.jobs.cancel(job_id)}

    def _post_session(self, body: dict) -> dict:
        self.session.set(body.get("clip"), body.get("buckets") or [])
        return {"ok": True, "session": self.session.to_dict()}


def _labeller_page(page: str) -> str:
    """Serve the ball labeller unchanged except for its two nav links."""
    page = page.replace('href="/court"', 'href="/label/court"')
    return page.replace(
        "<h1>Gold ball labeler</h1>",
        '<h1>Gold ball labeler</h1>\n  <a href="/" style="color:#8fd6ff;'
        'text-decoration:none;font-weight:600">&larr; Lab</a>')


def _train_page(page: str) -> str:
    """Re-point a labeller page at the training pool.

    Only the fetch/image URLs change, so the labelling behaviour — including its
    blindness to model output — is byte-for-byte the page that produced every
    gold label in this repo. The banner is there because the one thing a
    labeller must never be unsure of is which pool they are filling.
    """
    page = page.replace("/api/", "/train/api/").replace("/frames/", "/train/frames/")
    page = page.replace('href="/label/court"', 'href="/train/label/court"')
    page = page.replace('<a class="nav" href="/label">',
                        '<a class="nav" href="/train/label">')
    banner = ('<div style="background:#22303d;color:#8fd6ff;padding:6px 16px;'
              'font-size:13px;font-weight:600">TRAINING POOL (data/labels) — '
              'these labels are used to TRAIN. They are not a benchmark.</div>')
    return page.replace("<body>", "<body>\n" + banner, 1)


def _court_page(page: str) -> str:
    page = page.replace('<a class="nav" href="/">', '<a class="nav" href="/label">')
    return page.replace(
        "<h1>Gold court labeler</h1>",
        '<h1>Gold court labeler</h1>\n  <a href="/" style="color:#8fd6ff;'
        'text-decoration:none;font-weight:600">&larr; Lab</a>')


LAB_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SwingVision Lab</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #14171c; color: #dfe4ea;
         font: 14px/1.5 system-ui, sans-serif; }
  header { display: flex; align-items: center; gap: 16px; padding: 12px 20px;
           background: #1d2129; border-bottom: 1px solid #39404d; }
  header h1 { font-size: 16px; margin: 0; font-weight: 600; }
  header .sp { flex: 1; }
  .tabs { display: flex; gap: 4px; padding: 0 20px; background: #1d2129; }
  .tab { padding: 9px 18px; cursor: pointer; border: none; background: none;
         color: #8b93a1; font: inherit; border-bottom: 2px solid transparent; }
  .tab.on { color: #dfe4ea; border-bottom-color: #8fd6ff; font-weight: 600; }
  /* The guided flow. A step you cannot do yet is dimmed rather than hidden, so
     the whole path stays visible and nothing appears out of nowhere. */
  .stp { position: relative; }
  .stp .n { display: inline-flex; width: 26px; height: 26px; border-radius: 50%;
    align-items: center; justify-content: center; margin-right: 9px;
    background: #2a3140; color: #9aa4b2; font-size: 14px; font-weight: 700; }
  .stp.now { border-color: #8fd6ff; box-shadow: 0 0 0 1px #8fd6ff33; }
  .stp.now .n { background: #8fd6ff; color: #10141b; }
  .stp.done .n { background: #2e7d5b; color: #eafff5; }
  .stp.todo { opacity: .45; }
  .stp.todo button, .stp.todo input, .stp.todo select { pointer-events: none; }
  .sub { margin: 14px 0 4px; padding-top: 12px; border-top: 1px solid #232a35; }
  .badge { float: right; font-size: 12px; font-weight: 600; padding: 3px 10px;
    border-radius: 11px; background: #2a3140; color: #9aa4b2; }
  .stp.done .badge { background: #17392b; color: #7fe0b0; }
  .stp.now .badge { background: #10314a; color: #8fd6ff; }
  main { padding: 20px; max-width: 1180px; }
  section { display: none; } section.on { display: block; }
  .card { background: #1a1e25; border: 1px solid #39404d; border-radius: 8px;
          padding: 16px; margin-bottom: 16px; }
  .card h2 { font-size: 14px; margin: 0 0 12px; font-weight: 600;
             color: #8fd6ff; text-transform: uppercase; letter-spacing: .04em; }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
         margin-bottom: 10px; }
  label.f { display: flex; flex-direction: column; gap: 4px; font-size: 12px;
            color: #8b93a1; }
  select, button, input { font: inherit; border-radius: 6px;
      border: 1px solid #39404d; background: #262c37; color: #dfe4ea;
      padding: 7px 12px; }
  button { cursor: pointer; } button:hover:not(:disabled) { background: #313949; }
  button:disabled { opacity: .45; cursor: not-allowed; }
  button.go { background: #235c40; border-color: #2f7a55; font-weight: 600; }
  button.go:hover:not(:disabled) { background: #2c6f4d; }
  button.warn { background: #7c2d2d; border-color: #a33; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #262c37; }
  th { color: #8b93a1; font-weight: 600; font-size: 12px;
       text-transform: uppercase; letter-spacing: .03em; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  /* an under-mined dataset: the legacy tier runs 9-26% hard negatives, and
     dropping under ~8% is what diluted v3 (Session F). Worth seeing at a glance. */
  td.num.warn { color: #ff9c9c; font-weight: 600; }
  .pill { display: inline-block; padding: 1px 8px; border-radius: 10px;
          font-size: 11px; font-weight: 600; }
  .pill.gold { background: #4d4426; color: #e6d38a; }
  .pill.train { background: #22303d; color: #8fd6ff; }
  .pill.prot { background: #7c2d2d; color: #ffc9c9; }
  .pill.unver { background: #4d4426; color: #e6d38a; }
  .pill.ok { background: #1f3a2c; color: #7fd6a4; }
  .muted { color: #8b93a1; } .good { color: #7fd6a4; } .bad { color: #ff9c9c; }
  .warnbox { background: #2a2118; border: 1px solid #6b5424; color: #e6d38a;
             border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;
             font-size: 13px; }
  pre.log { background: #0f1216; border: 1px solid #39404d; border-radius: 6px;
            padding: 12px; max-height: 380px; overflow: auto; font-size: 12px;
            line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
  .jobline { display: flex; gap: 10px; align-items: center; padding: 5px 0;
             border-bottom: 1px solid #262c37; font-size: 13px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 8px; }
  .dot.running { background: #8fd6ff; } .dot.queued { background: #8b93a1; }
  .dot.done { background: #4caf7d; } .dot.failed { background: #d45; }
  .dot.cancelled { background: #776a33; }
  .hint { font-size: 12px; color: #8b93a1; margin-top: 6px; }
  a { color: #8fd6ff; }
</style>
</head>
<body>
<header>
  <h1>SwingVision Lab</h1>
  <span class="muted">label &rarr; train &rarr; score</span>
  <span class="sp"></span>
  <span id="devnote" class="muted"></span>
</header>
<div class="tabs">
  <button class="tab on" data-t="start">Start here</button>
  <button class="tab" data-t="clips">Clips</button>
  <button class="tab" data-t="label">Label</button>
  <button class="tab" data-t="train">Train</button>
  <button class="tab" data-t="score">Score</button>
  <button class="tab" data-t="jobs">Jobs</button>
</div>
<main>

<section id="start" class="on">
  <div class="card">
    <h2>Teach the model your footage</h2>
    <div class="hint">Six steps, top to bottom. Each one lights up when the one
      before it is done, so you never have to remember the order. Everything here
      is also available on the other tabs with more knobs &mdash; this is the same
      thing with the decisions already made.</div>
  </div>

  <div class="card stp" id="stp1">
    <h2><span class="n">1</span> Add your video <span class="badge"></span></h2>
    <div class="hint">Drop files into <code>data/incoming/</code> and they show up
      in this list.</div>

    <div class="sub">
      <b>Recorded more than you need? Trim it first.</b>
      <div class="hint">Optional, but everything after this is faster and cheaper
        on a short clip &mdash; and your labelling time gets spent on tennis
        instead of on people walking between points. Times can be
        <code>90</code>, <code>1:30</code> or <code>1:02:03</code>.</div>
      <div class="row">
        <label class="f">Video <select id="w-trimsrc"></select></label>
        <label class="f">From <input id="w-from" size="8" placeholder="2:00"></label>
        <label class="f">To <input id="w-to" size="8" placeholder="12:30"></label>
        <label class="f">Save as <input id="w-trimname" size="14" placeholder="my_match"></label>
        <button id="w-trim">Trim it</button>
      </div>
      <div class="hint">Leaves the original alone and writes a new file next to it,
        which then appears in the list below. Re-encodes so both ends land where you
        asked &mdash; a ten-minute cut takes about a minute.</div>
    </div>

    <div class="sub"><b>Then add it</b></div>
    <div class="row">
      <label class="f">Video <select id="w-video"></select></label>
      <label class="f">Short name <input id="w-id" size="16" placeholder="my_match"></label>
      <label class="f">What is it for?
        <select id="w-role">
          <option value="train">Teaching &mdash; the model learns from it</option>
          <option value="gold">Exam &mdash; the model is scored on it, never learns from it</option>
        </select></label>
      <button class="go" id="w-add">Add it</button>
    </div>
    <div class="warnbox"><b>This choice cannot be undone.</b> Exam footage is how
      you find out whether the model actually got better. If it ever gets trained
      on, every score it produces afterwards is meaningless. If you are unsure,
      pick <b>Teaching</b> &mdash; you can always add a different video as the exam.</div>
  </div>

  <div class="card stp" id="stp2">
    <h2><span class="n">2</span> Pick the frames you will look at <span class="badge"></span></h2>
    <div class="hint">You cannot label an hour of video. This picks a spread of
      frames worth your time.</div>
    <div class="row">
      <label class="f">Clip <select id="w-clip"></select></label>
      <label class="f">How many <input id="w-count" type="number" value="200" min="5" max="2000" size="6"></label>
      <label class="f">Only these times <span class="muted">(optional)</span>
        <input id="w-seg" size="22" placeholder="2:00-2:20, 7:30-7:50"></label>
      <button class="go" id="w-cut">Pick frames</button>
    </div>
    <div class="hint"><b>Long recording?</b> Put two or three rally time ranges in
      the box. Otherwise most of your clicks get spent on people walking between
      points.</div>
  </div>

  <div class="card stp" id="stp3">
    <h2><span class="n">3</span> Click the ball <span class="badge"></span></h2>
    <div class="hint">A magnifier follows your mouse; <kbd>+</kbd> and <kbd>&minus;</kbd>
      zoom it. If there is no ball in play, say so &mdash; those frames are worth
      as much as the others. If you genuinely cannot tell, mark it unsure rather
      than guessing.</div>
    <div class="warnbox">Some footage has a <b>burned-in scoreboard with a little
      tennis-ball icon</b> in a corner. It is not the ball. Ignore anything that
      does not move between frames.</div>
    <div class="row"><button class="go" id="w-label">Open the labeller &rarr;</button>
      <span id="w-label-note" class="muted"></span></div>
  </div>

  <div class="card stp" id="stp4">
    <h2><span class="n">4</span> Turn your clicks into training data <span class="badge"></span></h2>
    <div class="hint">One button. Cuts your labelled frames into the format the
      model reads.</div>
    <div class="row"><button class="go" id="w-build">Build it</button></div>
  </div>

  <div class="card stp" id="stp5">
    <h2><span class="n">5</span> Train <span class="badge"></span></h2>
    <div class="hint">This is the slow part &mdash; hours, not minutes. It runs in
      the background and you can close this page; watch it on the Jobs tab.</div>
    <div class="row">
      <label class="f">How long
        <select id="w-epochs">
          <option value="15">Quick look (~2 h) &mdash; is this idea working?</option>
          <option value="40" selected>Proper run (~6 h) &mdash; a model you could ship</option>
        </select></label>
      <button class="go" id="w-train">Start training</button>
    </div>
  </div>

  <div class="card stp" id="stp6">
    <h2><span class="n">6</span> Find out if it got better <span class="badge"></span></h2>
    <div class="hint">Scores the new model against your <b>exam</b> clips only.
      A model is never allowed to mark its own homework.</div>
    <div class="row">
      <label class="f">Model <select id="w-weights"></select></label>
      <button class="go" id="w-score">Score it</button>
    </div>
  </div>
</section>

<section id="clips">
  <div class="card">
    <h2>Add a clip</h2>
    <div class="row">
      <label class="f">Video
        <select id="v-video"></select></label>
      <label class="f">Clip id
        <input id="v-id" size="18" placeholder="am_indoor2"></label>
      <label class="f">Role
        <select id="v-role">
          <option value="gold">gold — a TEST clip, hand-labelled, never trained on</option>
          <option value="train">train — training footage, pseudo-labelled</option>
        </select></label>
      <button class="go" id="v-add">Add clip</button>
    </div>
    <div class="warnbox">The role is <b>one-way</b>. A gold clip is your exam
      paper: it can never enter a training set, or every score it produces
      becomes a lie. Pick deliberately — to change it you must register the
      footage under a new id.</div>
    <div class="hint">Drop new files into <code>data/incoming/</code> and they
      appear in this list. Adding a clip also runs the resolution gate and the
      calibration audit; watch it in Jobs.</div>
  </div>
  <div class="card">
    <h2>Registered clips</h2>
    <table id="t-clips"><tbody></tbody></table>
  </div>
</section>

<section id="label">
  <div class="card">
    <h2>Cut frames to label</h2>
    <div class="row">
      <label class="f">Clip <select id="f-clip"></select></label>
      <label class="f">Kind
        <select id="f-kind">
          <option value="ball">ball — stratified frames</option>
          <option value="court">court — uniform frames</option>
          <option value="noball">no-ball top-up — the negatives</option>
        </select></label>
      <label class="f">Count <input id="f-count" type="number" value="250"
                                    min="5" max="2000" size="6"></label>
      <label class="f">Segments (optional)
        <input id="f-seg" size="26" placeholder="2:00-2:20, 7:30-7:50"></label>
      <button class="go" id="f-go">Cut frames</button>
    </div>
    <div class="hint"><b>Long recording?</b> Put 2&ndash;3 rally time ranges in
      Segments and it samples only inside them. On a 20-minute clip, sampling
      the whole thing spends most of your clicks on players walking between
      points. Ball frames only &mdash; court and no-ball sweeps ignore it.</div>
    <div class="hint">Negatives are the most valuable labels you collect: a
      detector that is right when the ball is there but hallucinates one during
      a changeover is a bad detector, and only no-ball frames expose it.</div>
  </div>
  <div class="card">
    <h2>Focus this labelling session</h2>
    <div class="row">
      <label class="f">Clip <select id="s-clip"></select></label>
      <span id="s-buckets" class="row" style="margin:0"></span>
      <button id="s-set">Apply filter</button>
      <button id="s-clear">Show all frames</button>
    </div>
    <div id="s-state" class="hint"></div>
    <div class="hint">Far-court and blurred balls are where the remaining
      accuracy is, so it is worth spending clicks there rather than uniformly.
      The filter changes <i>which</i> frames you are shown; it never tells you
      anything about the frame in front of you, so each individual judgement
      stays blind.</div>
  </div>
  <div class="card">
    <h2>Open the labeller</h2>
    <div class="row">
      <a href="/label"><button>Ball &mdash; test pool &rarr;</button></a>
      <a href="/label/court"><button>Court &mdash; test pool &rarr;</button></a>
      <span style="width:18px"></span>
      <a href="/train/label"><button class="go">Ball &mdash; training pool &rarr;</button></a>
      <a href="/train/label/court"><button class="go">Court &mdash; training pool &rarr;</button></a>
    </div>
    <div class="hint">Same labeller either way. The pool is decided by the
      clip's role, and the two never mix: the test pool is the only honest
      scoreboard, the training pool is what the model learns from.</div>
    <table id="t-gold"><tbody></tbody></table>
  </div>
  <div class="card">
    <h2>Turn your labels into training data</h2>
    <div class="row">
      <label class="f">Clip <select id="h-clip"></select></label>
      <button class="go" id="h-go">Build training data from my labels</button>
    </div>
    <div class="hint">Until now the model only ever trained on labels the
      tracker generated itself &mdash; and it cannot see the far-court ball, so
      it could never teach it. Your clicks are the way past that.</div>
  </div>
</section>

<section id="train">
  <div class="card">
    <h2>Training data</h2>
    <table id="t-data"><tbody></tbody></table>
    <div class="hint">A row marked PROTECTED shares its source video with a gold
      manifest. It is excluded automatically, cannot be ticked, and is excluded
      again server-side regardless of what this page sends.</div>
    <div class="warnbox" id="t-unver" style="display:none"></div>
  </div>
  <div class="card">
    <h2>Train</h2>
    <div class="row">
      <label class="f">Model
        <select id="t-model">
          <option value="ballnet">BallNet — the ball detector</option>
          <option value="courtnet">CourtNet — court keypoints</option>
        </select></label>
      <label class="f">Epochs <input id="t-epochs" type="number" value="40"
                                     min="1" max="500" size="5"></label>
      <label class="f">Save as <input id="t-out" size="20"></label>
      <button class="go" id="t-go">Start training</button>
    </div>
    <div id="t-note" class="hint"></div>
  </div>
  <div class="card">
    <h2>Weights</h2>
    <table id="t-weights"><tbody></tbody></table>
  </div>
</section>

<section id="score">
  <div class="card">
    <h2>Score against human labels</h2>
    <div class="row">
      <label class="f">What
        <select id="e-kind">
          <option value="detector">ball detector, raw</option>
          <option value="chain">ball through the shipped chain</option>
          <option value="court">court — classical detector</option>
          <option value="court_learned">court — learned CourtNet</option>
        </select></label>
      <label class="f">Clip (chain only)
        <select id="e-clip"><option value="">all</option></select></label>
      <button class="go" id="e-go">Run</button>
    </div>
    <div class="row" id="e-weights"></div>
    <div class="hint">Everything here is scored against frames a human clicked.
      Recall and false-fire move independently — read both, never one.</div>
  </div>
  <div class="card">
    <h2>Results</h2>
    <div id="e-results"><p class="muted">No runs yet.</p></div>
  </div>
</section>

<section id="jobs">
  <div class="card">
    <h2>Jobs</h2>
    <div id="j-list"></div>
  </div>
  <div class="card">
    <h2>Output <span id="j-title" class="muted"></span>
      <button id="j-cancel" class="warn" style="float:right">Cancel</button></h2>
    <pre class="log" id="j-log">Select a job.</pre>
  </div>
</section>

</main>
<script>
const $ = (s) => document.querySelector(s);
const el = (t, c, txt) => { const e = document.createElement(t);
  if (c) e.className = c; if (txt !== undefined) e.textContent = txt; return e; };
let OV = null, watching = null, offset = 0, logTimer = null, RESULTS = [], VIDEOS = [];

async function get(u) { const r = await fetch(u); return r.json(); }
async function post(u, b) {
  const r = await fetch(u, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });
  return r.json();
}

document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("on"));
  document.querySelectorAll("section").forEach(x => x.classList.remove("on"));
  t.classList.add("on"); $("#" + t.dataset.t).classList.add("on");
  if (t.dataset.t === "jobs" || t.dataset.t === "score") refreshJobs();
});

function fmt(n, d) { return n === null || n === undefined ? "–" : Number(n).toFixed(d === undefined ? 1 : d); }

// ---- the guided flow -------------------------------------------------------
// Everything here is DERIVED from the overview, never stored. The wizard has no
// state of its own to fall out of sync with the tabs: pick a clip on the Clips
// tab and this reflects it, and vice versa.
function wizClip() {
  const s = $("#w-clip");
  return s && s.value ? s.value : null;
}
function wizStatus() {
  const clip = wizClip();
  const reg = (OV.registry || []).find(r => r.id === clip) || null;
  const pool = reg && reg.role === "gold" ? (OV.gold_ball || []) : (OV.train_ball || []);
  const lab = pool.find(c => c.clip === clip) || null;
  const ds = (OV.datasets || []).find(d => (d.name || d.dataset) === clip) || null;
  return {
    clip, reg, role: reg ? reg.role : null,
    frames: lab ? (lab.total || 0) : 0,
    labelled: lab ? (lab.labelled || 0) : 0,
    dataset: ds,
    weights: (OV.weights || []).length,
    results: (RESULTS || []).length,
  };
}
function renderWizard() {
  const st = wizStatus();
  // A step is DONE on evidence, not on "you clicked the button" — reopening the
  // page mid-flow has to land you in the right place.
  const done = [
    (OV.registry || []).length > 0,
    st.frames > 0,
    st.labelled > 0,
    !!st.dataset,
    st.weights > 0,
    st.results > 0,
  ];
  const note = [
    (OV.registry || []).length + " clip(s) added",
    st.frames ? st.frames + " frames ready" : "no frames yet",
    st.labelled ? st.labelled + " of " + st.frames + " clicked" : "not started",
    st.dataset ? "built" : "not built",
    st.weights ? st.weights + " model(s)" : "none trained",
    st.results ? st.results + " result(s)" : "not scored",
  ];
  // The current step is the first not-done one; everything after it is locked.
  let cur = done.findIndex(d => !d);
  if (cur < 0) cur = done.length - 1;
  // A later step cannot read as done while an earlier one is not. Steps 5 and 6
  // count models and results across the WHOLE lab, which may predate this flow
  // entirely — without this the page cheerfully says "train: done" to someone who
  // has not yet added a video.
  for (let i = cur + 1; i < done.length; i++) done[i] = false;
  for (let i = 0; i < 6; i++) {
    const c = $("#stp" + (i + 1));
    if (!c) continue;
    c.classList.remove("done", "now", "todo");
    c.classList.add(done[i] ? "done" : (i === cur ? "now" : "todo"));
    const b = c.querySelector(".badge");
    b.textContent = done[i] ? "done · " + note[i]
                            : (i === cur ? "do this now" : "waiting");
  }
  const ln = $("#w-label-note");
  if (ln) ln.textContent = !st.clip ? "add a clip first"
    : st.reg ? (st.role === "gold" ? "exam pool" : "teaching pool") + " · " + st.clip
             : st.clip;
}

function fillWizard() {
  // unregistered videos -> step 1; registered clips -> step 2; models -> step 6
  const keep = s => s && s.value;
  const opts = (sel, items, label, value) => {
    if (!sel) return;
    const prev = sel.value;
    sel.innerHTML = "";
    items.forEach(it => { const o = el("option", null, label(it));
                          o.value = value(it); sel.appendChild(o); });
    if (!items.length) {
      // an empty VALUE, so wizClip() reports "nothing selected" rather than
      // handing the placeholder text to the API as a clip id
      const o = el("option", null, "— none —"); o.value = ""; sel.appendChild(o);
    }
    if (prev && items.some(it => value(it) === prev)) sel.value = prev;
  };
  opts($("#w-video"), (VIDEOS || []).filter(v => !v.registered),
       v => v.video.split("/").pop() + "  (" + v.size_mb + " MB)", v => v.video);
  // trimming works on ANY video, including one already registered — you may want
  // a shorter version of a clip you have already added
  opts($("#w-trimsrc"), VIDEOS || [],
       v => v.video.split("/").pop() + "  (" + v.size_mb + " MB)", v => v.video);
  opts($("#w-clip"), OV.registry || [],
       r => r.id + "  (" + (r.role === "gold" ? "exam" : "teaching") + ")", r => r.id);
  opts($("#w-weights"), OV.weights || [], w => w.name || w, w => w.name || w);
  const vs = $("#w-video"), id = $("#w-id");
  if (vs && id) vs.onchange = () => { if (!keep(id))
    id.value = vs.value.split("/").pop().replace(/\\.mp4$/, ""); };
  const c = $("#w-clip"); if (c) c.onchange = renderWizard;
}

function wizWire() {
  const go = (btn, fn) => { const b = $(btn); if (b) b.onclick = fn; };
  go("#w-trim", async () => {
    const to = $("#w-to").value.trim();
    if (!to) return alert("Say where to stop — the 'To' box.");
    const r = await post("/api/lab/trim", { video: $("#w-trimsrc").value,
      start: $("#w-from").value.trim() || "0", end: to,
      name: $("#w-trimname").value.trim() });
    if (r.error) return alert(r.error);
    watch(r.job);
  });
  go("#w-add", async () => {
    const r = await post("/api/lab/intake", { video: $("#w-video").value,
      id: $("#w-id").value.trim(), role: $("#w-role").value });
    if (r.error) return alert(r.error);
    watch(r.job); await refresh();
  });
  go("#w-cut", async () => {
    const r = await post("/api/lab/frames", { id: wizClip(), kind: "ball",
      count: +$("#w-count").value, segments: $("#w-seg").value });
    if (r.error) return alert(r.error);
    watch(r.job);
  });
  go("#w-label", () => {
    const st = wizStatus();
    // the pool is decided by the clip's role, never by the user picking a button
    location.href = st.role === "gold" ? "/label" : "/train/label";
  });
  go("#w-build", async () => {
    const r = await post("/api/lab/human_dataset", { id: wizClip() });
    if (r.error) return alert(r.error);
    watch(r.job);
  });
  go("#w-train", async () => {
    const r = await post("/api/lab/train", { model: "ballnet",
      epochs: +$("#w-epochs").value, out: (OV.suggest || {}).ballnet, exclude: [] });
    if (r.error) return alert(r.error);
    watch(r.job);
  });
  go("#w-score", async () => {
    const r = await post("/api/lab/eval", { kind: "ball",
      weights: $("#w-weights").value, clip: null });
    if (r.error) return alert(r.error);
    watch(r.job);
  });
}

async function refresh() {
  OV = await get("/api/lab/overview");
  const ip = OV.interpreters;
  $("#devnote").textContent =
    (ip.train ? "train venv ok (" + OV.device + ")" : "NO TRAIN VENV") +
    " · " + (ip.cpu ? "cpu venv ok" : "NO CPU VENV");
  $("#devnote").className = (ip.train && ip.cpu) ? "muted" : "bad";

  // videos
  const vs = VIDEOS = await get("/api/lab/videos");
  const sel = $("#v-video"); sel.innerHTML = "";
  vs.filter(v => !v.registered).forEach(v => {
    const o = el("option", null, v.video + "  (" + v.size_mb + " MB)");
    o.value = v.video; sel.appendChild(o);
  });
  if (!sel.options.length) sel.appendChild(el("option", null, "— none unregistered —"));
  sel.onchange = () => { if (!$("#v-id").value)
    $("#v-id").value = sel.value.split("/").pop().replace(/\.mp4$/, ""); };

  // registry table
  const tb = $("#t-clips tbody"); tb.innerHTML = "";
  const head = el("tr"); ["Clip", "Role", "Video", "Size", "FPS", "Calibration", ""]
    .forEach(h => head.appendChild(el("th", null, h))); tb.appendChild(head);
  OV.registry.forEach(r => {
    const tr = el("tr");
    tr.appendChild(el("td", null, r.id));
    const rc = el("td"); rc.appendChild(el("span", "pill " + r.role, r.role));
    tr.appendChild(rc);
    tr.appendChild(el("td", "muted", r.video));
    tr.appendChild(el("td", "num", (r.width || "?") + "x" + (r.height || "?")));
    tr.appendChild(el("td", "num", fmt(r.fps, 2)));
    tr.appendChild(el("td", r.pts_file ? "" : "muted", r.pts_file || "none"));
    const bc = el("td"); const b = el("button", null, "Calibrate");
    b.onclick = async () => {
      const res = await post("/api/lab/calibrate", { id: r.id });
      if (res.error) return alert(res.error);
      window.open(res.url, "_blank");
    };
    bc.appendChild(b); tr.appendChild(bc);
    tb.appendChild(tr);
  });

  // clip pickers. Frame-cutting offers every registered clip — the role picks
  // the pool for you, so there is nothing to get wrong here.
  fill($("#f-clip"), OV.registry.map(r => r.id + "  [" + r.role + "]"));
  [...$("#f-clip").options].forEach((o, i) => { o.value = OV.registry[i].id; });
  fill($("#h-clip"), OV.registry.filter(r => r.role === "train").map(r => r.id));
  fill($("#s-clip"), OV.gold_ball.map(c => c.clip));
  // only calibrated gold clips: the chain evaluator runs the court gate
  fill($("#e-clip"), OV.chain_clips, true);

  // gold progress
  const gt = $("#t-gold tbody"); gt.innerHTML = "";
  const gh = el("tr"); ["Clip", "Pool", "Kind", "Labelled", "Of"]
    .forEach(h => gh.appendChild(el("th", null, h))); gt.appendChild(gh);
  OV.gold_ball.forEach(c => addGold(gt, c, "ball", "gold"));
  OV.gold_court.forEach(c => addGold(gt, c, "court", "gold"));
  (OV.train_ball || []).forEach(c => addGold(gt, c, "ball", "train"));
  (OV.train_court || []).forEach(c => addGold(gt, c, "court", "train"));

  // datasets
  const dt = $("#t-data tbody"); dt.innerHTML = "";
  const dh = el("tr");
  ["Use", "Dataset", "Frames", "Labels", "No-ball", "Hard negs", "Source", "Gold check"]
    .forEach(h => dh.appendChild(el("th", null, h))); dt.appendChild(dh);
  OV.datasets.forEach(d => {
    const tr = el("tr");
    const uc = el("td");
    const cb = el("input"); cb.type = "checkbox"; cb.className = "dsel";
    cb.value = d.name; cb.checked = !d.protected; cb.disabled = d.protected;
    cb.title = d.protected ? "Protected — cannot be trained on" : "Include in training";
    uc.appendChild(cb); tr.appendChild(uc);
    tr.appendChild(el("td", null, d.name));
    tr.appendChild(el("td", "num", d.frames));
    tr.appendChild(el("td", "num", d.labels));
    tr.appendChild(el("td", "num", d.negatives));
    // The mined-confuser count with its share of labels. The legacy tier runs
    // 9-26%; under ~8% is the dilution Session F measured as the cause of the v3
    // regression, so it is flagged rather than left for the reader to divide.
    const hc = el("td", "num", d.hard_count + " (" + d.hard_pct + "%)");
    if (!d.hard_negatives) { hc.className = "num muted"; hc.textContent = "not mined"; }
    else if (d.hard_pct < 8) hc.className = "num warn";
    tr.appendChild(hc);
    tr.appendChild(el("td", "muted", d.source || "not recorded"));
    const f = el("td");
    if (d.state === "protected")
      f.appendChild(el("span", "pill prot", "PROTECTED"));
    else if (d.state === "unverified")
      f.appendChild(el("span", "pill unver", "UNVERIFIED"));
    else if (d.state === "hash-checked") {
      const p = el("span", "pill ok", "checked (pixels)");
      if (d.gold_check)
        p.title = "No source video recorded, so verify_dataset_not_gold.py compared "
                + "the frames themselves against " + d.gold_check.n_clips + " gold clips: "
                + "closest match " + d.gold_check.min_hamming + "/64 bits (a real match is "
                + "0-4). Checked " + d.gold_check.date + ".";
      f.appendChild(p);
    }
    else f.appendChild(el("span", "pill ok", "checked"));
    tr.appendChild(f);
    dt.appendChild(tr);
  });
  const nUnver = OV.datasets.filter(d => d.state === "unverified").length;
  const nHash = OV.datasets.filter(d => d.state === "hash-checked").length;
  let note = "";
  if (nUnver)
    note += "<b>" + nUnver + "</b> dataset dir(s) record no source video, so the gold " +
      "guard cannot check them either way. train_ballnet passes these silently. " +
      "They are ticked by default (that is the current behaviour) — untick them " +
      "if you want them out. Run tools/verify_dataset_not_gold.py to settle it " +
      "from the pixels instead. ";
  if (nHash)
    note += "<b>" + nHash + "</b> dir(s) record no source video but were cleared by " +
      "comparing their frames against every gold clip (verify_dataset_not_gold.py) — " +
      "hover the pill for the margin.";
  $("#t-unver").innerHTML = note;
  $("#t-unver").style.display = note ? "" : "none";

  // weights
  const wt = $("#t-weights tbody"); wt.innerHTML = "";
  const wh = el("tr"); ["Weights", "Size (MB)", "Modified"]
    .forEach(h => wh.appendChild(el("th", null, h))); wt.appendChild(wh);
  OV.weights.forEach(w => {
    const tr = el("tr");
    tr.appendChild(el("td", null, w.name));
    tr.appendChild(el("td", "num", w.size_mb));
    tr.appendChild(el("td", "muted", w.modified));
    wt.appendChild(tr);
  });

  // weights checkboxes for scoring
  const ew = $("#e-weights"); ew.innerHTML = "";
  OV.weights.filter(w => w.name.endsWith(".pt") && !w.name.startsWith("yolo"))
    .forEach(w => {
      const lab = el("label", "f"); lab.style.flexDirection = "row";
      lab.style.alignItems = "center"; lab.style.gap = "6px";
      const cb = el("input"); cb.type = "checkbox"; cb.value = w.path;
      cb.className = "wsel";
      lab.appendChild(cb); lab.appendChild(el("span", null, w.name));
      ew.appendChild(lab);
    });

  if (!$("#t-out").value) suggestName();
  $("#t-model").onchange = suggestName;
  renderSession();
  fillWizard();
  renderWizard();
}

function suggestName() {
  const m = $("#t-model").value;
  $("#t-out").value = OV.suggest[m] || "";
  $("#t-note").textContent =
    "Saves to backend/weights/. An existing filename is refused — new run, new file.";
}

function addGold(tb, c, kind, pool) {
  const tr = el("tr");
  tr.appendChild(el("td", null, c.clip));
  const pc = el("td");
  pc.appendChild(el("span", "pill " + (pool === "gold" ? "gold" : "train"),
                    pool === "gold" ? "test" : "train"));
  tr.appendChild(pc);
  tr.appendChild(el("td", "muted", kind));
  const done = c.labeled >= c.total && c.total > 0;
  tr.appendChild(el("td", "num " + (done ? "good" : ""), c.labeled));
  tr.appendChild(el("td", "num muted", c.total));
  tb.appendChild(tr);
}

function fill(sel, values, blank) {
  const cur = sel.value;
  sel.innerHTML = "";
  if (blank) sel.appendChild(el("option", null, "all"));
  values.forEach(v => { const o = el("option", null, v); o.value = v;
                        sel.appendChild(o); });
  if (cur) sel.value = cur;
}

async function renderSession() {
  const clip = $("#s-clip").value;
  const box = $("#s-buckets"); box.innerHTML = "";
  if (clip) {
    const counts = await get("/api/lab/buckets?clip=" + encodeURIComponent(clip));
    Object.keys(counts).sort().forEach(b => {
      const lab = el("label", "f"); lab.style.flexDirection = "row";
      lab.style.alignItems = "center"; lab.style.gap = "5px";
      const cb = el("input"); cb.type = "checkbox"; cb.value = b;
      cb.className = "bsel";
      lab.appendChild(cb);
      lab.appendChild(el("span", null, b + " (" + counts[b] + ")"));
      box.appendChild(lab);
    });
  }
  const s = OV.session;
  $("#s-state").innerHTML = s.buckets && s.buckets.length
    ? "<b class='good'>Filter active</b> on <b>" + s.clip + "</b>: showing only " +
      s.buckets.join(", ") + ". The labeller will not offer any other frame."
    : "No filter — the labeller shows every frame in the manifest.";
}
$("#s-clip") && ($("#s-clip").onchange = renderSession);

$("#v-add").onclick = async () => {
  const res = await post("/api/lab/intake", {
    video: $("#v-video").value, id: $("#v-id").value.trim(),
    role: $("#v-role").value });
  if (res.error) return alert(res.error);
  $("#v-id").value = "";
  await refresh(); watch(res.job);
};

$("#f-go").onclick = async () => {
  const res = await post("/api/lab/frames", {
    id: $("#f-clip").value, kind: $("#f-kind").value,
    count: +$("#f-count").value, segments: $("#f-seg").value.trim() });
  if (res.error) return alert(res.error);
  watch(res.job);
};

$("#h-go").onclick = async () => {
  const res = await post("/api/lab/human_dataset", { id: $("#h-clip").value });
  if (res.error) return alert(res.error);
  watch(res.job);
};

$("#s-set").onclick = async () => {
  const buckets = [...document.querySelectorAll(".bsel:checked")].map(c => c.value);
  if (!buckets.length) return alert("Tick at least one bucket, or press Show all.");
  const res = await post("/api/lab/session",
                         { clip: $("#s-clip").value, buckets });
  OV.session = res.session; renderSession();
};
$("#s-clear").onclick = async () => {
  const res = await post("/api/lab/session", { clip: null, buckets: [] });
  OV.session = res.session; renderSession();
};

$("#t-go").onclick = async () => {
  // exclude = everything not ticked; the server re-adds protected dirs anyway
  const keep = new Set([...document.querySelectorAll(".dsel:checked")]
    .map(c => c.value));
  const excl = OV.datasets.map(d => d.name).filter(n => !keep.has(n));
  const res = await post("/api/lab/train", {
    model: $("#t-model").value, epochs: +$("#t-epochs").value,
    out: $("#t-out").value.trim(), exclude: excl });
  if (res.error) return alert(res.error);
  $("#t-out").value = ""; await refresh(); watch(res.job);
};

$("#e-go").onclick = async () => {
  const weights = [...document.querySelectorAll(".wsel:checked")].map(c => c.value);
  const res = await post("/api/lab/eval", {
    kind: $("#e-kind").value, weights, clip: $("#e-clip").value });
  if (res.error) return alert(res.error);
  watch(res.job);
};

$("#j-cancel").onclick = async () => {
  if (watching) await post("/api/lab/cancel", { id: watching });
};

function watch(id) {
  watching = id; offset = 0; $("#j-log").textContent = "";
  document.querySelector('.tab[data-t="jobs"]').click();
  pollLog();
}

async function pollLog() {
  clearTimeout(logTimer);
  if (!watching) return;
  const r = await get("/api/lab/job?id=" + watching + "&offset=" + offset);
  if (r.text) { $("#j-log").textContent += r.text;
                $("#j-log").scrollTop = $("#j-log").scrollHeight; }
  offset = r.offset || offset;
  $("#j-title").textContent = watching + " — " + r.status +
    (r.elapsed_s ? " (" + r.elapsed_s + "s)" : "");
  $("#j-cancel").disabled = !(r.status === "running" || r.status === "queued");
  const live = r.status === "running" || r.status === "queued";
  if (live) logTimer = setTimeout(pollLog, 900);
  else { refreshJobs(); loadResults(); }
}

async function refreshJobs() {
  const { jobs } = await get("/api/lab/jobs");
  const box = $("#j-list"); box.innerHTML = "";
  if (!jobs.length) { box.appendChild(el("p", "muted", "Nothing has run yet.")); return; }
  jobs.forEach(j => {
    const line = el("div", "jobline");
    line.appendChild(el("span", "dot " + j.status));
    const a = el("a", null, j.label); a.href = "#";
    a.onclick = (e) => { e.preventDefault(); watch(j.id); };
    line.appendChild(a);
    line.appendChild(el("span", "muted", j.status +
      (j.elapsed_s ? " · " + j.elapsed_s + "s" : "")));
    line.appendChild(el("span", "muted", j.created));
    box.appendChild(line);
  });
}

async function loadResults() {
  const rows = await get("/api/lab/results");
  RESULTS = rows;                       // step 6 of the guided flow reads this
  const box = $("#e-results"); box.innerHTML = "";
  if (!rows.length) { box.appendChild(el("p", "muted", "No runs yet.")); return; }
  rows.forEach(r => {
    const card = el("div"); card.style.marginBottom = "18px";
    const h = el("div", null, (r.tool || "eval") + " · " + (r.created || ""));
    h.style.fontWeight = "600"; h.style.marginBottom = "4px";
    card.appendChild(h);
    if (r.measured_against)
      card.appendChild(el("div", "hint", "Measured against: " + r.measured_against));
    const rowsArr = r.rows || [];
    if (rowsArr.length) {
      const t = el("table"); const tb = el("tbody");
      const cols = Object.keys(rowsArr[0]);
      const hr = el("tr"); cols.forEach(c => hr.appendChild(el("th", null, c)));
      tb.appendChild(hr);
      rowsArr.forEach(row => {
        const tr = el("tr");
        cols.forEach(c => {
          const v = row[c];
          tr.appendChild(el("td", typeof v === "number" ? "num" : "",
                            typeof v === "number" ? fmt(v) : String(v ?? "–")));
        });
        tb.appendChild(tr);
      });
      t.appendChild(tb); card.appendChild(t);
    }
    box.appendChild(card);
  });
}

wizWire();
// loadResults populates RESULTS, which step 6 reads — re-render once it lands.
refresh().then(() => { refreshJobs(); loadResults().then(renderWizard); });
setInterval(refreshJobs, 5000);
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8780)
    ap.add_argument("--gold-dir", default=str(GOLD_DIR))
    ap.add_argument("--device", default="cuda",
                    help="device for training and model evals (cuda|cpu)")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    for d in (CLIPS_DIR, RUNS_DIR, INCOMING, LABELS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    Handler.store = GoldStore(Path(args.gold_dir))
    Handler.train_store = GoldStore(LABELS_DIR)
    Handler.registry = Registry()
    Handler.jobs = JobRunner()
    Handler.session = SessionFilter()
    Handler.device = args.device

    url = f"http://127.0.0.1:{args.port}/"
    print(f"SwingVision Lab running at {url}")
    print(f"  cpu venv   : {PY_CPU or 'MISSING — intake needs backend/.venv'}")
    print(f"  train venv : {PY_TRAIN or 'MISSING — training needs backend/.venv-train'}")
    print(f"  gold dir   : {args.gold_dir}")
    print(f"  registry   : {CLIPS_DIR}")
    print("Ctrl+C here to stop. Labels save on every click; jobs log to data/runs/.")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, [url]).start()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
