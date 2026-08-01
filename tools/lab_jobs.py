"""Job runner for the Lab (tools/lab_server.py) — one subprocess at a time.

Training and evaluation are long, chatty, and GPU-bound. The Lab needs to start
them from a browser click, stream their output back to the page, and remember
what happened after the browser is closed. That is all this module does.

Design notes, each for a reason:

- ONE JOB AT A TIME. There is a single GPU (RTX 5060 Ti). Two concurrent training
  runs would either OOM or silently halve each other's throughput and make every
  timing number a lie. Jobs queue.
- EVERY JOB IS ON DISK. `data/runs/<id>.json` (status) and `data/runs/<id>.log`
  (stdout) are written as the job runs, not at the end. A crashed server, a
  closed browser, or a reboot still leaves the evidence. ML_PRACTICES: a result
  you can't reproduce isn't a result, and a training log you lost is worse.
- STDOUT IS TEE'D, NOT BUFFERED. The page polls by byte offset, so a 40-epoch
  run is readable while it runs rather than after it.
- NO SHELL. argv lists only, so a clip name with a space or a quote in it cannot
  turn into a command.

stdlib only, consistent with the rest of tools/.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO / "data" / "runs"

# Job status values. "queued" -> "running" -> one of the terminal three.
QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"
TERMINAL = (DONE, FAILED, CANCELLED)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Job:
    """One subprocess, its metadata, and its on-disk record."""

    def __init__(self, kind: str, argv: list[str], cwd: Path,
                 meta: dict | None = None, label: str = ""):
        self.id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.kind = kind                 # "train" | "eval" | "frames" | "intake"
        self.argv = [str(a) for a in argv]
        self.cwd = str(cwd)
        self.label = label or kind
        self.meta = dict(meta or {})
        self.status = QUEUED
        self.rc: int | None = None
        self.created = _now()
        self.started: str | None = None
        self.ended: str | None = None
        self.elapsed_s: float | None = None
        self.error: str | None = None

    @property
    def log_path(self) -> Path:
        return RUNS_DIR / f"{self.id}.log"

    @property
    def json_path(self) -> Path:
        return RUNS_DIR / f"{self.id}.json"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "label": self.label,
            "argv": self.argv, "cwd": self.cwd, "meta": self.meta,
            "status": self.status, "rc": self.rc, "error": self.error,
            "created": self.created, "started": self.started,
            "ended": self.ended, "elapsed_s": self.elapsed_s,
        }

    def save(self) -> None:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = self.json_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")
        os.replace(tmp, self.json_path)


class JobRunner:
    """A single-worker queue. Submit returns immediately with a job id."""

    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._pending: list[str] = []
        self._proc: subprocess.Popen | None = None
        self._current: str | None = None
        self._cv = threading.Condition(self._lock)
        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    # ---------- public API ----------

    def submit(self, kind: str, argv: list[str], cwd: Path,
               meta: dict | None = None, label: str = "") -> Job:
        job = Job(kind, argv, cwd, meta, label)
        job.save()
        with self._cv:
            self._jobs[job.id] = job
            self._order.append(job.id)
            self._pending.append(job.id)
            self._cv.notify()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 50) -> list[dict]:
        """Live jobs first (newest last submitted), then finished ones."""
        with self._lock:
            jobs = [self._jobs[i].to_dict() for i in reversed(self._order)]
        return jobs[:limit]

    def busy(self) -> bool:
        with self._lock:
            return self._current is not None or bool(self._pending)

    def cancel(self, job_id: str) -> bool:
        """Cancel a queued job, or kill a running one. True if anything happened."""
        with self._cv:
            job = self._jobs.get(job_id)
            if job is None or job.status in TERMINAL:
                return False
            if job.status == QUEUED:
                if job_id in self._pending:
                    self._pending.remove(job_id)
                job.status = CANCELLED
                job.ended = _now()
                job.save()
                return True
            proc = self._proc if self._current == job_id else None
        if proc is None:
            return False
        _kill_tree(proc)
        return True

    def tail(self, job_id: str, offset: int = 0) -> dict:
        """Bytes of the log from `offset`. The page polls this."""
        job = self.get(job_id)
        if job is None:
            return {"error": "no such job"}
        text, new_offset = "", offset
        path = job.log_path
        if path.exists():
            with open(path, "rb") as fh:
                fh.seek(max(0, offset))
                chunk = fh.read()
                new_offset = fh.tell()
            text = chunk.decode("utf-8", errors="replace")
        return {"id": job.id, "status": job.status, "rc": job.rc,
                "text": text, "offset": new_offset,
                "elapsed_s": job.elapsed_s, "error": job.error}

    def progress(self, job_id: str) -> list[dict]:
        """Every LABJSON progress line the job has emitted so far.

        train_ballnet.py / train_courtnet.py print one compact JSON object per
        epoch prefixed with LABJSON:. Anything else in the log is ignored, so a
        script without the prefix still runs fine — it just has no chart.
        """
        job = self.get(job_id)
        if job is None or not job.log_path.exists():
            return []
        rows = []
        for line in job.log_path.read_text(encoding="utf-8",
                                           errors="replace").splitlines():
            marker = line.find("LABJSON:")
            if marker < 0:
                continue
            try:
                rows.append(json.loads(line[marker + len("LABJSON:"):].strip()))
            except json.JSONDecodeError:
                continue   # a torn half-written line; it'll be whole next poll
        return rows

    def history(self, limit: int = 100) -> list[dict]:
        """Finished jobs from disk, so history survives a server restart."""
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        out = []
        for p in sorted(RUNS_DIR.glob("*.json"), reverse=True)[:limit]:
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        return out

    # ---------- worker ----------

    def _run_loop(self) -> None:
        while True:
            with self._cv:
                while not self._pending:
                    self._cv.wait()
                job_id = self._pending.pop(0)
                job = self._jobs[job_id]
                if job.status == CANCELLED:
                    continue
                self._current = job_id
            try:
                self._run(job)
            except Exception as exc:                     # never kill the worker
                job.status = FAILED
                job.error = f"{type(exc).__name__}: {exc}"
                job.ended = _now()
                job.save()
            finally:
                with self._cv:
                    self._current = None
                    self._proc = None

    def _run(self, job: Job) -> None:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        job.status = RUNNING
        job.started = _now()
        job.save()
        t0 = time.time()

        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")   # or the log arrives in slabs
        env.setdefault("PYTHONIOENCODING", "utf-8")

        with open(job.log_path, "wb") as log:
            log.write(f"$ {' '.join(job.argv)}\n"
                      f"  cwd: {job.cwd}\n"
                      f"  started: {job.started}\n\n".encode("utf-8"))
            log.flush()
            try:
                proc = subprocess.Popen(
                    job.argv, cwd=job.cwd, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    bufsize=0,
                )
            except OSError as exc:
                msg = f"\n[lab] could not start: {exc}\n"
                log.write(msg.encode("utf-8"))
                job.status = FAILED
                job.error = str(exc)
                job.ended = _now()
                job.elapsed_s = round(time.time() - t0, 1)
                job.save()
                return

            with self._lock:
                self._proc = proc

            assert proc.stdout is not None
            for chunk in iter(lambda: proc.stdout.read(1), b""):
                log.write(chunk)
                if chunk in (b"\n", b"\r"):
                    log.flush()
            proc.stdout.close()
            rc = proc.wait()
            log.flush()

        job.rc = rc
        job.elapsed_s = round(time.time() - t0, 1)
        job.ended = _now()
        if job.status == CANCELLED or rc in (-15, -9, 1073741510):
            job.status = CANCELLED
        else:
            job.status = DONE if rc == 0 else FAILED
            if rc != 0:
                job.error = f"exit code {rc}"
        job.save()


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the process AND its children.

    torch DataLoader workers are separate processes; terminating only the parent
    leaves them holding the GPU, and the next queued job then OOMs for no
    visible reason.
    """
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True)
    else:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
