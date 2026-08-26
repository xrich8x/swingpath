# Trimming was the missing first step

> Evidence for the `trimming-was-the-missing-first-step` row in [docs/STATE.md](../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

The Lab could *sample frames from inside* chosen time ranges but never *cut the video*, so an hour of phone footage stayed an hour and every perception pass decoded the warm-up and the breaks. `tools/trim_clip.py` + a Trim control in step 1 of the guided flow. It **re-encodes by default**: with `-ss` before `-i` and `-c copy`, ffmpeg snaps to the keyframe at or before the start, so the clip begins early *and ends early* — the exact bug already found once in the highlights cutter. Verified frame-accurate against the pixels (trim frame 0 == source frame 300 for a 5.0 s start at 60 fps, duration 7.00 s to the frame). `--fast` restores stream copy and says what it trades.
