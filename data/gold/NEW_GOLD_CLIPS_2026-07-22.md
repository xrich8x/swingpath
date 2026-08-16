> **KEEP.** The `.mp4` source files for these gold clips are gitignored, so this is
> the only record of HOW to regenerate them - segment, resolution and codec are
> pinned below. The manifests carry the `video_sha1` to verify a regenerated clip;
> this file carries the recipe.

# New gold test clips (2026-07-22)

Three human-labeled ball TEST clips added to widen the benchmark beyond
yt_rally2 + yt_match40 (both indoor/hard). These are **TEST data — never train on
them** (ML_PRACTICES). Chosen by the user for surface + angle diversity.

The source `.mp4` files are gitignored (`data/*.mp4`); the manifest (with
`video_sha1`) + the human labels JSON are the committed benchmark. To reproduce
a clip exactly, re-run the download + transcode below — the segment, resolution,
and codec are pinned.

| clip | surface | source | segment | res / fps | audio |
|---|---|---|---|---|---|
| `gold_shell` | hard (country club) | youtube `iLBMRRDs9O4` (Tiebreak Tens, Valle Verde) | 600–780 s | 1280×720 / 30 | yes |
| `gold_clay` | **clay** | youtube `sAjkpeRq4P4` (Amateur LK 13.4 vs 15.8) | 800–980 s | 1280×720 / **60** | yes |
| `gold_am` | hard (public) | youtube `RzfUg2tK0Sw` (USTA 4.0 NorCal) | 1200–1380 s | 1280×720 / 30 | yes |

All three carry audio (also unblocks the audio hit detector, `swingvision/audio.py`).

## Reproduce a clip

```bash
# from repo root; FF = imageio-ffmpeg's bundled binary
PY=backend/.venv/Scripts/python.exe
FF=$($PY -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
$PY -m yt_dlp --ffmpeg-location "$FF" \
   -f "bv*[height<=720]+ba/b[height<=720]" \
   --download-sections "*800-980" --force-keyframes-at-cuts \
   -o data/_tmp_clay.%(ext)s "https://www.youtube.com/watch?v=sAjkpeRq4P4"
"$FF" -y -i data/_tmp_clay.webm -c:v libx264 -crf 20 -preset fast \
   -pix_fmt yuv420p -c:a aac -movflags +faststart data/gold_clay.mp4
```

Frame extracts (`data/gold/frames/<clip>/`) are regenerable:
`select_gold_frames.py --video data/<clip>.mp4 --clip <clip> --extract-only`.

## Labeling (the human step)

240 uniformly-sampled frames per clip (uniform = cleanest for a generalization
test set; near/far split is done post-hoc from the clicks by image-y). Label with:

```bash
backend/.venv/Scripts/python.exe tools/gold_label_server.py
```

Click the ball; mark no-ball / unsure with the tool's keys. Writes
`data/gold/<clip>.labels.json`, which is the committed benchmark.
