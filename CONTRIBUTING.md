# Contributing

Bug reports, especially ones with a file that reproduces them, are the most
useful contribution.

## Reporting a problem

Include:

- What the log pane said. It reports the time source, the precision grade and
  any warnings per file, and usually identifies the problem on its own.
- The output of ExifTool on one affected file:
  ```powershell
  exiftool -CreationDate -CreateDate -TimeZone -Duration -CameraModelName "D:\clip.MP4"
  ```
- The camera model and firmware, and whether GPS had a lock.

[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) covers the known failure modes
and what their messages mean.

## Working on the code

The application is a single file, `GoProRealTime.pyw`, using only the Python
standard library. It shells out to `exiftool`, `ffmpeg` and `ffprobe`.

It is deliberately laid out in two halves, separated by a marker comment:

- **The engine**, above the marker — metadata parsing, anchor selection, span
  computation, subtitle generation, and construction of ffmpeg command lines.
  Pure functions, no Tkinter, individually testable.
- **The interface**, below — a single `launch_gui()` containing all widgets and
  handlers.

Keep that separation. Anything the engine can do should live above the marker,
so it stays usable from a script.

```bash
python -m py_compile GoProRealTime.pyw   # syntax
python -W error::SyntaxWarning -m py_compile GoProRealTime.pyw   # escape errors
```

Engine functions can be exercised without a display:

```python
import importlib.machinery, importlib.util
loader = importlib.machinery.SourceFileLoader("grt", "GoProRealTime.pyw")
grt = importlib.util.module_from_spec(importlib.util.spec_from_loader("grt", loader))
loader.exec_module(grt)

grt.parse_offset("-240")          # -14400
grt.spans_from_markers(...)       # labelled spans from an event list
grt.build_burn_command(...)       # the ffmpeg command, without running it
```

The GUI can be driven headlessly under `xvfb`; `GRT_AUTOTEST` accepts a
path-separated list of files to load on startup.

## Testing timing changes

Timing bugs produce output that looks correct. Verify against rendered frames
rather than against the code:

- Encode a clip with the frame number or presentation time drawn into it.
- Apply the change.
- Extract frames and read them back.

Every timing behaviour described in the [changelog](CHANGELOG.md) was confirmed
this way, and two of the three defects listed there were found by it.

## Style

- Follow PEP 8; the existing code wraps at 88 columns.
- Comment *why*, not *what*. A comment explaining that `settb` must precede
  `setpts` is worth keeping; one explaining that a loop iterates is not.
- Prefer reporting an inconsistency to silently resolving it. The application's
  usefulness in a research setting rests on its unwillingness to guess.
