# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [1.0] — 2026-09-25

First public release.

### Time recovery

- Absolute recording time recovered from three sources in order of precision:
  GPMF GPS telemetry (least-squares fit over the clip), the `tmcd` timecode
  track, and the QuickTime creation date. Each result is reported with a
  precision grade.
- GPS samples without a fix are rejected on two independent tests — an
  implausible dilution of precision, and a capture date outside the recording.
  Frozen and lagging clocks at the head of a clip are filtered before fitting.
- **Deep scan** searches the whole clip for a lock acquired after recording
  began; because the offset between GPS time and the video clock is constant
  once locked, a late fix still anchors frame 0 exactly.
- The timecode track is cross-checked against the file's creation date and
  rejected when it disagrees by more than 5 s, which catches the 60-vs-59.94
  fps drift GoPro's time-of-day timecode accumulates.
- Timezone offsets parsed in every form the toolchain emits, including
  ExifTool's numeric minutes (`-240`) under `-n`, with a fallback derived from
  the gap between the local and UTC creation dates.
- One camera timezone is resolved per session and applied to both videos and
  photographs, so the two cannot be interpreted under different offsets.

### Events and phases

- Events are markers: each runs until the next, and an `END` marker closes a
  run without opening one — so several runs can occupy a single recording.
- **Match photos to clips** reads a photo folder in a single ExifTool call and
  offers only the photographs taken while the loaded videos were recording,
  filterable by camera and selectable in bulk.
- Every event is checked against the loaded clips and marked in the table, with
  a tooltip naming the nearest clips on either side and the distance to each.
- Naming templates for experimental and sham-control runs, with custom names
  available throughout.
- **Clock shift** applies a measured offset between the photo camera and the
  video camera; the in-clip checks update live as it changes.

### Output

- Subtitle sidecars carrying the timestamp and the active phase.
- Burned-in overlays at full resolution, 4K, 1080p, 1280 px and 1024 px, all
  H.264 High / `yuv420p` / constant frame rate / one-second keyframe interval —
  the combination that plays and frame-steps reliably in mpv, and therefore in
  BORIS.
- Lossless no-re-encode option attaching the subtitles as a switchable track.
- Selectable text size, independent of output resolution.

### Trial extraction

- One file per trial, from a chosen starting phase to the end of the run, with
  configurable padding, by lossless stream copy.
- The exact keyframe the copy will land on is queried from `ffprobe` and the
  subtitle file is shifted by that precise amount, keeping timestamps correct
  to the frame rather than drifting by up to half a second.
- Optional chaining: create subtitles if missing, cut, and burn a scoring copy
  in a single unattended pass.
- `trials.csv` manifest mapping each trial to its source, offset and duration.

### Packaging

- Single-file application with no third-party Python dependencies.
- `build_portable.bat` verifies its inputs, builds with PyInstaller, bundles
  ffmpeg, ffprobe and ExifTool beside the executable, and produces a zip that
  runs on a Windows machine with nothing installed — verified by running a
  relocated bundle with an empty `PATH`.
- `find_videos.bat` locates recordings by their embedded recording time rather
  than by filesystem dates, which are rewritten when copying from an SD card.

### Notes on correctness

Three defects found during development are worth recording, since each produced
plausible-looking but wrong output:

- `setpts` quantises a sub-second anchor shift to whole frames unless the
  timebase is set to microseconds first, silently losing up to 17 ms at
  59.94 fps.
- ASS `Fontsize` is scaled by libass to the frame, not measured in pixels;
  deriving it from pixel height made high-resolution burns roughly five times
  too large.
- ExifTool's `-json` output cannot be parsed with a strict JSON reader when the
  `(-k)` build appends its keypress notice, or when warnings accompany it.
