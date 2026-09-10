# Can the Core ML export run on Linux instead of macOS? — YES, both models (2026-09-10)

> Cost question, answered **without running any CI**, by downloading and inspecting the
> actual `coremltools` Linux wheel and reading the installed `ultralytics` exporter.
> Companion to [`p0-0-coreml-export.md`](p0-0-coreml-export.md), which recorded the
> **Windows** failure. Linux had never been tried.

## Verdict

| Model | Path | Verdict on `ubuntu-latest` | Confidence |
| --- | --- | --- | --- |
| **Ball** (`BallNet v21`) | `torch.jit.trace` → `ct.convert` → `linear_quantize_weights` → `mlmodel.save(.mlpackage)` | **Yes** | High |
| **Pose** (`yolo11m-pose`) | `ultralytics` native `format="coreml"` | **Yes** | High |

Neither model needs macOS to *produce* a `.mlpackage`. The cheap path is worth trying
first. **What macOS still buys is a validation side-effect, not the export** — see
"What I could not determine" below, which is the honest cost of the cheap path.

Cost: `macos-14` bills **10x** on a private repo (~200 usable macOS-minutes of the free
2,000/month). `ubuntu-latest` bills **1x**. A failed Linux attempt costs a few minutes;
a macOS attempt costs ten times that whether it succeeds or not.

---

## 1. The Windows failure was never a statement about Linux

`p0-0-coreml-export.md` recorded the exact blocker: `RuntimeError: BlobWriter not
loaded`. The Windows wheel of `coremltools==9.0` is **pure Python** — confirmed again
here against the copy installed in `backend/.venv`:

```
find backend/.venv/Lib/site-packages/coremltools -maxdepth 2 \( -name "*.pyd" -o -name "*.so" -o -name "*.dll" \)
# -> zero results
```

Two compiled extensions are needed to *write* a modern `.mlpackage`:

- `libmilstoragepython` — the `BlobWriter`/`BlobReader` that serializes an `mlprogram`'s
  weight blob. **This is the thing that failed on Windows.**
- `libmodelpackage` — the `ModelPackage` writer that builds the `.mlpackage` bundle.

A third, `libcoremlpython`, wraps Apple's `CoreML.framework`. It is genuinely macOS-only.

## 2. The Linux wheel ships both writers

### 2a. A trap that would have produced a false NEGATIVE

The obvious command **silently lies**:

```bash
pip download coremltools --no-deps --only-binary=:all: \
    --platform manylinux_2_17_x86_64 --python-version 3.12 -d tmp
# -> Saved coremltools-4.0b3-py3-none-any.whl      (a 2020 pure-Python beta!)
```

Forcing the version reveals why: `ERROR: Could not find a version that satisfies the
requirement coremltools==9.0 (from versions: 4.0b3)`. coremltools does not use the
modern `manylinux_2_17` tag — it publishes under the **ancient `manylinux1`** tag.
Anyone who ran the obvious command and stopped would have concluded "no Linux wheel"
and kept paying 10x. From the PyPI JSON for 9.0:

```
coremltools-9.0-cp310-none-manylinux1_x86_64.whl
coremltools-9.0-cp311-none-manylinux1_x86_64.whl
coremltools-9.0-cp312-none-manylinux1_x86_64.whl   <-- the one CI would install
coremltools-9.0-cp313-none-manylinux1_x86_64.whl
```

Note the `cp312` interpreter tag with `none` ABI: version-specific compiled extensions,
not a pure-Python `py3-none-any`. The correct command is:

```bash
pip download coremltools --no-deps --only-binary=:all: \
    --platform manylinux1_x86_64 --python-version 3.12 -d tmp
```

**x86_64 only.** There is no `aarch64` Linux wheel at any version. `ubuntu-latest` is
x86_64, so this is fine — but an `ubuntu-24.04-arm` runner would fail. Do not "optimise"
the runner label to an ARM one.

### 2b. What is actually inside it

Unzipping `coremltools-9.0-cp312-none-manylinux1_x86_64.whl`:

```
coremltools/libmilstoragepython.so                              <-- the Windows blocker, PRESENT
coremltools/libmodelpackage.so                                  <-- the .mlpackage writer, PRESENT
coremltools/_deps/kmeans1d/_core.cpython-312-x86_64-linux-gnu.so <-- palettization kernel
```

Absent: `libcoremlpython.so`. That is the only one missing, and it is not on the export
path.

### 2c. The missing one is only used to RUN a model, never to save one

Every import site of `libcoremlpython` in the wheel is a load/predict/inspect path —
`models/compute_device.py`, `models/compute_plan.py`, `models/_compiled_model.py`,
`models/model.py`'s `_MLModelProxy` (prediction), and
`models/ml_program/experimental/compute_plan_utils.py`. None of them is reached by
`ct.convert(...)` + `save(...)`.

Its absence is handled, not fatal:

- `coremltools/__init__.py:138` wraps `from . import libcoremlpython` in a bare
  `try/except: pass`. Importing coremltools on Linux works.
- `models/model.py:55-58` catches the `ImportError`, logs a warning and sets
  `_MLModelProxy = None`.
- `MLModel._get_proxy_and_spec` is gated `if _MLModelProxy and not skip_model_load:` and
  otherwise falls through to `return None, specification, None`. Clean degradation, no
  exception.
- `optimize/coreml/_post_training_quantization.py:632` passes
  `skip_model_load=mlmodel.__proxy__ is None` — the quantization path **auto-adapts** to
  the no-proxy case. This is upstream deliberately accommodating non-macOS, not luck.

### 2d. `save()` is not a second risk

The brief's worst case was "conversion succeeds but `.mlpackage` serialization fails".
For a package, `MLModel.save()` (`models/model.py:693`) is:

```python
_shutil.copytree(self.package_path, save_path)
```

Pure Python. The bundle was already built during `ct.convert` by the two `.so` files that
**are** present (`converters/mil/converter.py:234` → `_create_mlpackage` → `ModelPackage`,
and `converters/mil/backend/mil/load.py:53` → `BlobWriter`). If conversion completes on
Linux, the save is a directory copy. The two halves do not fail independently.

### 2e. Upstream asserts this in an executable test

`coremltools/test/api/test_api_visibilities.py` (shipped inside the wheel):

```python
EXPECTED_MODULES = [... "libcoremlpython", ... "libmodelpackage", "libmilstoragepython", ...]

def test_top_level(self):
    if not ct.utils._is_macos():
        EXPECTED_MODULES.remove("libcoremlpython")
    _check_visible_modules(_get_visible_items(ct), EXPECTED_MODULES)
```

On non-macOS, upstream removes **only** `libcoremlpython` from the expected set and still
asserts the other two are importable. That is Apple stating, in code they run, that the
two extensions we need exist off macOS.

## 3. The pose half, assessed separately

The pose export goes through `ultralytics`, which is a separate risk — it could have
shelled out to Apple-only tooling. It does not. From `ultralytics` 8.4.75 (the version
installed here; `requirements-ml.txt` pins only `ultralytics>=8.3`):

`engine/exporter.py:1050`

```python
assert not WINDOWS, "CoreML export is not supported on Windows, please run on macOS or Linux."
```

Upstream names **Linux explicitly as a supported platform** for Core ML export. It is the
only platform gate in `export_coreml`. And in `utils/export/coreml.py:205-209`,
`torch2coreml` hard-codes:

```python
convert_kwargs = dict(..., convert_to="mlprogram", skip_model_load=True)
```

`skip_model_load=True` means ultralytics never asks coremltools to load the model into
the Core ML runtime — the one operation that needs the macOS-only extension. The pose
path avoids it **structurally**, on every platform.

The `int8` arm calls `coremltools.optimize.coreml.palettize_weights` with
`OpPalettizerConfig(mode="kmeans", nbits=8)`, which needs `scikit-learn` (ultralytics
auto-installs it) and coremltools' `kmeans1d` kernel — which is the third `.so` in the
Linux wheel. Covered.

### Two pose findings that are platform-independent but worth recording

These are **not** Linux problems. They are true of the existing macOS workflow too, and
they surfaced only because this audit read the exporter. Neither is fixed here —
`tools/export_coreml_p0.py` was out of scope for this run.

- **`nms=True` is a silent no-op for a pose model.** `exporter.py:1067-1070` warns
  `"'nms=True' is only available for Detect models"` and ignores it for any non-detect
  task, so `pipeline_coreml` never runs. The exported pose `.mlpackage` has **no built-in
  NMS**; NMS must be done on-device in our pipeline. Good news for portability (the NMS
  pipeline builder was the most Apple-flavoured code in the path), but it means the
  handoff to the on-device pose stage is one stage larger than the script's arguments
  imply.
- **`ct_model.save()` in ultralytics has a silent `.mlmodel` fallback.**
  `utils/export/coreml.py` and `exporter.py:1119-1125` catch a failed `.mlpackage` save
  and re-save as a legacy `.mlmodel`, returning that path.
  `tools/export_coreml_p0.py:87-91` then `os.rename`s whatever came back onto a
  `*.mlpackage` name. A silent degradation would therefore ship a legacy protobuf **file**
  wearing a `.mlpackage` name — exactly the "worst outcome" this investigation was asked
  to rule out, and it would be invisible in the log. The new workflow therefore
  **verifies every output is a directory containing `Manifest.json`** rather than trusting
  the exit code. Apply the same check to any macOS run.

## 4. Two install hazards the Linux workflow must handle (the macOS one does not)

- **torch.** On Linux x86_64, plain `pip install torch` pulls the **CUDA** build plus
  several GB of `nvidia-*` wheels. On `macos-14` (arm64) the PyPI wheel is CPU-only and
  small, which is why the existing workflow gets away with it. The Linux workflow
  installs from `https://download.pytorch.org/whl/cpu` — which is what
  `backend/requirements-ml.txt`'s own header comment already instructs.
- **numpy.** `exporter.py:1046` calls
  `check_requirements(["coremltools>=9.0", "numpy>=1.14.5,<=2.3.5"])` because
  **numpy 2.4.x breaks coremltools Core ML export** (apple/coremltools#2633). A fresh
  install today resolves numpy to 2.5.x (2.5.0 is what is in `backend/.venv`).
  `check_requirements` would pip-install a downgrade *mid-run*, which does **not** affect
  the numpy already imported into the running process. The workflow pins `numpy<=2.3.5`
  at install time. **This hazard applies to `macos-14` identically** and is a plausible
  reason a first macOS run would have burned 10x minutes and failed anyway.

## 5. What I could NOT determine without running it

Stated plainly, because the point of this document is that nobody re-derives it.

1. **Execution was never performed.** All of the above is artifact inspection and source
   reading on a Windows machine. I did not run `ct.convert` on Linux. The `.so` files
   were listed, not loaded — `manylinux1` is glibc 2.5, far below `ubuntu-latest`'s 2.39,
   so ABI compatibility is expected, but "expected" is not "observed".
2. **The Linux artifact is less validated than a macOS artifact would be, and this is the
   real cost of the cheap path.** For the **ball** model, `tools/export_coreml_p0.py`
   calls `ct.convert` without `skip_model_load`, so it defaults to `False`. On macOS that
   makes coremltools actually load the produced model into the Core ML runtime — a free
   smoke test that catches a malformed graph at export time. On Linux `_MLModelProxy` is
   `None`, that check is skipped, and the first real validation moves to Xcode on the
   phone. For the **pose** model this changes nothing, since ultralytics sets
   `skip_model_load=True` on every platform — pose is unvalidated at export on macOS too.
3. **Bit-identity between a Linux-produced and a macOS-produced `.mlpackage` is not
   established** and should not be assumed. The pose `int8` arm runs k-means
   palettization via scikit-learn; clustering is not guaranteed to be
   platform-invariant. If a Linux export and a macOS export are ever compared, treat them
   as two arms of an uncontrolled A/B, not as the same artifact.
4. **Runner disk and wall-clock are unmeasured.** The workflow keeps the existing
   `df -h /` probes so the first run reports them.
5. **ANE dispatch is untouched by any of this.** It was never measurable off-device and
   still needs Xcode's Core ML Performance Report on a physical A13. Nothing here changes
   `p0-0-coreml-export.md` on that point.

## 6. What was done

Added `.github/workflows/coreml-export-linux.yml` — `workflow_dispatch` only,
`ubuntu-latest`, artifact name `coreml-export-linux` (distinct, so the two paths can
never be confused after download).

**`.github/workflows/coreml-export.yml` (macOS) is unchanged and remains the known-good
fallback.** Its header comment preserves the Windows history and should not be edited.
Try Linux first; if it fails, run the macOS job and attach its log here.

Neither workflow has been triggered. No `.mlpackage` exists yet, on any platform.
