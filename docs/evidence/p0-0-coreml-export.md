# P0-0 — Core ML export needs macOS, not just the measurement (found 2026-08-27)

> Evidence for the `coreml-export-requires-macos` row in [docs/STATE.md](../STATE.md)
> (Open). The pm-agent iOS plan's P0-0 handoff assumed the export step (producing
> `.mlpackage` files) could run anywhere and only the Xcode measurement needed a Mac.
> **That assumption is wrong** — the export step itself is blocked on this Windows
> machine, before any measurement question is reached.

## What was attempted

`tools/export_coreml_p0.py` — traces `BallNet` (v21 weights) with `torch.jit.trace`
and converts with `coremltools.convert(..., minimum_deployment_target=ct.target.iOS18)`
to the modern `.mlpackage`/`mlprogram` format; exports `yolo11m-pose` at 1280/640/384
via ultralytics' native `format="coreml"` path. The script is correct and complete —
run it on macOS and it should work as written.

## What happened

`coremltools==9.0`'s PyPI wheel for Windows is **pure Python**. The compiled native
extensions it ships for macOS — `libcoremlpython` (loads/runs an `MLModel`,
compute-plan inspection, compute-unit queries) and `libmilstoragepython` (the
`BlobWriter`/`BlobReader` that serializes an `mlprogram`'s weights) — are **absent**.
Every import prints `Failed to load ... No module named 'coremltools.lib*python'`.

The MIL graph conversion itself succeeds (frontend trace → MIL ops → the optimization
passes all run fine — this is pure Python). It fails at the last step, writing the
binary weights blob:

```
RuntimeError: BlobWriter not loaded
```

**Diagnostic, not a fix:** the legacy `convert_to="neuralnetwork"` format — which
embeds weights directly in the protobuf instead of a separate blob, so it never calls
`BlobWriter` — **does export successfully on Windows** (confirmed: BallNet v21 traced
and converted to a 1.9 MB `.mlmodel` with no errors). This is not usable as the P0-0
deliverable: it predates the modern ANE compute-unit API pm-agent's plan specifies
(`computeUnits = .cpuAndNeuralEngine`), it has no defined behavior for
`minimum_deployment_target=iOS18`, and ultralytics' pose export additionally needs an
NMS pipeline stage that itself depends on the missing `mlprogram` machinery — so even
the diagnostic path doesn't extend to the pose model. It was not saved as an artifact.

## What this means for the plan

**Every session that touches Core ML export or Core ML model inspection needs to run
on macOS.** This is broader than P0-0's own framing ("build the export here, measure
on a Mac") — the export is blocked too, so P0-0 cannot be executed from a Windows
Claude Code session at all, in either half.

This is a **process/tooling constraint to route around, not a project finding** —
it says nothing about the plan's viability, the pose latency question, or ANE dispatch.
It only says where the work has to run.

## What is ready

`tools/export_coreml_p0.py` exists, is logically complete, and needs no changes to run
on macOS — only a working `coremltools` install (`pip install coremltools` on macOS
pulls the full wheel with native extensions). Once it produces the `.mlpackage` files,
the remaining P0-0 steps (Xcode Core ML Performance Report on a physical iPhone 11,
reading per-layer compute-unit assignment) are unchanged from the original brief.
