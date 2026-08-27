"""PM Gate Config - a browser UI to manage the automatic PM-review Stop hook.

The hook itself lives in .claude/settings.json ("hooks" -> "Stop"), but that
file is machine-composed: the real source of truth is .claude/pm_gate_config.json
(enabled, model, timeout, and a list of independently-toggleable check
criteria). This tool never hand-edits the prompt text -- it always rebuilds
the Stop hook block from the structured config, so Save in the browser and
editing the JSON by hand both end up in the same place.

    py tools/pm_gate_config_server.py            # opens the browser UI
    py tools/pm_gate_config_server.py --build     # just rebuild settings.json and exit

Stdlib only -- no venv needed, same as tools/lab_server.py and
tools/court_setup_server.py.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO / ".claude" / "pm_gate_config.json"
SETTINGS_PATH = REPO / ".claude" / "settings.json"

MODEL_CHOICES = ["opus", "sonnet", "haiku", "opusplan"]

# Only used if pm_gate_config.json is missing or unreadable -- lets "Reset to
# defaults" recover from a bad edit without needing this file's git history.
DEFAULT_CONFIG = {
    "enabled": True,
    "model": "opus",
    "timeout": 90,
    "preamble": (
        "You are the PM gate for the SwingVision tennis-video-analysis project, "
        "reviewing the turn Claude Code just finished on behalf of a non-technical "
        "PM who cannot read code and relies entirely on this check. Decide whether "
        "the turn needs to pause and explain itself in plain English before it's "
        "allowed to end.\n\nFirst: if the hook input's stop_hook_active field is "
        "true, return {\"ok\": true} immediately and do nothing else (this is a "
        "repeat firing; never block twice in a row on the same turn).\n\nOtherwise, "
        "ground your judgment in what ACTUALLY happened, not what Claude said "
        "happened: run `git status` and `git diff` (and `git diff --cached`) in the "
        "project root to see real changes this turn, and skim CLAUDE.md's most "
        "recent Status entries + Gotchas section and SCOREBOARD.md's 'What has not "
        "worked' table for standing context. If the diff touches "
        "backend/swingvision/court.py, scoring.py, calibration.py, courtfit.py, "
        "ball.py, or schema.py, also open the changed section to see what actually "
        "moved.\n\nGround truth you must hold the diff to, because this project's "
        "whole discipline is not treating these as tunable: a tennis court is fixed "
        "regulation geometry (23.77m baseline-to-baseline, 10.97m doubles / 8.23m "
        "singles width, net at 11.885m, service line 6.40m from the net, mirrored "
        "in backend/swingvision/court.py and frontend/src/lib/court.js); a tennis "
        "ball is ~6.7cm; a racket is roughly 68cm; a real ball in flight follows "
        "gravity+drag(+Magnus), never a straight line or a still hover; standard "
        "scoring is deuce/ad/tiebreak-at-6/best-of-3 (backend/swingvision/scoring.py). "
        "You also need working knowledge of this project's actual ML/CV stack to "
        "judge technical claims: BallNet is a TrackNet-style heatmap CNN (small, "
        "fast, easily confused with racket heads/HUD graphics -- 'bright pixel "
        "tracking' onto the wrong bright pixel is this project's single "
        "most-fought failure mode), tracking is smoothed with a "
        "constant-acceleration Kalman/RTS filter that interpolates gaps but must "
        "never extrapolate blindly off-frame, and the core ML tension recorded in "
        "this repo is recall vs. false-positive rate, where detector-level "
        "precision gains have repeatedly failed to reach the rendered output (see "
        "SCOREBOARD 'What has not worked').\n\nBlock -- return {\"ok\": false, "
        "\"reason\": \"...\"} -- if ANY of the ACTIVE checks below is true for the "
        "turn just finished:"
    ),
    "closing": (
        "If NONE of the active checks above happened, return {\"ok\": true}. Do "
        "not invent a problem to justify blocking -- most turns are fine and "
        "should pass silently. When you do block, write the reason in plain "
        "English for someone who cannot read code: what happened, which file or "
        "decision it concerns, and why it matters, in 3-5 sentences, no jargon "
        "left unexplained.\n\nHook input: $ARGUMENTS"
    ),
    "criteria": [
        {"id": 1, "title": "Undisclosed product/threshold/default change", "active": True,
         "text": "A tennis-domain or geometry assumption changed without saying so: a "
                 "scoring rule, a court constant, a confidence threshold that decides "
                 "what the dashboard tells the user is trustworthy (call_confident, "
                 "speed_confident, the court-consensus vote bar, score_thresh, a gate "
                 "radius), or the default detector/model file -- changed without "
                 "explicitly flagging it as a decision made."},
        {"id": 2, "title": "Fix assumes something physically untrue", "active": True,
         "text": "A proposed or applied fix treats a physical tennis fact as if it were "
                 "tunable, or silently conflates a pixel-space heuristic with a "
                 "real-world measurement (e.g. describing a threshold in pixels as if "
                 "it were metres, or vice versa, without noting the difference)."},
        {"id": 3, "title": "Re-proposes a measured dead end", "active": True,
         "text": "An ML/CV change re-proposes something SCOREBOARD.md's 'What has not "
                 "worked' table already measured and killed, without new evidence -- "
                 "e.g. raising the score threshold, lowering the court-consensus bar, "
                 "racquet-box negation, more training data alone, tightening a gate "
                 "radius, pose-proximity mining."},
        {"id": 4, "title": "Unqualified number", "active": True,
         "text": "A number is reported without stating what it was measured against. "
                 "This project's #1 rule: never let a model grade its own homework -- "
                 "a number measured against the model's own prior output, a "
                 "pseudo-label, or training data is not accuracy and must be labeled "
                 "as such."},
        {"id": 5, "title": "Scope creep", "active": True,
         "text": "Claude did meaningfully more than was asked: an unrelated refactor, "
                 "a bonus feature, or scope creep beyond the actual request."},
        {"id": 6, "title": "Unilateral product call", "active": True,
         "text": "A product/design decision that belongs to the PM was made "
                 "unilaterally: shipping a result already measured as a loss, "
                 "changing what counts as a trustworthy measurement, changing "
                 "match.json's shape (schema.py)."},
        {"id": 7, "title": "Quietly weakened a guardrail after hitting a wall", "active": True,
         "text": "Claude hit a wall (a test failed, a model underperformed, a "
                 "calibration refused) and quietly narrowed scope or weakened a "
                 "guardrail -- e.g. turned a refuse into a silent accept, loosened a "
                 "warning into nothing -- instead of surfacing it plainly."},
    ],
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def build_prompt(cfg: dict) -> str:
    """Compose the final Stop-hook prompt from the structured config. Only
    ACTIVE criteria are included, renumbered 1..N regardless of their stored id
    so a toggled-off check leaves no gap in what the model reads."""
    active = [c for c in cfg.get("criteria", []) if c.get("active", True)]
    lines = [str(cfg.get("preamble", "")).strip(), ""]
    for i, c in enumerate(active, 1):
        lines.append(f"{i}. {c['title']}: {c['text']}")
    lines.append("")
    lines.append(str(cfg.get("closing", "")).strip())
    return "\n".join(lines)


def apply_to_settings(cfg: dict) -> None:
    """Rebuild the "Stop" block in .claude/settings.json from cfg, leaving
    every other hook (e.g. the scoreboard-guard PreToolUse check) untouched."""
    settings = {}
    if SETTINGS_PATH.exists():
        try:
            settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            settings = {}
    settings.setdefault("hooks", {})

    if cfg.get("enabled", True) and any(c.get("active", True) for c in cfg.get("criteria", [])):
        settings["hooks"]["Stop"] = [
            {
                "hooks": [
                    {
                        "type": "agent",
                        "model": cfg.get("model", "opus"),
                        "timeout": int(cfg.get("timeout", 90)),
                        "prompt": build_prompt(cfg),
                    }
                ]
            }
        ]
    else:
        settings["hooks"].pop("Stop", None)

    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>PM Gate Config</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: -apple-system, Segoe UI, sans-serif; max-width: 880px;
         margin: 32px auto; padding: 0 16px; line-height: 1.45; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .sub { color: #888; margin-bottom: 24px; font-size: 14px; }
  .row { display: flex; gap: 16px; align-items: center; margin: 10px 0; flex-wrap: wrap; }
  .row label { font-weight: 600; min-width: 110px; }
  select, input[type=number] { padding: 6px 8px; font-size: 14px; }
  .toggle { transform: scale(1.3); margin-right: 6px; }
  .card { border: 1px solid #8883; border-radius: 8px; padding: 12px 14px; margin: 10px 0; }
  .card.off { opacity: 0.5; }
  .card-head { display: flex; align-items: center; gap: 10px; }
  .card-head input[type=text] { flex: 1; font-weight: 600; font-size: 14px;
                                 padding: 4px 6px; }
  textarea { width: 100%; box-sizing: border-box; margin-top: 8px; font-size: 13px;
             font-family: ui-monospace, monospace; padding: 8px; min-height: 64px; }
  .del { background: none; border: none; color: #c33; cursor: pointer; font-size: 18px; }
  button.primary { background: #2a6df4; color: #fff; border: none; border-radius: 6px;
                   padding: 10px 18px; font-size: 14px; cursor: pointer; }
  button.secondary { background: none; border: 1px solid #8886; border-radius: 6px;
                      padding: 8px 14px; font-size: 13px; cursor: pointer; }
  .bar { display: flex; gap: 10px; margin: 18px 0; align-items: center; }
  #status { font-size: 13px; color: #2a6df4; }
  pre#preview { white-space: pre-wrap; background: #8881; padding: 12px; border-radius: 8px;
                font-size: 12.5px; max-height: 320px; overflow: auto; display: none; }
  details { margin-top: 24px; }
</style>
</head>
<body>
<h1>PM Gate Config</h1>
<div class="sub">Manages the automatic Stop-hook review in this SwingVision repo only
  (.claude/settings.json). Changes here take effect on your next turn.</div>

<div class="row">
  <label><input type="checkbox" id="enabled" class="toggle"> Gate enabled</label>
</div>
<div class="row">
  <label for="model">Model</label>
  <select id="model"></select>
  <label for="timeout" style="min-width:auto;margin-left:16px;">Timeout (s)</label>
  <input type="number" id="timeout" min="10" max="300" style="width:70px;">
</div>

<h3>Checks (toggle, edit, or add your own)</h3>
<div id="criteria"></div>
<button class="secondary" onclick="addCriterion()">+ Add check</button>

<div class="bar">
  <button class="primary" onclick="save()">Save</button>
  <button class="secondary" onclick="resetDefaults()">Reset to defaults</button>
  <button class="secondary" onclick="togglePreview()">Preview compiled prompt</button>
  <span id="status"></span>
</div>
<pre id="preview"></pre>

<script>
let cfg = null;
const MODELS = __MODEL_CHOICES__;

async function load() {
  cfg = await (await fetch('/api/config')).json();
  render();
}

function render() {
  document.getElementById('enabled').checked = !!cfg.enabled;
  const sel = document.getElementById('model');
  sel.innerHTML = MODELS.map(m => `<option value="${m}">${m}</option>`).join('');
  sel.value = cfg.model;
  document.getElementById('timeout').value = cfg.timeout;

  const box = document.getElementById('criteria');
  box.innerHTML = '';
  cfg.criteria.forEach((c, i) => {
    const div = document.createElement('div');
    div.className = 'card' + (c.active ? '' : ' off');
    div.innerHTML = `
      <div class="card-head">
        <input type="checkbox" class="toggle" ${c.active ? 'checked' : ''}
               onchange="cfg.criteria[${i}].active=this.checked; render()">
        <input type="text" value="${escapeAttr(c.title)}"
               oninput="cfg.criteria[${i}].title=this.value">
        <button class="del" title="remove" onclick="removeCriterion(${i})">&times;</button>
      </div>
      <textarea oninput="cfg.criteria[${i}].text=this.value">${escapeHtml(c.text)}</textarea>`;
    box.appendChild(div);
  });
}

function escapeHtml(s) { return (s || '').replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])); }
function escapeAttr(s) { return escapeHtml(s).replace(/"/g, '&quot;'); }

function addCriterion() {
  const nextId = Math.max(0, ...cfg.criteria.map(c => c.id)) + 1;
  cfg.criteria.push({id: nextId, title: 'New check', active: true, text: ''});
  render();
}
function removeCriterion(i) { cfg.criteria.splice(i, 1); render(); }

function readForm() {
  cfg.enabled = document.getElementById('enabled').checked;
  cfg.model = document.getElementById('model').value;
  cfg.timeout = parseInt(document.getElementById('timeout').value, 10) || 90;
}

async function save() {
  readForm();
  const r = await (await fetch('/api/save', {method: 'POST', body: JSON.stringify(cfg)})).json();
  document.getElementById('status').textContent = r.ok
    ? 'Saved -- takes effect on your next turn in Claude Code.' : 'Save failed.';
  setTimeout(() => document.getElementById('status').textContent = '', 4000);
}

async function resetDefaults() {
  if (!confirm('Reset every check back to the shipped defaults?')) return;
  cfg = await (await fetch('/api/reset', {method: 'POST'})).json();
  render();
  document.getElementById('status').textContent = 'Reset. Click Save to apply.';
}

async function togglePreview() {
  const pre = document.getElementById('preview');
  if (pre.style.display === 'block') { pre.style.display = 'none'; return; }
  readForm();
  const r = await (await fetch('/api/preview', {method: 'POST', body: JSON.stringify(cfg)})).json();
  pre.textContent = r.prompt;
  pre.style.display = 'block';
}

load();
</script>
</body>
</html>
""".replace("__MODEL_CHOICES__", json.dumps(MODEL_CHOICES))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path == "/api/config":
            self._send(200, load_config())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/save":
            cfg = self._body()
            save_config(cfg)
            apply_to_settings(cfg)
            self._send(200, {"ok": True, "config_path": str(CONFIG_PATH),
                              "settings_path": str(SETTINGS_PATH)})
        elif self.path == "/api/reset":
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            save_config(cfg)
            apply_to_settings(cfg)
            self._send(200, cfg)
        elif self.path == "/api/preview":
            cfg = self._body()
            self._send(200, {"prompt": build_prompt(cfg)})
        else:
            self._send(404, {"error": "not found"})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8795)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--build", action="store_true",
                     help="rebuild .claude/settings.json from the current config and exit "
                          "(no server, no browser)")
    args = ap.parse_args()

    if args.build:
        cfg = load_config()
        if not CONFIG_PATH.exists():
            save_config(cfg)
        apply_to_settings(cfg)
        print(f"Rebuilt {SETTINGS_PATH} from {CONFIG_PATH}")
        return

    if not CONFIG_PATH.exists():
        save_config(load_config())

    url = f"http://127.0.0.1:{args.port}/"
    print(f"PM Gate Config: {url}")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, [url]).start()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
