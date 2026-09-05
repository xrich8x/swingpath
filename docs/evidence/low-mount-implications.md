# The net-occlusion crossover: what it does to v1, the gold set, and the founder queue

> **DELIVERABLE:** the product consequences of the 2026-09-05 finding that below a
> **2.0–2.2 m** mount the net tape overlaps the far baseline in the image
> ([setup-envelope-net-occludes-far-baseline.md](setup-envelope-net-occludes-far-baseline.md),
> STATE *What has not worked*). Written by pm, 2026-09-05. **Nothing here re-derives the
> geometry**; every number is cited from the row that owns it.
>
> Five points: (1) what it does to v1 and the honest fallback · (2) what it does to the
> gold set — court vs ball vs speed · (3) the refusal surface · (4) the founder queue,
> re-ranked · (5) good news or bad news. Then one recommendation and the one thing that
> would change it.
>
> **Rule 3 check, done before writing:** nothing proposed here appears in STATE's *What
> has not worked*. In particular I propose **no new autonomous calibration gate** — net
> posts, fitted hfov, gravity/arc and every ground-plane statistic are all in that table
> already, and §3's design deliberately ships a **binary** rather than the corroboration
> ladder those rows killed.

---

## 0. The one-paragraph version

This is **good news**, and §5 argues it without hedging. It converts an unbounded problem
— verify an arbitrary calibration after the fact, which has now failed five times — into a
bounded one the user solves in ten seconds before recording. The cost is real: v1 acquires
a hard mount requirement, and the honest fallback for a user who cannot meet it is a
**reduced-output mode**, not a refusal to run. The gold set survives better than it looks
— every **pixel-domain** ball number is untouched, and this project has already *measured*
that the ball chain is homography-free. What is genuinely exposed is that **this project
owns no confirmed metric footage**: the four named mounts are 1.36–1.74 m, all below the
crossover. The single highest-leverage action on the board is now **15 minutes of founder
time recording one clip above 2.5 m at his own court** — because if he cannot, no user can,
and v1's setup story is broken in a way that no amount of engineering fixes.

---

## 1. What this does to v1

### 1.1 The call

**Guided framing becomes a hard requirement, stated as a live check rather than as a
number, with a warn-not-block posture at capture and a block on metric outputs.** v1 keeps
everything it had; it gains one setup gate and one degraded mode.

**Do not ship "mount at 2.5 m."** A user cannot measure 2.5 m and will estimate it wrong,
and the comfortable-clearance threshold is not one number anyway — it is **2.19–2.98 m**
depending on standoff, lens and resolution. Ship the question the geometry actually asks:
**"is the far baseline visibly clear of the net tape?"** That is self-verifying, needs no
homography, needs no model, and it answers for the user's *actual* position rather than an
average one. The live criterion backend-dev is building right now is exactly this artefact,
and it is the load-bearing half of the setup screen I already queued for frontend-dev.

### 1.2 What the user actually does

1. Opens the app at the court, holds the phone up behind the baseline.
2. Live preview shows a framing state. Amber: **"Raise the camera — the net is hiding the
   far baseline."** Green: **"Framing good."** It updates as he moves, so raising the phone
   is a physical search with immediate feedback, not a spec to comply with.
3. Green → clamp or prop it there, tap four corners, record, analyse. Full outputs.
4. Cannot get to green → §1.4.

### 1.3 Does the clamp instruction shrink the market? Yes, and here is by how much

**Honestly: a fence clamp at 2.5 m is not a free instruction.** Three separate frictions,
and I am naming them rather than assuming compliance:

- **It needs a fence.** Most public hard courts and most club courts have one. Some do not,
  and indoor courts frequently have a wall or curtain instead.
- **It needs an accessory.** A clamp is a ~$20–30 purchase the user must make *before first
  value*. Any product that requires a purchase before the first result loses most of its
  funnel, and that is a bigger effect than the fence availability.
- **It needs reach.** 2.5 m is above head height. Mounting and retrieving it twice per
  session is friction the user feels every time, not once.

**But the requirement is a camera height above the COURT PLANE, not above the ground the
user is standing on** — and that opens fallbacks that cost nothing:

- Standard photo tripod (1.5–1.8 m) **on a courtside bench** (~0.45 m) = 1.95–2.25 m —
  at or just over the crossover. On a picnic table (~0.75 m) it clears comfortably.
- Spectator seating, a clubhouse balcony, a raised path behind the court, a stack of two
  benches. Any of these clears without buying anything.
- A standing tripod on flat ground (~1.5 m) **does not clear it, ever**, and no amount of
  careful clicking fixes that. That is the case the app has to handle honestly.

So the addressable set is not "people with a fence and a clamp" — it is "people who can
find 2.5 m of elevation at their court," which is a much larger group but still not
everyone. **I am not going to pretend I know the fraction.** §4 turns that into a
15-minute founder experiment rather than a guess.

### 1.4 The honest fallback, which matters more than the happy path

**When the user cannot get to green, the app records anyway, analyses anyway, and withholds
exactly the outputs that need a metric court.** It does not refuse, and it does not lie.

| Output | Below the crossover | Why |
|---|---|---|
| Shot list, shot count, shot types | **Ships** | Pixel-domain and pose-domain. No homography in the loop. |
| Per-rally clips, dead-time trim, highlights reel | **Ships** | A rally boundary is a **time**, not a place. Mount height is irrelevant to it. |
| Ball trail / visual overlay | **Ships** | Drawn in image space. |
| **Ball speed in km/h** | **Withheld** | Speed is pixel track → world via homography. A court compressed onto its near half scales every speed by an unknown factor. |
| **Bounce map in court coordinates** | **Withheld** | Same homography, and its whole value is *where on the court*. |
| **Player distance run / court coverage** | **Withheld** | Same. |
| **Line calls** | **Never shown** | Already parked (founder ruling 2026-08-29), and independently below the majority-class floor at these heights. |

**What the user sees is not an error, it is a shorter results screen** with one persistent
line: *"Speeds and the bounce map need a higher camera. Here is how."* That is a product
that still works at 1.5 m — it is a shot-and-rally product rather than a measurement
product — and it converts every low-mount user into a user with a reason to raise the
camera next time, rather than a user with a wrong number.

**The consequence three steps out, stated because nobody will catch it otherwise:** this
makes speed and the bounce map **conditional features**, which means the results UI can no
longer assume they exist. Every screen that renders them needs an absent state designed
from the start, and retrofitting that at session 40 costs several times what designing it
now costs. That is a real bill this finding sends to frontend-dev, and it is why the
setup-screen brief and the results-screen brief now have to share a decision.

---

## 2. What it does to the gold set and the numbers derived from it

**Precision matters here, and both over- and under-claiming are wrong. The clean split is
COORDINATE SYSTEM, not clip.**

### 2.1 Untouched: everything measured in pixels against human clicks

**No ball number in this project is at risk.** hit@10, per-frame recall, solid- and
faded-ghost counts, the BallNet-v21-vs-TrackNet-vs-WASB comparison, the int8-vs-fp32 parity
in pixels, the court precision gate's own 20 px bar — all of these are distances **in the
image** between a model output and a human click. A homography never enters.

This is not my inference; the project **measured** it. From the BallNet-vs-TrackNet chain
row: *the court gate removes 0 locks on 7 calibrated clips × 2 arms, and `--no-gate` is
byte-identical — so T23's broken `yt_match40` calibration cannot have touched it.* That was
run to answer a different question and it answers this one exactly: **the ball chain does
not consume the calibration.** A wrong court cannot move a ball number, therefore an
unconfirmable court cannot make one suspect.

### 2.2 At risk: everything expressed in metres, km/h or court coordinates

Speed, bounce location, distance run, near/far player identity, any court-relative gate.
These are the outputs T23 already burned us on: `yt_match40`'s bad homography made the
pipeline **call the near player far** and cost two published figures (`11.0% @1280`,
`8.8 m mount`). That is the failure mode, and it is an inversion, not a degradation.

**But the finding does not say these clips are miscalibrated.** It says something weaker
and different: *a still frame cannot confirm they are calibrated correctly.* The evidence
file states this explicitly and I am not going to inflate it. Per clip:

| Clip | Mount | Court status | What its numbers are worth |
|---|---|---|---|
| `yt_match40` | 1.64 m | **Re-clicked and confirmed 2026-09-05.** The wrong version survives as a `.bak` and the pair is the only settled truth in the corpus. | Metric numbers usable again; the two withdrawn figures are re-derivable. |
| `am_hard_utr` | 1.74 m | **Unconfirmable from a still frame** — but corroborated by two independent off-plane checks: net-tape camera height agrees to **−3.7%**, and the net-anchor render is internally consistent to **0.4 px** with the ground line an exact match. | Metric numbers stand, with the *pre-existing* limit unchanged: measurable to only **7.5 m of 23.77 m**, so far-court figures there were always recall, never measurement. |
| `demo30` | 1.38 m | **Unconfirmable and un-cross-checkable.** Its 47.9 px net span is below the tape instrument's own resolution, so no independent check can be run on it at all. | Its speeds were already never citable (CLAUDE.md). Extend that: **no world-coordinate number from `demo30` is citable**, not just speed. |
| `flexi_joy_p01` | 1.36 m | Unconfirmable. | Same posture as `demo30` unless an off-plane check is run on it. |

**The net change to the published record is one line**, and it is a downgrade of `demo30`
from "speeds not citable" to "no metric output citable." Everything else was already
carrying its caveat. The recommended STATE wording is in §6.

### 2.3 Is this the close-call table re-expressed? No — it is a second, independent cost on the same axis

The founder flagged this correctly as the thing to get right. The two are **different
failures that happen to share a remedy**:

- **The close-call curve (54.0% at 1.0 m, ~69% at 3 m, ~81% at 8 m, vs a 56.2%
  majority-class floor)** is a *precision* ceiling. It assumes the homography is **correct**
  and asks how finely a bounce can be resolved at that height. It is about resolution.
- **The net-occlusion crossover** is an *identifiability* limit. It asks whether a correct
  homography can be established or confirmed **at all** from the image. It is about truth.

They compound rather than duplicate: at 1.4 m you cannot confirm the court, **and** even if
it happened to be right the close calls would be worse than answering "in" every time. So
this is **not a known cost re-expressed — it is a new cost**, and it lands on outputs the
close-call curve never touched (speed, bounce map), because line calling is already parked.

**The good part of that answer:** the remedy is the same remedy. Both say *get the camera
higher*. The product therefore asks the user for **one** thing, not two, and the live check
is the single instrument that serves both. That is why §5 is a good-news verdict despite
this section adding a cost.

---

## 3. The refusal surface

I named the refusal surface last run as **the largest un-owned area in v1**. This adds the
biggest single item in it. Here is the whole design, and it is deliberately small: **one
bit of state, three places it appears, two different postures.**

### 3.1 The one bit

Every recording carries a single boolean: **framing verified** — was the far baseline
visibly clear of the net tape at capture? Nothing more. **I am not proposing a three-state
ladder or a corroboration path**, and that is a deliberate rejection: net posts, fitted
hfov, gravity/arc and every ground-plane statistic are already in STATE's *What has not
worked*, four of them measured out on 2026-09-05 alone. v1 does not ship a fifth
autonomous gate wearing a new hat. One bit, set before a homography exists, which is
precisely why it is the one check that can work.

### 3.2 Where it appears, what it says, and whether it blocks

| # | Where | Posture | What it says |
|---|---|---|---|
| 1 | **Live, in the camera preview, during setup** — the primary surface | **WARN. Never block.** | Amber: *"Raise the camera — the net is hiding the far baseline. Speeds and the bounce map need a clear view of it."* Green: *"Framing good."* Updates continuously as the user moves. |
| 2 | **At calibration, after the four taps, before analysis** | **BLOCK the metric outputs, not the analysis.** | *"We can't confirm the far corners from this camera height — at this height the net tape sits on top of the far baseline. We'll analyse your shots and rallies. Speeds and the bounce map need a higher camera."* Offers a loupe re-tap with the net drawn at both heights, so a user who *did* click the net can see it. |
| 3 | **On the results screen, attached to the numbers, permanently** | **Persistent badge, not a toast.** | Speeds and bounce map either absent, or present with *"estimated — camera too low to verify the court."* |

**Why capture never blocks, and this is the load-bearing decision:** a recording you refuse
to make is a match lost forever. The user is courtside, the match is starting, and an app
that says "no" at that moment is uninstalled. A recording made at a bad height still yields
a shot list, rally clips and a highlights reel — a real product — so there is never a
reason to refuse the capture itself.

**Why the metric outputs do block rather than warn:** this project's entire accuracy-floor
discipline exists because a confidently wrong number destroys trust in everything around
it. `yt_match40` is the standing proof: a homography that passed a 0.9 px residual audit
while all four corners sat on asphalt and a hedge, which **inverted** the near/far player
and cost two published figures. A warned-but-shown speed is a screenshot in a group chat
with no warning attached to it. Withheld is honest; caveated is not, at the moment the
number leaves the app.

### 3.3 Surface #3 is the one that will get skipped, so name it now

The badge must be a **property of the stored match record**, not of the session that
produced it. A user opens a match three weeks later, or shares it. If "framing verified"
lives in view state rather than in the record, the caveat evaporates on the second view —
which is the exact mechanism by which this project has already had **three** published
figures survive their own withdrawal in stale copies. That is a `schema.py` question, and
it is the one place this section touches the data contract.

---

## 4. The founder queue, re-ranked

This changes the queue substantially — it **deletes** one ask, **shrinks** another,
**adds a new one at the top**, and leaves the A13 purchase where it was.

| # | Ask | Time | Change | Why |
|---|---|---|---|---|
| **0** | **Record ONE clip from above 2.5 m at the court you actually play on.** Phone on whatever elevation you can find — fence clamp, tripod on a bench, balcony. Two minutes of rally. Note what you had to do to get up there. | **~15 min** | **NEW, and it goes to the top** | This is the falsifier for v1's entire setup story, and it is 15 minutes. **This project's four named mounts are 1.36–1.74 m — it owns no confirmed metric footage at all.** If the founder cannot get a phone above 2.2 m at his own court with gear he owns, no user will, and the answer in §1 changes from "require the framing" to "cut metric outputs from v1." Nothing else on the board can flip a v1 feature set for a quarter of an hour. Secondary benefit: it is also the first compliant clip for every future metric measurement. |
| **1** | **Buy one used A13-or-newer iPhone.** | ~15 min + money | **Unchanged at the top tier**, with a stronger case | Nothing here touches throughput, int8-vs-fp32 or thermals, so its rank is untouched. But it gains a **fourth** consumer: the live framing check in §3 runs in a **camera preview loop**, and whether that is affordable at preview frame rate on an A13 is unmeasured like everything else. |
| **2** | **Look at ONE corner sheet: `sAjkpeRq4P4`.** | **~2 min**, down from ~10 | **Shrunk from "review the two unsettled sheets" to one** | `sAjkpeRq4P4` is at **3.33 m — above the crossover**, so the information *is* in the image and a human eye can settle it. And qa measured it as **the worse of the two** (tape offset ~29–31 px *and* ground offset ~22–25 px, same direction) despite the automated bar reading it clean. Answerable and probably wrong: the best two minutes on the list. |
| **—** | ~~Settle `am_hard_utr`'s corner sheet~~ | — | **DELETED** | At **1.74 m it is below the crossover: un-confirmable from a still frame, in principle.** Asking the founder to look at it is asking him to do something the geometry says cannot be done. It is not "unsettled pending a human" — it is **closed as unconfirmable**, corroborated instead by two independent off-plane checks (net-tape height −3.7%, net-anchor internally consistent to 0.4 px). This finding resolves half of the old item #2 by making it unanswerable, which is a genuine resolution. |
| **—** | ~~Re-click `yt_match40`~~ | — | **DONE — verify before re-asking** | STATE now describes "the CORRECT `yt_match40`" against a known-wrong `.bak`, and refers to it as *just re-clicked and confirmed*. My last run had this as founder item #1. It is off the list. |
| **3** | **Re-label the 8 mislabelled court gold frames** in the Lab (rule 9). | ~1 min | Unchanged | Bundle with #2 — same sitting, same tool. |
| **4** | **~3–6 h point-boundary labelling.** | 3–6 h | **Unchanged, and explicitly NOT affected** | Worth stating so nobody wastes a session re-screening the corpus for mount height: **a point boundary is a time, not a place.** It needs no homography, so the crossover is irrelevant to it. Low-mount clips are perfectly good labelling material for this. |
| **5** | **Click points along the four outer court lines** — the falsifier for the court closure. | ~30–60 min | Unchanged, still last | Its best case still changes no v1 decision. Ranking a cheap item last is the point of ranking by leverage. |

**One new decision for DECISIONS_PENDING, not an ask:** does v1 ship the reduced-output
mode in §1.4 and block metric outputs below the crossover? That is a product call — mine to
recommend, the founder's to approve — and it is appended there rather than asked here.

**Sequencing note for the lead:** #0 is the only item whose answer can delete work, so it
goes out first and alone. #2 and #3 are one two-minute sitting. #1 has a purchase lead time,
so it goes in the same batched update and its clock starts while machine work continues.

## 5. Good news or bad news — good, and it is not close

**Good news. Clearly, and I am not hedging it.** Four reasons, in order of weight:

1. **It replaces an unbounded problem with a bounded one.** Five autonomous gates have
   failed to tell a correct court from a wrong one. That was not five tuning failures; it
   was one impossible task attempted five ways — *verify an arbitrary calibration after the
   fact*. The replacement is a question asked **before** a homography exists, in a preview
   loop, with two lines and no model. A project with five open bugs just became a project
   with one settled constraint, and the gate that replaces them is by far the easiest thing
   in the family to build.

2. **It makes the accuracy story honest and, for the first time, achievable.** Until today,
   "is this court right?" had no answer for a whole class of footage and nobody knew which
   class. Now the answer is a stated boundary, and the app can *tell the user which side of
   it they are on*. That is the difference between a product that is sometimes wrong for
   reasons nobody can name and a product that knows when it does not know.

3. **The cost is small and it mostly is not new.** Only metric outputs are affected — speed
   and the bounce map. Every pixel-domain ball number is untouched and this project has
   already measured that (§2.1). Line calls, the other metric casualty, are already parked.
   And the remedy the constraint asks for is the same remedy the close-call curve has been
   asking for on a different axis, so the user is asked for one thing, not two.

4. **The bill arrives at the right time.** The results screen has to be designed with an
   absent-speed state. Learning that now, before frontend-dev builds it, is worth several
   sessions; learning it at session 40 is a retrofit.

**The genuinely bad part, stated inside the good rather than hidden after it:** this project
has been measuring world-coordinate outputs on footage it cannot verify, and it owns no
confirmed metric clip. That is a **corpus gap**, not an accuracy loss — no number is
retracted by this finding — but it means the *next* metric measurement is blocked on
footage that does not exist yet. That is exactly why §4 puts a 15-minute recording at the
top of the queue.

**And a real risk, priced rather than dismissed:** the requirement might not be meetable in
practice. If typical amateur players cannot find 2.5 m of elevation, v1 ships as a
shot-and-rally product and the measurement half is cut. That would be bad news — but it
would be bad news we discovered for 15 minutes instead of at launch, which is itself the
good version of a bad outcome.

---

## 6. The recommendation, and the one thing that would change it

**Ship the live framing check as the setup gate, warn-not-block at capture and block on
metric outputs, with §1.4's reduced mode as the honest fallback — and get one compliant
clip recorded this week before frontend-dev commits to a results-screen design.**

That is one call with three parts, and the parts do not separate: the check without the
fallback is an app that refuses users, the fallback without the check is an app that never
knows which mode it is in, and both without the clip are built against an assumption nobody
has tested on a real court.

**The one thing that would change it:** *the founder cannot get a phone above ~2.2 m at his
own court with gear a normal person owns.* If that is the outcome of §4 item 0, the
recommendation inverts — the framing requirement is unshippable, and v1's answer becomes
**cut speed and the bounce map from v1 entirely** and ship the shot-and-rally product,
which needs no metric court and therefore no setup gate at all. That is a smaller v1 but a
coherent one, and it is a much better place to arrive at session 15 than at session 45.

**Nothing else changes it.** Not a better fitter, not a sixth gate, not a learned court
model — the crossover is set by the net's physical height against the far half's depth, a
property of the court rather than of the camera, and no software reaches information that
is not in the image.

---

## Recommended STATE wording, for the lead to apply (pm does not edit STATE)

Two rows. The first is a downgrade, the second is a new product row.

> `demo30` **loses metric citability entirely, not just speed** — at a 1.38 m mount its
> court is unconfirmable from a still frame, and its 47.9 px net span is below the net-tape
> instrument's resolution so no independent off-plane check can be run on it either. Was
> "speeds never citable"; now **no world-coordinate number from `demo30` is citable**.
> `am_hard_utr` (1.74 m) is likewise unconfirmable but survives on two independent
> corroborations (net-tape height −3.7%, net-anchor internally consistent to 0.4 px), with
> its pre-existing 7.5 m-of-23.77 m depth limit unchanged.
> [evidence/low-mount-implications.md](evidence/low-mount-implications.md)

> **v1 gains a framing gate and a reduced-output mode.** Below the ~2.0–2.2 m crossover the
> app **warns but never blocks capture**, still ships the shot list, rally clips and
> highlights (all time- or pixel-domain), and **withholds speed, the bounce map and
> distance run** (all homography-domain). One bit — *framing verified* — stored on the match
> record, not in view state. **No new autonomous calibration gate**: net posts, fitted hfov,
> gravity/arc and every ground-plane statistic are already measured out.
> [evidence/low-mount-implications.md](evidence/low-mount-implications.md)

---

## NOT ESTABLISHED THIS RUN

- **What fraction of amateur courts allow a 2.5 m mount.** Unknown, and I refuse to guess
  it. §4 item 0 is the cheapest way to get a first data point.
- **Whether the wider 27–29-clip calibration corpus contains clips above the crossover.**
  Only four mounts are named in the evidence and all four are below; `sAjkpeRq4P4` at 3.33 m
  proves at least one other clip is above. Not enumerated here.
- **Whether the live framing check is affordable in a camera preview loop on an A13.**
  Unmeasured like every other on-device number. Folded into §4 item 1's case.
- **Whether `yt_match40`'s two withdrawn figures have actually been re-derived** since the
  re-click. STATE describes the calibration as confirmed; it does not say the figures were
  recomputed. Worth one check before either is quoted again.
