#!/usr/bin/env bash
# E1's headline experiment: hold the FOOTAGE and the DETECTOR fixed, vary only
# the frame rate. yt_rally2 is natively 60 fps and is one of our two
# human-gold-labelled clips, so the same 300 clicks score every condition.
#
# Decimation is done on the ingest stream (the tracker literally sees a 30/24/15
# fps video), so temporal machinery — bgsub, the static-fixture gate, the
# tracker's motion continuity — is exercised at the tested rate, not faked.
#
# Run from backend/:  bash ../tools/run_fps_sweep.sh
set -euo pipefail

PY=./.venv-train/Scripts/python.exe
VID=../data/yt_rally2.mp4
KP=../data/yt_rally2_pts.json
OUT=../data/output/fps
mkdir -p "$OUT"

for model in tracknet wasb; do
  for cond in "60 --frame-step 1" "30 --frame-step 2" "24 --target-fps 24" "15 --frame-step 4"; do
    fps="${cond%% *}"; flag="${cond#* }"
    dst="$OUT/rally2_${model}_${fps}fps.perception.json"
    if [ -f "$dst" ]; then echo "skip $dst"; continue; fi
    echo "=== $model @ ${fps}fps"
    $PY ../tools/ball_perception.py --video "$VID" --ball-model "$model" \
        --device cuda --keypoints "$KP" $flag --out "$dst"
  done
done
