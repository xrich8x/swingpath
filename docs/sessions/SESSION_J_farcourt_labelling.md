# Session J — make far-court labelling actually usable

**Kickoff prompt:** `Do Session J (docs/sessions/SESSION_J_farcourt_labelling.md)`
**User brings:** nothing for steps 1-3. Step 4 needs ~30 minutes of their clicking.

## Why this exists

Far-court recall is the largest remaining ball problem and it is **detector-shaped**:
Session G part 3 measured the court gate costing *zero* far-court recall on all three
calibrated clips, so the geometry lever is spent, and on am_hard_utr the dominant
failure is the detector simply not firing (7,934 of 28,998 frames, 3.1x larger than
every gate rejection combined). SESSION_E §E3j predicted the last ~20% cannot be
taught by pseudo-labels because the teacher cannot see it either. Human far-court
labels are the lever that is left.

Session I built the queue and ran a pilot. **The pilot half-failed, for a reason
that is fixable, and it exposed two plumbing gaps.** Evidence:
[data/output/farcourt_label_yield.md](../../data/output/farcourt_label_yield.md).

Established, do not re-derive:

| | |
|---|---|
| Size of the hole | **4,087** far-court frames the tracker missed, **1,259** distinct bracketed gaps |
| Reachability | **89%** sit in gaps of <=10 frames, anchored both sides |
| Auto-filling them | **MEASURED NEGATIVE** — interpolation lands within 10 px only **63%** of the time, and is flat across bridge length (62/60/64% at 1-2/3-5/6-9 frames). No safe subset. Human labels are required, not assumed |
| Are the frames readable? | **Yes at source resolution.** 10 of 12 gap frames got a ball. The 512x288 network input is not readable (~1.6 px ball) — always extract from `data/train_clips/` |

## The three blockers

### 1. Burned-in graphics poison the labels

On the four pilot clips carrying a scoreboard, **every click landed on the
scoreboard's tennis-ball icon**, 112-645 px from the real ball. On the four clean
clips the human agreed with the tracker to **0.6-7.2 px**. So labelling HUD footage
today produces *negative* value — it teaches that a scoreboard graphic is a ball,
which is a confuser the detector already fires on.

**Fix.** Detect the burned-in region and mask it before the frame reaches the
labeller. A HUD is static across the whole clip, so a per-clip temporal median (or
a min/max-variance mask over a few hundred sampled frames) finds it without any new
labels — the same clean-plate idea already used in `court_setup_server.py`. Mask by
painting it flat, not by cropping: cropping changes the frame geometry and the
coordinates would stop matching the source.
Record the mask in the manifest so it is auditable.

**Gate:** on the four known-HUD clips the mask must cover the scoreboard on 100% of
sampled frames and must not touch the court. Verify by eye on a contact sheet —
this is a labelling input, so a wrong mask is worse than none.

### 2. The queue has no route into training data

`tools/labels_to_dataset.py` takes a single `--video` and treats label keys as
frame indices into it. The far-court queue is deliberately the opposite: renumbered
frames 0..N drawn from **12 different videos**, with the origin recorded per frame
(`src_dataset`, `src_frame`, `video`, `video_frame` in the manifest).

**Fix.** Either teach `labels_to_dataset` a multi-source mode driven by the
manifest, or have a converter split the queue's labels back into per-source-clip
label files and call the existing tool once per clip. **Prefer the second** — it
leaves the audited single-video path untouched and reuses its gold-leak refusal
per clip.

**Gate:** a round trip. Convert, then confirm every produced sample's pixels match
the frame the human actually saw (the same dHash/abs-diff check that verified the
window mapping in Session I). A silent off-by-one here poisons training invisibly.

### 3. The pilot's own labels must be quarantined

`data/labels/farcourt_pilot.labels.json` holds 36 human labels of which roughly a
third sit on scoreboard icons. Today only a paragraph in an evidence file stops a
future build consuming them.

**Fix.** A mechanical refusal, not a note. Simplest honest option: mark the queue in
its manifest as `"contaminated": "HUD clicks, see farcourt_label_yield.md"` and have
the converter refuse any manifest carrying that key without `--force`.
**Do not delete the labels** — they are human ground truth and they are the evidence
for blocker 1.

## Then, and only then

### 4. Re-run the pilot, masked

Same 12 gaps, HUD masked. **This is the go/no-go for the whole session.** If the
human still cannot find the ball on the clean clips, stop and record it — the fix
would be new footage, not more clicking.

### 5. Scale the queue

Target **300-400 gaps**, one frame per gap (every frame inside a gap is a
near-duplicate; the midpoint is the hardest and most informative). Round-robin
across clips is already implemented. **Open question for the user, ask before
spending their time:** spread evenly across all 12 clips, or weight toward the
amateur low-camera footage the product targets? Different answers give different
models.

### 6. Train and score

## Pre-registered gates — write these down before looking at any result

Primary, because far-court recall is the point:

- **pooled `far_px` over the 6 gold clips must rise by >= 3 pts** (baseline
  `ballnet_v21`: recall 69.4%, far_px 68.8%, far_geo 72.5%).

Guards, because the specific risk of far-court training is teaching the detector to
paint a plausible arc where the ball is invisible:

- pooled overall recall must not drop more than 2 pts;
- **solid ghosts must not rise** (pooled over the 3 calibrated clips; `ballnet_v21`
  scores **9**). Run `tools/gate_verdict.py`, which pools by summing numerators and
  denominators and prints the required-n beside the verdict.

**State the weakness of that last guard out loud when reporting.** It is a count of
~9 out of **74** no-ball frames, where sampling alone moves the count +/-3.4. It can
only detect a near-elimination; a real 30% worsening would be invisible. "Ghosts did
not rise" therefore means "nothing catastrophic happened", not "nothing happened".

## Guardrails

- **Train with `--seed`** (default 0) and keep it identical across arms. Session I's
  pair had no seed and its detector result — false fire 53.9 -> 42.2% on 6 of 6
  clips — is still **unattributable** because of it.
- Every checkpoint now carries `recipe_stamp`. Do not ship one that lacks it.
- `assert_no_gold_leak` and the one-way gold/train split still apply; the queue
  builder re-runs the check and refuses to write into `data/gold/`.
- **Never quote a `--frame-step 1` number as shipped behaviour** (two wrong
  conclusions have come from this).
- Never quietly edit human ground truth to suit a model.
- Do not re-propose whole-frame negative mining, pose proximity, racquet-box
  negation, or a tighter court/vertical gate — all measured negatives with numbers
  in SCOREBOARD.

## Files

| File | Change |
|---|---|
| `tools/mask_hud.py` | **new** — find and mask burned-in graphics per clip |
| `tools/select_farcourt_labels.py` | apply the mask when extracting; record it in the manifest |
| `tools/farcourt_labels_to_dataset.py` | **new** — split the queue's labels per source clip, call `labels_to_dataset` for each |
| `tools/labels_to_dataset.py` | refuse a manifest marked contaminated without `--force` |
| `backend/tests/` | mask coverage; round-trip pixel identity; the contamination refusal |
| `SCOREBOARD.md`, this file | record it |

## Out of scope

Ghost-ball work (nine failures; the survivors all have `run_len = 1` and are
kinematically indistinguishable from a real ball). Court detection. The 60 fps
product decision. Rally over-splitting.
