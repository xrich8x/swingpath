"""false_fire_viewer.py — click through every false fire, at two zoom levels.

WHY THIS EXISTS
---------------
`inspect_false_locks.py --contact-sheet` writes PNG grids, and every
classification this project has published (Session F's 71 raw locks, Session I's
universal five) was done by squinting at one. That works for a tally and fails at
the question that keeps coming up: *is the thing under the crosshair a real
tennis ball?* A 140 px context crop answers "what object is this attached to" and
a ball at that zoom is an ambiguous blob; answering "is it a ball" needs a 44 px
crop blown up, which then destroys the context. Two sheets, no way to hold both.

So this pairs them. One HTML file, no server, no network: every false lock as a
context tile, click it for context + zoom side by side, arrow keys to walk the
set. Filters by clip, by which models fire, and by class.

THE MARKER NEVER COVERS THE EVIDENCE. Context tiles get an open crosshair, zoom
tiles get corner ticks set well outside the candidate. A marker painted over the
pixels being judged is how you end up classifying your own annotation.

WHAT IT IS NOT: a labelling tool. It writes nothing. Classifications belong in
data/gold/false_lock_classes.json, entered deliberately, so a tally stays an
artifact that can be re-derived and disagreed with.

  py tools/false_fire_viewer.py --locks data/output/false_fires/new/locks.json \\
      --compare v21=data/output/false_fires/ballnet_v21/locks.json \\
      --compare armA=data/output/false_fires/pool_old_s0/locks.json \\
      --out data/output/false_fires/false_fires.html
"""
from __future__ import annotations

import argparse
import base64
import html
import json
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]

CTX_SRC, CTX_PX = 140, 260      # context: what object does this belong to
ZOOM_SRC, ZOOM_PX = 44, 400     # zoom: is this literally a ball


def _jpeg(im, quality=82) -> str:
    ok, buf = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode("ascii")


def _crop(im, x, y, src_px, out_px, interp):
    h, w = im.shape[:2]
    x0, y0 = max(0, x - src_px // 2), max(0, y - src_px // 2)
    x1, y1 = min(w, x0 + src_px), min(h, y0 + src_px)
    c = im[y0:y1, x0:x1]
    if c.size == 0:
        return None, 0, 0
    sx, sy = out_px / max(x1 - x0, 1), out_px / max(y1 - y0, 1)
    c = cv2.resize(c, (out_px, out_px), interpolation=interp)
    return c, int((x - x0) * sx), int((y - y0) * sy)


def _mark_context(c, cx, cy):
    """Open crosshair — a gap at the centre so the lock itself stays visible."""
    for d in (-18, 9):
        cv2.line(c, (cx + d, cy), (cx + d + 9, cy), (0, 0, 255), 1)
        cv2.line(c, (cx, cy + d), (cx, cy + d + 9), (0, 0, 255), 1)


def _mark_zoom(c, cx, cy, r=40, arm=14):
    """Corner ticks well clear of the candidate. Nothing over the pixels."""
    for ddx, ddy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        cv2.line(c, (cx + ddx * r, cy + ddy * r),
                 (cx + ddx * (r - arm), cy + ddy * r), (0, 0, 255), 2)
        cv2.line(c, (cx + ddx * r, cy + ddy * r),
                 (cx + ddx * r, cy + ddy * (r - arm)), (0, 0, 255), 2)


def build_tiles(locks, frames_root):
    out = []
    for r in locks:
        src = frames_root / r["clip"] / f"f{r['frame']:05d}.jpg"
        im = cv2.imread(str(src))
        if im is None:
            continue
        x, y = int(round(r["x"])), int(round(r["y"]))
        ctx, cx, cy = _crop(im, x, y, CTX_SRC, CTX_PX, cv2.INTER_LINEAR)
        zoom, zx, zy = _crop(im, x, y, ZOOM_SRC, ZOOM_PX, cv2.INTER_NEAREST)
        if ctx is None or zoom is None:
            continue
        _mark_context(ctx, cx, cy)
        _mark_zoom(zoom, zx, zy)
        out.append({**r, "ctx": _jpeg(ctx), "zoom": _jpeg(zoom, 88)})
    return out


# The file is written as UTF-8 and opened from disk with no HTTP charset
# header, so without this the browser falls back to windows-1252 and every em
# dash renders as mojibake.
PAGE = """<meta charset="utf-8">
<title>False fires — {{TITLE}}</title>
<style>
:root{--bg:#0e1116;--panel:#161b23;--line:#2a3140;--tx:#e6edf5;--dim:#93a1b5;
      --hot:#ff6b6b;--ok:#4ec9a7;--warn:#f0b429;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
     font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--panel);
       border-bottom:1px solid var(--line);padding:14px 18px}
h1{margin:0 0 4px;font-size:17px;letter-spacing:-.01em}
.sub{color:var(--dim);font-size:12.5px}
.bar{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
button{background:#1e2733;color:var(--tx);border:1px solid var(--line);
       border-radius:999px;padding:5px 12px;font-size:12.5px;cursor:pointer}
button:hover{border-color:#3d4a5e}
button.on{background:var(--tx);color:#0e1116;border-color:var(--tx);font-weight:600}
main{padding:18px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.09em;color:var(--dim);
   margin:26px 0 10px;font-weight:600}
h2 span{color:var(--tx);text-transform:none;letter-spacing:0;font-weight:400}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}
figure{margin:0;cursor:zoom-in;position:relative;border-radius:6px;overflow:hidden;
       border:1px solid var(--line);background:#000}
figure img{display:block;width:100%;height:auto}
figcaption{position:absolute;left:0;right:0;bottom:0;padding:3px 5px;
           background:linear-gradient(transparent,rgba(0,0,0,.85));
           font-size:10.5px;color:#ffe98a;font-family:ui-monospace,monospace}
.tags{position:absolute;top:4px;left:4px;display:flex;gap:3px}
.tag{font-size:9px;padding:1px 4px;border-radius:3px;font-weight:700;
     background:#000a;border:1px solid var(--line);color:var(--dim)}
.tag.only{background:var(--hot);color:#fff;border-color:var(--hot)}
dialog{border:none;background:transparent;padding:0;max-width:96vw}
dialog::backdrop{background:#000d}
.view{background:var(--panel);border:1px solid var(--line);border-radius:10px;
      padding:16px;color:var(--tx)}
.view .pair{display:flex;gap:14px;flex-wrap:wrap;justify-content:center}
.view img{border-radius:6px;background:#000}
.view .meta{margin-top:12px;font-family:ui-monospace,monospace;font-size:12px;
            color:var(--dim);text-align:center}
.view .meta b{color:var(--tx)}
.lab{font-size:11px;color:var(--dim);text-align:center;margin-bottom:5px}
.hint{color:var(--dim);font-size:11.5px;text-align:center;margin-top:10px}
.empty{color:var(--dim);padding:30px;text-align:center}
</style>
<header>
  <h1>False fires — {{TITLE}}</h1>
  <div class="sub">{{SUB}}</div>
  <div class="bar" id="bar"></div>
</header>
<main id="main"></main>
<dialog id="dlg"><div class="view">
  <div class="pair">
    <div><div class="lab">context — {{CTX}} px of source</div><img id="vctx"></div>
    <div><div class="lab">zoom — {{ZOOM}} px of source, nearest-neighbour</div><img id="vzoom"></div>
  </div>
  <div class="meta" id="vmeta"></div>
  <div class="hint">&larr; &rarr; to step &middot; Esc to close</div>
</div></dialog>
<script>
const ROWS = {{ROWS}}, CLIPS = {{CLIPS}}, MODELS = {{MODELS}};
let filt = {clip:null, model:null}, order = [], cur = 0;
const $ = s => document.querySelector(s);

function pass(r){
  if (filt.clip && r.clip !== filt.clip) return false;
  if (filt.model === '__only') return MODELS.every(m => !r.also[m]);
  if (filt.model && !r.also[filt.model]) return false;
  return true;
}
function render(){
  const main = $('#main'); main.innerHTML = ''; order = [];
  for (const clip of CLIPS){
    const rs = ROWS.filter(r => r.clip === clip && pass(r));
    if (!rs.length) continue;
    const h = document.createElement('h2');
    h.innerHTML = clip + ' <span>' + rs.length + ' shown</span>';
    main.appendChild(h);
    const g = document.createElement('div'); g.className = 'grid';
    for (const r of rs){
      const i = order.length; order.push(r);
      const f = document.createElement('figure');
      f.innerHTML = '<img loading="lazy" src="' + r.ctx + '">' +
        '<div class="tags">' + MODELS.map(m =>
          '<span class="tag' + (r.also[m] ? '' : ' only') + '">' +
          (r.also[m] ? m : 'no ' + m) + '</span>').join('') + '</div>' +
        '<figcaption>' + r.frame + (r.klass ? ' · ' + r.klass : '') + '</figcaption>';
      f.onclick = () => open_(i);
      g.appendChild(f);
    }
    main.appendChild(g);
  }
  if (!order.length) main.innerHTML = '<div class="empty">nothing matches</div>';
}
function open_(i){
  cur = i; const r = order[i];
  $('#vctx').src = r.ctx; $('#vzoom').src = r.zoom;
  $('#vmeta').innerHTML = '<b>' + r.clip + ':' + r.frame + '</b> &nbsp; ' +
    'img (' + r.x + ', ' + r.y + ')' +
    (r.court_x === null ? '' : ' &nbsp; court (' + r.court_x + ', ' + r.court_y + ') m') +
    (r.klass ? ' &nbsp; class <b>' + r.klass + '</b>' : '') +
    '<br>' + MODELS.map(m => (r.also[m] ? '' : 'not ') + 'fired by ' + m).join(' &middot; ') +
    ' &nbsp; [' + (i + 1) + ' / ' + order.length + ']';
  $('#dlg').showModal();
}
document.addEventListener('keydown', e => {
  if (!$('#dlg').open) return;
  if (e.key === 'ArrowRight') open_((cur + 1) % order.length);
  if (e.key === 'ArrowLeft')  open_((cur - 1 + order.length) % order.length);
});
function chip(label, on, fn){
  const b = document.createElement('button');
  b.textContent = label; if (on) b.className = 'on';
  b.onclick = fn; $('#bar').appendChild(b);
}
function bar(){
  $('#bar').innerHTML = '';
  chip('all clips', !filt.clip, () => { filt.clip = null; bar(); render(); });
  for (const c of CLIPS)
    chip(c, filt.clip === c, () => { filt.clip = c; bar(); render(); });
  const sep = document.createElement('span'); sep.style.width = '18px';
  $('#bar').appendChild(sep);
  chip('any', !filt.model, () => { filt.model = null; bar(); render(); });
  for (const m of MODELS)
    chip('also ' + m, filt.model === m,
         () => { filt.model = m; bar(); render(); });
  chip('this model only', filt.model === '__only',
       () => { filt.model = '__only'; bar(); render(); });
}
bar(); render();
</script>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--locks", required=True,
                    help="inspect_false_locks.py --json output for the model under review")
    ap.add_argument("--compare", action="append", default=[],
                    help="repeatable NAME=path/to/locks.json — shows, per lock, "
                         "whether that model fires on the same frame")
    ap.add_argument("--frames-root", default="data/gold/frames")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    blob = json.loads(Path(args.locks).read_text(encoding="utf-8"))
    locks = blob["locks"]
    others = {}
    for spec in args.compare:
        name, _, path = spec.partition("=")
        ob = json.loads(Path(path).read_text(encoding="utf-8"))
        others[name] = {(r["clip"], r["frame"]) for r in ob["locks"]}

    tiles = build_tiles(locks, REPO / args.frames_root)
    for t in tiles:
        t["also"] = {n: ((t["clip"], t["frame"]) in s) for n, s in others.items()}

    clips = list(dict.fromkeys(t["clip"] for t in tiles))
    p = blob.get("pooled", {})
    sub = (f"{p.get('fires', len(tiles))} locks on {p.get('n_scored', '?')} "
           f"human 'no ball' frames ({p.get('false_fire', '?')}%) &middot; "
           f"weights {html.escape(str(blob.get('weights')))} &middot; "
           f"stage {blob.get('stage')} &middot; measured against human gold clicks")

    keep = ("clip", "frame", "x", "y", "court_x", "court_y", "klass",
            "ctx", "zoom", "also")
    rows = [{k: t.get(k) for k in keep} for t in tiles]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    # Token replacement, not %-formatting: the page embeds JavaScript, and JS
    # uses % as modulo. A `%`-formatted template breaks the moment anyone edits
    # the script block, which is exactly what happened the first time.
    page = PAGE
    for token, value in (("{{TITLE}}", html.escape(Path(args.locks).parent.name)),
                         ("{{SUB}}", sub),
                         ("{{CTX}}", str(CTX_SRC)), ("{{ZOOM}}", str(ZOOM_SRC)),
                         ("{{ROWS}}", json.dumps(rows)),
                         ("{{CLIPS}}", json.dumps(clips)),
                         ("{{MODELS}}", json.dumps(list(others)))):
        page = page.replace(token, value)
    Path(args.out).write_text(page, encoding="utf-8")
    mb = Path(args.out).stat().st_size / 1e6
    print(f"wrote {args.out} ({len(tiles)} locks, {mb:.1f} MB)")


if __name__ == "__main__":
    main()
