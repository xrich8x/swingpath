# Speed, line calls & measurement — CLOSED

**Things tried here that did NOT work, and the number that killed each one.**

Read this before proposing anything in this area. Hard rule 3: **do not re-propose these.** Nine
distinct ideas in this project have been re-proposed at least once, each costing a run to re-kill.

**The code is gone, not lost.** Where a row names a deleted file, recover it with:

```bash
git log --diff-filter=D --oneline -- <path>     # find the commit that removed it
git show <sha>^:<path>                          # print the file as it last existed
```

A row here is a verdict. The mechanism and the war story live in `docs/evidence/`.

| What was tried | What we did | The result that killed it | Deleted code | Evidence |
|---|---|---|---|---|
| **Using the SwingVision HUD as a speed reference** | OCR the burned-in MPH panel, compare | **CAPPED, NOT EXTENDED.** A 'HUD MAE' is **agreement with another estimator, not accuracy**. Hard rule 12 bars new ones; `tools/synth_truth.py` is the only absolute reference | `tools/hud_ocr.py, tools/hud_compare.py` | - |
| **`scale_ok` as a speed-confidence gate** | Gate speeds on the metre/pixel scale | **The gate hid the MORE accurate speeds.** Always test whether a gate predicts error before shipping it | `tools/speed_confidence.py` | [speed-confidence-vs-hud](../evidence/speed-confidence-vs-hud.md) |
| **Bias-correcting the -15% speed gap** | Scale speeds up to match radar | **Not a bug - do not correct it.** Speed is *average* ball speed over the shot; radar catches the peak just off the racquet. Drag is **-21.7%** against synth truth | - | [synthetic-ground-truth](../evidence/synthetic-ground-truth.md) |
| **Per-frame false-fire as the product metric** | Optimise per-frame false-alarm rate | **Not the product.** Pick on ghost-ball + `event_audit`; 'phantom speed' vs the HUD is identically zero and was dropped | - | [per-frame-false-fire-is-not-the-product](../evidence/per-frame-false-fire-is-not-the-product.md) |
