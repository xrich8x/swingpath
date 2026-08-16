> **SUPERSEDED / READ WITH CARE** — stamped 2026-08-15.
> The masking works, but the problem it was built for was mis-diagnosed - see farcourt_anchor_audit.md. The far-court label lever is closed (gap_findability.md).

# Masking burned-in graphics before a human labels the frame

Five of the far-court pilot's 36 clicks landed inside a burned-in scoreboard
(`farcourt_anchor_audit.md`). A label on a scoreboard teaches the detector that
a scoreboard is a ball, which is a confuser it already fires on, so those clicks
are worth less than nothing. `tools/mask_hud.py` paints the graphics flat before
the frame reaches the labeller; `select_farcourt_labels.py` applies the mask and
records the boxes in the queue manifest.

Artifacts: `data/hud_masks.json` (the boxes), `data/output/hud_masks.jpg`
(median plate before/after, per clip), `data/output/hud_mask_verify.jpg` (THE
GATE — every box cropped out of 4 real frames with the mask applied).

---

## 1. MEASURED NEGATIVE: no temporal statistic separates a graphic from static scenery here

The plan said "a HUD is static across the whole clip, so a per-clip temporal
median or a min/max-variance mask finds it without any new labels". On these 12
clips it does not, and it fails in both directions. Three statistics were tried,
80-100 frames sampled across each whole clip at a 960-px working resolution.

**(a) Per-pixel temporal std.** These are edited compilations with cuts and
auto-exposure, so almost nothing is stable:

| | clips |
|---|---|
| fraction of frame with std < 6/255 is **0.00** | `rz4T0-VALNw`, `tC0z7FYvMks`, `WjHZrIYteDA` — two of which carry an obvious scoreboard |
| fraction with std < 6/255 is **> 45%** | `am_dbl_classb` (46%), `RZ_wyJ9rI3Q` (57%), `VZWi6Vf-sX0` (56%) — locked-off cameras over an empty court, so a variance mask paints the COURT |

**(b) Agreement with the temporal median** (share of sampled frames within 3
grey levels of it). Better — it survives the score digits changing and it
survives a cut — but the same split remains: `RZ_wyJ9rI3Q` and `VZWi6Vf-sX0`
still have 50% and 33% of the frame at agreement >= 0.90, and `6jp23ghDY9Q`,
`8-BkpjFFIhQ` and `WjHZrIYteDA` have **0.0%** at that bar.

**(c) Correlation with the frame's global brightness.** The principled version:
a composited graphic is drawn after the camera, so it should not track
auto-exposure the way real scene pixels do. It flags **26-65% of the frame** on
7 of 12 clips — the temporal signal at any pixel a player walks through is
dominated by the player, not by exposure. Not usable.

## 2. What the automatic rule is, and what it actually finds

Rigidity (b) plus three geometric constraints, all four required:

1. **small and flush to a frame border** — an overlay is composited against an
   edge; the court is neither;
2. **rigid against a NON-rigid surround** (agreement inside minus agreement in a
   ring outside). This is the constraint that keeps the court out: empty court
   and sky are rigid, but so is everything around them;
3. **synthetic structure** — edge density in the median plate. Flat court and
   flat sky have almost none.

2 and 3 are both needed: 2 alone accepts the far treeline (rigid, structured,
edge-adjacent) and 3 alone accepts a strip of court under a busy sideline.

**MEASURED result: it finds the "Shots Tracked by SWINGVISION" watermark on
every clip that carries one, and NONE of the six score panels.** The watermark
is the most valuable target — its logo is literally a yellow tennis ball — but
the panels are unreachable: they sit over sky or over dark stands, which are as
rigid as the panel, so constraint 2 rejects them by construction. On 3 clips the
panel is not a candidate at any setting, because whole-clip agreement inside it
never reaches 0.60 (the player names and scores change mid-clip).

An earlier, looser cut of the same rule painted **37% of `ewqSn18xdsY`** and
18.5% of `nQan0M5JDM8`, court included — the failure mode is not theoretical.

## 3. So the rest is hand-authored, and that is the honest answer

The training pool is a fixed set of twelve clips. The remaining boxes are read
off the median plates, carry `"src": "manual"`, survive a re-run of the
detector, and are verified on the same sheet. Two auto proposals that lay on the
court are recorded as `"src": "rejected"` so a re-run cannot resurrect them.

| clip | boxes | painted | what |
|---|---|---|---|
| `6jp23ghDY9Q` | 1 | 6.1% | score panel |
| `8-BkpjFFIhQ` | 0 | 0% | no overlay |
| `am_dbl_classb` | 0 | 0% | no overlay |
| `col_hard_zheng` | 1 (2 rejected) | 5.6% | score panel |
| `ewqSn18xdsY` | 1 (1 rejected) | 4.5% | swingvision watermark + ball |
| `nQan0M5JDM8` | 1 | 5.6% | score panel |
| `rz4T0-VALNw` | 1 | 6.8% | score panel |
| `RZ_wyJ9rI3Q` | 4 | 16.0% | panel, radar, speed readout, watermark + ball |
| `tC0z7FYvMks` | 3 | 13.0% | subscribe banner, radar + readout, watermark + ball |
| `TilAFMPc0yg` | 4 | 19.0% | panel, radar, speed readout, watermark + ball |
| `VZWi6Vf-sX0` | 3 | 11.9% | radar, speed readout, watermark + ball |
| `WjHZrIYteDA` | 0 | 0% | no overlay |

`col_hard_zheng`'s "NewYCPhoto" watermark is deliberately NOT masked: it is
plain white text lying over the court, so covering it would paint court for no
confuser benefit. Masking is not free where the graphic sits on the playing
surface, and that trade is made per box, not per clip.

## 4. The gate

*The mask must cover the graphic on 100% of sampled frames and must not touch
the court.* Checked on **19 boxes x 4 real frames** (not the median plate — a
panel that widens mid-clip averages away in the plate and is still there on the
frame the labeller gets). `--verify-sheet` crops each box with a 45 px margin so
a leak shows as a bright fragment beside flat grey.

**First run FAILED on 3 boxes**, all of which the plate had hidden:

- `RZ_wyJ9rI3Q`'s SwingVision watermark — the **yellow ball icon** sat below the
  box on all 4 frames;
- `nQan0M5JDM8` and `TilAFMPc0yg` score panels — both widen when the player
  names get longer, leaking score digits past the right edge.

Boxes widened; **second run passes on all 19 x 4**. `data/output/hud_mask_verify.jpg`
is the artifact — a graphic visible outside a red rectangle is a failure.

On "must not touch the court": the score panels sit over sky, ceiling, stands or
trees on every clip that has one, so they cost nothing. The bottom-right
watermarks and the right-edge radar do overlap court, unavoidably — that is
where the graphic is, and a ball behind it is unlabelable in the source video
too. `select_farcourt_labels` therefore also **drops any gap whose prior falls
inside a mask box**, so a human is never asked to find a ball under a grey
rectangle.
