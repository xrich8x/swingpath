# int8 ball-graph parity — QA verification

**Verdict: the headline STANDS as written.** "3 of 6 clips fail the shipped graph's
parity bar (am_hard_utr, yt_rally2, gold_shell); pooled 5/528 both-fire frames" is
recomputed CONFIRMED, exactly, straight from the six committed JSONs' full `diffs_px`
lists (not the truncated `worst_frames`). The two mitigation rejections (Arm B
byte-identical, Arm C real-but-still-failing) are also CONFIRMED from the artifacts.
The one place the lead's narrative overreaches is the "close race" mechanism story
(check 3): the 0.15px-margin threshold was picked to fit the 5 known failures, and the
"all 5 failures are close races" framing does not survive tightening that threshold to
0.05 (drops to 2 of 5) — so treat "close races explain the int8 failures" as a
plausible, evidence-consistent story, not an independently-verified mechanism. The one
part of it that IS threshold-independent — zero close races on the two cleanly-passing
clips — does hold up.

## 1. Recompute pooled numbers from the six committed summary JSONs

**CONFIRMED.** Recomputed directly from `diffs_px` (the full per-frame list, not
`worst_frames`) in all six `data/output/ball_detector_int8_parity_summary__<clip>.json`:

| clip | total | null_agree | both_nonnull | n(diffs_px) | fail(diffs_px, >10px) | fail(worst_frames top-10) | median px | max px | bars.no_frame_gt_10px_pass |
|---|---|---|---|---|---|---|---|---|---|
| am_hard_utr | 178 | 170 | 53 | 53 | 1 | 1 | 0.1632 | 70.8311 | False |
| yt_rally2 | 178 | 176 | 149 | 149 | 3 | 3 | 0.1441 | 75.3931 | False |
| yt_match40 | 178 | 170 | 93 | 93 | 0 | 0 | 0.0000 | 1.3620 | True |
| gold_clay | 178 | 175 | 77 | 77 | 0 | 0 | 0.0000 | 0.9595 | True |
| gold_am | 178 | 173 | 67 | 67 | 0 | 0 | 0.1374 | 0.6879 | True |
| gold_shell | 178 | 177 | 89 | 89 | 1 | 1 | 0.0000 | 185.0655 | False |

Pooled: **5 failing / 528 both-fire = 0.95%** — matches the claim exactly.
Clips failing condition 3: **am_hard_utr, yt_rally2, gold_shell = 3/6** — matches the
claim exactly (the failing clips named match too, not just the count).

`len(diffs_px) == both_nonnull` held for every clip (asserted programmatically), so
the denominator is not in question. `worst_frames` (top-10 truncation) and the full
`diffs_px` list **agree exactly** on both the count and identity of >10px frames for
every clip — because no clip has more than 3 failing frames, all of them fit inside
the top-10 truncation window, so truncation happens not to hide anything here. This
is a fact about these six files, not a general property of `worst_frames` — a clip
with >10 failures would need the full list, and the table above shows I used the full
list (`diffs_px`), not the truncated one, for the reported count.

## 2. Summaries actually about the clips they name

**CONFIRMED.** For each of the six summaries: the `clip` field matches the filename
suffix, the `video` field points to a real, existing file under `data/incoming/`, and
no two summaries share a `video` path (checked programmatically, zero duplicates).

| clip | clip field matches filename | video path | exists |
|---|---|---|---|
| am_hard_utr | yes | `data/incoming/Hardcourt/am_hard_utr.mp4` | yes |
| yt_rally2 | yes | `data/incoming/Shell/yt_rally2.mp4` | yes |
| yt_match40 | yes | `data/incoming/Hardcourt/yt_match40.mp4` | yes |
| gold_clay | yes | `data/incoming/Clay/gold_clay.mp4` | yes |
| gold_am | yes | `data/incoming/Hardcourt/gold_am.mp4` | yes |
| gold_shell | yes | `data/incoming/Shell/gold_shell.mp4` | yes |

Surface split from the video paths: Hardcourt 3 (am_hard_utr, yt_match40, gold_am),
Shell 2 (yt_rally2, gold_shell), Clay 1 (gold_clay) — matches the pre-registration's
stated "Hardcourt 3 / Shell 2 / Clay 1" exactly, a second independent cross-check that
these six files are the six clips the lane says they are. No sign of the earlier
mislabelling recurring (the failure mode where `BALL_PARITY_DIR`-only runs overwrote
one clip's numbers into another's file) — every file's internal fields are
self-consistent with its own name.

## 3. "Close race" claim (margin_census.py)

**CONFIRMED at the pre-registered threshold, with a real caveat on robustness.**

Ran the lead's actual `<scratchpad>/margin_census.py` unmodified (found at the literal
path the brief named). At `CLOSE=0.15` it reproduces the claim exactly:

```
clip            both-fire   close races   % close   guard-fail
am_hard_utr     53          4                7.5%   0
yt_rally2       149         9                6.0%   0
yt_match40      93          0                0.0%   0
gold_clay       77          0                0.0%   0
gold_am         67          1                1.5%   0
gold_shell      89          2                2.2%   0
POOLED close races: 16/528 both-fire frames = 3.0%   (guard failures: 0)
```
Close-race tags: `am_hard_utr` {0119,0146,**0147**,0149}; `yt_rally2`
{0024,0025,0034,**0108**,**0109**,**0110**,0118,0140,0141}; `gold_shell`
{**0097**,0176}. All 5 known-failing frames (`am_hard_utr` 0147, `yt_rally2`
0108/0109/0110, `gold_shell` 0097) are inside the close-race set — matches the claim.
`yt_match40` and `gold_clay` (the two clean-passing clips): **0 close races each** —
matches the claim. Guard (top-blob centroid must equal the real `_decode()` answer in
`js_results.json`, tol 0.01px) never fired across 528 frames.

**Is the guard real or a rubber stamp?** It is a real guard in the sense that it has
room to fail — a wrong threshold, wrong connectivity, or a different scoring formula in
the replica would show up as a mismatch against the actual JS decode output, and it
does not fail once across 528 frames on 6 diverse clips/surfaces. It does not rule out
a bug shared identically by both the replica and the real decoder (no independent third
implementation), which is a real but narrower gap than "rubber stamp."

**Was 0.15 chosen before or after seeing the failures — checked directly, and yes,
after.** The script's own comment states it plainly: *"Chosen from the 5 observed
failures (widest fp32 margin among them 7.4%) with headroom."* I recomputed the exact
margins for all 5 known failures directly from the heatmap blobs (score = area × peak,
same as the script):

| clip | tag | winner score | runner-up score | margin (1 − ratio) |
|---|---|---|---|---|
| am_hard_utr | 0147 | 3300 | 3146 | 4.67% |
| yt_rally2 | 0108 | 3146 | 2904 | **7.69%** |
| yt_rally2 | 0109 | 2860 | 2662 | 6.92% |
| yt_rally2 | 0110 | 2640 | 2640 | 0.00% (exact tie) |
| gold_shell | 0097 | 2860 | 2662 | 6.92% |

Widest observed margin is 7.69%, not exactly the "7.4%" the code comment cites (small,
unexplained ~0.3-point discrepancy — not chased further, does not change the
conclusion). **This confirms the threshold is NOT independent of the result it is used
to explain** — it was picked with headroom over the exact failures it is now cited as
predicting, which is circular for the "16/528" and "all-5-are-close-races" framing. The
brief's skepticism is warranted: that reduces "close races explain the failures" from an
independent finding to a description that was built to fit.

**What DOES survive independently — the threshold-sweep, run separately (0.05, 0.10,
0.20, 0.30 added to the pre-registered 0.15):**

| CLOSE | pooled close/both | am_hard_utr | yt_rally2 | gold_am | gold_shell | yt_match40 | gold_clay |
|---|---|---|---|---|---|---|---|
| 0.05 | 7/528 (1.3%) | 2/53 | 3/149 | 1/67 | 1/89 | 0/93 | 0/77 |
| 0.10 | 16/528 (3.0%) | 4/53 | 9/149 | 1/67 | 2/89 | 0/93 | 0/77 |
| 0.15 (pre-reg) | 16/528 (3.0%) | 4/53 | 9/149 | 1/67 | 2/89 | 0/93 | 0/77 |
| 0.20 | 17/528 (3.2%) | 4/53 | 10/149 | 1/67 | 2/89 | 0/93 | 0/77 |
| 0.30 | 20/528 (3.8%) | 4/53 | 13/149 | 1/67 | 2/89 | 0/93 | 0/77 |

Two things this settles:
- **The "0 close races on yt_match40 and gold_clay" result is robust** — it holds
  unchanged at every threshold tested, 0.05 through 0.30, not just at the one picked
  post-hoc. This part of the claim does not depend on the specific 0.15 value.
- **The "all 5 failures are close races" claim is NOT robust to threshold choice** — at
  `CLOSE=0.05` (margin ≤5%), only **2 of 5** known failures remain classified as close
  races (`am_hard_utr` 0147 and the exact-tie `yt_rally2` 0110); `yt_rally2` 0108, 0109
  and `gold_shell` 0097 (margins 6.9-7.7%) fall outside. It only becomes "5 of 5" once
  the threshold is opened past ~8% — i.e. past the widest margin actually observed in
  the failures, which is exactly circular by construction, not surprising.

**Net verdict on check 3: CONFIRMED the numbers as computed, CORRECTED the framing.**
The pooled "16/528 = 3.0%" and "5/5 failures are close races" figures are real outputs
of a real script, but they are not independent evidence for the mechanism — the
threshold was tuned to make the failures fit inside "close race," so of course they do.
The one number in this whole exercise that IS independent of the tuning is "0 close
races in the 2 passing clips," and it holds at every threshold tried.

## 4. Two rejected mitigations (Arm B / Arm C) confirmed from artifacts

**CONFIRMED.**

**Arm B (`per_channel=True`) byte-identical to shipped — confirmed three independent ways:**
- My own `sha256sum` right now: `tracknet_ball.int8.onnx` and
  `tracknet_ball.int8.perchannel.onnx` both hash to
  `601bba24a8cb81af329cd598bfabd94f1bf1722cc7845cd700913c0fce896035`, both 10,918,923
  bytes.
- `tracknet_ball.int8.perchannel.onnx.provenance.json`'s own stamped `output.sha256`
  (written at export time, 2026-09-03T04:21:49Z) already equals its stamped
  `control_arm_int8.sha256` — the file said this about itself before I re-checked it.
- Op-type histogram identical between the two graphs (18 `ConvInteger`, 18
  `DynamicQuantizeLinear`, etc. — every count matches). `mobile/export_int8_perchannel.py`
  explicitly refuses to write to the shipped path (`if OUT == SHIPPED_INT8: sys.exit(1)`),
  so this is not a case of one script silently overwriting the other into agreement.
- Direct blob evidence for the frame the mechanism was named on: in
  `<scratchpad>/ball_parity/blobs_pc8.json`, frame `0147`'s `int8_control` and `pc8`
  (Arm B) top-blob decode are the **exact same float pair**
  `(313.0769230769231, 191.53846153846155)` — not merely close, identical to full
  float precision, which is what byte-identical graphs should produce.

**Arm C (`nodes_to_exclude=[final Conv]`) is a real, different graph, and still fails:**
- Op histogram: 17 `ConvInteger` + 1 `Conv` (fp32) + 17 `DynamicQuantizeLinear`, vs the
  shipped graph's 18/0/18. Matches the claim exactly.
- Size: 11,361,976 bytes = 11.36 MB (decimal), vs shipped 10,918,923 = 10.92 MB. Matches.
- `tracknet_ball.int8.lastconv_fp32.onnx.provenance.json` records `control_arm_int8.sha256`
  = the same shipped hash above with `"note": "NOT modified by this script"` — the export
  script itself asserts it left the control alone, consistent with git showing the shipped
  file untouched (see below).
- Direct blob evidence for frame `0147` in `<scratchpad>/ball_parity/blobs_lc8.json`: the
  true blob's **area goes 15 (fp32) -> 2 (int8 control) -> 3 (Arm C)** against a target of
  15 — this is the exact "15 -> 2 -> 3" figure the journal cites, found in a primary
  artifact, not re-derived from prose. Arm C's decode for 0147 is
  `(313.25, 191.58333333333334)`, still locked onto the false (wrong) blob, just a
  slightly different point on it than the control's `(313.0769230769231,
  191.53846153846155)` — consistent with "0147 got 0.16 px WORSE" (both wrong, barely
  different from each other). I did not locate primary blob dumps for 0108/0109/0110 in
  the time budget for this check (see COULD-NOT-CHECK below); 0147's dump is a direct,
  literal match to the cited mechanism, which is the strongest single piece of evidence
  offered for Arm C's rejection.

**Shipped `tracknet_ball.int8.onnx` was NOT modified:**
- `git status --porcelain -- mobile/models/` and `git diff --stat` show nothing tracked
  to diff — **`mobile/models/*.onnx` is gitignored** (`.gitignore` lines 40-42), so git
  cannot attest to this file directly; this is a gap in what git alone can confirm, not a
  finding of tampering.
- Substitute evidence that is sufficient here: filesystem mtime shows
  `tracknet_ball.int8.onnx` dated **Jun 25 21:00**, while both new export scripts' outputs
  are dated **Sep 3** (12:21 and 12:42) — the shipped file predates today's export work by
  months and was not touched by it. Both export scripts also assert in their own
  provenance JSON that the control file was untouched, and both scripts contain an
  explicit guard against writing to the shipped path (read directly in
  `mobile/export_int8_perchannel.py`, lines 70-72: refuses if `OUT == SHIPPED_INT8`).

**COULD-NOT-CHECK (small gap):** I did not find or run a primary check of the claimed
"3 of 4 screen frames still fail" count for Arm C across all four frames (`am_hard_utr`
0147, `yt_rally2` 0108/0109/0110) — only 0147 has a located blob dump. The 0147 evidence
found is a strong, literal match to the cited numbers, so I have no reason to doubt the
other three, but I have not independently verified them from a primary artifact.

## NOT ESTABLISHED THIS RUN

- **Arm C's screen-frame result for 3 of the 4 named frames.** Located a primary blob
  dump (`blobs_lc8.json`) confirming frame `am_hard_utr` 0147's exact "area 15→2→3"
  figure, but did not locate or reconstruct equivalent primary dumps for `yt_rally2`
  0108/0109/0110 in the time available. Not contradicted by anything found — just not
  independently re-derived for those three frames.
- **The exact 0.29-point gap between my recomputed widest margin (7.69%) and the
  script comment's cited "7.4%"** — small, noted, not chased down (could be a rounding
  convention difference, e.g. runner-up/winner vs 1-runner/winner computed at a
  different stage).
- A minor filesystem oddity while starting this check (my own copy-paste error in
  transcribing a long Windows path, initially made it look like the scratchpad
  directories didn't exist) cost several tool calls before I found my own transcription
  error — noted in the journal so it isn't re-chased if this resumes, but it did not
  affect any reported number, all of which came from the corrected, verified paths.
