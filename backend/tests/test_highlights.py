"""Per-rally clips: the boundary maths, and the one property that must hold.

Cutting is I/O; the part that can be silently wrong is the arithmetic around it.
The load-bearing property is that a clip NEVER starts after the rally's first
contact — if it does, the clip opens with the point already under way, which is
exactly the failure the pre-pad and the keyframe-snap direction exist to prevent.

Ranking is pinned too, because it is duplicated in the dashboard: if the CLI and
the UI disagreed about which rally was the best, nothing in the product would
surface the contradiction.
"""

import json
import os
import shutil
import subprocess

import pytest

from swingvision import highlights as hl


def _match():
    """Three rallies: a long one, a fast one, and one at t=0 against the edge."""
    return {
        "video": {"filename": "m.mp4", "fps": 30.0, "width": 1280,
                  "height": 720, "duration_s": 60.0},
        "shots": [
            {"id": 1, "speed_kmh": 60.0}, {"id": 2, "speed_kmh": 65.0},
            {"id": 3, "speed_kmh": 70.0}, {"id": 4, "speed_kmh": 120.0},
            {"id": 5, "speed_kmh": 200.0, "speed_confident": False},
            {"id": 6, "speed_kmh": 80.0},
        ],
        "rallies": [
            {"id": 0, "start_s": 1.0, "end_s": 4.0, "shot_ids": [1]},
            {"id": 1, "start_s": 10.0, "end_s": 20.0, "shot_ids": [2, 3, 4]},
            {"id": 2, "start_s": 30.0, "end_s": 59.5, "shot_ids": [5, 6]},
        ],
    }


# --- bounds -----------------------------------------------------------------

def test_clip_starts_before_the_first_contact():
    """THE property. The pre-pad is what makes a clip watchable: rally.start_s is
    the first CONTACT, so cutting there opens mid-swing."""
    for r in _match()["rallies"]:
        start, _ = hl.clip_bounds(r, 60.0)
        assert start <= r["start_s"], r


def test_clamps_at_the_start_of_the_video():
    start, _ = hl.clip_bounds({"start_s": 1.0, "end_s": 4.0}, 60.0)
    assert start == 0.0, "asked ffmpeg to seek before the file begins"


def test_clamps_at_the_end_of_the_video():
    _, end = hl.clip_bounds({"start_s": 30.0, "end_s": 59.5}, 60.0)
    assert end == 60.0, "asked ffmpeg for time past the end of the file"


def test_unknown_duration_does_not_clamp_the_end():
    _, end = hl.clip_bounds({"start_s": 30.0, "end_s": 59.5}, None)
    assert end == pytest.approx(59.5 + hl.POST_PAD_S)


def test_bounds_never_invert():
    start, end = hl.clip_bounds({"start_s": 80.0, "end_s": 90.0}, 10.0)
    assert end >= start


# --- ranking ----------------------------------------------------------------

def test_longest_rally_ranks_first():
    ranked = hl.rank_rallies(_match())
    assert ranked[0]["rally_id"] == 1 and ranked[0]["rank"] == 1


def test_ranking_ignores_unconfident_speeds_like_the_dashboard():
    """Rally 2 holds a 200 km/h shot flagged unconfident. If it counted, rally 2
    would outrank rally 1 on speed — and the UI, which filters the same way,
    would disagree with the reel."""
    top = {r["rally_id"]: r for r in hl.rank_rallies(_match())}
    assert top[2]["top_speed_kmh"] == 80.0


def test_all_unconfident_falls_back_rather_than_reporting_zero():
    m = _match()
    m["shots"] = [{"id": 9, "speed_kmh": 99.0, "speed_confident": False}]
    m["rallies"] = [{"id": 0, "start_s": 0.0, "end_s": 2.0, "shot_ids": [9]}]
    assert hl.rank_rallies(m)[0]["top_speed_kmh"] == 99.0


def test_ranking_is_deterministic_on_ties():
    m = _match()
    for i, r in enumerate(m["rallies"]):
        r["shot_ids"], r["start_s"], r["end_s"] = [1], 0.0, 1.0
    order = [r["rally_id"] for r in hl.rank_rallies(m)]
    assert order == sorted(order), "tied rallies must fall back to a stable key"


def test_every_ranked_rally_explains_itself():
    for r in hl.rank_rallies(_match()):
        assert r["why"] and "shot" in r["why"]


def test_top_n_truncates():
    assert len(hl.rank_rallies(_match(), top_n=2)) == 2


# --- cutting (needs the bundled ffmpeg) -------------------------------------

def _make_video(path, seconds=14, gop=30):
    """`gop` is the keyframe interval in FRAMES at 30 fps. It is a parameter
    because the truncation bug below only bites when the keyframe spacing exceeds
    the post-pad — at gop=30 (1 s) even the broken code looked correct."""
    ff = hl.ffmpeg_exe()
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", f"testsrc=size=320x180:rate=30:d={seconds}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", str(gop), str(path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.mark.skipif(hl.ffmpeg_exe() is None, reason="bundled ffmpeg unavailable")
def test_cuts_clips_and_writes_a_manifest(tmp_path):
    src = tmp_path / "src.mp4"
    _make_video(src)
    m = _match()
    m["video"]["duration_s"] = 12.0
    m["rallies"] = [{"id": 0, "start_s": 3.0, "end_s": 5.0, "shot_ids": [1]},
                    {"id": 1, "start_s": 7.0, "end_s": 9.0, "shot_ids": [2, 3]}]

    out = tmp_path / "rallies"
    man = hl.cut_clips(str(src), m, str(out))

    assert len(man["clips"]) == 2 and all(c["ok"] for c in man["clips"])
    for c in man["clips"]:
        assert (out / c["file"]).stat().st_size > 0
    written = json.loads((out / "highlights.json").read_text(encoding="utf-8"))
    assert written["clips"] == man["clips"]


def test_snap_picks_the_last_keyframe_at_or_before():
    keys = [0.0, 5.0, 10.0, 15.0]
    assert hl.snap_to_keyframe(12.4, keys) == 10.0
    assert hl.snap_to_keyframe(10.0, keys) == 10.0, "exactly on a keyframe"
    assert hl.snap_to_keyframe(0.0, keys) == 0.0
    assert hl.snap_to_keyframe(-1.0, keys) is None
    assert hl.snap_to_keyframe(5.0, []) is None


@pytest.mark.skipif(hl.ffmpeg_exe() is None, reason="bundled ffmpeg unavailable")
def test_keyframes_are_enumerable(tmp_path):
    src = tmp_path / "src.mp4"
    _make_video(src)
    keys = hl.keyframe_times(str(src))
    assert len(keys) >= 2 and keys[0] == pytest.approx(0.0)
    assert keys == sorted(keys)


@pytest.mark.skipif(hl.ffmpeg_exe() is None, reason="bundled ffmpeg unavailable")
def test_clip_contains_the_whole_rally_including_its_end(tmp_path):
    """THE regression. Asking ffmpeg for a time and letting it snap looks right
    and is not: with `-ss` before `-i`, `-t` counts from the KEYFRAME, so a snap
    of dt slides the whole window back and lops dt off the END. With a 1 s
    keyframe interval and a rally that starts just after one, the first cut of a
    real match was losing the finish of short points. Cutting ON a keyframe makes
    both edges exact."""
    # COARSE keyframes (5 s), matching the real clip that exposed this. At 1 s
    # spacing the broken code still covered the rally, so a fine-GOP fixture
    # would pass either way and prove nothing.
    src = tmp_path / "src.mp4"
    _make_video(src, gop=150)
    m = _match()
    m["video"]["duration_s"] = 14.0
    # start_s deliberately lands mid-GOP so a naive seek must snap backwards.
    m["rallies"] = [{"id": 0, "start_s": 5.6, "end_s": 7.4, "shot_ids": [1]}]

    c = hl.cut_clips(str(src), m, str(tmp_path / "out"))["clips"][0]
    assert c["ok"]
    assert c["start_s"] <= c["rally_start_s"], "clip opens inside the rally"
    assert c["end_s"] >= c["rally_end_s"], "clip ends before the rally does"
    assert c["lead_in_s"] >= 0


@pytest.mark.skipif(hl.ffmpeg_exe() is None, reason="bundled ffmpeg unavailable")
def test_every_clip_of_a_dense_match_contains_its_rally(tmp_path):
    """Swept across offsets, because the failure depends on where a rally falls
    relative to the keyframe grid — one lucky rally proves nothing."""
    src = tmp_path / "src.mp4"
    _make_video(src, gop=150)
    m = _match()
    m["video"]["duration_s"] = 14.0
    m["rallies"] = [{"id": i, "start_s": 2.0 + i * 0.37,
                     "end_s": 2.0 + i * 0.37 + 0.9, "shot_ids": [1]}
                    for i in range(12)]

    for c in hl.cut_clips(str(src), m, str(tmp_path / "out"))["clips"]:
        assert c["ok"], c
        assert c["start_s"] <= c["rally_start_s"] and c["end_s"] >= c["rally_end_s"], c


@pytest.mark.skipif(hl.ffmpeg_exe() is None, reason="bundled ffmpeg unavailable")
def test_a_rally_with_no_shots_is_skipped_not_cut(tmp_path):
    src = tmp_path / "src.mp4"
    _make_video(src)
    m = _match()
    m["video"]["duration_s"] = 12.0
    m["rallies"] = [{"id": 0, "start_s": 3.0, "end_s": 5.0, "shot_ids": []}]
    man = hl.cut_clips(str(src), m, str(tmp_path / "out"))
    assert man["clips"][0]["skipped"] and not man["clips"][0].get("ok")


@pytest.mark.skipif(hl.ffmpeg_exe() is None, reason="bundled ffmpeg unavailable")
def test_reel_concatenates_the_top_clips(tmp_path):
    src = tmp_path / "src.mp4"
    _make_video(src)
    m = _match()
    m["video"]["duration_s"] = 12.0
    m["rallies"] = [{"id": 0, "start_s": 2.0, "end_s": 4.0, "shot_ids": [1]},
                    {"id": 1, "start_s": 6.0, "end_s": 9.0, "shot_ids": [2, 3, 4]}]
    out = tmp_path / "out"
    man = hl.cut_clips(str(src), m, str(out), reel=True, top_n=2)
    assert man["reel"] == "highlights.mp4"
    assert (out / "highlights.mp4").stat().st_size > 0
    assert not (out / "_reel.txt").exists(), "concat list left behind"
