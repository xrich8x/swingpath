# SwingVision teardown, and how to call a bounce the camera cannot see

**researcher, 2026-09-16.** Written in response to the founder directive of 2026-09-16: the app
must call every bounce, including bounces hidden from the camera. This file establishes what
SwingVision publicly does, then ranks the ways a hidden bounce can be called on one iPhone.
**Nothing was run. No STATE row, no SPEC edit, no code.**

| Tag | Means |
|---|---|
| **[M]** | MEASURED in this repo, with the source file named |
| **[P]** | PUBLISHED, with a link. **[P-mkt]** means the source is the company's own marketing or its founder |
| **[A]** | MY ARITHMETIC or INFERENCE. It uses the pinhole model and P1's camera (1920 px wide, hfov 100°, f = 805.5 px, h = 3.0 m, 6.0 m behind the near baseline). No data behind it |

**Rule 12 is respected throughout.** SwingVision's calls, overlays and numbers appear here only as
*claims about their product*. None of them is used as truth, as a target, or as a tuning signal.

---

## 0. The answer in six lines

1. **No public source says how SwingVision handles a hidden bounce.** It does concede that it
   sometimes cannot call at all. **SPEC §3's sentence is VERIFIED**, but no cause is published (§1.3).
2. **SwingVision beats the distance problem mainly through the capture setup, not a clever
   estimator.** Its own setup guide gives **no line calls from a ground mount, "half court line
   calls" from a fence mount, and "full court line calls" only from its raised Swing Stick.** For
   top-accuracy events it adds **a second phone on the other side ("above 99%")**. That is our
   measured `D²/(f·h)` limit (R1), solved with height and a second viewpoint (§1.4).
3. **Its only disclosed 3D method is learned**, from a patent (US11893808B2). A network maps the
   pixel pattern of the ball *and the court lines* to a 3D property. It is trained on 3D
   measurements from an instrumented training event (radar, lidar or calibrated multi-camera). The
   patent says nothing about occlusion, bounce physics or trajectory fitting (§1.4).
4. **The "97% within 10 cm" figure is self-reported.** The founder said so on the record in
   October 2025: *"this hasn't been verified by others, it's just been verified by us"*. **No
   independent line-call accuracy measurement exists that I could find.** The two academic studies
   test placement and speed agreement (ICC), not line calls. ITF PAT approval is a separate process
   from ITF line-calling (ELC) classification (§1.2).
5. **The best route for a hidden bounce with the ball visible before and after is to join the
   two arcs where they meet on the ground (H1 = our R6).** This does not escape the distance
   blindness, it inherits it: **a bridged bounce is at best as good as a seen one.** In the near
   court, where the near player causes most hidden bounces, the geometry leaves a lot of slack
   (1 px = 1.5-4 cm). In the far court it leaves almost none, seen or hidden.
6. **The cheapest decisive test** needs no 3D fitter and no bounce model on the estimator side.
   Hide 0 / 9 / 24 frames around the true bounce on the simulator, intersect two quadratic image
   tracks, and cast the result onto the ground (§4). It needs one rig extension: the rig is
   currently flight-only.

---

## 1. What SwingVision actually does

### 1.1 Setup requirements

| Claim | Tag | Source |
|---|---|---|
| All three mounts sit **"behind the baseline in middle"** of the court | [P-mkt] | [Set Up Your Recording](https://swing.vision/guides/set-up-your-recording) (read via a text renderer; the site renders client-side) |
| **Ground mode** (phone leaned on a water bottle, net tape inside an on-screen rectangle): **no line calls** | [P-mkt] | same |
| **Fence mount: "half court line calls"** | [P-mkt] | same |
| **Swing Stick on top of the fence: "Unlock full court line calls"** | [P-mkt] | same |
| Swing Stick is a **"patented phone mount"**, $49.99 bundle | [P-mkt] | [Swing Stick page](https://swing.vision/shop/swing-stick-offer) |
| Swing Stick **"extends 2 feet (60 cm) above"** the fence | **UNVERIFIED.** It appears only in a search-engine summary. No primary page I reached states a height | — |
| Real-time line calling needs **iOS/iPadOS 18** | [P-mkt] | set-up guide |
| Recording device: **iPhone 11 / SE (2020) or newer, 2020 iPad Pro or newer**. That is an **A13 floor, the same as ours** | [P-mkt] | [Challenge Line Calls](https://swing.vision/guides/challenge-line-calls) |
| App listing: iOS 18, A12 or later, 749.9 MB | [P-mkt] | [App Store](https://apps.apple.com/us/app/swingvision-tennis-pickleball/id989461317) (text renderer) |
| **60 fps and 1080p.** *"if you don't record at 60 fps, you won't even see the ball bounce"* | [P] | [Apple Developer, Behind the Design, 2023-06-05](https://developer.apple.com/news/?id=0pg4dthn) |
| A user reports it **"Limits video to HD even if your phone can do 4k"** (2025-08-30) | [P] (user review, n=1) | App Store listing |
| Tips: sun behind the device; place it opposite the windscreen | [P-mkt] | set-up guide |
| Tournament setup: **iPhone on the fence behind the baseline on one side**, talking to an **iPad on a tripod at the net post** | [P] | [Tennis.com, Jon Levey, 2024-12-08](https://www.tennis.com/baseline/articles/fair-play-swingvision-puts-its-electronic-line-calling-to-the-test-in-tournament-play) |
| **Calibration step:** automatic or manual taps? | **UNVERIFIED.** No public page I reached describes it. A job ad asks for "intrinsic and extrinsic calibrations, projection matrices, ray casting" ([AngelList](https://angel.co/company/swingvision/jobs/105513-machine-learning-engineer-computer-vision-ai)), so explicit camera geometry exists somewhere in their stack | — |
| **Lens (ultra-wide or not)** | **UNVERIFIED** | — |

**[A] What the mount ladder means.** SwingVision does not promise every line from every mount. It
unlocks line calling **by mount height**, and it sells the accessory that reaches the top rung. That
is exactly what our arithmetic predicts. Down-court error per pixel is `D²/(f·h)`, so the far half
of the court needs height. A second mechanism favours height too, **the net**. From a mount of
height `h`, the net tape hides the ground behind it, which is then seen only *through the net mesh*,
out to range `D_net·h/(h − H_net)`:

| Mount h | Ground seen through the mesh extends this far past the net (centre, 0.914 m) | at the posts (1.07 m) |
|---|---|---|
| 2.0 m | beyond the far baseline (the whole far court) | the whole far court |
| 3.0 m | **7.8 m**, past the far service line (6.40 m) | 9.9 m |
| 4.0 m | 5.3 m | 6.5 m |
| 5.0 m | 4.0 m | 4.9 m |

**Clearing the far service line above the tape needs `h ≥ 3.47 m` (centre) to `4.06 m` (posts).**
That is my arithmetic, not their disclosure. It is *consistent with* "half court from a fence clip,
full court from a mast above the fence". I cannot verify that this is their reasoning, and which
half "half court" means is also unverified.

### 1.2 Line calling: what they claim, and what anyone independent measured

**Marketing and founder claims, kept apart:**

| Claim | Tag | Source |
|---|---|---|
| "**97% of calls correct for shots landing within 10 centimeters of line.** The human eye is only 90% accurate" | [P-mkt] (quoted by the journalist) | Tennis.com 2024-12-08 |
| "97%... in their tests", attributed to the company, not independently verified | [P] | [Tennisnerd, 2024-12-20](https://www.tennisnerd.net/news/live-line-calling-from-swingvision/43158) |
| Founder, Oct 2025: *"internally right now you know **this hasn't been verified by others, it's just been verified by us** today but we're seeing that swing vision is around 97% for those really close calls"* | [P-mkt] (founder's own words) | [Second Serve podcast ep. 292, 2025-10-16](https://secondservepodcast.com/2025/10/16/ep-292-disputed-line-calls/) |
| Founder: ITF silver is *"at least 95% for those calls... any line, whether it's the baseline, the service line, a really fast serve"*. SwingVision was **seeking** it, not holding it | [P-mkt] | same |
| Founder: **two-camera version, "one phone on each side... close call accuracy is like above 99%"** | [P-mkt] | same |
| Smart Court: "97-99% correct"; "later in 2025... a 2-camera option, which will increase the accuracy for line calling even further" | [P-mkt] | [Tennisnerd, 2025-03-01](https://www.tennisnerd.net/news/swingvision-smart-court-complete-ai-system-for-tennis/45328) |
| "around 95% for close-line calls", speeds ±10% | [P-mkt] (search summary; primary page not rendered) | swing.vision FAQ (answers did not render) |
| Speed is **the average from contact to bounce, "20% less than top speed"** | [P] | [Tennis.com, Levey, 2022-10-23](https://www.tennis.com/news/articles/swingvision-delivers-pro-level-insights-for-recreational-players) |

**Speed of the call.** Challenges are reviewed after the point, on an Apple Watch, a second phone or
the iPad. Audio "Live Line Calls" exist ("Hear real-time line calls with audio feedback", v11.9.51).
**No latency figure is published.** [P-mkt, App Store version history]

**Independent evidence, the complete list I could find:**

| Study | What it tested | What it did NOT test |
|---|---|---|
| *The Concurrent Validity of Mobile Application for Tracking Tennis Performance*, Applied Sciences 13(10):6195, 2023, [doi](https://doi.org/10.3390/app13106195) [P] | N = **5** elite male juniors. Serve **placement ICC 0.83-0.87**, **speed ICC 0.76-0.80**, stroke detection ICC 0.97, against video analysis | **Line calls. Landing error in cm.** ICC is agreement, not error |
| *How valid is the commercially available tennis match analysis mobile application?*, IJPAS 24(1), 2024, [doi](https://doi.org/10.1080/24748668.2023.2268475) [P, abstract only] | "high proportional similarity and percent agreement" with criterion data; **"optimal angle data had much more similar results... than the suboptimal data"** | Line calls. Full text not reached |
| **ITF Player Analysis Technology approval**, test code **PAT-25-037**, 2025-10-31, iOS 17+, software 11.9.6 [P] | That the product is approved as **PAT** | **PAT approval is a separate process from ELC classification** ([ITF ELC page](https://www.itftennis.com/en/about-us/tennis-tech/classified-elc-systems/)). The [approval report PDF](https://www.itftennis.com/media/15294/pat-25-037-approval-report-swingvision.pdf) **did not text-extract, so I have not read it.** It may contain numbers. That is an open item, not a finding |
| USTA Southern California: four tournaments plus the Dennis Rizza Classic (8 courts) | Deployment and player behaviour | No published accuracy figures. The USTA and club comments are impressions [P, Tennis.com / Tennisnerd] |

**Whether SwingVision holds ITF ELC classification (Bronze or Silver): UNVERIFIED.** The ITF list
page did not render. The founder described SwingVision as working toward it in Oct 2025. For
comparison, **PlayReplay** announced the first real-time ITF **Silver** classification
([ITF](https://www.itftennis.com/en/news-and-media/articles/playreplay-electronic-line-calling-system-achieves-real-time-silver-status/)).

**Confidence that no public independent measurement of SwingVision's line-call accuracy exists:
0.75.** What would move it: the text of PAT-25-037, or an ITF ELC classification report.

### 1.3 Blocked or unseen bounces

**SPEC §3's claim, "documented as occasionally unable to call at all": VERIFIED.**
- Tennis.com, Levey, 2024-12-08: *"The single camera system has limitations and there are instances
  when it can't make the call."* [P]
- Tennisnerd, 2024-12-20: *"with just one camera, there are some limitations and the tests showed
  that in a few shots, the system was unable to make the call."* [P]
- **Neither source gives a rate or a cause.** "Blocked by a player" is plausible but **not stated
  anywhere I found.** "A few shots" is the only magnitude on record.

**How SwingVision handles a hidden bounce: NOT PUBLICLY DOCUMENTED.** I searched their guides and
FAQ titles, the App Store notes, the patent, two podcasts, press and user reviews. Nothing describes
trajectory bridging, prediction through occlusion, or a "no call" message. **Confidence that no
public source describes it: 0.70.** Three indirect clues, each graded:

1. **v11.9.65 (Sep 2): "Fixed volleyed shots being incorrectly called 'out' by Audio Line Calls."**
   [P-mkt] A volley never bounces, yet the system produced a landing call. **[A]** There are two
   readings and I cannot choose between them. (a) The call is extrapolated from the flight before
   the ball lands, which would be trajectory prediction. (b) The racket contact was mistaken for a
   bounce. Both fit. Confidence in (a) over (b): **0.4.**
2. **The speed definition, "average from contact to bounce"** [P], means the system holds a hit
   point and a bounce point with a time between them. **[A]** That is a two-endpoint trajectory
   model, but it says nothing about unseen bounces.
3. **Their accuracy path is more viewpoints, not more inference.** Two phones "one on each side".
   Their closest competitor, In/Out, does the same (§1.7).

### 1.4 How it gets distance from one camera

- **The patent: US11893808B2, "Learning-based 3D property extraction."** [P]
  ([Google Patents](https://patents.google.com/patent/US11893808B2)). Filed 2020-11-30,
  published as US20220171957A1 on 2022-06-02, granted **2024-02-06**. Inventors Swupnil Kumar Sahai,
  Richard Hsu, Adith Balamurugan, Neel Sesh Ramachandran. Assigned to Mangolytics Inc., then
  SwingVision, Inc. (Jan 2024).
  - **Claim 1:** a mobile device whose camera captures a 2D image containing "a reference visual
    feature" (the court lines) and the object. *"a neural network trained to extract from the 2D
    image a 3D property of the object... by correlating an arrangement of pixels... that correspond
    to the object and an arrangement of pixels... that correspond to the reference visual feature
    to the 3D property."*
  - **Training truth:** a training event "outfit[ted]... with a set of 3D sensors" (**radar,
    lidar**), or "with multiple cameras that are positioned and calibrated", with timestamps.
  - **Outputs named:** 3D location, velocity, orientation, size, and scoring events ("a tennis ball
    landing outside of a service court", foot faults).
  - **Not disclosed:** an explicit homography or calibration step, a physics or trajectory model,
    bounce detection, occlusion handling. The mount is described as a tripod behind the baseline,
    and "can be mounted anywhere... the app... can adjust its geometry accordingly".
  - *Caveat:* read through a summarising fetch, not the raw claims text. A second fetch of the
    USPTO PDF returned a **hallucinated assignee (Hawk-Eye)** and was discarded. A patent discloses
    what was *claimed*, which need not be what ships.
- **Job adverts** [P-mkt]: Core ML + Swift, plus "intrinsic and extrinsic calibrations, projection
  matrices, ray casting". Head of ML (posted 2026-05-07, [freehire](https://freehire.me/jobs/head-of-machine-learning-swingvision-inc-u6ynhhrv)):
  "continuously optimizing neural networks for speed, memory, and battery efficiency using Core ML
  and the Apple Neural Engine."
- **LiDAR, depth sensors, IMU, ball-size depth:** **no public source mentions any of them.**
  UNVERIFIED either way. LiDAR is not present on the A13 devices they support.
- **[A] What a learned 3D mapping can and cannot do.** A network cannot put information into the
  pixels that is not there. At the far baseline, 1 px is ~36 cm down-court no matter who
  interprets it. What a network trained on 3D truth *does* learn is the **population prior**: where
  rally balls usually land given where they were hit, the stroke, the player's position. That is
  our route R4 (a MAP fit with priors) done implicitly. My inference is that their near-line
  numbers rest on (i) height, (ii) a strong learned prior, and (iii) since 2025, a second phone.
  **Confidence 0.5. It is an inference and cannot be verified from outside.**

### 1.5 On-device compute

| Claim | Tag | Source |
|---|---|---|
| "This app is basically not possible without Neural Engine." 1080p × 60 fps processed | [P-mkt] | Apple Developer 2023-06-05 |
| "AI processes your video in real-time... using just the power of your device"; >95% of customers record natively on iPhone | [P-mkt] (search summaries) | swing.vision, ITA page |
| **"Added a verbal notification when real-time audio feedback gets disabled due to device overheating"** | [P-mkt] (release note) | App Store |
| A Mac app exists for processing imported footage | [P-mkt] | FAQ titles |
| Model sizes, frame rate processed live | **UNVERIFIED** | — |

**The overheating note matters.** SwingVision, on the same A13-plus fleet, **turns live calls off
when the phone overheats.** That is published evidence that sustained load is binding for them, and
it supports this project's standing rule to budget sustained compute, never peak.

### 1.6 Pose and player tracking

- "track the ball trajectory **and player movements**", heat maps, court positioning [P-mkt].
  "how to shape up your posture and footwork" [P-mkt, Apple 2023].
- **Whether player or pose tracking feeds line calls or hit detection: NO SOURCE.** The patent's
  claim 1 names only the object and the reference feature (court lines).
- The founder rules on scope. What is on record is only that they track players for stats.

### 1.7 Comparable products

| Product | How it gets depth / handles unseen bounces | Tag |
|---|---|---|
| **In/Out** (Infinity Cube) | Net-post unit with two cameras. Its patent **US10143907B2** (Gentil, priority 2015-12-09, [Google Patents](https://patents.google.com/patent/US10143907B2)) calls a bounce on "an abrupt change in direction" consistent with a gravity model, then treats the ball as **on the court plane** and maps it through a court model. **If the ball leaves view without bouncing, a timeout gives no call.** A **microphone** decides which side of the court the ball is on, and an optional laser handles close calls. **Line Devices** (2-8 extra units on baselines, sidelines and service lines) override the net unit, and in "independent call mode" *"the Net Device doesn't need to see the ball bounce"* ([support](https://support.inout.tennis/line-device)). In/Out sued Mangolytics in 2022 (S.D. Cal. 3:22-cv-547, US 10,467,478) ([Bloomberg Law](https://news.bloomberglaw.com/ip-law/patent-suit-targets-ex-tesla-engineers-tennis-ball-tracking-app)) | [P] |
| **Zenniz** | **4 cameras** (2 in the net-post unit, 1 behind each baseline) plus **"30 strategically placed microphones"**, using "patented audio triangulation" to find landing and strike points. Cameras "Verify & Confirm Audio System Decisions". Claims "7mm" | [P-mkt] ([Zenniz](https://zenniz.com/smart-corner/how-does-zenniz-work)) |
| **Baseline Vision** | Net-post unit, "two 4K cameras", 3D trajectory, call within 0.5 s | [P-mkt] |
| **Wingfield** | Behind-baseline unit with **two integrated high-speed cameras**, ITF PAT | [P-mkt] |
| **PlayReplay** | Multi-camera installed system, **first real-time ITF Silver** | [P]; camera count not found |
| **Hawk-Eye** | ~10 high-speed cameras, triangulation, "mean error of about 3.6mm" (via [aceify](https://aceify.me/the-ace/electronic-line-calling-tennis-hawk-eye-explained/), citing Collins & Evans 2008). Another camera covers an occluded view | [P], secondary |
| PlaySight, Mojo | Not researched to a citable standard in this pass | — |

**[A] The pattern across the whole field:** every product that calls lines at tournament grade
**adds a viewpoint** (a second camera, line units, a net-post stereo pair) **or adds an acoustic
array.** Nobody publishes a single-camera method that recovers an *unseen* bounce. **In/Out's
patent is the only public single-camera design, and it declines to call when no bounce is seen.**

---

## 2. What any hidden-bounce method is up against: the arithmetic

**[M]** R1: with the bounce **visible**, median error is **5.4 cm across the camera ray** and
**1.28 m along it**. **[M]** R1b: at the far doubles corner, 18% of the along-ray error leaks across
the sideline. **[M]** P1: 6.1% within 10 cm at 2 px.

**[A] How much pixel error a bridged bounce can afford.** A hidden bounce can only be placed by
inferring the pixel where it *would* have been, then casting that pixel onto the ground. The
inferred pixel has to be good to `0.1·f·h/D²` px for 10 cm down-court:

| Bounce range from camera | Allowed inferred-pixel error for 10 cm | Where on court (P1 camera) |
|---|---|---|
| 6 m | **6.7 px** | near baseline |
| 10 m | 2.4 px | 4 m inside the near baseline |
| 12 m | 1.7 px | near service line |
| 20 m | 0.60 px | 2 m past the net |
| 29.8 m | 0.28 px | far baseline |

**[A] Who hides the ball, and where.** A player of height 1.8 m standing `Dp` from a 3 m camera hides
the ground from `Dp` out to `2.5·Dp`. The **near player** therefore hides bounces **in the near
court, exactly where the table above is most forgiving.** The **far player** hides ground mostly
beyond the far baseline. The **net mesh** covers the far service boxes at 3 m (§1.1). At a 1.74 m
mount (`am_hard_utr`), a 1.8 m player is taller than the camera, so everything behind them in their
angular width is hidden.

**[A] How extrapolation error grows with the gap.** Fit a straight line to n = 10 frames at 2 px on
one side and extrapolate into the gap. The perpendicular error at the bounce is about **1.3 px with
no gap, 2.2 px across a 9-frame (150 ms) gap, and 3.8 px across 24 frames (400 ms).** Curvature
makes it worse, a second side makes it better, and a shallow crossing angle between the two
tracks makes the along-track part worse. **This is order-of-magnitude only.** It is exactly what §4
measures.

**Reading those together [A]:** a 150 ms hidden bounce in the near court needs ~2-7 px and plausibly
gets it. A hidden bounce in the far court needs < 0.6 px, and a *visible* one already fails there.
**SPEC §6's table is written independent of range. The geometry says it cannot be:** the same
150 ms gap is cheap at 6 m and unaffordable at 20 m. That is a fact about the table's shape, not a
recommendation to narrow anything.

---

## 3. Ranked routes for calling a hidden bounce

Ranked by (value) × (confidence) ÷ (cost to falsify). Every route states what pins the distance
(hard rule 7).

| # | Route | Pins distance with | Plausible accuracy | Cost to falsify | Status |
|---|---|---|---|---|---|
| **H1** | **Two-sided arc intersection, then cast onto the ground.** 2D image-space first, full 3D joint fit (R6) second | the **z = 0 plane at the bounce**, known camera. Time comes from where the two tracks cross | near court: close to a visible bounce for ≤150 ms gaps. Far court: no better than a visible bounce, which already fails | **~1 h plus a rig extension** (§4) | OPEN. **Not** the CLOSED `bounce_hypothesis` / `restitution_set` / `bounce_reset` rows, which are 2D Kalman smoother changes |
| **H2** | **Audio bounce time as the time pin for H1** | pins **time only**. It turns "find where two curves cross" into "evaluate the pre-bounce curve at a known t" | removes most of the along-track error from not knowing the bounce time | sensitivity: free on the rig. Real precision: **only a court session** (CAPTURE_PROTOCOL §6 GATE 0) | OPEN. STATE: the audio screen is label-free (0/88 self-declared useless), **no recall figure** |
| **H3** | **A call with a confidence attached, on every bounce** (propagate H1's σ; call IN/OUT when the margin exceeds kσ, otherwise still call, with a stated confidence) | nothing new. It is the decision rule | most bounces land well away from lines, so a 30-50 cm σ still decides them | free once H1 emits a σ | OPEN. This is SPEC §6's 150-400 ms margin rule, generalised |
| **H4** | **Mount height as a requirement** (SwingVision's Swing Stick answer) | larger `f·h` | [A] `h ≥ 3.5-4.1 m` clears the far service boxes from the net mesh. The far baseline at 10 cm still needs `f·h ≥ 8,862 px·m` (routes §7) | free on the existing `height*` configs, plus H1 on each | OPEN. A capture-protocol change, not a product cut |
| **H5** | **Second iPhone at the other end** (SwingVision's own ">99%", In/Out's line devices) | **each phone calls its own near half** (at most 13 cm/px at the net, 5.5 cm/px at the service line [A]), or true triangulation | the only route in this table with a published, if self-reported, claim at this level | real footage needed. The rig can model it cheaply | **CLAUDE.md defers "stereo depth / second camera" to v2. The founder's call.** Calling each half separately needs no frame sync [A] |
| **H6** | **Player-anchored endpoints**: hit point from the striker's feet, end point from the returner's contact | ground contact of the feet, ±reach | **[M]** P1: an oracle launch point alone gave 4.6x but did not reach 10 cm. **Two** anchors are untested | rig: ~1 h with oracle anchors | **Needs person/pose detection. SPEC §9 is out of v1. The founder's call.** SwingVision tracks players [P-mkt], but its use in calls is unsourced |
| **H7** | **The ball's shadow as a second view** (outdoor, sun) | the shadow is on z = 0 and offset along the sun's direction, like a second camera at infinity | unknown. The shadow of a 6.7 cm ball is 2-3 px and low-contrast at range | needs real footage and a new detector | SPECULATIVE. Sunny outdoor only. Close to the rule-6 detector ban |
| **H8** | **Learned 3D from 2D** (SwingVision's patent) | a learned population prior, trained on 3D truth | cannot beat §2's per-pixel limit. It can only add priors (= R4) | **needs an instrumented training court (radar, lidar or multi-camera). We have none.** Using SwingVision outputs is barred (rule 12) | Low. It also cuts against "do not ML-ify geometry" |

**Dead, with the reason:**
- **Depth from ball size.** [A] Needs 0.83% diameter precision at 12 m, and motion blur is 8x the ball
  (routes §3).
- **Locating the bounce with the iPhone's own microphones.** [A] With ~14 cm between mics and
  1 sample = 7.1 mm at 48 kHz, the array resolves **bearing to ~3°**, and in the far field it
  gives **no range at all**. Bearing is the axis vision already measures to ~5 cm. Zenniz needs
  30 microphones spread around the court. **Audio on one phone is a clock, not a locator.**
- **2D Kalman coasting across the gap.** **[M]** `ball/CLOSED.md` M1: 1-2 frame coasted positions
  sit at a **19.9 px median** on real TrackNet clips. That is 3-10x the whole near-court budget
  above. H1 fits both sides; it does not coast one side.
- **Pose as the depth pin.** SPEC §6's contact detector. **[M]** An oracle launch point still fails
  by 5x (P1). It can only enter as H6's second anchor.

**Confidence in the ranking's top two (H1 then H2): 0.7.** What would move it: §4's result. If
H1's 150 ms arm degrades the near band more than 3x, H4 and H5 become the only routes with a
mechanism, and both are capture or scope decisions.

---

## 4. The cheapest test that says whether joining the arcs can work (pre-registered)

**Rig facts first [M].** `tools/synth_truth.simulate` uses `simulator_torch`, which is
**flight only** (its docstring: "the bounce is handled separately"). `tools/mono3d_ceiling.py` cuts
the track at the true bounce. **There is no post-bounce data today.** The numpy
`ball_physics/tennis_tracker/physics/simulator.py` does simulate bounces
(`simulate(..., bounces=N)`, a spin-aware impulse `_bounce(e_n, e_t, mu)` at line 59). The rig
extension is therefore to generate the true 3D path with `bounces=1` from the numpy simulator, then
project and add noise exactly as bar A does. That is backend-dev or qa work. I have not written it.

**Why a 2D intersection first.** It needs **no 3D fitter** and **no bounce model on the estimator
side**. The fitter and the simulator therefore share no bounce model, so R6's restitution
self-grading hazard does not arise. It is a **lower bound** on the full 3D joint fit, and it takes
microseconds per flight, not the ~1,050 s of a `fit_arc` sweep.

**Configuration.** Bar A exactly: 2.0 px noise, 0.30 dropout, 60 fps, h = 3.0 m, 1920×1080,
hfov 100°, seed 0, n = 500, `draw_launch` unchanged. Horizon long enough for ≥0.5 s after the bounce.

**Estimator (fixed before running).** Remove every frame within the gap, centred on the true bounce
time. Take the last 10 visible frames before the gap and the first 10 after it. Fit per-coordinate
quadratics `u(t), v(t)` on each side. Take `t*` in the gap that minimises
`‖pre(t) − post(t)‖²`, and the bounce pixel as the mean of the two curves at `t*`. Cast that pixel
onto `z = 0` through the rig's known camera. Score against the simulator's true bounce, split into
radial and tangential about the camera ray, as R1 did.

**Arms (the gap is the only variable).**
- **G0**: no frames removed (the visible-bounce reference, same estimator)
- **G9**: 9 frames removed = 150 ms (SPEC §6 row 1)
- **G24**: 24 frames removed = 400 ms (SPEC §6 row 2)
- **G9-audio / G24-audio**: as G9/G24, but with `t*` fixed at `t_true + N(0, 0.15 frame)`. **This grades
  an assumed noise model, so it is reported as a SENSITIVITY, never as evidence** (rule 1). Real
  audio precision comes only from the court session.

**Bands.** Bounce range from the camera: **near ≤ 12 m** (where the near player hides bounces),
mid 12-20 m, far > 20 m. All three are reported. The near band is primary.

**Precursor, reported first.** The fraction of flights with ≥ 5 in-frame post-bounce observations
inside the horizon, per band. **If under 60% overall, the full 3D R6 dies here**, as the routes doc
pre-registered. H1-2D is still scored on the flights that have them, and the fraction is reported
alongside.

**Primary bar.** Near band, **G9 median total error ≤ 1.5 × the near-band G0 median.**
**Secondary.** Near band, G24 ≤ 3 × G0. Also reported, but not gating: the **SPEC §6 check**,
the share of near-band G9 flights within 10 cm and of G24 within 25 cm, set against a 90% rate so it
lines up with §3.
**Kill.** Near-band G9 median > **3 ×** G0. Two-sided bridging then fails even where the geometry is
kind, and hidden-bounce calls rest on H4, H5 or H6, all capture or scope decisions.

**Known ways this flatters the method, stated before it runs:**
1. The camera is exact. P8 C1 says a four-tap calibration is not. Add a perturbed-calibration arm
   *afterwards*, as a separate variable.
2. The noise is i.i.d. Gaussian. **Real occlusion corrupts the frames at the gap edges** (partial
   ball, player edge), and M1's 19.9 px is the real-data warning. A follow-up arm gives the 2 frames
   next to each gap edge 3x noise.
3. The flight population is uniform, not a tennis population (routes §5).
4. The simulator's bounce model shapes the post-bounce curve. The quadratic estimator does not share
   it, but a strong spin kick could make the quadratic misfit. That is a real test, not an artefact.

**Confidence the primary bar passes: 0.60.** **What would disprove H1:** the kill firing.
**This is the cheapest finding in this file to falsify.**

**Feasibility on an A13 [A].** Two 3-parameter least-squares fits, a 1-D minimisation and one
ray-plane intersection per bounce: microseconds on the CPU, no ANE. **Confidence it fits the 16.7 ms
budget: 0.95.** The full 3D joint fit (R6) is a different matter: **0.20, unmeasured** (routes R6).
**Note that a hidden bounce cannot be called ON the bounce frame.** The post-bounce side needs about
10 frames (~170 ms) after the ball reappears. INSTANT, as SPEC §8 defines it, cannot hold for a
hidden bounce by construction. That is a timing fact for pm, not a narrowing.

---

## 5. For the PM: the tradeoffs, plainly (decisions left open)

- **Calling every bounce is achievable in the sense of emitting a call. Calling every bounce at
  10 cm is not, from a 3 m single phone, visible or hidden.** The honest way to meet the founder's
  instruction without refusing is H3: every bounce gets IN or OUT with a confidence. Most bounces
  land far enough from a line that the confidence is high. SPEC §3's refusal rule would have to
  change for this, and that is a founder and pm decision.
- **SwingVision's own answers are capture answers:** height (Swing Stick) and a second phone. Both
  collide with current text. The first collides with CLAUDE.md's "regardless of mount height"
  premise, which R1 already undercut. The second collides with "second camera: v2". **Neither needs
  new research to adopt, only a ruling.**
- **INSTANT versus hidden bounces.** A bridged call arrives ~170 ms after reappearance, not on the
  bounce frame.
- **Pose.** SwingVision tracks players, but nothing public says it uses them for calls. H6 is the
  route that would need pose, and it is untested even with oracle anchors.

## 6. Open questions

1. What does ITF report PAT-25-037 actually contain? The PDF did not extract, and it may hold the
   only third-party numbers on SwingVision.
2. Is SwingVision ITF ELC-classified (Bronze or Silver) as of today? The list page did not render.
3. Which half is "half court line calls" from a fence mount, and what is the Swing Stick's true
   height? Both are unverified.
4. How often are real amateur bounces hidden, by the near player, the net mesh, or leaving frame? **No
   ground truth exists.** The capture session could tally it cheaply.
5. Is a far-court bounce audible and timeable on a phone? CAPTURE_PROTOCOL GATE 0 answers it in five
   minutes on court.
6. Does a real detector's error at the gap edges look like M1's 19.9 px or like the rig's 2 px? That
   decides whether §4's result transfers.

## Sources

- [swing.vision: Set Up Your Recording](https://swing.vision/guides/set-up-your-recording) ·
  [Challenge Line Calls](https://swing.vision/guides/challenge-line-calls) ·
  [FAQ](https://swing.vision/faq) · [Swing Stick](https://swing.vision/shop/swing-stick-offer)
  (all rendered via a text proxy; the site is client-side)
- [App Store listing](https://apps.apple.com/us/app/swingvision-tennis-pickleball/id989461317)
- [Tennis.com, Levey, 2024-12-08](https://www.tennis.com/baseline/articles/fair-play-swingvision-puts-its-electronic-line-calling-to-the-test-in-tournament-play) ·
  [Tennis.com, Levey, 2022-10-23](https://www.tennis.com/news/articles/swingvision-delivers-pro-level-insights-for-recreational-players)
- [Tennisnerd, 2024-12-20](https://www.tennisnerd.net/news/live-line-calling-from-swingvision/43158) ·
  [Tennisnerd, 2025-03-01](https://www.tennisnerd.net/news/swingvision-smart-court-complete-ai-system-for-tennis/45328)
- [Second Serve podcast ep. 292, 2025-10-16](https://secondservepodcast.com/2025/10/16/ep-292-disputed-line-calls/) ·
  [ep. 189, 2023-11-05](https://secondservepodcast.com/2023/11/05/ep-189-swingvision-magic-tennis-technology/) (no technical content)
- [Apple Developer, Behind the Design, 2023-06-05](https://developer.apple.com/news/?id=0pg4dthn)
- [US11893808B2](https://patents.google.com/patent/US11893808B2) · [US10143907B2](https://patents.google.com/patent/US10143907B2)
- [Bloomberg Law, 2022-04-21](https://news.bloomberglaw.com/ip-law/patent-suit-targets-ex-tesla-engineers-tennis-ball-tracking-app)
- [AngelList ML Engineer](https://angel.co/company/swingvision/jobs/105513-machine-learning-engineer-computer-vision-ai) ·
  [freehire Head of ML](https://freehire.me/jobs/head-of-machine-learning-swingvision-inc-u6ynhhrv)
- [ITF PAT-25-037 report](https://www.itftennis.com/media/15294/pat-25-037-approval-report-swingvision.pdf) (not text-extracted) ·
  [ITF classified ELC](https://www.itftennis.com/en/about-us/tennis-tech/classified-elc-systems/) ·
  [PlayReplay Silver](https://www.itftennis.com/en/news-and-media/articles/playreplay-electronic-line-calling-system-achieves-real-time-silver-status/)
- [Applied Sciences 2023, doi:10.3390/app13106195](https://doi.org/10.3390/app13106195) ·
  [IJPAS 2024, doi:10.1080/24748668.2023.2268475](https://doi.org/10.1080/24748668.2023.2268475)
- [In/Out Line Device](https://support.inout.tennis/line-device) ·
  [Zenniz](https://zenniz.com/smart-corner/how-does-zenniz-work) ·
  [aceify, Hawk-Eye explainer](https://aceify.me/the-ace/electronic-line-calling-tennis-hawk-eye-explained/)
- Chen, Cai, Wang, Yan, *Monocular Visual Analysis for Electronic Line Calling of Tennis Games*,
  [arXiv:2107.09255](https://arxiv.org/abs/2107.09255), 2021. Bounce found "by minimizing the fitting
  loss of the uncertain point". **99.4% is ball positioning on 394 samples. The bounce result is
  81.8% of 11 samples.** Footage unstated. The method's two-sided fit is a search-summary reading,
  unverified from the PDF.
- Gossard, Ziegler, Zell, *TT3D: Table Tennis 3D Reconstruction*,
  [arXiv:2504.10035v2](https://arxiv.org/html/2504.10035v2), 2025-06-25. Drag + Magnus + Coulomb
  bounce, **parameterised at the bounce**, sub-frame bounce by piecewise segmentation and a
  ray-plane intersection. **Synthetic 2 px, 130 trajectories: MAE 8.9-29.8 cm by viewpoint. No real
  3D truth.** Table-tennis scale; it does not transfer to a 23.77 m court. It is H1/R6 in published
  form.

---

## LEAD ADDENDUM 2026-09-16 — verification, and a metric mismatch worth knowing

**Verified by the lead against the sources:** patent US11893808B2 is assigned to Mangolytics Inc. /
Swingvision Inc. and describes a neural network trained on 2D images paired with 3D measurements from
radar, lidar or calibrated multi-camera rigs, with no physics model, bounce detection or occlusion
handling. SwingVision's own pages (via search) say the Swing Stick mounts on top of the back fence and
extends ~60 cm (2 ft) above it, with the whole court in view, for full-court calls. The setup-guide page
itself renders client-side and could not be read directly.

**SwingVision's 97% and SPEC §3's 10 cm are DIFFERENT METRICS.** SwingVision's claim is the share of
IN/OUT calls that are **correct**, among shots **landing within 10 cm of a line**. SPEC §3's bar is
**landing-position error under 10 cm** on >=90% of near-line calls. Related, not the same: a ball
landing 8 cm inside can be called correctly with a 7 cm error in the right direction. Rewording §3 is
the founder's call; nothing here changes it, and bar A stays FAILED.

**SwingVision's metric on P1's existing data — descriptive, no bar, zero compute.** Unfitted flights
count as wrong calls. Singles court, `analytics.line_call`. 95% Wilson intervals in brackets.

| Config | Band | n | 3D arc fit | 2D control |
|---|---|---|---|---|
| perfect pixels, 3.0 m | within 30 cm | 15 | 93% [70-99] | 80% [55-93] |
| 2 px noise (bar A), 3.0 m | within 10 cm | **4** | 50% [15-85] | 50% [15-85] |
| 2 px noise (bar A), 3.0 m | within 30 cm | 15 | 60% [36-80] | 60% [36-80] |
| 2 px noise (bar A), 3.0 m | within 100 cm | 48 | 75% [61-85] | 81% [68-90] |

**It cannot be measured properly on this data: only 4 of 441 flights land within 10 cm of a line**,
because the simulator draws landings uniformly. What the 30 cm band shows is that, at realistic
noise, both methods sit far below 97% — but on n=15. **The next simulator test must use a
near-line-weighted flight population** so this metric has a real denominator.
