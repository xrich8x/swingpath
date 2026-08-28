"""tools/eval_detector_chain_ab.py must keep reproducing the SHIPPED ball chain.

WHY THIS TEST EXISTS. The chain A/B tool re-implements the post-detector ladder
so it can run it twice on two cached detectors without paying for two full
pipeline runs. A re-implementation is only a measurement of the product while it
stays identical to the product. This project already has a named trap for that
(T15: an eval that drifted from the pipeline it claimed to measure), and there is
a live example in the tree — tools/chain_cache.py's run_chain OMITS
remove_outliers, so the same caches score differently through it.

So this pins two things against pipeline.analyze_video's own source:

  1. ORDER — the sequence of swingvision.ball functions called.
  2. PARAMETERS — the numeric literals each is called with.

It reads the pipeline's source rather than running it because analyze_video
needs a video, a model and a GPU. Source inspection is the only way to assert
"these two ladders agree" for the price of a unit test. If this test fails
because the pipeline was legitimately retuned, the fix is to update the tool and
RE-RUN the A/B — not to relax the test. A stale eval reports the old pipeline's
numbers under the new pipeline's name.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

BALL_FNS = {"remove_outliers", "rectify_track", "suppress_false_locks",
            "gate_ball_to_court", "smooth_forecast"}


def _fn_source(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {path}")


def _ladder(fn: ast.FunctionDef, module_aliases: set[str]):
    """(call name, {kwarg: literal-ish source}) for each ball-chain call, in order."""
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr in BALL_FNS):
            continue
        if not (isinstance(f.value, ast.Name) and f.value.id in module_aliases):
            continue
        kw = {k.arg: ast.unparse(k.value) for k in node.keywords if k.arg}
        out.append((f.attr, kw, node.lineno))
    out.sort(key=lambda t: t[2])
    return [(n, kw) for n, kw, _ in out]


@pytest.fixture(scope="module")
def ladders():
    pipe = _fn_source(REPO / "backend" / "swingvision" / "pipeline.py", "analyze_video")
    tool = _fn_source(REPO / "tools" / "eval_detector_chain_ab.py", "chain")
    return _ladder(pipe, {"ball_mod"}), _ladder(tool, {"B"})


def test_same_stages_in_the_same_order(ladders):
    pipe, tool = ladders
    assert [n for n, _ in pipe] == [n for n, _ in tool], (
        "the A/B tool's ladder no longer matches pipeline.analyze_video's.\n"
        f"  pipeline: {[n for n, _ in pipe]}\n"
        f"  tool:     {[n for n, _ in tool]}"
    )


def test_every_stage_appears_exactly_once(ladders):
    pipe, _ = ladders
    names = [n for n, _ in pipe]
    assert sorted(names) == sorted(set(names)), f"duplicate stage in pipeline: {names}"
    assert set(names) == BALL_FNS, f"pipeline ladder changed shape: {names}"


#: The pipeline literals the tool must mirror. Written out rather than derived so
#: a change to EITHER side fails, instead of both drifting together.
EXPECTED = {
    "remove_outliers": {"max_jump": "0.06"},
    "rectify_track": {"max_speed_px": "3000.0", "resid_px": "35.0"},
    "smooth_forecast": {},
}


def _numbers(src: str) -> list[str]:
    return [t for t in ast.unparse(ast.parse(src, mode="eval")).replace("(", " ")
            .replace(")", " ").replace("*", " ").replace("/", " ").split()
            if t.replace(".", "").isdigit()]


@pytest.mark.parametrize("stage", sorted(EXPECTED))
def test_tuning_constants_match_the_pipeline(ladders, stage):
    pipe, tool = ladders
    p = dict(pipe)[stage]
    t = dict(tool)[stage]
    for arg, literal in EXPECTED[stage].items():
        assert literal in _numbers(p[arg]), (
            f"pipeline.{stage}({arg}=...) no longer contains {literal}; "
            f"it is {p[arg]!r}. Retune the tool and RE-RUN the A/B.")
        assert literal in _numbers(t[arg]), (
            f"eval_detector_chain_ab.{stage}({arg}=...) is {t[arg]!r}, which no "
            f"longer contains the pipeline's {literal}.")


def test_res_scale_is_applied_wherever_the_pipeline_applies_it(ladders):
    """Trap: every pixel threshold scales by frame_height/720 (CLAUDE.md). A tool
    that drops the scaling reports 720p behaviour on 1080p clips."""
    pipe, tool = ladders
    for stage in ("rectify_track",):
        p, t = dict(pipe)[stage], dict(tool)[stage]
        for arg in ("max_speed_px", "resid_px"):
            assert "res_scale" in p[arg], f"pipeline stopped scaling {stage}.{arg}"
            assert "rs" in t[arg] or "res_scale" in t[arg], (
                f"the A/B tool does not scale {stage}.{arg}: {t[arg]!r}")
    for name, kw in tool:
        if name == "suppress_false_locks":
            assert "rs" in kw.get("res_scale", ""), kw


def test_gate_is_conditional_on_a_homography_in_both(ladders):
    """gate_ball_to_court is the only H-dependent stage. Both sides must skip it
    when there is no calibration, or the uncalibrated gold clips would crash
    rather than being scored H-free."""
    for path, fn in ((REPO / "backend" / "swingvision" / "pipeline.py", "analyze_video"),
                     (REPO / "tools" / "eval_detector_chain_ab.py", "chain")):
        src = ast.unparse(_fn_source(path, fn))
        i = src.index("gate_ball_to_court")
        assert "H is not None" in src[max(0, i - 400):i], (
            f"{path.name}:{fn} calls gate_ball_to_court without an H guard")
