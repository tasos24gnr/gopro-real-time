# Troubleshooting

The log pane reports what happened for every file. Most questions are answered by reading it; this covers the cases where the message needs interpreting.

## Startup

### `exiftool NOT FOUND`

Millisecond GPS timing is unavailable and times fall back to a coarse source. Put `exiftool.exe` — or the file exactly as downloaded, `exiftool(-k).exe` — together with its `exiftool_files` folder beside the program, and restart.

The `-k` in the original filename makes ExifTool wait for a keypress before exiting. The application feeds it an empty stdin so it exits cleanly, and accepts either filename.

### Double-clicking `run.bat` flashes a window and nothing happens

Python is not on `PATH`. Reinstall from python.org with **"Add python.exe to PATH"** ticked on the first installer screen, then reopen the terminal. Or use the portable build, which needs no Python at all.

### `Windows protected your PC` on first launch

SmartScreen reacting to an unsigned program. **More info → Run anyway.** Unavoidable without a code-signing certificate. Corporate machines with application whitelisting may block it outright, which only the machine's administrator can change.

## Time sources

### `SECOND grade only`

No GPS fix and no usable timecode, so the anchor came from the file's creation date: accurate to about a second. Usable, but do not quote sub-second absolute times from it.

### `0 usable (N with no fix)`

The receiver was powered but never locked. Those telemetry samples carry a placeholder date and a dilution-of-precision of 99.99, and are rejected. Tick **deep scan** in case a lock was acquired later in the clip — a lock five minutes in still pins down frame 0 exactly, because the offset between GPS time and the video clock is constant once locked.

If deep scan also finds nothing, that clip contains no GPS time. Check whether GPS was enabled at all (Preferences → Regional), and whether the location had sky view.

### `timecode is −37.0 s from the file's creation date`

Expected, and handled. GoPro counts time-of-day timecode at 60 fps while the video runs at 59.94 — about one second lost every 17 minutes since it was last set. The timecode is frame-accurate for *relative* timing and unreliable as an absolute clock, so it is rejected when it disagrees with the creation date by more than 5 s.

### The displayed clock is right but the `UTC-xxxx` suffix is wrong

The camera's timezone setting was wrong. The clock is correct because the anchor is derived and re-displayed with the same offset, which cancels. Only the label is affected. See [TIMEZONES.md](TIMEZONES.md).

## Events and photos

### `NONE of your events fall inside this clip`

The log prints both windows and the gap between them. Read the gap:

| Gap | Likely cause |
|---|---|
| A whole number of hours | Timezone mismatch between the photo camera and the video camera |
| A different day entirely | Photos from another session, or a wrong date on the stills camera |
| Minutes or seconds | The two clocks genuinely differ — put the difference in **Clock shift** |

Photo times are read **when you add them**, using the timezone setting in force at that moment. If you change *Clock shown* afterwards, re-add the photos rather than assuming the table updated.

### Match photos to clips finds nothing

The log reports how many files ExifTool examined, how many had capture times, and how many fell inside the loaded clips — which distinguishes the three cases.

- **0 files examined** → wrong folder, or a permissions problem.
- **Files examined, none with a capture time** → those files carry no EXIF capture time. Photo-derived events cannot work; add events manually instead.
- **Photos with times, none inside** → a clock or timezone problem, not a file problem. Both time ranges are printed for comparison.

The dialog requires videos to be loaded first, because matching is done against their recording windows.

### An event shows ⚠ instead of ✓

It falls outside every loaded clip. Hover for the reason: the tooltip names the nearest clips on either side and the distance to each. With chaptered recordings an event often lands in the gap between two chapters, in which case loading the other chapter resolves it.

## Output

### Nothing appears in VLC

The subtitle file must sit beside the video with the same base name. If it does not appear automatically, use **Subtitle → Sub Track** and select it.

### The burned text is the wrong size

Subtitle `Fontsize` is not a pixel measurement — it is scaled by libass to the frame, so one value renders at the same proportion of the picture at every resolution. Use the **Text size** dropdown (Small / Normal / Large) rather than expecting resolution to change it.

### Burning takes hours

Expected at full resolution: decoding 5.3K HEVC dominates, and the output resolution barely affects it. See [BORIS.md](BORIS.md) for measurements and the ways around it — cut before burning, use a smaller preset, or burn from a camera-generated proxy.

### A burn produced a file but it looks wrong

Burn one trial, check it, then commit to the batch. The **first 20 s only** checkbox exists for this.

## Cutting

### The cut starts slightly before the requested point

By design, and accounted for. A stream copy cannot cut between keyframes, so the cut lands on the previous one — up to about half a second early. The application asks `ffprobe` exactly which keyframe that will be and shifts the subtitle file by that precise amount, so the timestamps remain correct to the frame. The log reports the shift.

### `(clipped by the clip's edge)`

The trial window extends past the start or end of the recording, so it was truncated. Usually means the recording stopped before the trial ended, or a chapter boundary falls inside the trial.

### A trial spans two chapters

Not currently handled: a trial is cut from a single file. Join the chapters first (BORIS's **Tools → Merge media files**, or `ffmpeg -f concat`), or treat the trial as two pieces. Starting and stopping the recording per trial avoids the situation entirely.

## Getting more detail

Run the underlying commands by hand. In PowerShell, prefix with `.\` for programs in the current folder, and use **single quotes** around ExifTool arguments — PowerShell expands `$GPSDateTime` inside double quotes.

```powershell
# what does this file say about itself?
.\exiftool.exe -CreationDate -CreateDate -TimeZone -Duration "D:\clip.MP4"

# is there GPS telemetry, and does it have a fix?
.\exiftool.exe -ee -f -n -api LargeFileSupport=1 -if '$GPSDateTime' `
    -p '$SampleTime|$GPSDateTime|$GPSDOP' "D:\clip.MP4" | Select-Object -First 10

# what does the timecode track say?
.\ffprobe.exe -v error -show_entries stream_tags=timecode -of default=nw=1 "D:\clip.MP4"
```
