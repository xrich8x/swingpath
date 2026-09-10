# backend-dev - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (2026-09-10) CAN THE CORE ML EXPORT RUN ON LINUX?

Cost question. `.github/workflows/coreml-export.yml` runs on macos-14 = 10x billing
on a private repo (~200 free macOS-min/month). If ubuntu-latest works it is 1x.
Export has NEVER been run; no .mlpackage exists.
The macOS choice was made because the WINDOWS wheel lacks libmilstoragepython /
libcoremlpython -> `RuntimeError: BlobWriter not loaded`. Linux was never tried.

QUESTION: can coremltools on Linux do `ct.convert` AND `mlmodel.save(.mlpackage)`?
Assess BALL (torch.jit.trace + ct.convert + linear_quantize_weights) and POSE
(ultralytics native format="coreml") SEPARATELY - pose may shell out to Apple tooling.

METHOD (suggested, not mandated): pip download the manylinux wheel, unzip, look for
the compiled extensions + the MIL/mlpackage writer path. No CI.

DELIVERABLE: docs/evidence/coreml-export-on-linux.md (verdict per model, confidence,
what could NOT be determined without running). If yes/probably: ADD an ubuntu-latest
workflow_dispatch-only variant. Do NOT touch the macOS workflow.

NOT-THIS-RUN: triggering CI, pushing, committing, editing export_coreml_p0.py or
coreml-export.yml, anything in ios/, docs/STATE.md, ball/speed/score/court work.

## STATE - **TASK COMPLETE.** Verdict YES for BOTH models, high confidence, no CI run.
DELIVERED: docs/evidence/coreml-export-on-linux.md (verdict table, the manylinux1
trap, wheel contents, ultralytics evidence, 5 explicit could-NOT-determine items);
.github/workflows/coreml-export-linux.yml (ubuntu-latest, workflow_dispatch only,
YAML+embedded-python validated, NOT triggered); a SUPERSEDED-IN-PART banner on
docs/evidence/p0-0-coreml-export.md; agent memory coreml-export-runs-on-linux.md.
macOS coreml-export.yml UNCHANGED. Nothing pushed or committed. docs/STATE.md left
to the LEAD (NOT-THIS-RUN). Biggest honest caveat: Linux skips the convert-time
model load that macOS does for the BALL path, so the artifact is less validated.

FINDINGS (do not re-derive):
F1. TRAP: `pip download coremltools --platform manylinux_2_17_x86_64 --python-version
    3.12` silently resolves to **coremltools 4.0b3** (a 2020 py3-none-any wheel) and
    looks like "no Linux wheel". WRONG. The real tag is the ancient `manylinux1`:
    `coremltools-9.0-cp312-none-manylinux1_x86_64.whl`. Use --platform manylinux1_x86_64.
F2. Linux wheel 9.0 SHIPS: libmilstoragepython.so (the BlobWriter that Windows lacked
    -> the actual blocker), libmodelpackage.so (the .mlpackage writer),
    _deps/kmeans1d/_core.cpython-312-x86_64-linux-gnu.so (palettization).
    ABSENT: libcoremlpython.so. That one is macOS-only and is only used to RUN/inspect
    a model: compute_device.py, compute_plan.py, _compiled_model.py, predict.
    coremltools/__init__.py:138 wraps `from . import libcoremlpython` in try/except pass.
    models/model.py:55-58 sets _MLModelProxy=None on failure; _get_proxy_and_spec is
    gated `if _MLModelProxy and not skip_model_load` -> no crash.
F3. MLModel.save() for a package is `shutil.copytree(self.package_path, save_path)` -
    pure Python. The package is built during convert by the two .so files that ARE
    present. So save is not a second risk.
F4. POSE: ultralytics 8.4.75 engine/exporter.py:1050
    `assert not WINDOWS, "CoreML export is not supported on Windows, please run on
    macOS or Linux."` - upstream explicitly blesses Linux.
F5. POSE GOTCHA A: our task is "pose", not "detect". exporter.py:1067-1070 -> nms=True
    is WARNED AND IGNORED for non-detect. So `nms=True` in export_coreml_p0.py is a
    NO-OP; pipeline_coreml (the riskiest Apple-ish path) never runs. Exported pose
    .mlpackage has NO built-in NMS -> on-device NMS is mine to write. Report it.
F6. POSE GOTCHA B (silent-corruption risk): exporter.py wraps `ct_model.save(f)` in
    try/except and on failure SILENTLY falls back to `.mlmodel`. export_coreml_p0.py
    then os.rename()s whatever came back to `*.mlpackage` -> a legacy protobuf FILE
    wearing a .mlpackage name. The new workflow MUST verify each output is a DIRECTORY
    containing Manifest.json. Do not modify the script (NOT-THIS-RUN); guard in CI.

## LOG
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.
- Confirmed blocker on Windows is BlobWriter (libmilstoragepython), per
  docs/evidence/p0-0-coreml-export.md. libcoremlpython is only needed to RUN a model
  (prediction/compute-plan), not to SAVE one -> may be irrelevant to export.

## DONE-PREV (2026-09-09 task 6, COMPLETE - do not redo)
Pool 20->16 strict ruling: eval/run_refs.py EXCLUDED_CLIPS, backend/tests/
test_refs_pool_strict16.py (13 tests), docs/evidence/pool-strict-16.md. Suite 706.
