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

---

# Results (2026-08-10) — steps 1-3 done, and blocker 1 was mis-diagnosed

Full evidence: [farcourt_anchor_audit.md](../../data/output/farcourt_anchor_audit.md),
[farcourt_hud_mask.md](../../data/output/farcourt_hud_mask.md),
[farcourt_pilot_clicks.jpg](../../data/output/farcourt_pilot_clicks.jpg),
[hud_mask_verify.jpg](../../data/output/hud_mask_verify.jpg).

## The correction, first

**Blocker 1 as written is wrong, and it matters because it set the session's
priorities.** Re-adjudicating all 36 pilot clicks at 5x against the frames:

| claim in the brief | measured |
|---|---|
| "on the four pilot clips carrying a scoreboard, **every** click landed on the scoreboard's tennis-ball icon" | **5 of 36** clicks are inside a burned-in graphic, and they landed on score digits and panel body, not a ball icon |
| the four clips named as HUD-carrying | **two of them carry no overlay at all** (`yt_8-BkpjFFIhQ`, `yt_WjHZrIYteDA`) — and were 503-569 px and 112-406 px out anyway |

What 11 of 29 ball clicks actually landed on is empty sky, foliage, flat court or
a floodlight. **The dominant failure is that the two ANCHORS bracketing those
gaps were themselves false locks** — a wall speaker, a treetop, a parked car.
The queue selects a gap when the tracker is confident on both sides, and about
half the time that is two false positives.

| | gaps | midpoints on a real ball |
|---|---|---|
| >= 1 anchor confirmed by the human | 5 | **5 of 5** |
| neither confirmed | 7 | **0 of 7** |

Ruled out first: the queue does show the frame it claims — 0 of 36 mismatch.

## Step 1 — HUD masking. DONE, gate passed on the second attempt.

`tools/mask_hud.py`. **MEASURED NEGATIVE: no temporal statistic finds a graphic
on this footage** (std / median-agreement / correlation-with-exposure all fail in
both directions; numbers in the evidence file). With geometry added the rule is
safe but incomplete — it finds the SwingVision watermark on every clip that has
one and none of the six score panels. Twelve fixed clips, so the rest are
hand-authored (`"src": "manual"`, survive a re-detect) and two auto proposals
that lay on the court are recorded `"src": "rejected"`.

Gate: **19 boxes x 4 REAL frames**, not the median plate. First run FAILED on 3
boxes the plate had hidden — including `RZ_wyJ9rI3Q`'s yellow ball icon sitting
below its box, and two panels that widen when player names get longer. Second
run passes.

## Step 2 — route into training data. DONE.

`tools/farcourt_labels_to_dataset.py` splits the 12-video queue back into
per-clip label files and calls the audited single-video converter once each, so
its gold-leak refusal runs per clip. It also **enforces the anchor control**,
which is the evidence-driven addition: a midpoint is accepted only if the human
confirmed an anchor beside it. On the pilot that keeps 5 of 5 usable midpoints
and drops 7 of 7 unusable ones (n=12 gaps).

Two selection-time alternatives were tried first and both FAILED, which is why
the control is label-time: local roam does not separate confirmed from
unconfirmed anchors (14.0-220.2 vs 13.2-238.8 px), and `suppress_false_locks`
keeps only 1 of the 5 confirmed gaps.

**The round-trip gate needed a different instrument than the brief specified.**
dHash verified Session I's *window* mapping (±1600 frames, different scene); the
risk here is ±1 frame on a 60 fps static court, where every candidate reads 14
bits and JPEG plus the 1080p→512×288 resize contribute 6-8 of their own — the
test would have passed identically whether the mapping was right or wrong. Now
an argmin of mean-abs-diff over ±3 frames, reporting its margin so a frozen
scene declares itself unresolvable instead of quietly passing. A test corrupts a
built sample and requires the gate to catch it.

## Step 3 — quarantine. DONE.

`farcourt_pilot.manifest.json` carries `contaminated`; **both** converters refuse
it without `--force`. The labels are not deleted — they are the evidence for
everything above.

## Steps 4-6 — NOT run

`data/labels/farcourt_pilot2` is built and waiting in the Lab: **30 gaps, 90
frames**, ~5 minutes. It does two jobs at once, which pull against each other:

- **12 REPEATS** of the original pilot gaps (`--repeat-from`), so the mask is the
  only thing that changed and the comparison is controlled;
- **18 FRESH** gaps, because the repeats carry the labeller's memory of the first
  pass and cannot be used to estimate a rate.

Repeats are interleaved (queue positions 0, 3, 5, 8, ...), not stacked at the
front, so drift over the session cannot land on one group. Which is which is
recorded in the manifest and never shown in the UI.

**Pre-registered prediction:** masking fixes frames 0/1/2/7/8 and nothing else,
because the other 11 bad clicks are anchor failures, not HUD failures. If the
re-run shows that, the anchor control is validated on independent data.

**Step 5 needs a planning number the brief did not have.** The anchor control
discards every gap whose anchors were false locks — on the pilot **7 of 12
(confirmation rate 42%)**, i.e. ~2.4 queued gaps per usable label, so a 300-label
target needs ~700 gaps queued rather than 300. That estimate rests on n=12; the
18 fresh gaps in the re-run are there to give it a second, independent reading
before an hour of clicking is committed to it. Clip mix is decided: **even
round-robin**, the selector's existing behaviour.

## Step 4 — RUN. The mask works; the anchor control has a hole.

90 of 90 labelled. Full read-out in
[farcourt_anchor_audit.md](../../data/output/farcourt_anchor_audit.md) §6.

**The prediction was half right.** `yt_6jp23ghDY9Q` went from clicking inside the
scoreboard to clicking **1 px from the tracker's own anchor** once the panel was
painted out — the mask did exactly its job. `yt_8-BkpjFFIhQ`, which has no mask,
went from three clicks on empty cloud to three *unsure*: the labeller got more
careful unprompted. And on the five clips where a ball genuinely exists, the two
passes reproduce to **0-7 px**.

**What was not predicted, and matters more:** the confirmation rate on the same
twelve gaps went 42% -> 75%, and inspection says at least two of the four flips
are the human clicking a static wall mark or a window — on `yt_VZWi6Vf-sX0`, the
*same* wall mark the tracker locked onto, agreeing to 2-5 px. Across each gap the
human's clicks moved 1-8 px while the tracker's prior moved 60-583 px.

**The anchor control measures agreement with the tracker, not correctness.** A
labeller who cannot find the ball tends to click the most ball-like thing in the
frame, which is what the detector locked onto for the same reasons. This is
"never let a model grade its own homework" with a human substituted in.

The fix is a rule that has to arrive *before* the click, not a filter after it —
**a ball in play is somewhere different on every frame** — so it is now the lead
line on the labelling page and on the Lab's Label tab, along with per-tab
orientation for all five tabs. Deliberately NOT turned into a threshold: the
separation looks clean (1-8 px vs 17-116 px) but was found after looking at these
twelve gaps, so it is pre-registered for the next queue instead of fitted to this
one.

**Consequence for step 5:** the fresh-gap rate of 78% cannot size the next queue —
it inherits the same hole. The true rate is somewhere between it and pass 1's
42%. Sizing waits for one round labelled under the new rule.

## Out of scope

Ghost-ball work (nine failures; the survivors all have `run_len = 1` and are
kinematically indistinguishable from a real ball). Court detection. The 60 fps
product decision. Rally over-splitting.
