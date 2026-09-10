# iOS Core ML latency harness

**This is an instrument, not a product.** It exists to answer three v1 decisions
that were blocked on "there is no iOS app to install" (`docs/DECISIONS_PENDING.md`
item −1): sustained on-device throughput at thermal steady state, the int8-vs-fp32
ship call, and the cost half of pose affordability. It has no camera, no court
overlay, no navigation. One screen: a model list, a Run button, a results log.

**Nothing in this directory has been built or run.** There is no Mac anywhere in
this project — the only compiler that will ever touch this code is the
GitHub-hosted `macos-14` runner in `.github/workflows/ios-latency-harness.yml`,
and that workflow has not been triggered. Everything below is written to the best
of documented, public Core ML / Xcode behavior; the "What I could not verify"
section at the bottom says exactly where the risk sits.

## What it measures

For each Core ML model bundle it finds:
- a **quick block**: 10 untimed warm-up predictions, then 50 timed ones — median
  and p95 milliseconds.
- a **sustained block**, length set by a Stepper in the app (default 2 minutes,
  0–30): predictions back-to-back, bucketed into 30-second windows, each bucket
  reporting its own median/p95 **and** `ProcessInfo.thermalState` at that moment.
  A degrading median across buckets, or `thermalState` climbing past `nominal`,
  is the sustained-throughput answer this harness exists to produce. A long
  sustained run (10–30 min) is what actually stresses thermal steady state —
  the default 2 minutes is a fast smoke test, not the real measurement.

Every line is written to the on-screen log **and** appended live to
`Documents/harness_session_log.txt` as it happens (not buffered to the end), so an
interrupted run still leaves a real partial record — the same reason the product
app itself is built to resume rather than restart.

## Design decision: how models get onto the device

Two options were weighed, per the brief:

**Bundling `.mlpackage` files into the app at build time** — simplest from a code
standpoint (Xcode compiles them into the app's `.mlmodelc` automatically), but it
means **every model swap is a fresh CI build**, and macOS runners on this private
repo bill at **10x** against a ~2,000-minute/month free budget — roughly 2–4
builds total. This harness exists specifically to compare **8 model variants**
(`ballnet_v21.{fp16,int8}` and `yolo11m-pose.{1280,640,384}.{fp16,int8}`, per
`tools/export_coreml_p0.py`), and the whole point is to try more than one. Bundling
would burn the entire CI budget on packaging alone, before a single latency number
exists.

**Chosen instead: load from the app's Documents directory.** `Info.plist` sets
`UIFileSharingEnabled` and `LSSupportsOpeningDocumentsInPlace`, which exposes the
app's Documents folder to file-transfer tools and to the iOS Files app. Model
swaps then cost **zero CI minutes** — only a file transfer on the Windows/iPhone
side. The cost is that the app has to compile the model itself, on-device, at
runtime (see below) rather than relying on Xcode's build-time compile — a small
amount of extra app code, in exchange for not re-billing macOS minutes every time
someone wants to try a different tag.

**This one CI build should be treated as precious.** Read the whole workflow
before triggering it; if it fails, fix from the log rather than re-running blind.

## Does Core ML need `.mlmodelc`, and where does that compilation happen?

**Yes — the runtime always needs a compiled `.mlmodelc`, never a raw `.mlpackage`
directly. The question is only WHERE the compile happens, and this harness
deliberately picks the on-device path.**

- **Build-time compile (not used here):** if a `.mlpackage` is added to an Xcode
  target as a resource, Xcode's build system invokes `coremlc` during the build
  and embeds the resulting `.mlmodelc` in the app bundle. This is the path every
  Core ML tutorial shows, and it is exactly what bundling (rejected above) would
  require.
- **Runtime compile (what this harness does):** `MLModel.compileModel(at:)` is a
  **public, documented API** (present since iOS 11, and extended to accept
  `.mlpackage` directories, not only `.mlmodel` files) that compiles a model to a
  temporary `.mlmodelc` on-device and hands back its URL, which is then loaded
  with `MLModel(contentsOf:configuration:)`. This is the mechanism Apple documents
  for **downloadable / post-install models** — i.e. exactly this harness's
  situation, a model that arrives after the app is already installed.

`ios/App/ModelRunner.swift`'s `loadCompiled(from:)` calls this API. **High
confidence this is the correct mechanism; not verified by an actual on-device
compile, because that needs the device and there has been no build yet.**

## Getting a model onto the phone — the exact Windows-side path

1. **On the Windows PC:** locate the exported model(s) under `ios/coreml_export/`
   (produced by `tools/export_coreml_p0.py` via `.github/workflows/coreml-export.yml`
   — a *different* workflow, already existing, not touched by this one). Each
   `.mlpackage` is a **folder**, not a single file.
2. **Zip it.** Right-click the `.mlpackage` folder → *Send to* → *Compressed
   (zipped) folder*. Do this per model you want to test.
   - Why zip at all, instead of dragging the folder straight over: whether the
     Windows file-transfer tool below preserves a *nested* folder's internal
     structure when dragged in as a folder is untested here (see "What I could
     not verify"). A single `.zip` file removes that risk entirely, and iOS can
     unzip it natively — no extra app, no extra code in this project.
3. **Install "Apple Devices" from the Microsoft Store** (the current
   iTunes-for-Windows successor; it is what exposes per-app **File Sharing** on
   Windows without a Mac). Connect the iPhone by USB (or Wi-Fi sync once paired),
   trust the computer on the phone if prompted.
4. In Apple Devices, select the phone, go to the **File Sharing** section, choose
   **LatencyHarness** in the app list, and drag the `.zip` file into its Documents
   pane.
5. **On the iPhone**, open the **Files** app → **On My iPhone** → **LatencyHarness**.
   The `.zip` will be there. Tap it and choose **Extract** — this is a built-in
   iOS Files feature, no third-party unzip app needed. The extracted `.mlpackage`
   folder appears right next to it, already inside the app's Documents folder —
   no further copy step required.
6. Open the LatencyHarness app (or tap **Rescan** if it was already open) — the
   model should now be listed.

Repeat steps 2–6 per model you want to test. Nothing here touches CI.

## Installing the app itself (sideloading with a free Apple ID)

1. **Trigger the build** — someone with push/Actions access runs
   `.github/workflows/ios-latency-harness.yml` manually (Actions tab →
   *iOS latency harness (build only, unsigned)* → *Run workflow*). This was
   **deliberately not done** by whoever wrote this harness — triggering CI costs
   real money on a private repo and is the founder's/lead's call, same standing
   rule as `coreml-export.yml`.
2. **Download the artifact**: `ios-latency-harness-unsigned-ipa`, containing
   `LatencyHarness-unsigned.ipa`. It is unsigned — installing it needs a
   sideloading tool, not a plain "install .ipa" action.
3. **Install with Sideloadly or AltStore** (both run on Windows, both work with a
   free Apple ID):
   - **Sideloadly** (simplest for a one-off .ipa): plug in the iPhone, drag the
     `.ipa` onto Sideloadly, sign in with your Apple ID when prompted, click
     Start. It resigns the .ipa with your ID's ad-hoc certificate and installs it.
   - **AltStore**: requires AltServer running on the Windows PC and the phone on
     the same network the first time; then "Install from file" with the .ipa.
4. **On the phone**, trust the developer certificate once: Settings → General →
   VPN & Device Management → tap your Apple ID → Trust.
5. **The 7-day expiry, and what re-signing means in practice**: a free (non-paid)
   Apple ID's signing certificate expires after **7 days**, after which the app
   refuses to launch (a "not trusted"/expired message). This is an Apple platform
   limit, not a bug in this harness. In practice: if the app stops opening,
   re-run Sideloadly against the **same** `.ipa` file already downloaded — this
   does **not** require a new CI build, only a new sign+install pass on Windows.
   AltStore can auto-refresh in the background if AltServer stays running and
   reachable, but do not rely on that unattended for a multi-week test — check in
   on it at least weekly.
6. **Bundle identifier**: `com.swingpath.latencyharness`, set once in
   `ios/project.yml`. If it collides with something else already sideloaded under
   the free-account limit (10 apps at a time), both Sideloadly and AltStore expose
   a way to override the bundle ID at install time (Sideloadly: an explicit
   "Bundle ID" field in its advanced options; AltStore: automatic, to work around
   the same limit) — no project change or rebuild needed either way.

## Reading the numbers

- **Quick block** — `median` / `p95` in milliseconds, over 50 predictions after
  10 discarded warm-up runs. This is the "phone is idle and cool" number — a
  reasonable proxy for a single shot, not for a whole match.
- **Sustained block** — one line per 30-second bucket: `n` (samples in that
  bucket), `median`, `p95`, and `thermal` (`nominal` / `fair` / `serious` /
  `critical`, from `ProcessInfo.thermalState`). What answers the throughput
  decision:
  - **Median ms roughly flat across buckets, thermal stays `nominal`/`fair`** →
    the model is affordable for a sustained (60–90 min) match analysis at this
    compute-unit configuration.
  - **Median ms climbs across buckets, or thermal reaches `serious`/`critical`**
    → this model, at this precision/size, is not affordable for the full
    foreground-analysis duration the product needs. That is exactly the kind of
    result that should go to `pm` for a product cut (smaller input size, int8
    instead of fp16, or analyse a set rather than a whole match) — this harness
    only measures; it does not recommend a cut on its own.
  - Run each of `ballnet_v21.fp16` vs `.int8`, and each pose size × tag, back to
    back on the **same** phone in the **same** sitting (thermal state carries
    over between models if you don't let the phone cool down — that's realistic
    for how the product will actually run all of them in one session, not a
    confound to correct for).
- **Copy results button** — puts the full on-screen log on the clipboard. There
  is no Mac to read an Xcode console or Instruments trace from, so this — plus
  the `harness_session_log.txt` file retrievable the same way models arrive (drag
  it back out via the same File Sharing pane) — is the only way numbers leave the
  device. Paste directly into a message back to the team; do not retype or
  round anything by hand.
- **Never quote a number from this harness as if measured on an A13.** The test
  device is an iPhone 17, far above the project's stated floor (A13 / iPhone 11).
  A number here is evidence about *this specific phone*; whether it generalises
  down to the floor device is a separate, unanswered question. Per this project's
  standing rule, no phone fps/latency number existed in this repo before this
  harness — do not let a first number from a top-of-line device get treated as
  the floor number by mistake in whatever writes it into `docs/STATE.md`.

## What I could not verify (read this before trusting the build to work first try)

- **`MLModel.compileModel(at:)` accepting a `.mlpackage` directory, not just a
  `.mlmodel` file.** High confidence based on documented Apple behavior (this is
  the whole reason the API exists for post-install models); not exercised by an
  actual compile anywhere in this session.
- **Whether Apple Devices' (Windows) File Sharing pane correctly preserves a
  dragged-in `.mlpackage` *folder's* internal structure**, as opposed to a single
  file. Unverified either way — this is exactly why the transfer instructions
  above use a **zip + native iOS Files extract** instead of a raw folder drag,
  sidestepping the question rather than depending on an answer to it.
- **The pose model's exact Core ML input feature name and type** (Ultralytics'
  native `format="coreml"` export with `nms=True`). Not guessed: `ModelRunner`
  builds its dummy input generically from `model.modelDescription`, so whatever
  the real name/type turns out to be, the harness should still construct a valid
  input for it. If it does not — if the pose export uses an input feature type
  this harness's `dummyInput(for:)` doesn't handle (see the `unsupportedFeature`
  cases in `ModelRunner.swift`) — the app will report a clear "unsupported model
  feature" error for that model rather than crash, and that error is itself a
  useful finding to report back.
- **`xcodebuild -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO`
  producing a `.app` at `build/Build/Products/Release-iphoneos/LatencyHarness.app`.**
  Believed correct (a commonly documented pattern for unsigned device builds) but
  not run. The packaging step in the workflow checks this path exists and prints
  the actual directory tree if not, so a wrong guess here fails loudly in the CI
  log rather than producing a silently broken artifact.
- **Which Xcode version `macos-14` currently has installed**, and whether it
  includes the iOS 18 SDK this project's deployment target needs. The workflow
  hedges (prefers an `Xcode_16*.app` if present, else falls through to the
  runner's default) rather than hardcoding a version number nobody here can
  confirm is still there.
- **XcodeGen's `xcodegen generate` producing a working `.xcodeproj` from
  `project.yml`** — not run locally (no `xcodegen` on this Windows machine in
  this session), only reasoned about from the documented spec format.
- **SwiftUI/Swift concurrency specifics** in `ContentView.swift` (a
  `DispatchSemaphore` + `Task` bridge used once, to call the one `async throws`
  Core ML API from otherwise-synchronous background-queue code, specifically to
  avoid actor-isolation complexity that would be even harder to reason about
  without a compiler). `SWIFT_VERSION` is pinned to `5.0` in `project.yml` so
  that any `Sendable`-capture issues in that bridge surface as warnings, not
  build errors — but this has not been compiled anywhere.

## What this is not

No camera capture, no court overlay, no ball tracking, no product UI. Those stay
with the main app work (frontend-dev's other briefs). Nothing here changes
`tools/export_coreml_p0.py`, `docs/STATE.md`, or any ball/speed/score logic.
