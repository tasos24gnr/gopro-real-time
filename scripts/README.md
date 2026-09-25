# Scripts

Windows batch files. Each one can be double-clicked.

## `run.bat`

Launches `GoProRealTime.pyw` without a console window. Requires Python with
Tkinter installed and on `PATH`. Not needed if you use the portable build.

## `build_portable.bat`

Builds the portable bundle: checks that everything it needs is present, builds
with PyInstaller, copies the helper programs in beside the executable, and
produces `GoProRealTime_portable.zip`.

Run it from the repository root, or from this folder — it finds the source
either way. It needs these alongside `GoProRealTime.pyw`, none of which are in
this repository:

| | Where from |
|---|---|
| `ffmpeg.exe`, `ffprobe.exe` | [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) — *essentials* build, from `bin\` |
| `exiftool.exe` + `exiftool_files\` | [exiftool.org](https://exiftool.org) — Windows package |

The GitHub Actions workflow does the same thing on every push, so this is only
needed for building locally.

## `find_videos.bat`

Lists videos recorded within a given time window, searching the time stored
**inside** each file rather than the filesystem dates — which Windows rewrites
when you copy from an SD card, so they record the copy rather than the shoot.

```bat
find_videos.bat
find_videos.bat 2026:08:27 09:30 11:30 "D:\Lab Tests"
```

Arguments are the date, start time, end time and folder; with none, it uses its
built-in defaults. It prints matches, writes a CSV of the details, and offers to
copy the matching files into a subfolder.

Two things worth knowing before trusting an empty result: the window is matched
against **camera local time**, so a camera set to the wrong timezone will fall
outside a tight window; and files with no `CreationDate` are skipped silently.
If a search returns less than expected, widen it and look at the actual times —
the script prints a command that lists every video with its recorded time.
