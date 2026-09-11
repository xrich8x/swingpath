"""A bare weight name must not mean different things in different directories.

`YOLO("yolo11m-pose.pt")` resolves against the CURRENT WORKING DIRECTORY, and
ultralytics silently DOWNLOADS the checkpoint when it does not find one there. So
the same call read a local file when run from `backend/` and reached for the
network when run from the repo root.

The observable symptom was disk, not behaviour: both directories ended up holding
byte-identical 41 MB and 113 MB copies of the same two checkpoints, one per place
somebody had run a script from (found 2026-09-10 during a repo audit). Deleting a
duplicate without fixing the resolution would have converted a wasted 154 MB into
a silent network fetch — on a project whose standing constraint is that it works
100% offline, and where `tools/p0_3_crop_probe.py` names those weights bare and is
run from the repo root.

WHAT THESE PIN, and the asymmetry is the whole safety argument:

  * a bare name we HAVE becomes an absolute path — the download cannot happen;
  * a bare name we DO NOT have is returned untouched — so the no-local-checkpoint
    behaviour is exactly what it was before, and this resolver can only ever turn
    a download into a local read, never the reverse;
  * an explicit path is never rewritten.

Rule 8: a refactor must prove it changed nothing. `test_an_unknown_name_is_passed_
through_unchanged` is that proof for the only case where behaviour could differ.
"""

import os

import pytest

from swingvision import pose

BARE = [w for w, _ in pose.QUALITY_PRESETS.values()]


def test_every_preset_names_a_bare_filename():
    """If a preset ever gains a path, the resolver stops applying to it and this
    test says so rather than letting the download path come back quietly."""
    for name in BARE:
        assert os.sep not in name and not os.path.isabs(name), name


@pytest.mark.parametrize("name", sorted(set(BARE)))
def test_a_preset_weight_resolves_to_a_real_file_if_we_have_one(name):
    resolved = pose.resolve_weights(name)
    if resolved == name:
        pytest.skip(f"{name} is not present in this checkout")
    assert os.path.isabs(resolved)
    assert os.path.isfile(resolved)
    assert os.path.basename(resolved) == name


def test_resolution_does_not_depend_on_the_working_directory(tmp_path, monkeypatch):
    """THE POINT OF THE MODULE. Same answer from the repo root, from backend/,
    and from an unrelated temp directory."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(pose.__file__)))
    answers = set()
    for cwd in (here, os.path.dirname(here), str(tmp_path)):
        monkeypatch.chdir(cwd)
        answers.add(pose.resolve_weights(BARE[0]))
    assert len(answers) == 1, f"resolution moved with the CWD: {answers}"


def test_an_unknown_name_is_passed_through_unchanged():
    """The no-op proof. A name with no local file must reach ultralytics exactly
    as before, so behaviour where nothing is downloaded yet is unchanged."""
    assert pose.resolve_weights("definitely-not-a-real-model.pt") == (
        "definitely-not-a-real-model.pt")


@pytest.mark.parametrize("path", ["weights/ballnet.pt", "sub/dir/x.pt",
                                  os.path.join(os.sep, "abs", "x.pt")])
def test_an_explicit_path_is_never_rewritten(path):
    assert pose.resolve_weights(path) == path


def test_no_duplicate_pose_checkpoints_remain_on_disk():
    """The audit finding itself, kept as a test so it cannot silently come back.

    Running a script from the repo root used to create a second copy of a 41 MB or
    113 MB checkpoint there. With the resolver in place that no longer happens, so
    a reappearing root-level copy means someone re-introduced a CWD-relative load.
    """
    backend = os.path.dirname(os.path.dirname(os.path.abspath(pose.__file__)))
    repo = os.path.dirname(backend)
    dupes = [n for n in set(BARE)
             if os.path.isfile(os.path.join(repo, n))
             and os.path.isfile(os.path.join(backend, n))]
    assert not dupes, (
        f"pose checkpoints duplicated at the repo root and in backend/: {dupes}. "
        f"Something is loading them relative to the working directory again.")
