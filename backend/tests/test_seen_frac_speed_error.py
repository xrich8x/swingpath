"""Pins for `tools/seen_frac_speed_error.py`.

That tool is the sole reproducer for `docs/evidence/does-seen-frac-predict-speed-error.md`
and for qa's rebuild in `docs/evidence/seen-frac-gate-qa-verification.md`. Its whole value
is that it lands on both sets of published digits, so it needs pinning against drift in the
shipped chain it invokes (`ball.smooth_forecast` / `cap_court_jumps` / `smooth_and_fill`,
`calibration.image_to_court`, `analytics.shot_speed_kmh`) or in its own RNG draw order.

The regression pin uses a small `--n 200` single-clip run (a few seconds), not the published
`--n 1200 x 3` configuration; §8.1 of the evidence file carries the full-size reproduction.
"""
import io
import contextlib

import pytest

import seen_frac_speed_error as T


def _run(argv):
    with contextlib.redirect_stdout(io.StringIO()):
        return T.main(argv)


def test_band_boundary_convention_matches_the_gate():
    """0.50 is ACCEPTED by `seen_frac >= 0.5`, so it must land in the HIGH band.

    2.9% of rows in the published run sit exactly on 0.50 (evidence file §8.2), so a
    `<` / `<=` slip here moves a real slice of the sample in the direction that flatters
    the gate. This is the cheap guard against that.
    """
    rows = [{"seen_frac": 0.35, "abs_pct_err": 10.0},   # low band, inclusive edge
            {"seen_frac": 0.49, "abs_pct_err": 30.0},
            {"seen_frac": 0.50, "abs_pct_err": 1.0},    # HIGH band, not low
            {"seen_frac": 0.64, "abs_pct_err": 3.0},
            {"seen_frac": 0.65, "abs_pct_err": 999.0},  # excluded, exclusive edge
            {"seen_frac": 0.34, "abs_pct_err": 999.0}]  # excluded
    b = T.band_ratio(rows)
    assert b["n1"] == 2 and b["n2"] == 2
    assert b["med1"] == pytest.approx(20.0)
    assert b["med2"] == pytest.approx(2.0)
    assert b["ratio"] == pytest.approx(10.0)
    assert b["floor_ok"] is False          # n=2 is under the pre-registered n>=15 floor


def test_verdict_logic_is_the_preregistered_one():
    """G >= 1.5x on >= 2 of 3 clips; N <= 1.1x on >= 2 of 3; floor n>=15 in EACH band.

    The bar is pre-registered and a failed bar stays failed, so the mapping from ratios to
    a verdict letter is pinned rather than left to be re-read off the code.
    """
    def rows_at(ratio, n):
        # med1 = 10*ratio in the low band, med2 = 10 in the high band
        return ([{"seen_frac": 0.40, "abs_pct_err": 10.0 * ratio}] * n
                + [{"seen_frac": 0.55, "abs_pct_err": 10.0}] * n)

    class Cfg:
        gate_g, gate_n = 1.5, 1.1
        min_speed_kmh, max_speed_kmh = -1.0, 1e9

    def verdict(ratios, n=20):
        by_clip = {f"c{i}": rows_at(r, n) for i, r in enumerate(ratios)}
        for rows in by_clip.values():
            for r in rows:
                r["est_kmh"] = 100.0
                r["court_cov"] = 0.5
        return T.analyse(by_clip, Cfg())["unrestricted"]["verdict"]

    assert verdict([1.6, 1.7, 0.9]) == "G"
    assert verdict([1.6, 1.2, 0.9]) == "I"      # only 1 clip at G, only 1 at N
    assert verdict([1.0, 1.05, 1.6]) == "N"
    assert verdict([1.6, 1.7, 0.9], n=10) == "UNDERPOWERED"   # below the n>=15 floor


def test_shipped_runoff_is_still_2_5_metres():
    """The evidence file's harness ran the runoff box at 4.0 m; shipped is 2.5 m.

    As of 2026-09-03 the tool's DEFAULT is the shipped 2.5; `--runoff-m 4.0` reproduces
    the superseded sections 4/5. Its provenance stamp records the shipped value alongside.
    If `pipeline.RUNOFF_M` ever moves, both the default and that stamp become a lie, so
    pin both here.
    """
    import re
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "swingvision" / "pipeline.py").read_text(
        encoding="utf-8")
    m = re.search(r"^\s*RUNOFF_M\s*=\s*([0-9.]+)", src, re.M)
    assert m, "RUNOFF_M no longer found in pipeline.py"
    assert float(m.group(1)) == 2.5

    # ...and the tool defaults to it (changed 2026-09-03; was 4.0, a fidelity defect)
    ns = _parse_defaults()
    assert ns.runoff_m == 2.5


def _parse_defaults():
    """Resolve the tool's argparse defaults without running the experiment."""
    import contextlib
    captured = {}
    real = T.run_clip

    def stub(name, a):
        captured["a"] = a
        raise SystemExit(0)

    T.run_clip = stub
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            with pytest.raises(SystemExit):
                T.main(["--clips", "yt_rally2"])
    finally:
        T.run_clip = real
    return captured["a"]


def test_regression_pin_small_run():
    """Exact-value pin. Seeded, one clip, n=200 — a few seconds.

    If this moves, either the shipped speed chain changed or the harness's RNG draw order
    did; both invalidate the published digits and neither should pass silently.
    """
    # --runoff-m 4.0 is EXPLICIT here: these pinned digits are the superseded
    # sections 4/5 configuration, and the tool now defaults to the shipped 2.5.
    pay = _run(["--n", "200", "--seed", "0", "--clips", "yt_rally2",
                "--runoff-m", "4.0"])
    assert pay["clips"]["yt_rally2"]["n_usable"] == 146
    assert pay["clips"]["yt_rally2"]["hfov_deg"] == pytest.approx(93.7062050970, abs=1e-9)

    b = pay["results"]["unrestricted"]["per_clip"]["yt_rally2"]["band"]
    assert (b["n1"], b["n2"]) == (28, 36)
    assert b["ratio"] == pytest.approx(1.8922451115, abs=1e-9)

    b = pay["results"]["shipped_shot"]["per_clip"]["yt_rally2"]["band"]
    assert (b["n1"], b["n2"]) == (23, 31)
    assert b["ratio"] == pytest.approx(1.2449584517, abs=1e-9)

    # provenance must read the RESOLVED config, not a preset table
    cfg = pay["provenance"]["resolved_config"]
    assert cfg["n"] == 200 and cfg["seed"] == 0 and cfg["clips"] == ["yt_rally2"]
    assert cfg["runoff_m"] == 4.0
    assert pay["provenance"]["shipped_runoff_m"] == 2.5
