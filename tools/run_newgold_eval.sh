#!/usr/bin/env bash
# Score BallNet vs TrackNet on the 3 new gold clips (E3k). No calibration on
# these clips, so the court gate is OFF — a pure detector comparison, exactly
# the yt_match40 cold-clip protocol. frame_step=1 so every labelled frame scores.
# Run from backend/:  bash ../tools/run_newgold_eval.sh
set -u
PY=./.venv-train/Scripts/python.exe
O=../data/output/fps/newgold
mkdir -p "$O"
for clip in gold_shell gold_clay gold_am; do
  for model in tracknet ours; do
    dst="$O/${clip}_${model}.perception.json"
    if [ -f "$dst" ]; then echo "skip $dst"; continue; fi
    echo "=== $clip / $model"
    $PY ../tools/ball_perception.py --video ../data/$clip.mp4 \
        --ball-model $model --device cuda --frame-step 1 \
        --out "$dst" 2>&1 | tail -1
  done
done
echo "ALL PERCEPTION DONE"
