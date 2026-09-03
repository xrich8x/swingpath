# qa memory

Inherited 2026-08-28. The gate definitions, known-hard areas and checker quirks are in
this agent's system prompt — read it first; it is the authoritative copy.

## Live results to check against

- **P0-2 pose downscale: FAILED its gate, 2026-08-27.** Far-player detection
  `yt_match40` 11.0% @1280 -> 0.1% @640 -> 0.0% @384; `am_hard_utr` 1.0% -> 0.0% -> 0.0%.
  Near player barely moves. Gate allowed 2 points absolute. Recorded as a measured
  negative; do not let it be re-proposed as untested.
- **P0-3 crop-around-contact: UNMEASURED, not negative.** A first attempt reporting 78.8%
  was invalidated on visual inspection — the 448 px box catches the near player
  regardless, and the contact population was wrong. Any retry needs a correct population.
- **Core ML export needs macOS.** `coremltools`' Windows wheel cannot serialize weights
  (`BlobWriter not loaded`). `.github/workflows/coreml-export.yml` runs it on a GitHub
  Actions macOS runner; untested end-to-end as of 2026-08-28.

- **Line-call margin curve measured, 2026-08-28** (pm queue item 5).
  [line_call_margin_curve.md](line_call_margin_curve.md) — real amateur mounts are at/
  below the majority floor under 10 cm from a line, clear it from ~20 cm; recommended
  band 0.20 m, refuses 39% of close (0.5 m) calls. Not built, measurement only.

- **Doorman (concurrency cap) + journal system verified, 2026-08-28.**
  [agent_cap_doorman_verified.md](agent_cap_doorman_verified.md) — cap/fail-open/
  parking/hand-back/no-double-fire/TTL-sweep/wiring/journals all measured PASS by
  feeding synthetic hook payloads directly to `agent_cap.py`. Three real gaps found
  (not fixed): a TOCTOU race at the PreToolUse check (no reservation side-effect,
  demonstrated), a `safe_name()` collision that undercounts live agents (demonstrated),
  and silent >8000-char prompt truncation in the Stop-event hand-back (queue storage
  itself is not truncated). Also: this session's declared cwd was a decoy/stale
  subfolder, not the real repo root — see that file for the path note.

- **Court-mask-sweep parked item verified DEAD, 2026-09-02.**
  [court-mask-sweep-item-is-already-shipped.md](court-mask-sweep-item-is-already-shipped.md)
  — the "12 vs 11" sweep result is the already-shipped surface router (f41a489,
  2026-08-21), re-banked not re-proposed; 3 independent runs agree 12/20, 0 wrong,
  median 8.1px range 1.7-13.9 vs human clicks. Evidence committed: docs/evidence/
  court-mask-sweep-item-is-already-shipped.md (333d38b).
- **Process trap: ending a turn to "wait" on a backgrounded Bash job does not keep you
  listening for its notification.** [background-wait-does-not-survive-ending-turn.md]
  (background_wait_does_not_survive_ending_turn.md) — poll in a foreground loop within
  one tool call instead; hit this on the court-mask-sweep task, coordinator had to
  intervene.

- **int8 ball-graph parity headline verified 2026-09-03, close-race mechanism corrected.**
  [int8_parity_verified_but_close_race_threshold_is_post_hoc.md](int8_parity_verified_but_close_race_threshold_is_post_hoc.md)
  — 5/528, 3/6 clips CONFIRMED exactly; Arm B/C mitigation rejections CONFIRMED from
  hashes+op counts+blob dumps; but the "close race" 0.15px threshold was picked after
  seeing the 5 failures — "all 5 are close races" is NOT threshold-robust (2/5 at 0.05),
  while "0 close races in the 2 clean clips" IS robust across 0.05-0.30.

## Standing

Never fix what you are checking. Never move a gate to fit a result. A borderline pass is
a pass — say borderline. `docs/TRAPS.md` (T01-T22) is the catalogue of process failures
that have fired here more than once.
[qa_does_not_write_to_codebase.md](qa_does_not_write_to_codebase.md) — a task brief
asking for an evidence file/STATE row does not override this; findings go in the report
text only. Also: a stray `claude-md-cap.sh` hook error on an unrelated Bash call is
likely cross-talk from another concurrent agent mid-edit of CLAUDE.md — retry once or
twice before treating it as a real block.
