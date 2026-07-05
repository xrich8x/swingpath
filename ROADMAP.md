# Product Roadmap — Model Fixes → Feature Impact

Owner: engineering (Claude) · Stakeholder: Richmond · Updated 2026-07-05
Constraint: **self-reliant ML only** — no third-party answer keys; training data is
generated (synthetic), harvested (user calibrations), or hand-labeled by us.

## Feature scorecard (today)

| Product feature | State today | Blocked by |
|---|---|---|
| Court overlay + auto-setup | Works on learned angles (user's court, broadcast); new angles need one corner-drag | WS2 |
| Ball trail in video | ~87% coverage; vanishes on fastest shots; regression mystery on fresh runs | WS1 |
| Line calls (IN/OUT) | Working, honest uncertainty flags; far court often "uncertain" | WS1 |
| Shot speed | NOT credible — serves read ~70% hot (flat-ground assumption) | WS3 |
| Shot type (FH/BH/serve/volley/overhead) | Good when pose visible; far player usually missing | WS4 |
| Spin (topspin/slice) | Guess-level heuristic, unvalidated | WS3+WS4 |
| Rallies, double-bounce, scoring | Rules correct; quality = upstream track quality | WS1 |
| Movement stats | Near player only | WS4 |
| Serve analytics, heatmaps, highlights, winners/errors, history, mobile | Not built (designs exist) | WS5 |

## WS1 — Ball perception (P0)

| # | Fix | What it is | Product impact when done | Effort |
|---|---|---|---|---|
| 1.1 | Diagnose fresh-run tracking regression | Same detector tracks worse today than the archived run; find the variable (GPU numerics / background sampling) | None visible — but NOTHING can be measured until fixed; prerequisite to all of WS1 | S |
| 1.2 | BallNet v2: wrong-answer flashcards | Retrain our detector with neighbor-court balls + logos marked as explicit negatives | Ball trail stops teleporting to the next court; our model becomes usable standalone | M |
| 1.3 | Synthetic blurred balls | Paste physics-correct motion-blurred ball streaks onto real court frames = unlimited perfect labels | Coverage on FAST shots (the vanishing-ball complaint) | M |
| 1.4 | Gold-label tool + 30 min of clicks | Tiny UI: user clicks the real ball on ~200 sampled frames | First HONEST benchmark (today's numbers grade against our own guesses) | S |

Target: ≥95% honest coverage on user footage; ball never leaves the court visually.

## WS2 — Court perception (P0/P1)

| # | Fix | What it is | Product impact | Effort |
|---|---|---|---|---|
| 2.1 | White-paint self-check | Before trusting an auto-found court, verify proposed lines actually lie on white pixels; refuse otherwise | No more confidently-wrong courts; product degrades to "drag corners please" instead of garbage output | S |
| 2.2 | CourtNet v4: synthetic angles | Warp existing calibrated frames into thousands of artificial camera angles; retrain | Auto-setup works on many new angles out of the box | M |
| 2.3 | Productize the learning loop | Every user corner-drag auto-joins the dataset; scheduled retrain + eval gate | The "it keeps learning" promise becomes automatic instead of manual | M |

Target: new angle → either correct auto-setup or an explicit setup request; never silent garbage.

## WS3 — Physics & measurement (P0 start, P1 finish)

| # | Fix | What it is | Product impact | Effort |
|---|---|---|---|---|
| 3.1 | Ball height from gravity | Fit parabolas to flight; solve height from one camera (gravity is a known constant) | THE speed fix — serves stop reading 70% hot; from first principles, no external answer key | L |
| 3.2 | Re-tune thresholds for self-calibrated lens | Gates were tuned when we guessed the lens; re-tune on measured values | Consistency; removes silent behavior drift | S |
| 3.3 | Physics fitter robust at 720p | Relax/re-architect the precision arc fit for noisy footage | Spin RPM + bounce-anchored speeds on ordinary clips | M |

Target: speed within ~10% of true on a clip with known ground truth we film ourselves (radar app / high-fps phone).

## WS4 — Players & shot understanding (P1/P2)

| # | Fix | What it is | Product impact | Effort |
|---|---|---|---|---|
| 4.1 | Far-player recovery | Run pose on an enlarged crop of the far half; track through sparse detections | Far player gets stats, movement, and shot detection — doubles the stat sheet | M |
| 4.2 | Spin v2 | 120/240fps slow-mo capture guidance + validate wrist-path against physics spin (3.3) | Topspin/slice labels become trustworthy | M |
| 4.3 | Handedness toggle | Manual per-player setting backstopping auto-inference | Correct FH/BH on short clips | XS |

## WS5 — Product features (unlocked after WS1–3)

| # | Feature | Needs | Effort |
|---|---|---|---|
| 5.1 | Serve analytics (1st/2nd %, placement) | WS1 + existing bounces | S |
| 5.2 | Player-position heatmaps | positions already computed; export + render | S |
| 5.3 | Auto-highlights / rally reel | rally times already exist; automated cutting | S |
| 5.4 | Winners / unforced errors | solid calls (WS1) + rules | M |
| 5.5 | Match history + trends | small database; biggest plumbing item | L |
| 5.6 | Mobile app shell | ML already exported; standard app-dev work | L |

## Release plan

**R1 — "Trust what you see"** (P0): 1.1 → 1.2 → 2.1, start 3.1
Demo: user's clip with continuous ball trail; a new clip either auto-calibrates correctly or asks for corners.
**R2 — "Believe the numbers"** (P1): finish 3.1, 1.3, 1.4, 3.2, 4.1
Demo: serve speed passes the sniff test; far player appears in stats.
**R3 — "Full stat sheet"** (P2): 5.1–5.4, 4.2, 3.3, 2.2/2.3
**R4 — "A real product"**: 5.5, 5.6.

## Inputs only the stakeholder can provide
1. One clean 1080p+ clip, steady elevated mount (unlocks 3.1 validation + far player)
2. ~30 minutes clicking balls in the label tool when built (1.4)
3. Corner-drag once per new camera angle (feeds 2.3)
4. Optional: one 120/240fps slow-mo rally (4.2)

Effort key: XS <1h · S = half session · M = 1–2 sessions · L = multi-session.
