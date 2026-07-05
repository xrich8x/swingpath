"""Browser tool for human gold-labeling of ball positions (HANDOFF §8 fix 1.4).

Serves a single-page labeling UI on localhost. Shows one frame at a time from
a manifest built by select_gold_frames.py; the labeler clicks the ball (a
magnifier loupe follows the cursor for the tiny far-court ball), or marks the
frame NO BALL / UNSURE. Every action is written straight to
data/gold/<clip>.labels.json, so closing the browser loses nothing — reopening
resumes at the first unlabeled frame.

Deliberately blind: the UI never shows any model's prediction or the frame's
selection bucket — otherwise the labels wouldn't be independent ground truth.

Handles any number of clips: every <clip>.manifest.json in the gold dir gets
an entry in the clip picker. To add a clip later, run select_gold_frames.py
on it and refresh the page.

Run from the repo root (stdlib only, no venv needed — but the venv works too):

  py tools/gold_label_server.py
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK = threading.Lock()


class GoldStore:
    """Manifests + labels for every clip in the gold dir; atomic saves."""

    def __init__(self, gold_dir: Path):
        self.gold_dir = gold_dir

    def clips(self) -> list[dict]:
        out = []
        for mpath in sorted(self.gold_dir.glob("*.manifest.json")):
            man = json.loads(mpath.read_text(encoding="utf-8"))
            labels = self.load_labels(man["clip"])["labels"]
            out.append({
                "clip": man["clip"],
                "total": len(man["frames"]),
                "labeled": sum(1 for f in man["frames"]
                               if str(f["frame"]) in labels),
            })
        return out

    def manifest(self, clip: str) -> dict:
        path = self.gold_dir / f"{clip}.manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def labels_path(self, clip: str) -> Path:
        return self.gold_dir / f"{clip}.labels.json"

    def load_labels(self, clip: str) -> dict:
        path = self.labels_path(clip)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"clip": clip, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tool": "gold_label_server v1", "labels": {}}

    def set_label(self, clip: str, frame: int, label: dict | None) -> int:
        """Set or clear one frame's label; persist atomically. Returns the
        number of labeled frames."""
        with LOCK:
            data = self.load_labels(clip)
            key = str(frame)
            if label is None:
                data["labels"].pop(key, None)
            else:
                label["t"] = time.strftime("%Y-%m-%d %H:%M:%S")
                data["labels"][key] = label
            data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tmp = self.labels_path(clip).with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
            os.replace(tmp, self.labels_path(clip))
            return len(data["labels"])


class Handler(BaseHTTPRequestHandler):
    store: GoldStore  # set by main()

    def log_message(self, *a):  # silence per-request console spam
        pass

    def _send(self, code: int, body: bytes, ctype: str, cache: bool = False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if cache:
            self.send_header("Cache-Control", "max-age=86400, immutable")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def do_GET(self):
        from urllib.parse import parse_qs, urlparse

        url = urlparse(self.path)
        if url.path == "/":
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif url.path == "/api/clips":
            self._json(self.store.clips())
        elif url.path == "/api/state":
            clip = parse_qs(url.query).get("clip", [""])[0]
            try:
                self._json({"manifest": self.store.manifest(clip),
                            "labels": self.store.load_labels(clip)["labels"]})
            except FileNotFoundError:
                self._json({"error": f"no manifest for clip {clip!r}"}, 404)
        elif url.path.startswith("/frames/"):
            rel = url.path[len("/frames/"):]
            path = (self.store.gold_dir / "frames" / rel).resolve()
            if (self.store.gold_dir / "frames").resolve() not in path.parents:
                self._send(403, b"forbidden", "text/plain")
            elif path.is_file():
                self._send(200, path.read_bytes(), "image/jpeg", cache=True)
            else:
                self._send(404, b"missing frame (re-run select_gold_frames.py"
                                b" --extract-only?)", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path != "/api/label":
            self._send(404, b"not found", "text/plain")
            return
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n))
        labeled = self.store.set_label(req["clip"], int(req["frame"]),
                                       req.get("label"))
        self._json({"ok": True, "labeled": labeled})


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Gold ball labeler</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; background: #14171c; color: #dfe4ea;
         font: 14px/1.45 system-ui, sans-serif; user-select: none; }
  header { display: flex; align-items: center; gap: 14px; padding: 10px 16px;
           background: #1d2129; flex-wrap: wrap; }
  header h1 { font-size: 15px; margin: 0; font-weight: 600; }
  select, button { font: inherit; border-radius: 6px; border: 1px solid #39404d;
                   background: #262c37; color: #dfe4ea; padding: 6px 12px;
                   cursor: pointer; }
  button:hover { background: #313949; }
  button.noball { background: #7c2d2d; border-color: #a33; font-weight: 700;
                  padding: 6px 18px; }
  button.noball:hover { background: #943636; }
  button.unsure { background: #4d4426; border-color: #776a33; }
  #bar { flex: 1 1 160px; height: 10px; background: #262c37; border-radius: 5px;
         min-width: 120px; }
  #fill { height: 100%; width: 0; background: #4caf7d; border-radius: 5px;
          transition: width .15s; }
  #stage { position: relative; margin: 12px auto; width: fit-content; }
  #view { display: block; cursor: crosshair; border: 1px solid #39404d;
          border-radius: 4px; }
  #loupe { position: fixed; width: 184px; height: 184px; border-radius: 50%;
           border: 2px solid #9ab; pointer-events: none; display: none;
           z-index: 10; box-shadow: 0 4px 18px rgba(0,0,0,.6); }
  #status { text-align: center; min-height: 22px; font-size: 15px; }
  #status .ball { color: #7fd6a4; } #status .nob { color: #ff9c9c; }
  #status .uns { color: #e6d38a; }
  footer { text-align: center; color: #8b93a1; padding: 8px 16px 20px;
           font-size: 13px; }
  kbd { background: #262c37; border: 1px solid #39404d; border-radius: 4px;
        padding: 0 5px; font-family: inherit; }
  #done { display: none; text-align: center; font-size: 17px; color: #7fd6a4;
          padding: 6px; }
</style>
</head>
<body>
<header>
  <h1>Gold ball labeler</h1>
  <select id="clip"></select>
  <span id="count">–</span>
  <div id="bar"><div id="fill"></div></div>
  <button id="prev" title="left arrow">&#9664; Prev</button>
  <button id="next" title="right arrow">Next &#9654;</button>
  <button id="noball" class="noball" title="N">NO BALL (N)</button>
  <button id="unsure" class="unsure" title="S">Unsure (S)</button>
  <button id="clear" title="U">Clear (U)</button>
</header>
<div id="done">All frames labeled — you can close this window. The file is saved.</div>
<div id="stage">
  <canvas id="view"></canvas>
  <canvas id="loupe" width="184" height="184"></canvas>
</div>
<div id="status"></div>
<footer>
  <b>Click the ball in play</b> — the round magnifier follows your mouse; aim with its + crosshair.
  No ball in play / can't see it &rarr; <kbd>N</kbd>.
  Truly can't decide &rarr; <kbd>S</kbd>.
  <kbd>&larr;</kbd><kbd>&rarr;</kbd> move &middot; <kbd>U</kbd> clear this frame &middot;
  <kbd>+</kbd>/<kbd>&minus;</kbd> magnifier zoom
</footer>
<script>
"use strict";
const $ = id => document.getElementById(id);
const view = $("view"), vctx = view.getContext("2d");
const loupe = $("loupe"), lctx = loupe.getContext("2d");
let clip = null, frames = [], labels = {}, cur = 0, zoom = 4;
const imgs = new Map();   // frame -> Image (small cache)

function imgFor(f, cb) {
  if (imgs.has(f)) { const im = imgs.get(f); im.complete ? cb(im) : im.addEventListener("load", () => cb(im)); return; }
  const im = new Image();
  im.src = `/frames/${clip}/f${String(f).padStart(5, "0")}.jpg`;
  imgs.set(f, im);
  if (imgs.size > 40) imgs.delete(imgs.keys().next().value);
  im.addEventListener("load", () => cb(im));
}

function fitScale(im) {
  const w = Math.min(im.naturalWidth, window.innerWidth - 40);
  return w / im.naturalWidth;
}

function render() {
  const f = frames[cur];
  imgFor(f, im => {
    if (frames[cur] !== f) return;           // stale load
    const s = fitScale(im);
    view.width = Math.round(im.naturalWidth * s);
    view.height = Math.round(im.naturalHeight * s);
    vctx.drawImage(im, 0, 0, view.width, view.height);
    const lab = labels[f];
    if (lab && lab.ball === true) {
      const x = lab.x * s, y = lab.y * s;
      vctx.strokeStyle = "#4caf7d"; vctx.lineWidth = 2;
      vctx.beginPath(); vctx.arc(x, y, 9, 0, 7); vctx.stroke();
      vctx.beginPath(); vctx.moveTo(x - 14, y); vctx.lineTo(x + 14, y);
      vctx.moveTo(x, y - 14); vctx.lineTo(x, y + 14); vctx.stroke();
    }
    updateStatus();
    // preload the next two frames
    for (const g of [frames[cur + 1], frames[cur + 2]]) if (g !== undefined) imgFor(g, () => {});
  });
}

function updateStatus() {
  const f = frames[cur], lab = labels[f];
  let s = `Frame ${cur + 1} of ${frames.length}`;
  if (lab === undefined) s += " — unlabeled";
  else if (lab.ball === true) s += ` — <span class="ball">ball at (${Math.round(lab.x)}, ${Math.round(lab.y)})</span>`;
  else if (lab.ball === false) s += ' — <span class="nob">NO BALL</span>';
  else s += ' — <span class="uns">unsure (excluded from scoring)</span>';
  $("status").innerHTML = s;
  const n = Object.keys(labels).length;
  $("count").textContent = `${n} / ${frames.length} labeled`;
  $("fill").style.width = (100 * n / frames.length) + "%";
  $("done").style.display = n >= frames.length ? "block" : "none";
}

function firstUnlabeled(from = 0) {
  for (let i = 0; i < frames.length; i++) {
    const k = (from + i) % frames.length;
    if (labels[frames[k]] === undefined) return k;
  }
  return null;
}

async function save(frame, label) {
  if (label) labels[frame] = label; else delete labels[frame];
  updateStatus();
  await fetch("/api/label", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clip, frame, label }) });
}

function label(lab) {
  save(frames[cur], lab);
  render();
  setTimeout(() => {                           // auto-advance to next unlabeled
    const nxt = firstUnlabeled(cur + 1);
    if (nxt !== null) { cur = nxt; render(); }
    else updateStatus();
  }, 220);
}

function nav(d) { cur = Math.min(frames.length - 1, Math.max(0, cur + d)); loupe.style.display = "none"; render(); }

view.addEventListener("click", e => {
  const r = view.getBoundingClientRect(), f = frames[cur];
  imgFor(f, im => {
    const nx = (e.clientX - r.left) * im.naturalWidth / r.width;
    const ny = (e.clientY - r.top) * im.naturalHeight / r.height;
    label({ ball: true, x: Math.round(nx * 10) / 10, y: Math.round(ny * 10) / 10 });
  });
});

view.addEventListener("mousemove", e => {
  const f = frames[cur];
  imgFor(f, im => {
    if (frames[cur] !== f) return;
    const r = view.getBoundingClientRect();
    const nx = (e.clientX - r.left) * im.naturalWidth / r.width;
    const ny = (e.clientY - r.top) * im.naturalHeight / r.height;
    const L = loupe.width, src = L / zoom;
    lctx.imageSmoothingEnabled = zoom <= 2;
    lctx.fillStyle = "#000"; lctx.fillRect(0, 0, L, L);
    lctx.drawImage(im, nx - src / 2, ny - src / 2, src, src, 0, 0, L, L);
    lctx.strokeStyle = "rgba(120,220,160,.9)"; lctx.lineWidth = 1;
    lctx.beginPath(); lctx.moveTo(L / 2 - 12, L / 2); lctx.lineTo(L / 2 + 12, L / 2);
    lctx.moveTo(L / 2, L / 2 - 12); lctx.lineTo(L / 2, L / 2 + 12); lctx.stroke();
    let lx = e.clientX + 26, ly = e.clientY + 26;
    if (lx + L + 8 > window.innerWidth) lx = e.clientX - L - 26;
    if (ly + L + 8 > window.innerHeight) ly = e.clientY - L - 26;
    loupe.style.left = lx + "px"; loupe.style.top = ly + "px";
    loupe.style.display = "block";
  });
});
view.addEventListener("mouseleave", () => loupe.style.display = "none");

document.addEventListener("keydown", e => {
  if (e.target.tagName === "SELECT") return;
  if (e.repeat) return;   // a held key must not spray labels across frames
  const k = e.key.toLowerCase();
  if (k === "arrowright" || k === ".") nav(1);
  else if (k === "arrowleft" || k === ",") nav(-1);
  else if (k === "n") label({ ball: false });
  else if (k === "s") label({ ball: null, unsure: true });
  else if (k === "u") { save(frames[cur], null); render(); }
  else if (k === "+" || k === "=") { zoom = Math.min(10, zoom + 1); }
  else if (k === "-") { zoom = Math.max(2, zoom - 1); }
  else return;
  e.preventDefault();
});

$("prev").onclick = () => nav(-1);
$("next").onclick = () => nav(1);
$("noball").onclick = () => label({ ball: false });
$("unsure").onclick = () => label({ ball: null, unsure: true });
$("clear").onclick = () => { save(frames[cur], null); render(); };

async function loadClip(name) {
  const res = await fetch(`/api/state?clip=${encodeURIComponent(name)}`);
  const st = await res.json();
  clip = name;
  frames = st.manifest.frames.map(r => r.frame);
  labels = {};
  for (const [k, v] of Object.entries(st.labels)) labels[Number(k)] = v;
  imgs.clear();
  cur = firstUnlabeled() ?? 0;
  render();
}

(async () => {
  const clips = await (await fetch("/api/clips")).json();
  const sel = $("clip");
  for (const c of clips) {
    const o = document.createElement("option");
    o.value = c.clip; o.textContent = `${c.clip} (${c.labeled}/${c.total})`;
    sel.appendChild(o);
  }
  sel.onchange = () => loadClip(sel.value);
  const start = clips.find(c => c.labeled < c.total) || clips[0];
  if (!start) { $("status").textContent = "No manifests found — run select_gold_frames.py first."; return; }
  sel.value = start.clip;
  await loadClip(start.clip);
})();
window.addEventListener("resize", render);
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gold-dir", default=str(REPO / "data" / "gold"))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    Handler.store = GoldStore(Path(args.gold_dir))
    clips = Handler.store.clips()
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Gold labeler running at {url}")
    for c in clips:
        print(f"  {c['clip']}: {c['labeled']}/{c['total']} labeled")
    if not clips:
        print("  (no manifests found — run select_gold_frames.py first)")
    print("Press Ctrl+C in this window to stop. Progress is saved on every click.")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, [url]).start()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
