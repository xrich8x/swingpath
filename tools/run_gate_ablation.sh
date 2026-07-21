#!/usr/bin/env bash
# E3e gate ablation: attribute the ~22 points of recall that vanish between the
# detector (ball is the strongest blob on 70.9% of gold frames) and the shipped
# pipeline (49.2%). One run per gate, disabled in isolation; `allopen` bounds
# what every gate costs together.
#
# Run from backend/:  bash ../tools/run_gate_ablation.sh
set -u
PY=./.venv-train/Scripts/python.exe
VID=../data/yt_rally2.mp4
KP=../data/yt_rally2_pts.json
O=../data/output/fps/abl
mkdir -p "$O"

run() {
  local name="$1"; shift
  if [ -f "$O/$name.perception.json" ]; then echo "skip $name"; return 0; fi
  echo "=== $name $*"
  $PY ../tools/ball_perception.py --video "$VID" --ball-model tracknet \
      --device cuda --frame-step 1 --keypoints "$KP" \
      --out "$O/$name.perception.json" "$@" 2>&1 | tail -1
}

run baseline
run nocourt   --no-court-gate
run nostatic  --no-static-gate
run vel200    --velocity-gate 200
run velopen   --velocity-gate 99999
run nobgsub   --no-bgsub
run coast60   --max-coast 60
run allopen   --no-court-gate --no-static-gate --velocity-gate 99999 --max-coast 60
echo "ALL DONE"
