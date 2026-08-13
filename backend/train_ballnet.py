"""Train OUR ball detector (swingvision._ballnet.BallNet) on the pseudo-label
dataset built by build_ball_dataset.py / relabel_train_clips.py.

    .venv-train/Scripts/python.exe train_ballnet.py --epochs 40

Samples are 3-frame windows (newest first, 512x288, /255) with a Gaussian target
heatmap at the tracker's pseudo-label. Temporal split per clip: the last 20% of
labeled frames are validation (no leakage from smoothing/augmentation). Metric is
localization: predicted heatmap peak vs label (median px + hit-rate within 10px).
Best checkpoint -> weights/ballnet.pt.

v2 additions (HANDOFF §11): datasets may carry "negatives" — frame indices with
NO ball, trained against an all-zero heatmap. v1 never saw a negative, which is
why it fires at junk whenever play stops (60% FP on the human gold benchmark).
Val negatives report the false-fire rate (peak >= 0.5, the OurBallDetector
default score_thresh); model selection uses hit@10 minus false-fire so a
checkpoint can't win by firing everywhere.

GOLD PROTECTION: training on a clip a human hand-labelled would make every
benchmark number a lie (ML_PRACTICES: never let a model grade its own homework).
The forbidden set is derived from data/gold/*.manifest.json — the source video of
every gold clip — and checked against each dataset dir's recorded source, so a
newly labelled clip is protected the moment it exists. --exclude skips further
dirs by name and now ERRORS on a name that matches nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swingvision._ballnet import BallNet

IN_W, IN_H = 512, 288
SIGMA = 3.0
# Visibility-weighted loss (TOTNet §ablation): occlusion augmentation ALONE makes
# tracking WORSE; it only helps when the occluded (hard) samples are weighted higher
# so the model is forced to recover the ball from temporal context instead of the
# missing current-frame pixels. Synthetic-occlusion frames are our "fully occluded"
# visibility level and carry OCC_WEIGHT; everything else is 1.0.
OCC_WEIGHT = 3.0
# Negative frames (no ball, incl. mined hard negatives) carry an all-zero target,
# so with pos_weight=100 on the ball pixels and 4x more positives than negatives,
# a negative's loss is negligible and the model never learns to shut up on the
# HUD/post/fence confusers (measured: false-fire stuck ~90% on the val hard
# negatives even as recall recovered). Upweighting the negative SAMPLE is the
# direct lever — suppressing a false-fire now costs as much as finding a ball.
NEG_WEIGHT = 8.0


def gaussian_heatmap(x, y, w=IN_W, h=IN_H, sigma=SIGMA):
    xs = np.arange(w, dtype=np.float32)
    ys = np.arange(h, dtype=np.float32)
    gx = np.exp(-((xs - x) ** 2) / (2 * sigma * sigma))
    gy = np.exp(-((ys - y) ** 2) / (2 * sigma * sigma))
    return np.outer(gy, gx)


def _motion_blur_kernel(size, angle_deg):
    """A directional line kernel — simulates a fast ball / camera motion streak."""
    k = np.zeros((size, size), np.float32)
    k[size // 2, :] = 1.0
    M = cv2.getRotationMatrix2D((size / 2 - 0.5, size / 2 - 0.5), angle_deg, 1.0)
    k = cv2.warpAffine(k, M, (size, size))
    s = k.sum()
    return k / s if s > 0 else k


def gold_source_videos(root):
    """Basenames of the source videos behind every hand-labelled gold clip.

    Read from data/gold/*.manifest.json rather than hardcoded, because a hardcoded
    list rots silently: --exclude's default was ["indoor_elev"], a directory that
    does not exist in data/ball_dataset and never did, so the stated protection had
    been enforcing nothing — and could not have covered am_hard_utr when that clip
    was labelled. Deriving it means a new gold clip is protected on arrival.
    """
    import glob

    gold_dir = os.path.join(os.path.dirname(os.path.abspath(root)), "gold")
    out = {}
    for p in glob.glob(os.path.join(gold_dir, "*.manifest.json")):
        if ".court." in os.path.basename(p):
            continue    # court-corner labels, not a ball benchmark
        try:
            with open(p, "r", encoding="utf-8") as f:
                m = json.load(f)
        except Exception:
            continue
        vid = m.get("video")
        if vid:
            out[os.path.basename(vid).lower()] = m.get("clip", os.path.basename(p))

    # FOLLOW THE TRIM. A clip cut out of a longer recording gets a new filename,
    # and this guard matches on filename — so trimming silently defeated it. Found
    # live: gold clip `hd_shortcourt_1` is "7 UTR vs 8 UTR [UHf0LeMU2pg].mp4" and a
    # training set had been built from "UHf0LeMU2pg.mp4", the same footage cut
    # shorter. The guard reported no leak because the names differ.
    # data/train_clips/lineage.json records {trimmed name: source name}; any trim of
    # a gold source is gold too.
    lin = os.path.join(os.path.dirname(os.path.abspath(root)), "train_clips",
                       "lineage.json")
    try:
        with open(lin, "r", encoding="utf-8") as f:
            for cut, src in json.load(f).get("clips", {}).items():
                owner = out.get(os.path.basename(src).lower())
                if owner:
                    out[os.path.basename(cut).lower()] = owner
    except (OSError, ValueError):
        pass
    return out


def assert_no_gold_leak(root, exclude):
    """Abort if any dataset dir was built from a gold clip's video, or if an
    --exclude name matches no directory (a guard that silently matches nothing is
    worse than no guard — it reads as protection in the log)."""
    gold = gold_source_videos(root)
    dirs, leaks = [], []
    for tag in sorted(os.listdir(root)):
        d = os.path.join(root, tag)
        lp = os.path.join(d, "labels.json")
        if not os.path.isfile(lp):
            continue
        dirs.append(tag)
        if tag in exclude:
            continue
        try:
            with open(lp, "r", encoding="utf-8") as f:
                vid = (json.load(f).get("provenance") or {}).get("video")
        except Exception:
            vid = None
        if vid and os.path.basename(vid).lower() in gold:
            leaks.append((tag, gold[os.path.basename(vid).lower()]))
    if leaks:
        lines = "\n".join(f"    {t}  <- gold clip '{c}'" for t, c in leaks)
        raise SystemExit(
            "REFUSING TO TRAIN: these dataset dirs come from hand-labelled gold "
            f"clips, which are the TEST set:\n{lines}\n"
            "Every benchmark number would be measuring the model on its own "
            "training data. Remove the dir or pass it to --exclude deliberately.")
    unknown = [e for e in exclude if e not in dirs]
    if unknown:
        raise SystemExit(
            f"--exclude names no dataset dir: {unknown}\n"
            f"    available: {dirs}\n"
            "Refusing to run rather than print a protection that isn't happening.")
    print(f"[gold-guard] {len(gold)} gold clips known, none present in {len(dirs)} "
          f"dataset dirs")


def assert_no_swingvision_leak(root, exclude=()):
    """Abort if a dataset dir's clip carries a SwingVision overlay and has not
    been scrubbed.

    User instruction, 2026-08-13: do not train on SwingVision information. Five
    clips in the pool carry another system's rendered output — mini-court radar,
    stroke/speed readout, score panel, and a watermark that is a literal yellow
    tennis ball — and 83 pseudo-labels landed inside one of those graphics.

    Same shape as the gold guard, for the same reason: the rule has to be
    enforced by the trainer rather than remembered by whoever runs it. A dir is
    compliant when tools/scrub_swingvision.py has written swingvision_mask.json
    into it; BallWindows then paints the boxes at load and drops the in-box
    labels. Excluding the dir entirely is also compliant — it just costs the 27%
    of the pool those clips represent.
    """
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
    try:
        from scrub_swingvision import sv_clips
    except Exception as e:                       # tool absent: fail loud, not open
        raise SystemExit(f"REFUSING TO TRAIN: cannot import the SwingVision "
                         f"scrub guard ({e}). The rule is not optional.")
    stems = {f"yt_{s}" for s in sv_clips()}
    missing = []
    for tag in sorted(os.listdir(root)):
        d = os.path.join(root, tag)
        if not os.path.isfile(os.path.join(d, "labels.json")) or tag in exclude:
            continue
        if tag in stems and not os.path.isfile(
                os.path.join(d, "swingvision_mask.json")):
            missing.append(tag)
    if missing:
        raise SystemExit(
            "REFUSING TO TRAIN: these dataset dirs carry a burned-in SwingVision "
            "overlay and have not been scrubbed:\n"
            + "\n".join(f"    {t}" for t in missing)
            + "\nRun `py tools/scrub_swingvision.py --write`, or pass them to "
              "--exclude deliberately.")
    present = [t for t in stems if os.path.isdir(os.path.join(root, t))]
    print(f"[swingvision-guard] {len(present)} overlay clip(s) present, all scrubbed")


class BallWindows(Dataset):
    def __init__(self, root, split="train", val_frac=0.2, augment=True,
                 exclude=(), use_hard_negs=True, hard_weight=1.0, conf_radius=12):
        # (clip_dir, frame_idx, x, y, confusers); x is None => negative.
        # `confusers` are LOCATIONS of confirmed false fires on a frame whose ball
        # position we already know (mine_localised_negatives.py). They are not new
        # labels: the BCE target is ALREADY zero there. What they buy is WEIGHT —
        # the racquet head is otherwise one pixel among 147,400, scored the same as
        # empty sky. hard_weight=1.0 makes the whole mechanism an exact no-op.
        self.samples = []
        self.augment = augment and split == "train"
        self.hard_weight = float(hard_weight)
        self.conf_radius = int(conf_radius)
        # SwingVision overlays, painted at load. See tools/scrub_swingvision.py:
        # five training clips carry another system's rendered output, including a
        # watermark that is a literal yellow tennis ball, and 83 pseudo-labels
        # landed inside one. Keyed by directory so _frame can paint per clip.
        self.sv_masks: dict[str, list] = {}
        for tag in sorted(os.listdir(root)):
            if tag in exclude:
                continue
            d = os.path.join(root, tag)
            lp = os.path.join(d, "labels.json")
            if not os.path.isfile(lp):
                continue
            with open(lp, "r", encoding="utf-8") as f:
                meta = json.load(f)
            sv_drop: set[int] = set()
            svp = os.path.join(d, "swingvision_mask.json")
            if os.path.isfile(svp):
                with open(svp, "r", encoding="utf-8") as f:
                    sv = json.load(f)
                self.sv_masks[d] = sv.get("boxes") or []
                sv_drop = {int(i) for i in (sv.get("drop_labels") or [])}
            # A positive that sits inside a painted box is a label on flat grey.
            # Dropping beats keeping: these are the pseudo-labeller having locked
            # onto SwingVision's watermark ball.
            items = sorted((int(k), v) for k, v in meta["labels"].items()
                           if int(k) not in sv_drop)
            labeled = {int(k) for k in meta["labels"]}   # frames that HAVE a ball
            # Confuser LOCATIONS for these frames, if mined. Keyed by frame index.
            conf = {}
            cp = os.path.join(d, "localised_negatives.json")
            if self.hard_weight > 1.0 and os.path.isfile(cp):
                with open(cp, "r", encoding="utf-8") as f:
                    conf = {int(k): v for k, v in
                            (json.load(f).get("localised_negatives") or {}).items()}
            n_val = max(1, int(len(items) * val_frac))
            keep = items[:-n_val] if split == "train" else items[-n_val:]
            for idx, (x, y) in keep:
                self.samples.append((d, idx, float(x), float(y), conf.get(idx)))
            negs = sorted(meta.get("negatives", []))
            if negs:
                n_val = max(1, int(len(negs) * val_frac))
                nkeep = negs[:-n_val] if split == "train" else negs[-n_val:]
                self.samples += [(d, idx, None, None, None) for idx in nkeep]
            # Hard negatives (mine_hard_negatives.py): frames where BallNet
            # STATIC-fired on a fixture (HUD/post/fence/crowd) — its documented
            # false-fire weakness. Guard: never use a frame that HAS a labeled
            # ball as an all-zero-target negative, even if the fixture fire was
            # elsewhere in it (that frame does contain a ball).
            hp = os.path.join(d, "hard_negatives.json")
            if use_hard_negs and os.path.isfile(hp):
                with open(hp, "r", encoding="utf-8") as f:
                    hard = sorted(set(json.load(f).get("hard_negatives", []))
                                  - labeled - set(negs))
                if hard:
                    n_val = max(1, int(len(hard) * val_frac))
                    hkeep = hard[:-n_val] if split == "train" else hard[-n_val:]
                    self.samples += [(d, idx, None, None, None) for idx in hkeep]

    def counts(self):
        n_neg = sum(1 for s in self.samples if s[2] is None)
        return len(self.samples) - n_neg, n_neg

    def n_confuser_samples(self):
        """How many samples actually carry a weighted confuser disc.

        Goes in the checkpoint provenance: `--hard-weight 8` with zero confuser
        samples is arithmetically the shipped recipe, and without this number a
        no-op run is indistinguishable from a treatment run by its filename.
        """
        return sum(1 for s in self.samples if s[4])

    def __len__(self):
        return len(self.samples)

    def _frame(self, d, i):
        img = cv2.imread(os.path.join(d, f"{i:05d}.jpg"))
        if img is None:   # missing predecessor: repeat the nearest available
            img = cv2.imread(os.path.join(d, f"{max(i, 0):05d}.jpg"))
        boxes = self.sv_masks.get(d)
        if img is not None and boxes:
            # Paint out SwingVision's rendered output. Done at LOAD rather than
            # baked into the JPEGs so the scrub is re-applied on every run and
            # stays visible to anyone reading the code — a one-off rewrite of
            # 11k frames is invisible six months later. Same fill as
            # tools/mask_hud.py so a frame painted for training matches a frame
            # painted for the far-court label queue.
            for b in boxes:
                x0, y0 = max(0, int(b["x"])), max(0, int(b["y"]))
                x1, y1 = x0 + int(b["w"]), y0 + int(b["h"])
                img[y0:y1, x0:x1] = (60, 60, 60)
        return img

    def __getitem__(self, k):
        d, i, x, y, confusers = self.samples[k]
        confusers = list(confusers or ())
        frames = [self._frame(d, i), self._frame(d, i - 1), self._frame(d, i - 2)]
        negative = x is None
        occluded = False

        if self.augment:
            if random.random() < 0.5:     # horizontal flip
                frames = [cv2.flip(f, 1) for f in frames]
                confusers = [[IN_W - 1 - cx, cy] for cx, cy in confusers]
                if not negative:
                    x = IN_W - 1 - x
            if random.random() < 0.5:     # brightness / contrast jitter
                a = 1.0 + random.uniform(-0.25, 0.25)
                b = random.uniform(-20, 20)
                frames = [cv2.convertScaleAbs(f, alpha=a, beta=b) for f in frames]
            if random.random() < 0.5:     # small translation
                tx, ty = random.randint(-24, 24), random.randint(-16, 16)
                M = np.float32([[1, 0, tx], [0, 1, ty]])
                frames = [cv2.warpAffine(f, M, (IN_W, IN_H)) for f in frames]
                # The confusers must ride the SAME transform as the label, or the
                # extra weight lands on background and teaches nothing.
                confusers = [[cx + tx, cy + ty] for cx, cy in confusers]
                if not negative:
                    x, y = x + tx, y + ty
                    x = min(max(x, 0), IN_W - 1)
                    y = min(max(y, 0), IN_H - 1)
            if random.random() < 0.35:    # MOTION BLUR — fast ball / camera (BlurBall)
                ker = _motion_blur_kernel(random.choice([5, 7, 9, 11]),
                                          random.uniform(0, 180))
                frames = [cv2.filter2D(f, -1, ker) for f in frames]
            if not negative and random.random() < 0.30:
                # OCCLUSION (TOTNet): hide the ball in the NEWEST frame only, keeping
                # the target at its true spot. The prior two frames still show it, so
                # the model must learn to carry the ball through a brief occlusion
                # (a player/racket/net crossing) instead of dropping it.
                r = random.randint(8, 26)
                xi, yi = int(round(x)), int(round(y))
                col = tuple(int(v) for v in np.random.randint(0, 256, 3))
                cv2.rectangle(frames[0], (xi - r, yi - r), (xi + r, yi + r), col, -1)
                occluded = True

        arr = np.concatenate(frames, axis=2).astype(np.float32) / 255.0
        inp = np.ascontiguousarray(np.rollaxis(arr, 2, 0))
        if negative:
            hm = np.zeros((1, IN_H, IN_W), dtype=np.float32)
            x = y = -1.0   # sentinel: evaluate() separates negatives on x < 0
        else:
            hm = gaussian_heatmap(x, y)[None]
        # dtype pinned: augmentation clamps can make x/y ints, and a batch that
        # mixes Long and Float xy tensors fails to collate (torch.stack).
        w = NEG_WEIGHT if negative else (OCC_WEIGHT if occluded else 1.0)
        # Per-pixel weight: 1.0 everywhere, raised in a disc at each confuser.
        # All-ones when hard_weight == 1.0, which the loss treats as an exact no-op.
        wmap = np.ones((1, IN_H, IN_W), dtype=np.float32)
        if confusers and self.hard_weight > 1.0:
            disc = np.zeros((IN_H, IN_W), dtype=np.float32)
            for cx, cy in confusers:
                cxi, cyi = int(round(cx)), int(round(cy))
                if 0 <= cxi < IN_W and 0 <= cyi < IN_H:
                    cv2.circle(disc, (cxi, cyi), self.conf_radius, 1.0, -1)
            wmap = (1.0 + (self.hard_weight - 1.0) * disc)[None]
        return (torch.from_numpy(inp), torch.from_numpy(hm),
                torch.tensor([x, y], dtype=torch.float32),
                torch.tensor(w, dtype=torch.float32),
                torch.from_numpy(wmap))


def evaluate(model, loader, device, fire_thresh=0.5):
    """Positives: localization (median px error, hit@10). Negatives (xy < 0
    sentinel): false-fire rate — fraction whose peak clears fire_thresh, the
    OurBallDetector default score_thresh."""
    model.eval()
    errs, fires = [], []
    with torch.no_grad():
        for inp, _, xy, _, _ in loader:
            out = torch.sigmoid(model(inp.to(device)))[:, 0]
            B, H, W = out.shape
            flat = out.reshape(B, -1)
            peak = flat.max(dim=1).values.cpu()
            idx = flat.argmax(dim=1).cpu()
            px = (idx % W).float()
            py = (idx // W).float()
            neg = xy[:, 0] < 0
            errs += torch.hypot(px - xy[:, 0], py - xy[:, 1])[~neg].tolist()
            fires += (peak[neg] >= fire_thresh).tolist()
    errs = np.array(errs)
    med = float(np.median(errs)) if len(errs) else float("nan")
    hit10 = float((errs <= 10).mean()) if len(errs) else 0.0
    ff = float(np.mean(fires)) if fires else 0.0
    return med, hit10, ff


def hms(seconds: float) -> str:
    """Compact wall-clock, because 'how long will this take' had no answer.

    Nothing in this project recorded training time — the ballnet_v21 log has no
    timestamps at all — so an epoch count was the only handle on a run's cost.
    """
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m" if h else (f"{m}m{s:02d}s" if m else f"{s}s")


def _git_commit() -> str:
    """Best-effort commit hash for the checkpoint stamp; never fatal to a train run."""
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=os.path.dirname(os.path.abspath(__file__)),
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return "unknown"


def recipe_stamp(args, n_par: int, counts, n_confusers: int) -> dict:
    """How this checkpoint was made, saved inside it.

    ballnet_v21.pt carries nothing but its weights, so its recipe cannot be
    verified and any A/B against it confounds the change under test with whatever
    drifted since — Session I had to train its own baseline arm for exactly that
    reason. `confuser_samples` is here because `--hard-weight 8` with zero of them
    is arithmetically the shipped recipe, and a filename cannot tell you which
    happened.
    """
    tp, tn, vp, vn = counts
    return {"tool": "train_ballnet.py", "args": vars(args), "git": _git_commit(),
            "torch": torch.__version__, "params_m": round(n_par / 1e6, 2),
            "train_pos": tp, "train_neg": tn, "val_pos": vp, "val_neg": vn,
            "confuser_samples": n_confusers,
            "selection": "best (val hit@10 - false-fire), so NOT the last epoch"}


def emit(**fields) -> None:
    """One machine-readable line per epoch, for tools/lab_server.py.

    Prefixed so it is trivially separable from the human log and harmless if
    nothing is reading it: the Lab charts these, a terminal user ignores them.
    """
    print("LABJSON:" + json.dumps(fields), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/ball_dataset")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--out", default="weights/ballnet.pt")
    ap.add_argument("--hard-weight", type=float, default=1.0, dest="hard_weight",
                    help="per-pixel loss weight inside a mined confuser disc "
                         "(mine_localised_negatives.py). 1.0 = OFF and exactly the "
                         "shipped recipe. This is RE-WEIGHTING, not new labels: the "
                         "BCE target is already zero there, but the racquet head is "
                         "one pixel among 147,400 and scored like empty sky")
    ap.add_argument("--conf-radius", type=int, default=12, dest="conf_radius",
                    help="radius of that disc, in 512x288 px")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--exclude", nargs="*", default=[],
                    help="extra dataset dirs to skip. Gold clips are excluded "
                         "automatically from data/gold/*.manifest.json; a name here "
                         "that matches no dir is an error, not a no-op")
    ap.add_argument("--motion-attention", action="store_true", dest="motion_attention",
                    help="TrackNetV4-style learnable motion attention (frame-diff gate) "
                         "in BallNet — for the v4 model")
    ap.add_argument("--seed", type=int, default=0,
                    help="PAIRS AN A/B. Until this existed, two arms differed by "
                         "initialisation, shuffle order and augmentation draws as well "
                         "as by the flag under test, so a small effect could not be "
                         "attributed to the flag. Vary it deliberately to measure the "
                         "seed noise floor — that is the yardstick any effect must clear")
    args = ap.parse_args()

    # Not bit-determinism: cuDNN picks conv algorithms nondeterministically and
    # forcing otherwise costs real time. This pairs the things that dominate a short
    # run — the init and the order the data arrives in.
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    assert_no_gold_leak(args.data, args.exclude)
    assert_no_swingvision_leak(args.data, args.exclude)
    # Confuser weighting applies to TRAINING only. Weighting the validation loss
    # would change what "best checkpoint" means mid-experiment, and the whole point
    # is to compare against the shipped recipe on an unchanged yardstick.
    train_ds = BallWindows(args.data, "train", exclude=args.exclude,
                           hard_weight=args.hard_weight,
                           conf_radius=args.conf_radius)
    val_ds = BallWindows(args.data, "val", augment=False, exclude=args.exclude)
    tp, tn = train_ds.counts()
    vp, vn = val_ds.counts()
    print(f"train {tp}+{tn}neg / val {vp}+{vn}neg | device {args.device} | "
          f"excluded {args.exclude}")
    train_ld = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=2,
                          generator=torch.Generator().manual_seed(args.seed),
                          pin_memory=(args.device == "cuda"))
    val_ld = DataLoader(val_ds, batch_size=args.batch, num_workers=2)

    model = BallNet(motion_attention=args.motion_attention).to(args.device)
    n_par = sum(p.numel() for p in model.parameters())
    print(f"BallNet params: {n_par/1e6:.2f}M"
          f"{' (+motion-attention)' if args.motion_attention else ''}")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    # reduction='none' so we can weight each sample by its visibility (OCC_WEIGHT for
    # synthetic-occlusion frames) before averaging — the TOTNet fix that turns
    # occlusion augmentation from a regression into a gain.
    crit = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(100.0, device=args.device),
                                reduction="none")

    prov = recipe_stamp(args, n_par, (tp, tn, vp, vn),
                        train_ds.n_confuser_samples())

    best = -1.0
    t_start = time.time()
    emit(kind="start", epochs=args.epochs, out=args.out, device=args.device,
         train_pos=tp, train_neg=tn, val_pos=vp, val_neg=vn,
         params_m=round(n_par / 1e6, 2), excluded=args.exclude)
    for ep in range(1, args.epochs + 1):
        t_ep = time.time()
        model.train()
        tot = 0.0
        for inp, hm, _, w, wmap in train_ld:
            inp, hm, w = inp.to(args.device), hm.to(args.device), w.to(args.device)
            wmap = wmap.to(args.device)
            opt.zero_grad()
            per_px = crit(model(inp), hm)            # [B,1,H,W]
            # WEIGHTED mean over pixels. With wmap all ones this is sum/count, i.e.
            # exactly .mean() — so hard_weight=1.0 reproduces the shipped recipe
            # arithmetically and the learning rate needs no retune.
            per_sample = ((per_px * wmap).sum(dim=(1, 2, 3))
                          / wmap.sum(dim=(1, 2, 3)))  # [B]
            loss = (per_sample * w).mean()
            loss.backward()
            opt.step()
            tot += loss.item()
        sched.step()
        med, hit10, ff = evaluate(model, val_ld, args.device)
        # selection: find the ball AND shut up when there is none — a model
        # can't win the checkpoint race by firing everywhere
        score = hit10 - ff
        marker = ""
        if score > best:
            best = score
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            torch.save({"model_state_dict": model.state_dict(),
                        "provenance": dict(prov, epoch=ep, of_epochs=args.epochs,
                                           val_median_px=None if med != med else round(med, 2),
                                           val_hit10_pct=round(hit10 * 100, 2),
                                           val_false_fire_pct=round(ff * 100, 2))},
                       args.out)
            marker = "  <- saved"
        ep_s = time.time() - t_ep
        eta = ep_s * (args.epochs - ep)
        loss = tot / max(len(train_ld), 1)
        print(f"epoch {ep:3d}  loss {loss:.4f}  "
              f"val median {med:.1f}px  within10px {hit10*100:.1f}%  "
              f"false-fire {ff*100:.1f}%{marker}"
              f"   [{hms(ep_s)}/epoch, eta {hms(eta)}]", flush=True)
        emit(kind="epoch", epoch=ep, epochs=args.epochs, loss=round(loss, 5),
             median_px=None if med != med else round(med, 2),
             hit10=round(hit10 * 100, 2), false_fire=round(ff * 100, 2),
             score=round(score * 100, 2), saved=bool(marker),
             epoch_s=round(ep_s, 1), elapsed_s=round(time.time() - t_start, 1),
             eta_s=round(eta, 1))
    total = time.time() - t_start
    print(f"best (hit@10 - false-fire): {best*100:.1f}%  -> {args.out}"
          f"   (total {hms(total)})")
    emit(kind="final", best=round(best * 100, 2), out=args.out,
         total_s=round(total, 1))


if __name__ == "__main__":
    main()
