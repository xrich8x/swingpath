---
name: parity-before-features
description: User rule — recreate the existing product on mobile before proposing anything new; establish perception viability first, fix what is broken, only then layer features
metadata:
  type: feedback
---

**Recreate the existing product on mobile before proposing new features. Establish
whether the perception stack (court, ball, player) can run on-device at all, fix
whatever is broken there, and only then move to things like scoring or live calls.**

**Why:** given 2026-08-27, after I proposed shipping live line calls as mobile v1 because
they were the most-ported component. The user's reasoning is that "most ported" is not
"most valuable" — a phone app that does something *different* from the desktop tool means
one person maintaining two divergent products. The desktop analyzer is the product; the
phone is a deployment target for it, not a place to start a new product line.

**How to apply:** when scoping mobile, the default question is "what does the existing
pipeline need in order to run here," not "what is cheapest to ship here." Do not let port
readiness drive product sequencing. If I want to argue a subset should land first, argue
it **on the merits of the parity path** — e.g. that a subsystem's *output* can be
delivered by its existing designed fallback — not by substituting a different product.

Corollary the user was explicit about: a direction is not a decision I may not question.
Judgement is still the job; the constraint is on the *form* of the argument, not on
whether I may disagree.

Related: [[mobile-parity-first]], [[mobile-v1-scope-live-calls]]
