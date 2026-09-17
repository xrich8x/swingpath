---
name: capture-framing-is-a-scope-lever
description: What the camera is POINTED AT is a scope decision pm owns; relaxing "frame the whole court" is the only capture variant with a feasible band for 10 cm
metadata:
  type: project
---

**Rule: "frame the whole court" is a scope assumption, not a physical constraint — and it is
the assumption that makes the 10 cm bar impossible.** 2026-09-15.

**The two demands that collide (researcher's arithmetic, `monocular-3d-routes.md` §1):**
covering the far baseline at 10 cm needs `f·h >= 8,862 px·m`; framing the 10.97 m doubles
width from setback `S` caps `f <= 175·S`. At 1080p and a 3 m mount **no setback satisfies
both**. That is where "it is unreachable" comes from — and it silently assumes the full court
is in frame.

**Three variants, priced (pm arithmetic — re-derivable, not measured):**

- **Wide, full court, higher/further back.** 6 m mount + 12.6 m setback, or 4K + ~5.5 m.
  **Reject on product grounds.** All four of this project's confirmed mounts are 1.36-1.74 m
  and the "record one clip above 2.5 m" ask has been open for weeks. A spec an amateur cannot
  satisfy ships to nobody.
- **Telephoto, FAR HALF ONLY — the only variant with a feasible band.** Framing 10.97 m at
  29.77 m allows `hfov <= 20.9°`, `f <= 5209 px` at 1920. Need `f >= 2954` at h = 3 m: **a
  band exists** (hfov 21-36°). At bar A's 2 px noise the requirement doubles and the mount
  must rise to **h >= 3.4 m**. **Marginal, not impossible.** Costs: the near half of the court
  is out of frame (call one end at a time); fewer arc observations may worsen conditioning
  (unmeasured); and **the iPhone SE 2nd/3rd gen have no telephoto camera**, so an optical-tele
  spec narrows the supported device list below the stated A13 floor. The 4K-digital-crop
  alternative runs on any device but re-raises whether detector noise scales with resolution
  — a detector measurement, closed by rule 6, therefore undecidable.
- **Side mount — pre-killed, someone will propose it.** Camera 6 m outside the sideline level
  with the net: worst point 20.7 m not 29.8 m, but framing 23.77 m of length from 6 m needs
  `hfov ~126°`, so `f ~489 px` and `f·h = 1467` at 3 m → **29 cm/px vs the end mount's 36
  cm**. ~20% better, and it only **swaps** which lines are blind. Not a rescue.

**How to apply:** when a geometric requirement is declared impossible, check whether the
*framing* assumption inside it is a product choice before accepting the impossibility. And
always state the device-list consequence of a capture spec — it is three steps out and nobody
else will raise it.

Related: [[blind-axis-splits-the-accuracy-bar]], [[no-confirmed-metric-footage-exists]],
[[the-mount-crossover-splits-v1-outputs]].
