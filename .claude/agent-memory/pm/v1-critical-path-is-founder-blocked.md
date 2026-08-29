---
name: v1-critical-path-is-founder-blocked
description: The whole v1 mobile critical path (Core ML export, pose affordability on A13) is blocked on founder actions, so every queueable item is off the critical path — sequence the human asks first
metadata:
  type: project
---

Established 2026-08-29 while re-sequencing the queue from scratch.

**The fact.** Nothing on the v1 critical path is runnable by the team. The two gates that
decide whether an iPhone can run this pipeline at all are both waiting on the founder:

- **P0-0, Core ML export** — needs a Mac. `coremltools`' Windows wheel is pure Python and
  the native `BlobWriter` that serialises an `mlprogram`'s weights is absent, so the
  *export* fails, not merely the on-device measurement. No phone has run any part of this
  pipeline. Procurement, not minutes.
- **P0-2, pose affordability on an A13** — pose **binds runtime** (~1000 ms/frame ANE
  arithmetic; see [[mobile-parity-first]]). Its `yt_match40` column was WITHDRAWN because
  that clip's four clicked corners sit on asphalt and hedge, so the pipeline scored the
  NEAR player as far. Blocked on **one human re-click of four corners** (rule 9 bars us
  editing it).

**Why:** court and ball work look busy but neither decides whether v1 ships; the runtime
question does, and it cannot be answered on this machine.

**How to apply:** rank the founder's minutes as a scarce resource with a leverage
ordering, and lead any status report with it rather than burying it under the queue.
Highest leverage in the project is ~5 minutes re-clicking `yt_match40` — it unblocks the
top runtime risk. Build the rendered-corner audit sheets BEFORE asking, so the founder
only looks and never hunts. Batch every human ask into one update
([[human-asks-are-a-scarce-batched-resource]]) and dispatch the human-latency item first
so his clock runs while machine work continues.

**Corollary for the cut line:** if every queueable item is off the critical path, none of
them is urgent — which is exactly when a big speculative build (joint line-to-model court
correspondence, 4-8 sessions, can fail) looks deceptively attractive. Court auto-detection
is not required for v1 parity at all; manual 4-corner tap supplies the homography.
