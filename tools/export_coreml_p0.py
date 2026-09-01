"""P0-0 — export the pose and ball models to Core ML for the A13 latency measurement.

This produces .mlpackage files only. It does NOT and CANNOT measure on-device
latency or confirm ANE dispatch — that needs Xcode's Core ML Performance Report
running against a physical iPhone 11 (A13), which has no equivalent on this
platform. See docs/evidence/p0-0-coreml-export.md for what to do with the output.

New dependency: coremltools (pip install coremltools). Used only by this script,
same as onnx/onnxruntime are used only by mobile/export_tracknet.py — neither is
declared in a requirements file, following that existing precedent.

Run from repo root: backend/.venv/Scripts/python.exe tools/export_coreml_p0.py
"""

import os
import sys

import coremltools as ct
import torch
from ultralytics import YOLO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from swingvision._ballnet import BallNet

OUT = os.path.join(ROOT, "ios", "coreml_export")
os.makedirs(OUT, exist_ok=True)

# The pose checkpoint is NOT in the repo - `.gitignore`'s `*.pt` excludes it and only
# `ballnet*.pt` is excepted (those are trained in-house and not re-downloadable; this
# one is a stock Ultralytics release asset). A CI runner checks out a fresh tree, so
# hard-coding the local path made the macOS export job fail at the POSE step while
# succeeding at the ball step - and the pose model is the whole reason the job exists.
#
# Fall back to the bare name, which is how ultralytics fetches a stock checkpoint.
# A local run still prefers the file already on disk, so nothing re-downloads here.
_LOCAL_POSE = os.path.join(ROOT, "backend", "yolo11m-pose.pt")
POSE_WEIGHTS = _LOCAL_POSE if os.path.exists(_LOCAL_POSE) else "yolo11m-pose.pt"
BALL_WEIGHTS = os.path.join(ROOT, "backend", "weights", "ballnet_v21.pt")
BALL_W, BALL_H = 512, 288   # BallNet's trained resolution (backend/swingvision/_ballnet.py)
POSE_SIZES = [1280, 640, 384]


def export_ball():
    """BallNet v21: plain nn.Module, no ultralytics export path -> trace + coremltools."""
    ckpt = torch.load(BALL_WEIGHTS, map_location="cpu", weights_only=False)
    sd = ckpt["model_state_dict"]
    motion = any(k.startswith("motion.") for k in sd)
    model = BallNet(motion_attention=motion).eval()
    model.load_state_dict(sd, strict=True)

    example = torch.randn(1, 9, BALL_H, BALL_W)
    traced = torch.jit.trace(model, example)

    for precision, tag in [(ct.precision.FLOAT16, "fp16"), (ct.precision.FLOAT16, "int8")]:
        mlmodel = ct.convert(
            traced,
            inputs=[ct.TensorType(name="frames", shape=(1, 9, BALL_H, BALL_W))],
            outputs=[ct.TensorType(name="heatmap")],
            compute_precision=precision,
            compute_units=ct.ComputeUnit.CPU_AND_NE,
            minimum_deployment_target=ct.target.iOS18,
        )
        if tag == "int8":
            op_config = ct.optimize.coreml.OpLinearQuantizerConfig(mode="linear_symmetric")
            config = ct.optimize.coreml.OptimizationConfig(global_config=op_config)
            mlmodel = ct.optimize.coreml.linear_quantize_weights(mlmodel, config=config)
        path = os.path.join(OUT, f"ballnet_v21.{tag}.mlpackage")
        mlmodel.save(path)
        size_mb = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, fs in os.walk(path) for f in fs
        ) / 1e6
        print(f"exported {os.path.basename(path)}  ({size_mb:.1f} MB, fixed {BALL_W}x{BALL_H})")


def export_pose():
    """yolo11m-pose via ultralytics' native CoreML export — fixed shapes, one per size."""
    for size in POSE_SIZES:
        for int8, tag in [(False, "fp16"), (True, "int8")]:
            model = YOLO(POSE_WEIGHTS)
            out_path = model.export(
                format="coreml", imgsz=size, half=not int8, int8=int8,
                nms=True, dynamic=False, device="cpu",
            )
            dest = os.path.join(OUT, f"yolo11m-pose.{size}.{tag}.mlpackage")
            if os.path.abspath(out_path) != os.path.abspath(dest):
                if os.path.exists(dest):
                    import shutil
                    shutil.rmtree(dest)
                os.rename(out_path, dest)
            size_mb = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(dest) for f in fs
            ) / 1e6
            print(f"exported {os.path.basename(dest)}  ({size_mb:.1f} MB, fixed {size}x{size})")


if __name__ == "__main__":
    print("--- ball model (BallNet v21) ---")
    export_ball()
    print("\n--- pose model (yolo11m-pose) ---")
    export_pose()
    print(f"\nAll .mlpackage files written to {OUT}")
    print("These are NOT benchmarked. Latency and ANE-dispatch confirmation need "
          "Xcode's Core ML Performance Report on a physical iPhone 11 (A13) — "
          "see docs/evidence/p0-0-coreml-export.md.")
