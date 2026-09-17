---
name: live-path-has-no-refusal-surface
description: live.py emits a call or nothing — no confidence, no "too close", no false-lock suppression; refusal is the project's designed fallback and it is absent here
metadata:
  type: project
---

`backend/swingvision/live.py` and its JS mirror `mobile/live_calls.js` return either a
`LineCall` or `None`. `None` means "no bounce detected", never "I saw a bounce and I
can't call it." There is no confidence field and no refusal path.

Three concrete gaps, all product-visible:

1. **No too-close-to-call band.** The margin is computed (`_distance_inside`) but only
   displayed, never used to gate the verdict. A bounce 1 cm from the line renders with
   the same confidence as one 2 m inside.
2. **No false-lock suppression.** The offline path has `suppress_false_locks`; the live
   path has nothing. The dominant false-lock mode is measured — **59.2% of false locks
   travel with a person**, i.e. slow-moving detections near a player, which is *exactly*
   the local-speed-minimum signature the bounce detector looks for. Expect phantom calls
   at player positions.
3. **No serve boxes.** `analytics.is_in()` branches on `shot_type == "serve"` into
   `_in_service_region`. The live path never sees a shot type and calls
   `court.is_in_singles` for everything, so a **serve long is called IN** — the single
   most-disputed call in amateur tennis.

Also note the live path defaults to `line_margin_m = 0.05` (a 5 cm expansion, biasing
toward "in") while the offline path defaults to `margin = 0.0`. Live and offline
therefore disagree by construction on any ball within 5 cm outside a line. The instinct
is right — "in" plays on, so it is the cheaper error — but it is undocumented and
untested.

**Why this matters:** refusal is already this project's designed fallback for a court it
cannot read (established with the ~30-second manual court). Tennis makes refusal
*socially natural* on line calls too — "too close, play a let" is what humans do. The
band is a threshold on a number the code already computes, so this is the cheapest
trust-preserving feature available.

**How to apply:** no live IN/OUT verdict ships without the band, the serve-box branch,
and a measured phantom-call rate. Related: [[mobile-v1-scope-live-calls]],
[[line-call-numbers-assume-perfect-bounce]]
