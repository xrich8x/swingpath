# Ground truth & labelling — CLOSED

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
| **A burned-in SCOREBOARD as ground truth for points/rallies** | Built an OCR scoreboard reader | **BUILT, THEN REJECTED ON THE PREMISE** and reverted (`afffb5a`). It is somebody's data entry, not the court. **Hard rule 12. Do not rebuild** | - | [using-a-burned-in-scoreboard-as-ground](../evidence/using-a-burned-in-scoreboard-as-ground.md) |
| **Telling labellers the rule instead of enforcing it** | Documented the labelling rule | **MEASURED NEGATIVE.** Enforce in the tool, not in the instructions | - | [telling-labellers-the-rule-instead-of-enforcing](../evidence/telling-labellers-the-rule-instead-of-enforcing.md) |
| **Filling far-court labels by interpolating between anchors** | Interpolate between confident locks | **MEASURED NEGATIVE** - the anchors bracketing the gaps were themselves false locks | - | [filling-far-court-labels-by-interpolating-between](../evidence/filling-far-court-labels-by-interpolating-between.md) |
| **Finding burned-in graphics by any temporal statistic** | Three temporal detectors | **All three fail on this footage, in both directions** | - | [finding-burned-in-graphics-by-any-temporal](../evidence/finding-burned-in-graphics-by-any-temporal.md) |
| **Dead-time 'silence' negatives** | Mine negatives from dead time | **The wrong negatives** - confusers are not silence | - | - |
| **Trusting a tool's own docstring for whether it has been RUN** | Read the docstring | **STALE, twice** (T24). `eval/movers.py` and `eval/candidate_audit.py` both claimed UNRUN while STATE rows already carried their results. Cost: the lead told the founder an idea was untested | - | - |
