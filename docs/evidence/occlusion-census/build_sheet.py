"""P2 occlusion census - build the candidate pool and the founder's blind sheet.

Written by qa. Lives beside its evidence file (qa does not write tools/). Definitions are
pre-registered in docs/evidence/occlusion-census.md (commit 29d2e3e) and not changed here.

Run from anywhere:  backend/.venv/Scripts/python.exe docs/evidence/occlusion-census/build_sheet.py
Outputs (this directory): pool.json, source_key.json, items.js, tally_form.csv
"""
from __future__ import annotations

import csv
import json
import os
import random

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "data", "output")

SEED = 20260916
N_BATCHES = 2
# per batch (AMENDMENT A2): 110+20 am_hard_utr, 35+15 yt_match40 = 180 items
COMPOSITION = {"am_hard_utr": dict(pool=110, neg=20), "yt_match40": dict(pool=35, neg=15)}
# AMENDMENT A1 (2026-09-16, pre-label): pre-reg used centre = onset - 0.04 s and an A/V
# match window [-0.05, +0.15]. The measured audio excess over a random-time null sits at
# +0.10..+0.20 s after the pipeline's bounce times, so that window split real events.
AUDIO_LAG_CENTRE_S = 0.12          # estimated contact = onset - 0.12 s (measured offset peak)
WIN_PRE_S, WIN_POST_S = 0.30, 0.25  # same window shape for every item (blind to source)
CLUSTER_SPAN_S = 0.35              # start-anchored cluster span (A and V together)
ZONE_HALF_S = 0.175                # target zone half-width before Voronoi clipping
V_MERGE_S = 0.15                   # V-only pre-merge (unchanged from pre-reg)
GAP_MAX_S = 0.5
K_MED = 3

CLIPS = {
    "am_hard_utr": dict(video="data/incoming/Hardcourt/am_hard_utr.mp4", fps=60000 / 1001,
                        height=1080, mount_m=1.74,
                        tracks=["am_hard_utr.perception.json"],
                        match="am_hard_utr.json", audio=True),
    "yt_match40": dict(video="data/incoming/Hardcourt/yt_match40.mp4", fps=29.0,
                       height=720, mount_m=1.64,
                       tracks=["yt_match40_v1.perception.json", "yt_match40_v2.perception.json",
                               "yt_match40_fusion.perception.json",
                               "yt_match40_tracknet.perception.json"],
                       match="yt_match40.json", audio=False),
}


def track_fps(n_entries: int, duration_s: float) -> float:
    """The cached track's own index rate (am_hard_utr's is ~30 fps on a 60 fps video)."""
    return n_entries / duration_s


def reversals(ball_px, fps_eff: float, height: int) -> list[dict]:
    """Bracketed image-y reversals: DOWN (median dy over previous K valid pts) then UP."""
    vmin = 1.0 * height / 720.0  # px per cached-track step (both tracks index at ~30 fps)
    pts = [(i, p[1]) for i, p in enumerate(ball_px) if p is not None]
    out = []
    gap_max = GAP_MAX_S * fps_eff
    for j in range(K_MED, len(pts) - K_MED):
        prev = pts[j - K_MED:j + 1]
        nxt = pts[j:j + K_MED + 1]
        # contiguity: no gap larger than gap_max inside either run
        if any(b[0] - a[0] > gap_max for a, b in zip(prev, prev[1:])):
            continue
        if any(b[0] - a[0] > gap_max for a, b in zip(nxt, nxt[1:])):
            continue
        dprev = np.median([(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(prev, prev[1:])])
        dnext = np.median([(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(nxt, nxt[1:])])
        if dprev > vmin and dnext < -vmin:
            out.append(dict(idx=pts[j][0], bracketed=False))
        # gap case: last-down point j, first-up point j+1, gap between them
        if j + 1 < len(pts) - K_MED:
            a, b = pts[j], pts[j + 1]
            gap = b[0] - a[0]
            if 2 < gap <= gap_max:
                nxt2 = pts[j + 1:j + 2 + K_MED]
                if any(q[0] - p[0] > gap_max for p, q in zip(nxt2, nxt2[1:])):
                    continue
                dn2 = np.median([(q[1] - p[1]) / (q[0] - p[0]) for p, q in zip(nxt2, nxt2[1:])])
                if dprev > vmin and dn2 < -vmin:
                    out.append(dict(idx=(a[0] + b[0]) / 2.0, bracketed=True))
    return out


def cluster(events: list[dict], win: float) -> list[dict]:
    events = sorted(events, key=lambda e: e["t"])
    groups: list[list[dict]] = []
    for e in events:
        if groups and e["t"] - groups[-1][-1]["t"] <= win:
            groups[-1].append(e)
        else:
            groups.append([e])
    merged = []
    for g in groups:
        merged.append(dict(t=float(np.median([e["t"] for e in g])),
                           kinds=sorted({k for e in g for k in e["kinds"]}),
                           bracketed=any(e.get("bracketed") for e in g)))
    return merged


def vision_candidates(name: str, cfg: dict, duration_s: float) -> list[dict]:
    ev = []
    m = json.load(open(os.path.join(OUT, cfg["match"])))
    for s in m["shots"]:
        if s.get("bounce_t_s") is not None:
            ev.append(dict(t=float(s["bounce_t_s"]), kinds=["pipeline_bounce"]))
    for tr in cfg["tracks"]:
        p = json.load(open(os.path.join(OUT, tr)))
        bp = p["ball_px"]
        fe = track_fps(len(bp), duration_s)
        for r in reversals(bp, fe, cfg["height"]):
            ev.append(dict(t=r["idx"] / fe, kinds=["reversal_bracketed" if r["bracketed"]
                                                    else "reversal"],
                           bracketed=r["bracketed"]))
    return cluster(ev, V_MERGE_S)


def video_duration(cfg: dict) -> float:
    import subprocess
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=duration", "-of", "csv=p=0", os.path.join(ROOT, cfg["video"])]).decode().strip())


def load_audio(cfg: dict) -> list[float]:
    if not cfg["audio"]:
        return []
    return json.load(open(os.path.join(HERE, "audio_am_hard_utr_raw.json")))["times_s"]


def cluster_events(V: list[dict], A: list[float], dur: float) -> list[dict]:
    """AMENDMENT A1 (pre-label). Greedy START-anchored clustering of all A and V events:
    an event joins the open cluster if it is within CLUSTER_SPAN_S of the cluster's FIRST
    event, so no cluster spans more than CLUSTER_SPAN_S (no single-linkage chaining).
    Audio times are first moved to their estimated contact time (onset - AUDIO_LAG_CENTRE_S)."""
    ev = [dict(t=v["t"], kind="V", v_kinds=v["kinds"], bracketed=v["bracketed"]) for v in V]
    ev += [dict(t=a - AUDIO_LAG_CENTRE_S, kind="A", onset=a) for a in A]
    ev.sort(key=lambda e: e["t"])
    groups: list[list[dict]] = []
    for e in ev:
        if groups and e["t"] - groups[-1][0]["t"] <= CLUSTER_SPAN_S:
            groups[-1].append(e)
        else:
            groups.append([e])
    pool = []
    for g in groups:
        vs = [e for e in g if e["kind"] == "V"]
        as_ = [e for e in g if e["kind"] == "A"]
        centre = float(np.median([e["t"] for e in vs])) if vs else float(
            np.median([e["t"] for e in as_]))
        pool.append(dict(t_center=centre, hasA=bool(as_), hasV=bool(vs),
                         src=("AV" if as_ and vs else "A" if as_ else "V"),
                         audio_onsets_s=[e["onset"] for e in as_],
                         v_kinds=sorted({k for e in vs for k in e["v_kinds"]}),
                         bracketed=any(e["bracketed"] for e in vs)))
    pool.sort(key=lambda r: r["t_center"])
    # Target zones: Voronoi between neighbouring centres, clipped to +-ZONE_HALF_S.
    for i, r in enumerate(pool):
        lo = r["t_center"] - ZONE_HALF_S
        hi = r["t_center"] + ZONE_HALF_S
        if i > 0:
            lo = max(lo, (pool[i - 1]["t_center"] + r["t_center"]) / 2.0)
        if i + 1 < len(pool):
            hi = min(hi, (pool[i + 1]["t_center"] + r["t_center"]) / 2.0)
        r["zone0"] = max(0.0, lo)
        r["zone1"] = min(dur, hi)
        r["t0"] = max(0.0, r["t_center"] - WIN_PRE_S)
        r["t1"] = min(dur, r["t_center"] + WIN_POST_S)
    return pool


def build_pool(name: str, cfg: dict):
    dur = video_duration(cfg)
    V = vision_candidates(name, cfg, dur)
    A = load_audio(cfg)
    pool = cluster_events(V, A, dur)
    for i, r in enumerate(pool):
        r["pool_id"] = f"{name}#{i:04d}"
    return pool, dur, V, A


def chance_coincidence(V: list[dict], A: list[float], dur: float, shifts=(-37.3, -19.1, 11.7,
                                                                             23.9, 41.3)) -> dict:
    """Null for AV membership: circularly shift audio against vision and re-cluster.
    Returns the fraction of V-bearing clusters that also carry A (and vice versa) under
    the shift - the rate at which membership happens by accident."""
    fa, fv = [], []
    for s in shifts:
        As = sorted(((a + s) % dur) for a in A)
        p = cluster_events(V, As, dur)
        v_items = [r for r in p if r["hasV"]]
        a_items = [r for r in p if r["hasA"]]
        fa.append(sum(r["hasA"] for r in v_items) / max(1, len(v_items)))
        fv.append(sum(r["hasV"] for r in a_items) / max(1, len(a_items)))
    return dict(shifts_s=list(shifts), p_A_given_Vitem_null=float(np.mean(fa)),
                p_V_given_Aitem_null=float(np.mean(fv)),
                per_shift_A=[round(x, 4) for x in fa], per_shift_V=[round(x, 4) for x in fv])


def negative_space(pool: list[dict], dur: float, n: int, rng: random.Random) -> list[dict]:
    """Seeded windows from time no candidate zone covers. Centre drawn uniformly over the
    uncovered time; zone = [c - ZONE_HALF_S, c + ZONE_HALF_S] clipped to the uncovered
    interval it falls in; redraw if it overlaps an already chosen negative zone."""
    cov = sorted((r["zone0"], r["zone1"]) for r in pool)
    gaps, t = [], 0.0
    for z0, z1 in cov:
        if z0 > t:
            gaps.append((t, z0))
        t = max(t, z1)
    if t < dur:
        gaps.append((t, dur))
    total = sum(b - a for a, b in gaps)
    out = []
    tries = 0
    while len(out) < n and tries < 100000:
        tries += 1
        u = rng.uniform(0, total)
        for a, b in gaps:
            if u <= b - a:
                c = a + u
                break
            u -= b - a
        z0, z1 = max(a, c - ZONE_HALF_S), min(b, c + ZONE_HALF_S)
        if z1 - z0 < 0.05:
            continue
        if any(not (z1 <= o["zone0"] or z0 >= o["zone1"]) for o in out):
            continue
        out.append(dict(t_center=c, zone0=z0, zone1=z1, t0=max(0.0, c - WIN_PRE_S),
                        t1=min(dur, c + WIN_POST_S)))
    return out


def main():
    pools, meta = {}, {}
    for name, cfg in CLIPS.items():
        pool, dur, V, A = build_pool(name, cfg)
        pools[name] = pool
        cells = {c: sum(r["src"] == c for r in pool) for c in ("AV", "A", "V")}
        zone_cover = sum(r["zone1"] - r["zone0"] for r in pool)
        meta[name] = dict(duration_s=dur, n_vision_clustered=len(V), n_audio=len(A),
                          pool=len(pool), cells=cells, mount_m=cfg["mount_m"], fps=cfg["fps"],
                          bracketed_in_pool=sum(r["bracketed"] for r in pool),
                          zone_seconds=round(zone_cover, 2),
                          zone_fraction_of_video=round(zone_cover / dur, 4),
                          chance=chance_coincidence(V, A, dur) if A else None)
        print(name, meta[name])

    # AMENDMENT A2 (pre-label): per-batch composition, shuffled WITHIN the batch, so a
    # batch boundary is a clean stopping point. NEG items are windows from time that no
    # candidate zone covers - the audit of what the candidate source REJECTED.
    rng = random.Random(SEED)
    perm, negs = {}, {}
    for name in CLIPS:  # fixed order -> reproducible
        ids = list(range(len(pools[name])))
        rng.shuffle(ids)
        perm[name] = ids
        negs[name] = negative_space(pools[name], meta[name]["duration_s"],
                                    N_BATCHES * COMPOSITION[name]["neg"], rng)
        meta[name]["uncovered_seconds"] = round(
            meta[name]["duration_s"] - meta[name]["zone_seconds"], 2)

    items = []
    cur = {n: 0 for n in CLIPS}
    curn = {n: 0 for n in CLIPS}
    for bno in range(1, N_BATCHES + 1):
        batch = []
        for name in CLIPS:
            for _ in range(COMPOSITION[name]["pool"]):
                batch.append((name, "pool", perm[name][cur[name]])); cur[name] += 1
            for _ in range(COMPOSITION[name]["neg"]):
                batch.append((name, "neg", curn[name])); curn[name] += 1
        rng.shuffle(batch)
        items += [(bno,) + t for t in batch]

    rows, key = [], {}
    for n, (bno, clip, kind, idx) in enumerate(items, start=1):
        r = pools[clip][idx] if kind == "pool" else negs[clip][idx]
        item_id = f"P2-{n:03d}"
        rows.append(dict(item=item_id, batch=bno, clip=clip,
                         video="../../../" + CLIPS[clip]["video"], fps=CLIPS[clip]["fps"],
                         audio=CLIPS[clip]["audio"], t0=round(r["t0"], 3),
                         t_center=round(r["t_center"], 3), t1=round(r["t1"], 3),
                         zone0=round(r["zone0"], 3), zone1=round(r["zone1"], 3)))
        if kind == "pool":
            key[item_id] = dict(kind="pool", pool_id=r["pool_id"], src=r["src"],
                                v_kinds=r["v_kinds"], bracketed=r["bracketed"],
                                audio_onsets_s=r["audio_onsets_s"])
        else:
            key[item_id] = dict(kind="neg", neg_id=f"{clip}!neg{idx:03d}",
                                zone_len_s=round(r["zone1"] - r["zone0"], 4))
    meta["negatives"] = negs

    json.dump(dict(seed=SEED, meta=meta, pools=pools), open(os.path.join(HERE, "pool.json"), "w"),
              indent=1)
    json.dump(dict(note="SOURCE KEY - the founder must not open this before labelling.",
                   key=key), open(os.path.join(HERE, "source_key.json"), "w"), indent=1)
    with open(os.path.join(HERE, "items.js"), "w") as f:
        f.write("// generated by build_sheet.py - do not edit by hand\n")
        f.write("const P2_ITEMS = " + json.dumps(rows, indent=0) + ";\n")
    with open(os.path.join(HERE, "tally_form.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "batch", "clip", "t_center_s", "zone_s",
                    "Q1_bounce(Y/N/?)", "Q2_visibility(VISIBLE/PLAYER/NET/FRAME/BLUR/OTHER/?)",
                    "Q3_near_line(Y/N/?)", "Q4_half(NEAR/FAR/?)", "note"])
        for r in rows:
            w.writerow([r["item"], r["batch"], r["clip"], r["t_center"], f"{r['zone0']}-{r['zone1']}",
                        "", "", "", "", ""])
    print("items", len(items), {b: sum(r["batch"] == b for r in rows) for b in range(1, N_BATCHES + 1)})


if __name__ == "__main__":
    main()
