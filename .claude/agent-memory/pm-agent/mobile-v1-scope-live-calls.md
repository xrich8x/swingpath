---
name: mobile-v1-scope-live-calls
description: SUPERSEDED 2026-08-27 — live-calls-first was rejected; mobile direction is parity-first (recreate the existing product, perception stack first)
metadata:
  type: project
---

**SUPERSEDED on 2026-08-27, the same day it was written.** Kept because the reversal is
the instructive part.

I recommended shipping live line calls as mobile v1, standalone, ahead of the offline
analyzer — reasoning that live calls were ~70% ported while the analyzer was a rebuild.
**The user rejected it.** Direction, verbatim: *"Dont focus on new features first,
recreate all existing in the mobile shell instead so need to reinvision the court / ball
/ player tracking first to see if it will work on mobile and if not to address all the
fixes before moving on to things like scoring or live calls."*

Three specific reversals: court auto-detection is **not** cut, player pose is **not**
cut, live calls are **not** v1.

**Where my reasoning was actually wrong** (as opposed to merely out of line with the
direction): I built the case on the smoother being **non-causal by construction** and
treated that as a mobile blocker. It is not. The product is **offline-first by design
with no real-time requirement** (`docs/STATE.md`) — a phone records the clip, then runs
the full batch pipeline on-device afterwards, with the Kalman/RTS smoother over the
complete track exactly as today. Non-causality only binds if the output must be
real-time, and it does not. **Do not re-use that argument, and do not propose buffered
replay as a workaround for a constraint that is not active.**

The live-path defects I found remain valid and carry forward to whenever live is built —
see [[live-path-has-no-refusal-surface]]. The perfect-bounce caveat is broader than live
and applies to the desktop product being ported — see
[[line-call-numbers-assume-perfect-bounce]].

Current direction: [[mobile-parity-first]].
