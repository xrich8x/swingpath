# v2/ — the shelf

**Everything here works. None of it is in v1 scope. Do not build on it, do not import from it, and
do not delete it.**

Shelved 2026-09-11 by the founder audit. The rule that put things here: *"anything that doesn't serve
this target, shelve it into a different folder for v2."* The target is `docs/SPEC.md`.

**Shelved is not dead.** Dead work — things that were *tried and failed* — is deleted, with the
verdict recorded in the relevant `docs/<pillar>/CLOSED.md`. This folder is the other category: code
that does what it says, aimed at a product we are not building yet.

## What is here

| | Why it is shelved |
| --- | --- |
| `mobile/` | The ONNX / React-Native port: TrackNet exported to int8 with argmax baked into the graph, the ball decoder and the whole line-call brain ported to JS, verified bit-identical against Python two ways. **Wrong runtime, not wrong code** — v1 is iPhone-only on the Neural Engine, and this targets onnxruntime-react-native / NNAPI. **`live_calls.js` is the best prior art in the repo for the Swift port**: it is proof the call logic moves to another language cleanly, first pass. Read it before writing the Swift. |

## Deferred IN PLACE — not moved, because moving them breaks the build

These are out of v1 scope but still wired into `pipeline.py` and `run.py`. Extracting them is a
refactor with its own test proof (hard rule 9), not a file move, so they stay where they are and are
listed here instead. **Out of scope means do not extend them.**

| Code | Status |
| --- | --- |
| `backend/swingvision/pose.py` + `backend/yolo11m-pose.pt` | **All pose is out of v1** (`SPEC.md` §9, tossed). 50 references in `pipeline.py`. The other four YOLO checkpoints were deleted — 185 MB, and `yolo11x-pose` was measured NEGATIVE for the far player. |
| `backend/swingvision/events.py::classify_shot` | Shot type. Needs pose. Never had an accuracy number — **the only named feature in this project that was never measured.** |
| `backend/swingvision/scoring.py` | Match scoring. **CUT, not deferred.** Constructed directly at `pipeline.py:227` and `:2079`. |
| `backend/swingvision/highlights.py`, `corrections.py` | Rally clips and the correction UI. **CUT, not deferred.** Reached via `run.py highlights` / `run.py correct`. |
| `backend/swingvision/annotate.py` | Skeleton overlay render. Needs pose. |
| `backend/swingvision/speedspin.py` | Its physics is v1 (`SPEC.md` §5), but its **hit-vs-bounce split uses player proximity**, which is pose. That split needs replacing with a trajectory-based one before v1 can use it. |
| `frontend/` Review + Rallies tabs | Render corrections and rally clips. |

`ball_physics/` is **NOT shelved** — drag+Magnus trajectory fitting is v1 §5, and it is the only 3D
machinery in the repo. Its dead halves (a duplicate second TrackNet, an untrained spin net, three
demo scripts) were deleted; see `docs/platform/CLOSED.md` and `docs/ball/CLOSED.md`.

## Bringing something back

1. Check `docs/SPEC.md` — is it still listed under "v2, do not let these creep in"?
2. Check the pillar's `CLOSED.md` — was a version of it already measured and killed?
3. Pre-register a bar before writing code (hard rule 2).
