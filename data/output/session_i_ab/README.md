# Session I — localised confuser weighting, A/B

Raw JSON from `tools/eval_model_filters.py` and `tools/eval_detector_gold.py`,
scored against human gold clicks. Read with:

```
py tools/gate_verdict.py data/output/session_i_ab/filters_*.json \
    --baseline ballnet_i_base.pt --candidate ballnet_i_conf.pt
```

| file | what |
|---|---|
| `filters_yt_rally2.json` | full chain, 3.31 m camera, 258 ball / 26 no-ball |
| `filters_am_hard_utr.json` | full chain, 1.74 m phone at 1080p, 90 of 175 ball / 24 of 53 no-ball scoreable at step 2 |
| `filters_yt_match40.json` | full chain, 11.33 m broadcast, 184 ball / 24 no-ball |
| `detector_gold.json` | detector only, all 6 gold clips, 1201 ball clicks |
| `v21_*.json` | the shipped `ballnet_v21` through the same chain, for the frame-identity question only — which frames defeat it, not how it was trained |
| `hardcore.json` / `.png` | `inspect_false_locks --stage chain`: what v21's surviving ghosts actually are, classified by eye rather than by adjective |

Both arms are **15-epoch, undertrained by design** and neither is shippable. The
comparison is arm-to-arm only: `ballnet_v21.pt` carries no recipe, so an A/B against
it would confound this change with whatever drifted since.

The verdict and its caveats are written up in
[`docs/sessions/SESSION_I_localised_negatives.md`](../../../docs/sessions/SESSION_I_localised_negatives.md).
