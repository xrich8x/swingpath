"""Court Setup - the SwingVision-style ADJUSTABLE OVERLAY calibration tool.

Instead of clicking four corners from scratch, you get a whole court overlay you
nudge into place: drag the middle to slide it, pull a corner to scale/tilt it, and
the line-snap tightens it onto the paint. "Auto-detect" seeds the overlay from the
line-fit detector; if it locks onto the wrong rung you just drag it right.

    backend/.venv/Scripts/python.exe tools/court_setup_server.py --clip am_ntrp40
    backend/.venv/Scripts/python.exe tools/court_setup_server.py --frame path/to/frame.jpg
    backend/.venv/Scripts/python.exe tools/court_setup_server.py --video clip.mp4   # first frame

Save writes {landmark: [x_px, y_px]} (the 4 doubles corners) - exactly what
`run.py analyze --keypoints` consumes.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]


def auto_fit(frame):
    """Auto-detect the court, then snap it onto the lines. Returns {corner:[x,y]}
    (the fitted overlay) or None if the detector couldn't lock a court."""
    from swingvision import calibration, court
    import eval_court_autodetect as ad
    res = ad.autodetect(frame, calibration, court)
    if res is None:
        return None
    _, _, ref = res
    named = {k: [float(ref[k][0]), float(ref[k][1])] for k in DBL}
    _, out, _snapped, _c0, c1 = calibration.snap_to_lines(
        frame, named, min_coverage=0.0, max_move_px=60.0)
    use = out if all(k in out for k in DBL) else named
    # The free corner-snap can undo the detector's physical gate (it moves the 4
    # corners independently) — re-lock the snapped quad to a real camera view.
    h, w = frame.shape[:2]
    dt = ad._precompute(frame, calibration)[0]
    r = ad.cam_fit_quad(use, calibration, court, w, h, dt=dt)
    if r is not None:
        use = r[1]
    print(f"[setup] auto-fit court (coverage {c1:.2f})")
    return {k: [float(use[k][0]), float(use[k][1])] for k in DBL}

PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Court Setup</title>
<style>
  :root{--bg:#0e141b;--panel:#161f2a;--ink:#e7edf3;--muted:#93a2b3;--line:#26323f;
    --accent:#c8e04a;--ok:#34d17c;--warn:#ffb84a;}
  *{box-sizing:border-box} html,body{margin:0}
  body{background:var(--bg);color:var(--ink);font:15px/1.5 ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif;}
  header{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:12px 16px;
    border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}
  h1{font-size:15px;margin:0 12px 0 0;font-weight:700;letter-spacing:-.01em}
  button{font:inherit;font-weight:600;color:var(--ink);background:var(--panel);
    border:1px solid var(--line);border-radius:9px;padding:8px 13px;cursor:pointer}
  button:hover{border-color:var(--accent)} button:disabled{opacity:.5;cursor:default}
  button.primary{background:var(--accent);color:#182200;border-color:var(--accent)}
  button.ok{border-color:var(--ok);color:var(--ok)}
  .sp{flex:1}
  #status{padding:8px 16px;color:var(--muted);font-size:13.5px;min-height:20px}
  #status b{color:var(--ink)} #status .g{color:var(--ok)} #status .w{color:var(--warn)}
  .wrap{padding:8px 16px 40px;overflow:auto}
  canvas{background:#0c0e12;border-radius:10px;touch-action:none;cursor:grab}
  canvas.grabbing{cursor:grabbing}
  kbd{background:var(--panel);border:1px solid var(--line);border-bottom-width:2px;
    border-radius:5px;padding:0 5px;font:12px ui-monospace,Menlo,Consolas,monospace}
  .hint{color:var(--muted);font-size:12.5px;padding:0 16px 10px}
</style></head><body>
<header>
  <h1>Court Setup</h1>
  <button id="auto">Auto-detect</button>
  <button id="snap" class="primary">Snap to lines</button>
  <button id="big">Bigger</button>
  <button id="small">Smaller</button>
  <button id="reset">Reset</button>
  <span class="sp"></span>
  <button id="save" class="ok">Save calibration</button>
</header>
<div id="status">Drag the <b>middle</b> of the court to move it, a <b>corner</b> to reshape. Then <b>Snap to lines</b>.</div>
<div class="wrap"><canvas id="view"></canvas></div>
<div class="hint">Corners may sit outside the frame (in the dark margin) - place them where the lines would meet. <kbd>+</kbd>/<kbd>&minus;</kbd> resize &middot; arrow keys nudge.</div>
<script>
"use strict";
const $=id=>document.getElementById(id);
const view=$("view"), ctx=view.getContext("2d");
const CORNERS=[{key:"near_bl_doubles",m:[0,0]},{key:"near_br_doubles",m:[10.97,0]},
  {key:"far_br_doubles",m:[10.97,23.77]},{key:"far_bl_doubles",m:[0,23.77]}];
const KP={far_bl_doubles:[0,23.77],far_br_doubles:[10.97,23.77],near_bl_doubles:[0,0],
  near_br_doubles:[10.97,0],far_bl_singles:[1.37,23.77],near_bl_singles:[1.37,0],
  far_br_singles:[9.6,23.77],near_br_singles:[9.6,0],far_sl_left:[1.37,18.285],
  far_sl_right:[9.6,18.285],near_sl_left:[1.37,5.485],near_sl_right:[9.6,5.485],
  far_t:[5.485,18.285],near_t:[5.485,5.485]};
const LINES=[[[0,0],[10.97,0]],[[0,23.77],[10.97,23.77]],[[0,0],[0,23.77]],
  [[10.97,0],[10.97,23.77]],[[1.37,0],[1.37,23.77]],[[9.6,0],[9.6,23.77]],
  [[1.37,5.485],[9.6,5.485]],[[1.37,18.285],[9.6,18.285]],[[5.485,5.485],[5.485,18.285]]];
const NET=[[0,11.885],[10.97,11.885]];

function solveH(src,dst){const A=[],b=[];for(let i=0;i<4;i++){const[X,Y]=src[i],[u,v]=dst[i];
  A.push([X,Y,1,0,0,0,-X*u,-Y*u]);b.push(u);A.push([0,0,0,X,Y,1,-X*v,-Y*v]);b.push(v);}
  for(let c=0;c<8;c++){let p=c;for(let r=c+1;r<8;r++)if(Math.abs(A[r][c])>Math.abs(A[p][c]))p=r;
    [A[c],A[p]]=[A[p],A[c]];[b[c],b[p]]=[b[p],b[c]];if(Math.abs(A[c][c])<1e-12)return null;
    for(let r=0;r<8;r++){if(r===c)continue;const f=A[r][c]/A[c][c];
      for(let k=c;k<8;k++)A[r][k]-=f*A[c][k];b[r]-=f*b[c];}}
  const h=b.map((v,i)=>v/A[i][i]);return[[h[0],h[1],h[2]],[h[3],h[4],h[5]],[h[6],h[7],1]];}
function applyH(H,X,Y){const d=H[2][0]*X+H[2][1]*Y+1;
  return[(H[0][0]*X+H[0][1]*Y+H[0][2])/d,(H[1][0]*X+H[1][1]*Y+H[1][2])/d];}

let W=0,H=0,scale=1,padx=0,pady=0;const PAD=0.35;
let corners=[null,null,null,null], drag=null, mode=null, last=null;
const img=new Image();

function fit(){const avail=Math.max(320,(window.innerWidth||1000)-40);
  scale=Math.min(Math.max(avail/(W*(1+2*PAD)),0.1),1);
  padx=Math.round(PAD*W*scale);pady=Math.round(PAD*H*scale);
  view.width=Math.round(W*scale)+2*padx;view.height=Math.round(H*scale)+2*pady;}
function toImg(e){const r=view.getBoundingClientRect();
  const cx=(e.clientX-r.left)*view.width/r.width,cy=(e.clientY-r.top)*view.height/r.height;
  return[(cx-padx)/scale,(cy-pady)/scale];}
function centroid(){let x=0,y=0;for(const c of corners){x+=c[0];y+=c[1];}return[x/4,y/4];}
function isOff(c){return c[0]<0||c[1]<0||c[0]>W||c[1]>H;}
function inQuad(x,y){let hit=false;for(let i=0,j=3;i<4;j=i++){const[xi,yi]=corners[i],[xj,yj]=corners[j];
  if(((yi>y)!=(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi))hit=!hit;}return hit;}
function nearest(x,y){let best=null,bd=12/scale;for(let i=0;i<4;i++){
  const d=Math.hypot(corners[i][0]-x,corners[i][1]-y);if(d<bd){bd=d;best=i;}}return best;}

function defaultCourt(){corners=[[0.14*W,0.98*H],[0.86*W,0.98*H],[0.72*W,0.30*H],[0.28*W,0.30*H]];}

function render(){const s=scale;
  ctx.fillStyle="#0c0e12";ctx.fillRect(0,0,view.width,view.height);
  ctx.drawImage(img,padx,pady,Math.round(W*s),Math.round(H*s));
  ctx.strokeStyle="rgba(255,255,255,.28)";ctx.lineWidth=1;
  ctx.strokeRect(padx+.5,pady+.5,Math.round(W*s),Math.round(H*s));
  const P=(X,Y,Hm)=>{const p=applyH(Hm,X,Y);return[padx+p[0]*s,pady+p[1]*s];};
  const Hm=solveH(CORNERS.map(c=>c.m),corners);
  if(Hm){ctx.lineWidth=2;ctx.strokeStyle="rgba(120,220,160,.95)";
    for(const[a,b]of LINES){const p=P(a[0],a[1],Hm),q=P(b[0],b[1],Hm);
      ctx.beginPath();ctx.moveTo(p[0],p[1]);ctx.lineTo(q[0],q[1]);ctx.stroke();}
    ctx.strokeStyle="rgba(255,210,120,.95)";const n0=P(NET[0][0],NET[0][1],Hm),n1=P(NET[1][0],NET[1][1],Hm);
    ctx.beginPath();ctx.moveTo(n0[0],n0[1]);ctx.lineTo(n1[0],n1[1]);ctx.stroke();
    ctx.fillStyle="rgba(140,200,255,.9)";for(const k in KP){const p=P(KP[k][0],KP[k][1],Hm);
      ctx.beginPath();ctx.arc(p[0],p[1],2.3,0,7);ctx.fill();}}
  for(let i=0;i<4;i++){const c=corners[i],x=padx+c[0]*s,y=pady+c[1]*s,off=isOff(c);
    ctx.lineWidth=off?2.5:2;ctx.strokeStyle=off?"#ff9c4a":"#14171c";ctx.fillStyle="#ffd24a";
    ctx.beginPath();ctx.arc(x,y,7,0,7);if(!off)ctx.fill();ctx.stroke();
    ctx.fillStyle=off?"#ff9c4a":"#14171c";ctx.font="bold 11px system-ui";
    ctx.fillText(String(i+1)+(off?"*":""),x-3,off?y-11:y+4);}}

function setStatus(msg){$("status").innerHTML=msg;}
function corDict(){const o={};CORNERS.forEach((c,i)=>o[c.key]=[corners[i][0],corners[i][1]]);return o;}
function setDict(o){corners=CORNERS.map(c=>o[c.key].slice());}

view.addEventListener("pointerdown",e=>{const[x,y]=toImg(e);const h=nearest(x,y);
  if(h!==null){mode="corner";drag=h;}else if(inQuad(x,y)){mode="move";last=[x,y];view.classList.add("grabbing");}
  view.setPointerCapture(e.pointerId);});
view.addEventListener("pointermove",e=>{if(!mode)return;const[x,y]=toImg(e);
  if(mode==="corner"){corners[drag]=[x,y];}
  else{const dx=x-last[0],dy=y-last[1];for(const c of corners){c[0]+=dx;c[1]+=dy;}last=[x,y];}
  render();});
async function regularize(){const r=await api("/api/regularize",{corners:corDict()});
  if(r.corners){setDict(r.corners);render();
    if(r.moved>3)setStatus('Shape locked to a <b>real camera view</b> (adjusted '+r.moved.toFixed(0)+'px). Courts can’t warp — drag corners to steer, the shape stays legal.');}}
function endDrag(){const wasCorner=(mode==="corner");mode=null;drag=null;
  view.classList.remove("grabbing");if(wasCorner)regularize();}
view.addEventListener("pointerup",endDrag);view.addEventListener("pointercancel",endDrag);

function scaleBy(f){const[cx,cy]=centroid();for(const c of corners){c[0]=cx+(c[0]-cx)*f;c[1]=cy+(c[1]-cy)*f;}render();}
$("big").onclick=()=>scaleBy(1.06);$("small").onclick=()=>scaleBy(1/1.06);
$("reset").onclick=()=>{defaultCourt();render();setStatus("Overlay reset. Drag it over the court, then <b>Snap</b>.");};
document.addEventListener("keydown",e=>{const N={ArrowLeft:[-2,0],ArrowRight:[2,0],ArrowUp:[0,-2],ArrowDown:[0,2]}[e.key];
  if(N){for(const c of corners){c[0]+=N[0];c[1]+=N[1];}render();e.preventDefault();}
  else if(e.key==="+"||e.key==="=")scaleBy(1.06);else if(e.key==="-")scaleBy(1/1.06);});

async function api(path,body){const r=await fetch(path,{method:"POST",
  headers:{"Content-Type":"application/json"},body:JSON.stringify(body||{})});return r.json();}
$("auto").onclick=async()=>{setStatus("Auto-detecting the court...");$("auto").disabled=true;
  const r=await api("/api/autodetect",{});$("auto").disabled=false;
  if(r.corners){setDict(r.corners);render();setStatus('Auto-detected (line support '+(r.score*100|0)+'%). If it grabbed the wrong court, <b>drag it</b> onto the right one, then <b>Snap</b>.');}
  else setStatus('<span class="w">Auto-detect couldn’t lock a court</span> - drag the overlay onto it by hand, then <b>Snap</b>.');};
$("snap").onclick=async()=>{setStatus("Snapping to the white lines...");$("snap").disabled=true;
  const r=await api("/api/snap",{corners:corDict()});$("snap").disabled=false;
  if(r.corners){setDict(r.corners);render();
    setStatus(r.snapped?'<span class="g">Snapped onto the lines</span> (coverage '+(r.coverage*100|0)+'%). Adjust if needed, then <b>Save</b>.'
      :'<span class="w">Snap didn’t improve the fit</span> (coverage '+(r.coverage*100|0)+'%) - nudge it closer and try again.');}};
$("save").onclick=async()=>{const r=await api("/api/save",{corners:corDict()});
  if(r.ok){if(r.corners){setDict(r.corners);render();}
    setStatus('<span class="g">Saved</span> to <b>'+r.path+'</b>'+
      (r.moved>3?' (shape locked to a real camera view, adjusted '+r.moved.toFixed(0)+'px)':'')+
      ' - use it with <kbd>run.py analyze --keypoints</kbd>.');}
  else setStatus('Save failed.');};

fetch("/api/meta").then(r=>r.json()).then(m=>{W=m.w;H=m.h;
  img.onload=()=>{fit();
    if(m.seed){setDict(m.seed);setStatus('Auto-seeded a court - <b>drag</b> to fit, then <b>Snap</b>.');}
    else{defaultCourt();setStatus('Drag the <b>middle</b> of the court to move it, a <b>corner</b> to reshape. Then <b>Snap to lines</b>.');}
    render();};
  img.src="/frame.jpg";});
window.addEventListener("resize",()=>{if(W){fit();render();}});
</script></body></html>"""


def build_handler(state):
    import math

    import cv2
    import numpy as np
    from swingvision import calibration, court
    import eval_court_autodetect as ad

    frame = state["frame"]
    h, w = frame.shape[:2]
    ok, buf = cv2.imencode(".jpg", frame)
    jpg = buf.tobytes()
    dt = ad._precompute(frame, calibration)[0]   # line-distance map for Snap's polish

    def corners_named(d):
        return {k: [float(d[k][0]), float(d[k][1])] for k in DBL}

    def lock_shape(named, use_dt=False):
        """Project a (possibly hand-warped) quad onto the closest physical camera
        view of a regulation court. Returns (locked_corners, moved_px)."""
        r = ad.cam_fit_quad(named, calibration, court, w, h,
                            dt=dt if use_dt else None)
        if r is None:
            return named, 0.0
        locked = r[1]
        moved = max(math.hypot(locked[k][0] - named[k][0],
                               locked[k][1] - named[k][1]) for k in DBL)
        return locked, moved

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

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/index"):
                self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            elif self.path.startswith("/frame.jpg"):
                self._send(200, jpg, "image/jpeg")
            elif self.path == "/api/meta":
                self._send(200, {"w": w, "h": h, "seed": state.get("seed")})
            else:
                self._send(404, {"error": "not found"})

        def _body(self):
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")

        def do_POST(self):
            if self.path == "/api/meta":
                self._send(200, {"w": w, "h": h, "seed": state.get("seed")})
            elif self.path == "/api/autodetect":
                res = ad.autodetect(frame, calibration, court)
                if res is None:
                    self._send(200, {"corners": None})
                else:
                    Hd, score, ref = res
                    self._send(200, {"corners": corners_named(ref), "score": float(score)})
            elif self.path == "/api/snap":
                named = corners_named(self._body()["corners"])
                # Interactive snap: refine from wherever the user placed it and keep
                # any improvement (min_coverage=0 -> no absolute gate; the user is
                # looking at the result). Wider basin than the pipeline default.
                Hs, out, snapped, c0, c1 = calibration.snap_to_lines(
                    frame, named, min_coverage=0.0, max_move_px=60.0)
                use = out if all(k in out for k in DBL) else named
                # The corner-snap moves 4 corners independently — re-lock to a
                # physical camera view (with the paint polish) before returning.
                use, _ = lock_shape(use, use_dt=True)
                self._send(200, {"corners": corners_named(use),
                                 "snapped": bool(snapped), "coverage": float(c1)})
            elif self.path == "/api/regularize":
                # After a corner drag: keep the user's steering but resolve the
                # whole overlay as a rigid regulation court seen from a camera.
                named = corners_named(self._body()["corners"])
                locked, moved = lock_shape(named, use_dt=False)
                self._send(200, {"corners": corners_named(locked), "moved": float(moved)})
            elif self.path == "/api/save":
                named = corners_named(self._body()["corners"])
                # Never save an impossible court: pure shape lock (no paint pull —
                # at Save time the user's placement is the authority).
                locked, moved = lock_shape(named, use_dt=False)
                Path(state["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(state["out"]).write_text(
                    json.dumps(corners_named(locked), indent=2), encoding="utf-8")
                self._send(200, {"ok": True, "path": state["out"],
                                 "corners": corners_named(locked), "moved": float(moved)})
            else:
                self._send(404, {"error": "not found"})

    return Handler


def load_frame(args):
    import cv2
    if args.frame:
        img = cv2.imread(args.frame)
        if img is None:
            raise SystemExit(f"cannot read image: {args.frame}")
        return img
    if args.clip:
        d = REPO / "data" / "gold" / "frames" / args.clip
        jpgs = sorted(d.glob("*.jpg"))
        if not jpgs:
            raise SystemExit(f"no frames in {d}")
        return cv2.imread(str(jpgs[len(jpgs) // 2]))
    if args.video:
        cap = cv2.VideoCapture(args.video)
        ok, im = cap.read()
        cap.release()
        if not ok:
            raise SystemExit(f"cannot read first frame of {args.video}")
        return im
    raise SystemExit("pass --clip, --frame, or --video")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", help="gold clip id (uses a middle frame)")
    ap.add_argument("--frame", help="path to a single image")
    ap.add_argument("--video", help="path to a video (uses the first frame)")
    ap.add_argument("--out", default="court_pts.json", help="where Save writes the keypoints")
    ap.add_argument("--no-auto", action="store_true",
                    help="skip the auto-detect+snap at startup (start from a plain overlay)")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    frame = load_frame(args)
    state = {"frame": frame, "out": args.out, "seed": None}

    # Auto-fit on startup by default: detect the court, then snap it onto the lines,
    # so the overlay opens already fitted and the user only nudges if it's off.
    if not args.no_auto:
        state["seed"] = auto_fit(frame)

    Handler = build_handler(state)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Court Setup at {url}  (frame {frame.shape[1]}x{frame.shape[0]})")
    print("  Drag the overlay onto the court, Snap to lines, Save. Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, [url]).start()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
