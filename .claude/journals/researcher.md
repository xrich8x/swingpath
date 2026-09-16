# researcher — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-16 — SWINGVISION TEARDOWN + HIDDEN-BOUNCE ROUTES

Founder directive 2026-09-16: the app MUST call every bounce including hidden ones. Do NOT
recommend narrowing/refusing more. Find HOW.
Deliverable: `docs/evidence/swingvision-teardown.md`. No STATE row, no SPEC edit, no code.
Q1: what SwingVision does (setup, line calling + accuracy marketing vs independent, blocked
bounces — verify SPEC §3 claim "occasionally unable to call", distance from one camera,
on-device compute, pose/player tracking). Also PlaySight, Wingfield, Zenniz, In/Out, Mojo, Hawk-Eye.
Q2: ranked routes for hidden-bounce calls (R6 joint pre+post arcs, gap prediction vs SPEC §6
150/400 ms table, audio timing, others). Each: what pins distance, plausible accuracy,
pre-registered test on mono3d_ceiling/synth_truth. Report: cheapest test for joint arcs.
Label every claim MEASURED / PUBLISHED(link) / ARITHMETIC. Rule 12: SV outputs never truth.

## STATE — repo context read (routes doc incl R1/R1b, SPEC, CLOSED rows, STATE audio rows,
CAPTURE_PROTOCOL §6 audio). Now: web research on SwingVision.
Repo facts: docs/external/ DOES NOT EXIST. Glob/dir-Grep flaky here — Grep single files by path.
CLOSED rows relevant: ball/CLOSED bounce_hypothesis, v2 restitution_set, bounce_reset (all 2D
smoother), M1 bridges; measure/CLOSED SwingVision HUD capped. STATE:285 audio screen:
detect_impacts self-declares useless on 0/88 clips (label-free screen, no recall figure).
CAPTURE_PROTOCOL §6: audio accepted for timing w/ t = t_audio - d/c; ~5 frames delay at 30 m uncorrected.

### SV FINDINGS SO FAR (all PUBLISHED; swing.vision + apps.apple + patents.google + justia fetch FAIL - JS/DNS)
- tennis.com Jon Levey 2024-12-08: iPhone on fence BEHIND BASELINE one side + iPad tripod at net post;
  "97% of calls correct for shots landing within 10 cm of line" (SV claim); "single camera system has
  limitations and there are instances when it can't make the call" -> SPEC §3 claim VERIFIED (no cause given).
  4 USTA SoCal tournaments + Dennis Rizza Classic (Jack Kramer Club). 3 incorrect challenges/set.
- tennisnerd 2024-12-20: "in a few shots, the system was unable to make the call"; 97% is company claim.
- Apple dev "Behind the Design" 2023-06-05: 60 fps, 1080p, "not possible without Neural Engine"; Sahai CEO, Hsu CTO.
- search snippet: iOS/iPadOS 18; "~95% close-line calls", speeds +/-10%; Swing Stick 60 cm above fence top.
- Legal entity Mangolytics Inc. Patent US11893808B2 "Learning-based 3D property extraction",
  assigned Mangolytics Dec 2023 -> SwingVision Inc Jan 2024. READ via patents.google.com/patent/US11893808B2
  (no /en suffix works; /en DNS-failed): filed 2020-11-30 (US17/106,499), pub US20220171957A1 2022-06-02,
  granted 2024-02-06. Inventors Sahai, Hsu, Adith Balamurugan, Neel Sesh Ramachandran.
  CLAIM 1: mobile device camera + NN trained to extract 3D property by CORRELATING pixel arrangement of
  object AND of reference visual feature (court lines) -> 3D property. NO explicit homography/calibration
  described. Training labels: 3D sensors (radar, lidar) OR multiple calibrated cameras at a TRAINING EVENT,
  timestamped. Outputs: 3D location, velocity, orientation, size, scoring events ("ball landing outside
  service court", foot fault). Mount: tripod behind baseline, "can be mounted anywhere...adjust geometry".
  NO occlusion, NO physics model, NO bounce method disclosed (per fetch model; moderate trust).
  WARNING: the USPTO-PDF fetch model HALLUCINATED assignee Hawk-Eye - discard it.
- Sahai also inventor w/ Elluswamy + James Anthony Musk: portable drill instruction app (Justia).
- Job ads: ML Eng (AngelList) wants CoreML/Swift + "intrinsic and extrinsic calibrations, projection
  matrices, ray casting" (=> explicit geometry, not only the patent's learned map). Head of ML (freehire,
  posted 2026-05-07): Core ML + ANE on-device optimisation, iOS deploy.
- ITF PAT approval PAT-25-037 issued 2025-10-31, iOS 17+, sw 11.9.6. PAT != ELC classification (separate).
  ITF PDFs do NOT text-extract via WebFetch; saved copies are OUTSIDE project -> not read.
- Validity: Applied Sciences 2023 13(10):6195 (MDPI, 403): N=5 elite juniors; placement ICC 0.83-0.87,
  speed ICC 0.76-0.80, stroke detection ICC 0.97. IJPAS 2024 24(1) doi 10.1080/24748668.2023.2268475:
  "high agreement", errors from angle differences; optimal angle >> suboptimal. NEITHER tests line calls.
- Smart Court (tennisnerd 2025-03-01): 1 camera + kiosk; "later in 2025 ... 2-camera option, which will
  increase the accuracy for line calling"; claims 97-99%.
- Second Serve podcast ep 292 (2025-10-16), Sahai VERBATIM: 97% "hasn't been verified by others, it's
  just been verified by us"; ITF silver "at least 95% for those calls ... any line"; applying (not certified);
  "developing a two-camera version ... one phone on each side ... close call accuracy is like above 99%";
  Apple Watch challenge; live line calls social-play only. No occlusion talk found in transcript.
- **r.jina.ai/<url> RENDERS swing.vision pages** (direct fetch returns title only).
  set-up-your-recording: all mounts "behind the baseline in middle". Ground mode (phone vs water bottle,
  net tape in pink rect) = NO line calls; Fence Mount = "half court line calls"; Swing Stick on top of
  fence = "Unlock full court line calls". iOS 18 for real-time line calling. Sun behind; opposite windscreen.
  => SV GATES LINE-CALL COVERAGE BY MOUNT HEIGHT == our D^2/(f*h). KEY FINDING.
  challenge-line-calls: recording device iPhone 11 / SE(2020)+ or 2020 iPad Pro+ (=A13 floor, same as us);
  Watch S6+; remote iOS/Android; review bounce frame-by-frame. No statement on uncallable.
  faq via jina: questions only, answers not rendered.
- "Swing Stick extends 2 ft (60 cm) above fence": SEARCH-ENGINE SYNTHESIS ONLY, primary source not found
  -> UNVERIFIED. swing-stick-offer page: "patented phone mount", no height. Tennis.com 2022-10-23 (Levey):
  SV speed = average contact->bounce, "20% less than top speed"; top-of-fence mount recommended.
- Real-time: SV "AI processes your video in real-time ... ball trajectory and player movements ...
  power of your device" (search snippets, SV marketing); >95% record natively on iPhone. Mac app exists.
  Player tracking = heat maps/court positioning (marketing). Pose used for line calls: NO SOURCE.
- COMPETITORS: In/Out (Infinity Cube, 2017): net-post unit w/ 2 cameras; LINE DEVICE (2-8 units on
  baselines/sidelines/service lines) - "Line Device call WINS"; "independent call mode ... Net Device doesn't
  need to see the ball bounce" (support.inout.tennis/line-device). = extra viewpoint solves unseen bounce.
  In/Out patent US10143907B2 (Gentil, prio 2015-12-09) "Planar solutions to object-tracking problems":
  single fixed camera near net post; bounce = abrupt direction change consistent w/ gravity model, then
  z=0 -> court model (homography); leaves FOV w/o bounce for timeout -> NO call; microphone used to
  decide court side; optional laser for close calls. No interpolation of unseen bounces.
  Baseline Vision: net-post unit, "two 4K cameras", 3D trajectory, call within 0.5 s (marketing).
  PlayReplay: ITF SILVER real-time (first), multi-camera count not found.
- Zenniz (zenniz.com how-does-zenniz-work): 4 cameras (2 in net-post unit, 1 behind each baseline) +
  "30 strategically placed microphones", "patented audio triangulation" for landing/strike points;
  cameras "Verify & Confirm Audio System Decisions"; "7mm" (marketing). Installed, not phone.
  Wingfield: behind-baseline unit, 2 integrated high-speed cameras, ITF PAT. Hawk-Eye ~10 cams, 3.6 mm mean
  (aceify, citing Collins & Evans 2008). Owens/Harris/Stennett VIE 2003 pp182-185: indexed abstract says
  "single, fixed medium resolution camera" - contradicts common knowledge; DO NOT lean on it.
- LIT: Chen, Cai, Wang, Yan arXiv:2107.09255 (2021): monocular ELC; bounce by "minimizing the fitting loss
  of the uncertain point"; search synthesis says descending+ascending least-squares fits, intersection =
  bounce (method detail UNVERIFIED, PDF unreadable). 99.4% on 394 = ball positioning; 81.8% of 11 bounces.
  TT3D Gossard/Ziegler/Zell arXiv:2504.10035v2 (2025-06-25) table tennis: drag+Magnus+Coulomb bounce;
  "uses the bounce as the initial state", optimises v+spin just before bounce (IPopt/Casadi); bounce from
  piecewise polynomial segmentation -> ray-plane intersection, sub-frame; synthetic 2 px noise, 130 trajs:
  MAE 8.9-29.8 cm by viewpoint (side best). No real 3D GT. = R6 PUBLISHED FORM. Table scale != court.
- App Store via jina: requires iOS 18 + A12 (real-time tracking floor is A13 per guide); 749.9 MB;
  release note "verbal notification when real-time audio feedback gets disabled due to device overheating";
  11.9.65 (Sep 2) "Fixed volleyed shots being incorrectly called 'out' by Audio Line Calls" (=> a landing
  was produced for a bounce that never happened: extrapolation OR volley-as-bounce; ambiguous);
  11.9.57 "Fixed unwanted camera refocusing ... iPhone 16"; user 2025-08-30 "Limits video to HD even if
  your phone can do 4k".
- RIG FACT: synth_truth.simulate uses simulator_torch = FLIGHT ONLY, no bounce. Post-bounce data needs
  numpy ball_physics/tennis_tracker/physics/simulator.py simulate(bounces=N) w/ _bounce(e_n,e_t,mu) :59.
  A 3D joint fitter using that same bounce model = self-grading; a 2D image-intersection test does not.
- MY ARITHMETIC (P1 cam, setback 6, net D=17.885, far svc D=24.285, far base D=29.77):
  net tape (0.914) hides-behind-mesh ground to D*h/(h-0.914): h=3 -> 25.7 m = 7.8 m past net (far svc
  boxes seen THROUGH MESH). Far svc line clear of tape needs h>=3.47 (centre) / 4.06 (1.07 post).
  Near player H=1.8 at Dp hides ground Dp..Dp*h/(h-H) = 2.5*Dp at h=3 (near court = good geometry).
  10 cm needs bridged-bounce pixel err <= 0.1 f h / D^2: D=6 6.7px, D=10 2.4px, D=12 1.7px, D=20 0.6px.
  Linear-extrap perp err, n=10 each side, 2 px: gap0 1.37px, gap9 2.19px, gap24 3.79px (/sin crossing angle).
  iPhone mic TDOA baseline ~14 cm: bearing only, ~3 deg/sample @48k -> no range. Audio = TIMING only.
  Two phones (one each end): each near half ends at net D=17.9 -> 13 cm/px worst; svc line 5.5 cm/px.

## DONE 2026-09-16. If restarted: work is FINISHED, just report it.
Written: docs/evidence/swingvision-teardown.md. Memory: swingvision-public-method.md (new) +
monocular-3d-geometry.md (hidden-bounce + rig fact) + MEMORY.md index. No STATE/SPEC/code/subagent.
Ranking H1 two-sided intersection > H2 audio time pin > H3 call-with-confidence > H4 mount height >
H5 second phone (v2 scope, founder) > H6 player anchors (pose, founder) > H7 shadow > H8 learned 3D.

- Infinity Cube (In/Out "eyes") v Mangolytics, SD Cal 3:22-cv-547, filed 2022-04, US 10,467,478.

## LOG
- 2026-09-15 monocular-3d-routes.md DONE (R1..R7 ranking; Q3 = NO whole-court at 1080p/3 m).
- 2026-09-16 new task started; journal rewritten.
