#!/usr/bin/env python3
"""
GoPro Real Time  --  pick a video, get its true wall-clock time on screen.

Double-click it (or the built .exe), choose one or more GoPro files, press Run.
For each file it finds the exact UTC time of frame 0 from the camera's GPS
telemetry (millisecond resolution) and then writes either

  * a .srt sidecar    -- instant, lossless, toggle the clock on/off in VLC/mpv
  * a burned-in copy  -- <name>_ts.mp4, timestamp welded into the pixels

Helper binaries: exiftool (needed for GPS-grade precision) and ffmpeg/ffprobe.
Both are found on PATH, or just dropped next to this file / the .exe.
"""

from __future__ import annotations

import csv
import datetime as dt
import glob
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

# ---------------------------------------------------------------------------
# Engine  (no GUI code below this line until the MARKER)
# ---------------------------------------------------------------------------

APP_NAME = "GoPro Real Time"
VERSION = "1.0"

# Scallop shell, 64x64 PNG. Embedded so the app stays a single file.
ICON_PNG_B64 = (
    "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"
)

VIDEO_EXTS = (".mp4", ".mov", ".m4v")
DT_RE = re.compile(
    r"(\d{4})[:\-](\d{2})[:\-](\d{2})[ T](\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)"
    r"\s*(Z|[+\-]\d{2}:?\d{2})?"
)
NOWINDOW = 0x08000000 if os.name == "nt" else 0   # keep console flashes away


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_tool(name):
    """Prefer a copy sitting next to us, else fall back to PATH.

    exiftool ships from exiftool.org as 'exiftool(-k).exe', which everyone
    forgets to rename, so accept that spelling as well. The trailing '-k' makes
    it wait for a keypress before exiting -- run() feeds it an empty stdin so it
    doesn't hang.
    """
    names = [name + (".exe" if os.name == "nt" else "")]
    if name == "exiftool":
        names.append("exiftool(-k).exe")
    for d in (app_dir(), os.path.join(app_dir(), "bin"), getattr(sys, "_MEIPASS", "")):
        if not d:
            continue
        for exe in names:
            p = os.path.join(d, exe)
            if os.path.isfile(p):
                return p
    from shutil import which
    for exe in [name] + names:
        hit = which(exe)
        if hit:
            return hit
    return None


TOOLS = {}


def refresh_tools():
    for t in ("exiftool", "ffmpeg", "ffprobe"):
        TOOLS[t] = find_tool(t)
    return TOOLS


def run(cmd, timeout=None):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       stdin=subprocess.DEVNULL, creationflags=NOWINDOW)
    return p.returncode, p.stdout, p.stderr


# ------------------------------------------------------------ time helpers --
def parse_datetime(s):
    m = DT_RE.search(s or "")
    if not m:
        return None, False
    y, mo, d, h, mi = (int(m.group(i)) for i in range(1, 6))
    sec = float(m.group(6))
    off = m.group(7)
    epoch = dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc).timestamp() + sec
    if off and off != "Z":
        off = off.replace(":", "")
        sign = 1 if off[0] == "+" else -1
        epoch -= sign * (int(off[1:3]) * 3600 + int(off[3:5]) * 60)
    return epoch, bool(off)


def parse_offset(s):
    """Seconds east of UTC, from any of the shapes these tools emit.

    exiftool's human output is '-04:00', but under -n the same GoPro tag comes
    back as plain minutes ('-240'), which silently parsed as nothing before and
    dropped everything to UTC.
    """
    s = (s or "").strip()
    if not s:
        return None
    m = re.fullmatch(r"([+\-]?)(\d{1,2}):(\d{2})", s)          # -04:00
    if m:
        return (-1 if m.group(1) == "-" else 1) * (int(m.group(2)) * 3600
                                                   + int(m.group(3)) * 60)
    m = re.fullmatch(r"([+\-]?)(\d{2})(\d{2})", s)             # +0530
    if m:
        return (-1 if m.group(1) == "-" else 1) * (int(m.group(2)) * 3600
                                                   + int(m.group(3)) * 60)
    m = re.fullmatch(r"[+\-]?\d{1,3}", s)                      # -4 hours, -240 minutes
    if m:
        v = int(s)
        return v * 3600 if abs(v) <= 14 else (v * 60 if abs(v) <= 14 * 60 else None)
    return None


def camera_tz_offset(info):
    """The timezone the camera was set to, however we can get it.

    Preferred: the TimeZone tag. Failing that, the gap between the local
    CreationDate and the UTC CreateDate gives it away, rounded to the quarter
    hour because both are only second-accurate.
    """
    off = parse_offset(str(info.get("TimeZone") or ""))
    if off is not None:
        return off
    local, local_had = parse_datetime(str(info.get("CreationDate") or ""))
    utc, _ = parse_datetime(str(info.get("CreateDate") or ""))
    if local is not None and utc is not None and not local_had:
        return int(round((local - utc) / 900.0)) * 900
    return 0


def fmt(epoch, tz_offset):
    t = dt.datetime.fromtimestamp(epoch + tz_offset, dt.timezone.utc)
    return t.strftime("%Y-%m-%d %H:%M:%S.") + f"{t.microsecond // 1000:03d}"


def tz_label_for(offset):
    if offset == 0:
        return "UTC"
    sign = "+" if offset > 0 else "-"
    o = abs(int(offset))
    return f"UTC{sign}{o // 3600:02d}{o % 3600 // 60:02d}"


# ---------------------------------------------------------------- metadata --
def _extract_json(text):
    """exiftool(-k).exe appends its 'press ENTER' notice after the JSON, and
    some builds emit warnings around it, so take the array and ignore the rest."""
    a, b = text.find("["), text.rfind("]")
    if a < 0 or b < a:
        return None
    try:
        return json.loads(text[a:b + 1])
    except json.JSONDecodeError:
        return None


def container_info(path):
    if not TOOLS.get("exiftool"):
        return ffprobe_info(path)
    tags = ["-CreationDate", "-CreateDate", "-TimeZone", "-Duration", "-ImageWidth",
            "-ImageHeight", "-VideoFrameRate", "-CameraModelName"]
    rc, out, err = run([TOOLS["exiftool"], "-json", "-n", "-api",
                        "LargeFileSupport=1", *tags, path])
    rows = _extract_json(out) if out.strip() else None
    if not rows:
        return ffprobe_info(path)
    return rows[0]


def ffprobe_info(path):
    if not TOOLS.get("ffprobe"):
        raise RuntimeError("neither exiftool nor ffprobe found")
    rc, out, err = run([TOOLS["ffprobe"], "-v", "error", "-of", "json",
                        "-show_format", "-show_streams", path])
    if rc != 0:
        raise RuntimeError(f"ffprobe failed: {err.strip()[:200]}")
    d = json.loads(out)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    num, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den) if den and float(den) else 0.0
    tags = d.get("format", {}).get("tags", {})
    return {"CreateDate": tags.get("creation_time", ""),
            "CreationDate": tags.get("creation_time", ""),
            "Duration": float(d.get("format", {}).get("duration") or 0),
            "ImageWidth": v.get("width"), "ImageHeight": v.get("height"),
            "VideoFrameRate": fps, "CameraModelName": tags.get("model", "")}


def timecode_of(path):
    if not TOOLS.get("ffprobe"):
        return None
    rc, out, _ = run([TOOLS["ffprobe"], "-v", "error", "-of", "json", "-show_entries",
                      "stream_tags=timecode:format_tags=timecode", path])
    if rc != 0:
        return None
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return None
    for st in d.get("streams", []):
        tc = (st.get("tags") or {}).get("timecode")
        if tc:
            return tc
    return (d.get("format", {}).get("tags") or {}).get("timecode")


# -------------------------------------------------------------------- GPMF --
MAX_DOP = 20.0          # 99.99 means the receiver has no fix at all


def _exif_gps(path):
    """-> [(video_time, gps_epoch, dop_or_None), ...]

    -f makes exiftool print '-' for absent tags instead of dropping the line.
    Only the first GPS point of each telemetry payload carries a SampleTime,
    which is what ties GPS time to the video timeline, so those are the ones
    worth keeping.
    """
    rc, out, _ = run([TOOLS["exiftool"], "-ee", "-api", "LargeFileSupport=1", "-n",
                      "-q", "-f", "-if", "$GPSDateTime",
                      "-p", "$SampleTime|$GPSDateTime|$GPSDOP", path])
    samples = []
    for line in out.splitlines():
        bits = line.split("|")
        if len(bits) < 2:
            continue
        try:
            t = float(bits[0].strip().rstrip("s").strip())
        except ValueError:
            continue                      # '-' -> a later point in the payload
        e, _ = parse_datetime(bits[1])
        if e is None:
            continue
        try:
            dop = float(bits[2])
        except (IndexError, ValueError):
            dop = None
        samples.append((t, e, dop))
    samples.sort()
    return samples


def usable_fixes(samples, ref_epoch, log):
    """Discard points the receiver did not actually fix.

    Two tells: an implausible DOP, and a date nowhere near the recording (an
    unlocked receiver reports its firmware's default epoch, often 2021-03-07).
    """
    good, no_fix, wrong_era = [], 0, 0
    for t, e, dop in samples:
        if dop is not None and dop > MAX_DOP:
            no_fix += 1
            continue
        if ref_epoch and abs(e - ref_epoch) > 86400:
            wrong_era += 1
            continue
        good.append((t, e))
    if no_fix or wrong_era:
        bits = []
        if no_fix:
            bits.append(f"{no_fix} with no fix")
        if wrong_era:
            bits.append(f"{wrong_era} dated outside this recording")
        log(f"    telemetry: {len(samples)} GPS points, "
            f"{len(good)} usable ({', '.join(bits)})")
    return good


def _telemetry_head(path, seconds):
    """Pull just the telemetry track's first N seconds into a tiny temp file.

    '-discard all -discard:d:0 none' tells the demuxer to skip the video and
    audio chunks outright, so this touches a few MB instead of gigabytes.
    """
    if not TOOLS.get("ffmpeg"):
        return None
    tmp = os.path.join(tempfile.gettempdir(), f"_gprt_{os.getpid()}_{int(time.time())}.mp4")
    attempts = [
        ["-discard", "all", "-discard:d:0", "none", "-i", path, "-map", "0:d",
         "-c", "copy", "-copy_unknown", "-tag:d", "gpmd", "-t", str(seconds), tmp],
        ["-i", path, "-map", "0:d", "-c", "copy", "-copy_unknown", "-tag:d", "gpmd",
         "-t", str(seconds), tmp],
    ]
    for extra in attempts:
        rc, _, _ = run([TOOLS["ffmpeg"], "-v", "error", "-y", *extra], timeout=900)
        if rc == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 512:
            return tmp
        if os.path.exists(tmp):
            os.remove(tmp)
    return None


def gps_samples(path, fast_seconds, log=lambda s: None, ref_epoch=None, deep=False):
    """Usable GPS fixes, cheapest source first.

    The head of a clip is where the receiver is least likely to have locked, so
    if it yields nothing and the user asked for it, scan the whole file: a lock
    acquired five minutes in still pins down frame 0, because the offset
    between GPS time and the video clock is constant once locked.
    """
    if not TOOLS.get("exiftool"):
        return [], "no exiftool"

    if fast_seconds:
        tmp = _telemetry_head(path, fast_seconds)
        if tmp:
            try:
                raw = _exif_gps(tmp)
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            good = usable_fixes(raw, ref_epoch, log)
            if len(good) >= 2:
                return good, f"telemetry head, {fast_seconds}s"
            if raw and not deep:
                log("    no GPS lock in the first minute; tick 'deep scan' to "
                    "look for a lock later in the clip")
                return [], "no lock at the head"
        if not deep:
            log("    fast path found nothing; scanning the whole file...")

    log("    scanning the whole file for telemetry (slow)...")
    raw = _exif_gps(path)
    good = usable_fixes(raw, ref_epoch, log)
    if good:
        log(f"    first usable fix at {good[0][0]:.1f} s into the clip")
    return good, "full scan"


def clean_samples(samples, log):
    """Throw out GPS samples whose time does not belong to this recording.

    Two failure modes seen in the wild, both at the head of a clip while the
    receiver is still settling: the timestamp freezes (the same fix repeated),
    or it sits tens of seconds behind the video timeline before jumping into
    line. Either one drags a naive fit backwards.
    """
    if len(samples) < 4:
        return samples, ""
    notes = []

    # a) drop any run of repeated timestamps -- a frozen clock, not real time
    kept, i, n, frozen = [], 0, len(samples), 0
    while i < n:
        j = i
        while j + 1 < n and abs(samples[j + 1][1] - samples[i][1]) < 1e-6:
            j += 1
        if j > i:
            frozen += j - i + 1
        else:
            kept.append(samples[i])
        i = j + 1
    if frozen:
        notes.append(f"{frozen} frozen")

    # b) the offset (gps time - video time) must be constant; keep the majority
    if len(kept) >= 4:
        offs = sorted(e - t for t, e in kept)
        med = offs[len(offs) // 2]
        good = [(t, e) for t, e in kept if abs((e - t) - med) <= 1.0]
        if len(good) >= 3 and len(good) < len(kept):
            notes.append(f"{len(kept) - len(good)} off-timeline")
            kept = good

    if len(kept) < 3:
        return samples, "cleaning left too little, kept everything"
    return kept, (", ".join(notes) + " sample(s) discarded" if notes else "")


def linear_fit(samples):
    n = len(samples)
    tm = sum(t for t, _ in samples) / n
    em = sum(e for _, e in samples) / n
    den = sum((t - tm) ** 2 for t, _ in samples)
    slope = (sum((t - tm) * (e - em) for t, e in samples) / den) if den else 1.0
    intercept = em - slope * tm
    rms = math.sqrt(sum((e - (slope * t + intercept)) ** 2 for t, e in samples) / n)
    return slope, intercept, rms


# ------------------------------------------------------------------ anchor --
def gps_anchor(path, fast_seconds, log, ref_epoch=None, deep=False):
    s, scope = gps_samples(path, fast_seconds, log, ref_epoch, deep)
    if len(s) < 2:
        return None
    s, note = clean_samples(s, log)
    if note:
        log(f"    telemetry: {note}")
    if len(s) < 2:
        return None
    slope, intercept, rms = linear_fit(s)
    return {"name": "GPS", "source": f"GPS telemetry ({len(s)} samples, {scope})",
            "epoch": intercept, "slope": slope, "rms": rms, "grade": "ms"}


def timecode_anchor(path, info):
    tc = timecode_of(path)
    m = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})[:;](\d{2})", (tc or "").strip())
    if not m:
        return None
    h, mi, sec, f = (int(g) for g in m.groups())
    nominal = max(1, round(float(info.get("VideoFrameRate") or 30.0)))
    cam_off = camera_tz_offset(info)
    local, _ = parse_datetime(str(info.get("CreationDate") or ""))
    if local is None:
        return None
    day = math.floor((local + cam_off) / 86400) * 86400
    return {"name": "timecode", "source": f"timecode track {tc}",
            "epoch": day + h * 3600 + mi * 60 + sec + f / nominal - cam_off,
            "slope": 1.0, "rms": 1.0 / nominal, "grade": "frame"}


def filedate_anchor(info):
    e, had_off = parse_datetime(str(info.get("CreationDate") or ""))
    if e is None:
        e, had_off = parse_datetime(str(info.get("CreateDate") or ""))
        had_off = True
    if e is None:
        return None
    if not had_off:
        e -= camera_tz_offset(info)
    return {"name": "file date", "source": "file creation date", "epoch": e,
            "slope": 1.0, "rms": 0.5, "grade": "second"}


def find_anchor(path, info, fast_seconds, log, prefer="auto", tz_offset=0,
                deep=False, use_gps=True):
    """Work out all available anchors, show them side by side, then choose.

    GPS is the most precise source but not automatically the most trustworthy,
    and the timecode track is frame-accurate for relative timing yet drifts as
    an absolute clock (GoPro counts time-of-day timecode at 60 fps while the
    video runs at 59.94, losing ~1 s every 17 minutes). The creation date is
    coarse but hard to be badly wrong, so it referees.
    """
    cands = {}
    fd = filedate_anchor(info)
    ref_epoch = fd["epoch"] if fd else None
    for a in ((gps_anchor(path, fast_seconds, log, ref_epoch, deep)
               if use_gps else None),
              timecode_anchor(path, info), fd):
        if a:
            cands[a["name"]] = a
    if not cands:
        raise RuntimeError("no timestamp of any kind found in this file")

    for name in ("GPS", "timecode", "file date"):
        if name in cands:
            log(f"    {name:9s} {fmt(cands[name]['epoch'], tz_offset)}")

    # The file's creation date is coarse (whole seconds) but it is the hardest
    # of the three to be badly wrong, so it acts as the referee. A source that
    # sits more than 5 s away from it is not describing this recording.
    ref = cands.get("file date")
    warns = []
    plausible = []
    for name in ("GPS", "timecode"):
        if name not in cands:
            continue
        if ref is None:
            plausible.append(name)
            continue
        gap = cands[name]["epoch"] - ref["epoch"]
        if abs(gap) > 5:
            warns.append(f"{name} is {gap:+.1f} s from the file's creation date")
        else:
            plausible.append(name)

    if prefer != "auto" and prefer in cands:
        chosen = cands[prefer]
    elif "GPS" in plausible:
        chosen = cands["GPS"]
    elif "timecode" in plausible:
        chosen = cands["timecode"]
    elif ref is not None:
        chosen = ref
        warns.append("falling back to the creation date, so whole seconds only")
    else:
        chosen = cands[next(iter(cands))]
    warn = "; ".join(warns)

    chosen = dict(chosen)
    chosen["warn"] = warn
    chosen["candidates"] = cands
    return chosen


# ------------------------------------------------------------------ output --
def esc_path(p):
    return p.replace("\\", "/").replace(":", r"\:")


def build_filter(epoch, tz_offset, tz_label, info, font=None, fontsize=None,
                 x="20", y="20"):
    shown = epoch + tz_offset
    epoch_int = math.floor(shown)
    frac = shown - epoch_int
    size = fontsize or max(18, round(int(info.get("ImageHeight") or 1080) / 22))
    parts = []
    if frac > 1e-6:
        # settb first, or setpts rounds the shift to a whole frame (~17 ms).
        parts += ["settb=1/1000000", f"setpts=PTS+{frac:.6f}/TB"]
    text = (r"%{pts\:gmtime\:" + str(epoch_int) + r"\:%Y-%m-%d %H\\\:%M\\\:%S}"
            r".%{eif\:trunc(mod(t\,1)*1000)\:d\:3} " + tz_label)
    draw = [f"text='{text}'", "fontcolor=white", f"fontsize={size}", "box=1",
            "boxcolor=black@0.5", "boxborderw=10", f"x={x}", f"y={y}"]
    if font:
        draw.insert(0, f"fontfile='{esc_path(font)}'")
    parts.append("drawtext=" + ":".join(draw))
    return ",".join(parts)


# --------------------------------------------------------------- events ----
# "Sham" is the standard term for a control that mimics the procedure without
# the active part -- clearer in a methods section than "dummy" or "control".
SEQUENCE_TEMPLATES = {
    "Experiment": ("Habituation", "Exposure", "Post-exposure", "END"),
    "Control": ("Habituation", "Sham exposure", "Sham post-exposure", "END"),
}
SEQUENCE_TEMPLATE = SEQUENCE_TEMPLATES["Experiment"]
EVENT_PRESETS = ("Habituation", "Exposure", "Post-exposure",
                 "Sham exposure", "Sham post-exposure", "END")


def base_event_name(name):
    """'Exposure 2' -> 'Exposure', so a name matches across runs."""
    return re.sub(r"\s*\d+$", "", (name or "").strip())
END_WORDS = {"end", "ends", "finish", "finished", "stop", "done"}


def is_end_marker(name):
    """A marker that only closes the phase before it, opening nothing."""
    return name.strip().lower().rstrip("0123456789 ") in END_WORDS


def read_photo_time(path, tz_offset):
    """Absolute capture time of a still, sub-second where the camera wrote it."""
    if not TOOLS.get("exiftool"):
        raise RuntimeError("reading photo times needs exiftool")
    rc, out, err = run([TOOLS["exiftool"], "-json", "-n", "-DateTimeOriginal",
                        "-SubSecTimeOriginal", "-OffsetTimeOriginal",
                        "-CreateDate", "-SubSecTime", path])
    rows = _extract_json(out) if out.strip() else None
    if not rows:
        raise RuntimeError(f"cannot read {os.path.basename(path)}"
                           + (f": {err.strip().splitlines()[0][:60]}" if err.strip() else ""))
    d = rows[0]
    stamp = str(d.get("DateTimeOriginal") or d.get("CreateDate") or "")
    if not stamp:
        raise RuntimeError(f"{os.path.basename(path)} has no capture time")
    off = str(d.get("OffsetTimeOriginal") or "")
    epoch, had_off = parse_datetime(stamp + off)
    if epoch is None:
        raise RuntimeError(f"unreadable time in {os.path.basename(path)}")
    sub = str(d.get("SubSecTimeOriginal") or d.get("SubSecTime") or "").strip()
    if sub.isdigit():
        epoch += float("0." + sub)
    if not had_off:
        epoch -= tz_offset          # no zone recorded: read it as the shown zone
    return epoch


PHOTO_EXTS = ("jpg", "jpeg", "png", "heic", "heif", "dng", "cr2", "cr3", "nef",
              "arw", "raf", "orf", "rw2", "gpr", "tif", "tiff", "webp")


def read_photo_times_bulk(folder, tz_offset, recursive=True, log=lambda s: None):
    """Capture times for every photo under a folder, in one exiftool call.

    Returns (photos, note). One process for the lot: per-file calls take about
    a second each, which turns a shoot's worth of stills into a coffee break.
    """
    if not TOOLS.get("exiftool"):
        raise RuntimeError("reading photo times needs exiftool")

    def scan(use_ext):
        cmd = [TOOLS["exiftool"], "-json", "-n", "-DateTimeOriginal",
               "-SubSecTimeOriginal", "-OffsetTimeOriginal", "-CreateDate",
               "-SubSecTime", "-FileName", "-Directory", "-FileType"]
        if recursive:
            cmd.append("-r")
        if use_ext:
            for ext in PHOTO_EXTS:
                cmd += ["-ext", ext]
        cmd.append(folder)
        log("    " + " ".join(f'"{c}"' if " " in c else c for c in cmd[:1])
            + " ... " + f'"{folder}"')
        rc, out, err = run(cmd, timeout=900)
        rows = _extract_json(out) or []
        if not rows and out.strip():
            log(f"    exiftool said: {out.strip().splitlines()[0][:100]}")
        log(f"    exiftool: {len(rows)} file(s) examined"
            + (f", rc={rc}" if rc else "")
            + (f", {err.strip().splitlines()[0][:80]}" if err.strip() else ""))
        return rows

    rows = scan(True)
    if not rows:
        # Wrong extensions, or a folder holding something unexpected: look again
        # without filtering, so the user finds out what is actually in there.
        log("    no photos matched the usual extensions; looking at every file")
        rows = scan(False)

    photos, no_time = [], 0
    for d in rows:
        stamp = str(d.get("DateTimeOriginal") or d.get("CreateDate") or "")
        if not stamp:
            no_time += 1
            continue
        epoch, had_off = parse_datetime(stamp + str(d.get("OffsetTimeOriginal") or ""))
        if epoch is None:
            no_time += 1
            continue
        sub = str(d.get("SubSecTimeOriginal") or d.get("SubSecTime") or "").strip()
        if sub.isdigit():
            epoch += float("0." + sub)
        if not had_off:
            epoch -= tz_offset
        model = str(d.get("Model") or "").strip()
        serial = str(d.get("CameraSerialNumber") or "").strip()
        if model and serial:
            cam = f"{model} \u2026{serial[-4:]}"
        else:
            cam = model or (f"serial \u2026{serial[-4:]}" if serial else "unknown")
        photos.append({"path": os.path.join(str(d.get("Directory") or folder),
                                            str(d.get("FileName") or "?")),
                       "name": str(d.get("FileName") or "?"), "epoch": epoch,
                       "cam": cam})
    photos.sort(key=lambda p: p["epoch"])
    note = f"{len(rows)} file(s) seen, {len(photos)} with a capture time"
    if no_time:
        note += f", {no_time} without one"
    log("    " + note)
    return photos, note


def parse_moment(text, tz_offset):
    epoch, had_off = parse_datetime(text)
    if epoch is None:
        raise RuntimeError(f"cannot read {text.strip()!r} as a time "
                           f"(use YYYY-MM-DD HH:MM:SS.mmm)")
    return epoch if had_off else epoch - tz_offset


def spans_from_markers(markers, anchor, duration, shift=0.0):
    """Markers -> labelled spans in video seconds.

    Each marker opens a phase that runs until the next marker, so a run reads
    habituation -> exposure -> post test -> END. An END marker closes the phase
    before it without opening one, which is what lets several runs sit in the
    same clip without bleeding into each other. The final marker of all, if it
    is not an END, runs to the end of the clip.
    """
    ms = sorted(markers, key=lambda m: m["epoch"])
    spans = []
    for i, m in enumerate(ms):
        if is_end_marker(m["name"]):
            continue
        t0 = m["epoch"] + shift - anchor
        t1 = (ms[i + 1]["epoch"] + shift - anchor) if i + 1 < len(ms) else duration
        t0, t1 = max(0.0, t0), min(duration, t1)
        if t1 - t0 > 1e-6:
            spans.append((t0, t1, m["name"]))
    return spans


def phase_at(spans, t):
    for t0, t1, name in spans:
        if t0 <= t < t1:
            return name
    return None


def esc_text(s):
    for a, b in (("\\", r"\\\\"), (":", r"\:"), (",", r"\,"), ("%", ""), ("'", "")):
        s = s.replace(a, b)
    return s


def phase_filters(spans, info, font=None, fontsize=None, x="20"):
    """A quiet second line under the clock, on only during its own phase."""
    clock = fontsize or max(18, round(int(info.get("ImageHeight") or 1080) / 22))
    size = max(14, round(clock * 0.55))
    y = 20 + int(clock * 1.5)
    # nudged in from the clock's left edge so the two blocks read as a pair
    indent = str(int(x) + 7) if str(x).isdigit() else x
    out = []
    for t0, t1, name in spans:
        draw = [f"text='{esc_text(name)}'", "fontcolor=white@0.85", f"fontsize={size}",
                "box=1", "boxcolor=black@0.35", "boxborderw=7",
                "shadowcolor=black@0.6", "shadowx=1", "shadowy=1",
                f"x={indent}", f"y={y}",
                f"enable='between(t\\,{t0:.3f}\\,{t1:.3f})'"]
        if font:
            draw.insert(0, f"fontfile='{esc_path(font)}'")
        out.append("drawtext=" + ":".join(draw))
    return out


def locate_in_clips(epoch, spans):
    """Is this moment inside one of the loaded clips?

    spans: {path: {"epoch": start, "duration": secs}}
    -> (status, message) where status is "in", "out" or "unknown".

    When it misses, the useful answer is rarely one clip: with chaptered
    recordings a moment usually lands in the gap between two, so name both
    sides and how far it is from each.
    """
    usable = [(sp["epoch"], sp["epoch"] + sp["duration"], os.path.basename(path))
              for path, sp in spans.items() if not sp.get("error")]
    if not spans:
        return "unknown", "No videos selected yet, so this cannot be checked."
    if not usable:
        return "unknown", "No readable videos to check against."
    usable.sort()

    for t0, t1, name in usable:
        if t0 <= epoch <= t1:
            return "in", f"Inside {name}, {short_duration(epoch - t0)} in."

    before = [(t1, name) for t0, t1, name in usable if t1 < epoch]
    after = [(t0, name) for t0, t1, name in usable if t0 > epoch]
    parts = []
    if before:
        t1, name = max(before)
        parts.append(f"{short_duration(epoch - t1)} after {name} ends")
    if after:
        t0, name = min(after)
        parts.append(f"{short_duration(t0 - epoch)} before {name} starts")
    where = " and ".join(parts) if parts else "outside the loaded videos"
    tail = ("It will not be labelled. Either the clip that covers it is not "
            "loaded, or the two cameras' clocks disagree.")
    return "out", f"Outside every selected video: {where}. {tail}"


def short_duration(sec):
    """12:49, 1:02:05, 0:45 -- hours only when there are any."""
    sec = max(0, int(round(sec)))
    h, m, ss = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{ss:02d}" if h else f"{m}:{ss:02d}"


# ------------------------------------------------------ cutting trials ----
def runs_from_markers(markers):
    """Split the event list into runs.

    An END marker closes a run; anything after it starts the next. Names are
    never consulted beyond that, so custom names and several runs in one clip
    both work.
    """
    runs, current = [], []
    for m in sorted(markers, key=lambda m: m["epoch"]):
        current.append(m)
        if is_end_marker(m["name"]):
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return [r for r in runs if len(r) >= 2]


def trial_window(run, pad, cut_from=None):
    """(start - pad, last event + pad) in absolute time.

    cut_from names the phase the trial should begin at, so a habituation period
    that will not be scored need not be carried into the trial file. If that
    phase is not in this run, the run's first event is used instead.
    """
    start = run[0]
    if cut_from:
        for m in run:
            if base_event_name(m["name"]).lower() == cut_from.strip().lower():
                start = m
                break
    return start["epoch"] - pad, run[-1]["epoch"] + pad, start["name"]


def safe_name(text):
    out = "".join("_" if c in '/\\:*?"<>|' else c for c in text.strip())
    return "_".join(out.split()) or "trial"


def keyframe_at_or_before(video, t, back=12.0):
    """Where a stream copy will really start.

    Copying cannot cut mid-GOP, so the cut lands on the previous keyframe.
    Asking ffprobe which one that is turns an unknown error into a known
    offset, which is what lets the subtitles be shifted exactly.
    """
    if not TOOLS.get("ffprobe") or t <= 0:
        return 0.0
    lo = max(0.0, t - back)
    rc, out, _ = run([TOOLS["ffprobe"], "-v", "error", "-select_streams", "v:0",
                      "-skip_frame", "nokey", "-show_entries", "frame=pts_time",
                      "-of", "csv=p=0", "-read_intervals",
                      f"{lo:.3f}%{t + 0.5:.3f}", video], timeout=120)
    stamps = []
    for tok in out.replace(",", " ").split():
        try:
            stamps.append(float(tok))
        except ValueError:
            pass
    earlier = [k for k in stamps if k <= t + 1e-6]
    return max(earlier) if earlier else 0.0


def cut_command(video, start, duration, out_path):
    """-ss before -i so the skipped part is never decoded, and -c copy so the
    picture is untouched. Seconds to run, whatever the clip's length."""
    return [TOOLS["ffmpeg"], "-hide_banner", "-v", "error", "-stats", "-y",
            "-ss", f"{start:.3f}", "-i", video, "-t", f"{duration:.3f}",
            "-c", "copy", "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart", out_path]


SRT_TIME = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def _srt_secs(m):
    return (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            + int(m.group(4)) / 1000.0)


def shift_srt(src, dst, shift, duration):
    """Rebuild a subtitle file for a cut copy.

    The clock text is left exactly as it was -- 10:47:20 is still 10:47:20 --
    only the moment it appears moves, by however much was trimmed off the front.
    """
    with open(src, encoding="utf-8-sig", errors="replace") as fh:
        blocks = re.split(r"\r?\n\r?\n", fh.read().strip())
    kept = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        idx = 1 if "-->" in lines[1] else (0 if "-->" in lines[0] else None)
        if idx is None:
            continue
        times = SRT_TIME.findall(lines[idx])
        if len(times) < 2:
            continue
        found = list(SRT_TIME.finditer(lines[idx]))
        t0 = _srt_secs(found[0]) - shift
        t1 = _srt_secs(found[1]) - shift
        if t1 <= 0 or t0 >= duration:
            continue
        t0, t1 = max(0.0, t0), min(duration, t1)
        text = "\n".join(lines[idx + 1:])
        kept.append((t0, t1, text))
    with open(dst, "w", encoding="utf-8") as fh:
        for n, (t0, t1, text) in enumerate(kept, 1):
            fh.write(f"{n}\n{srt_time(t0)} --> {srt_time(t1)}\n{text}\n\n")
    return len(kept)


# ------------------------------------------------- burning existing subs ----
# BORIS plays video through the mpv library, so "will it work in BORIS" really
# means "will mpv decode it smoothly and step frames reliably". That points at
# plain H.264 High profile, yuv420p, constant frame rate and a short keyframe
# interval. BORIS's own re-encode tool targets 1024 px wide, so the default
# preset here matches it.
SUB_PRESETS = {
    "Full resolution (best detail, slowest)": {"width": 0, "suffix": "_burned",
                                               "encode": True},
    "4K 3840 px": {"width": 3840, "suffix": "_4k", "encode": True},
    "1080p 1920 px": {"width": 1920, "suffix": "_1080p", "encode": True},
    "BORIS proxy 1280 px": {"width": 1280, "suffix": "_boris1280",
                            "encode": True},
    "BORIS proxy 1024 px (safest for BORIS)": {"width": 1024, "suffix": "_boris",
                                               "encode": True},
    "No re-encode: attach subtitles as a switchable track":
        {"width": 0, "suffix": "_subs", "encode": False},
}
BORIS_DEFAULT = "BORIS proxy 1024 px (safest for BORIS)"
SUB_EXTS = (".srt", ".ass", ".ssa", ".vtt")
RISKY_IN_FILTER = set(":'[],\\")


def find_sidecar_subtitle(video):
    stem = os.path.splitext(video)[0]
    for ext in SUB_EXTS:
        if os.path.isfile(stem + ext):
            return stem + ext
    return None


def safe_subtitle_copy(sub):
    """libass sees the filter string, not a path, so characters that mean
    something to the filter parser have to go. Copying to a plain name beside
    the original sidesteps quoting entirely."""
    name = os.path.basename(sub)
    if not (set(name) & RISKY_IN_FILTER):
        return name, None
    safe = "_grt_subs" + os.path.splitext(name)[1]
    dest = os.path.join(os.path.dirname(os.path.abspath(sub)), safe)
    shutil.copyfile(sub, dest)
    return safe, dest


ASS_FONTSIZE = 18          # ~4% of frame height, whatever the resolution
# Beyond about 1.35 the timestamp line wraps, which looks worse than it reads.
TEXT_SCALES = {"Small": 0.75, "Normal": 1.0, "Large": 1.35}


def build_burn_command(video, sub, preset_name, info, gpu=False, half_fps=False,
                       on_top=False, crf="21", text_scale=1.0):
    """-> (cmd, cwd, output_path, temp_to_delete)

    Runs with cwd set to the video's folder so the filter only ever sees bare
    filenames: on Windows an absolute path carries a drive-letter colon, which
    the filter parser reads as an option separator.
    """
    preset = SUB_PRESETS[preset_name]
    folder = os.path.dirname(os.path.abspath(video)) or "."
    vname = os.path.basename(video)
    stem = os.path.splitext(vname)[0]
    src_w = int(info.get("ImageWidth") or 1920)
    src_h = int(info.get("ImageHeight") or 1080)
    fps = float(info.get("VideoFrameRate") or 30.0)

    if not preset["encode"]:
        out = stem + preset["suffix"] + ".mp4"
        cmd = [TOOLS["ffmpeg"], "-hide_banner", "-v", "error", "-stats", "-y",
               "-i", vname, "-i", os.path.basename(sub), "-map", "0", "-map", "1",
               "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
               out]
        return cmd, folder, os.path.join(folder, out), None

    subname, tmp = safe_subtitle_copy(sub)
    width = preset["width"] or src_w
    height = max(2, int(round(src_h * width / src_w / 2)) * 2)
    # Fontsize is NOT pixels: libass scales it to the frame, so a fixed value
    # keeps the text the same proportion of the picture at every resolution.
    # Deriving it from the pixel height made full-resolution burns enormous.
    size = max(6, round(ASS_FONTSIZE * text_scale))
    align = 7 if on_top else 1
    style = (f"FontName=Consolas,Fontsize={size},BorderStyle=3,Outline=1,"
             f"Shadow=0,BackColour=&H80000000&,Alignment={align},"
             f"MarginL=20,MarginV=20")

    chain = []
    if preset["width"] and width < src_w:
        chain.append(f"scale={width}:-2:flags=bicubic")
    chain.append(f"subtitles={subname}:force_style='{style}'")
    out_fps = fps / 2 if half_fps else fps
    if half_fps:
        chain.append("fps=30000/1001" if abs(fps - 59.94) < 0.5 else f"fps={out_fps:.6f}")
    chain.append("format=yuv420p")

    gop = max(1, int(round(out_fps)))
    out = stem + preset["suffix"] + ".mp4"
    cmd = [TOOLS["ffmpeg"], "-hide_banner", "-v", "error", "-stats", "-y",
           "-i", vname, "-vf", ",".join(chain),
           "-c:v", "h264_nvenc" if gpu else "libx264",
           "-profile:v", "high", "-pix_fmt", "yuv420p"]
    if gpu:
        cmd += ["-preset", "p4", "-cq", crf]
    else:
        cmd += ["-preset", "veryfast", "-crf", crf]
    cmd += ["-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0",
            "-fps_mode", "cfr", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "128k", out]
    return cmd, folder, os.path.join(folder, out), tmp


def srt_time(t):
    t = max(0.0, t)
    ms = int(round((t - math.floor(t)) * 1000))
    s = int(t)
    if ms == 1000:
        s, ms = s + 1, 0
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d},{ms:03d}"


def write_srt(out, epoch, tz_offset, tz_label, duration, interval=0.1, phases=()):
    """Plain text on purpose: markup tags leak as literal characters in some
    players, so the phase is set off with spacing and a middle dot instead."""
    n = max(1, int(duration / interval) + 1)
    with open(out, "w", encoding="utf-8") as fh:
        for i in range(n):
            t0, t1 = i * interval, min((i + 1) * interval, duration)
            text = f"{fmt(epoch + t0, tz_offset)} {tz_label}"
            name = phase_at(phases, t0)
            if name:
                text += f"   ·   {name}"
            fh.write(f"{i + 1}\n{srt_time(t0)} --> {srt_time(t1)}\n{text}\n\n")
    return n


def discover(paths, recursive=False):
    found = []
    for item in paths:
        if os.path.isdir(item):
            hits = glob.glob(os.path.join(item, "**/*" if recursive else "*"),
                             recursive=recursive)
        elif any(c in item for c in "*?["):
            hits = glob.glob(item, recursive=recursive)
        else:
            hits = [item]
        for h in hits:
            stem, ext = os.path.splitext(h)
            if os.path.isfile(h) and ext.lower() in VIDEO_EXTS and not stem.endswith("_ts"):
                found.append(os.path.abspath(h))
    return sorted(set(found))


# ---------------------------------------------------------------------------
# MARKER: GUI
# ---------------------------------------------------------------------------
def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title(f"{APP_NAME} {VERSION}")
    try:
        root._icon = tk.PhotoImage(data=ICON_PNG_B64)
        root.iconphoto(True, root._icon)
    except Exception:
        pass                        # an icon is never worth failing to start over
    # Never open taller than the screen, or the buttons land below the taskbar.
    screen_h = root.winfo_screenheight()
    screen_w = root.winfo_screenwidth()
    root.geometry(f"{min(1060, max(900, screen_w - 80))}"
                  f"x{min(880, max(560, screen_h - 140))}")
    root.minsize(900, 560)

    files = []
    filespans = {}          # path -> {"epoch", "duration"} for the file table
    msgs = queue.Queue()
    worker = {"thread": None, "stop": False, "proc": None}

    # ---- widgets ----------------------------------------------------------
    # Claimed first so a short window can never push them off the bottom.
    bottom = ttk.Frame(root, padding=(10, 6, 10, 10))
    bottom.pack(side="bottom", fill="x")

    bar = ttk.Progressbar(root, mode="determinate")
    bar.pack(side="bottom", fill="x", padx=10)

    top = ttk.Frame(root, padding=10)
    top.pack(fill="x")

    ttk.Button(top, text="Select video files…",
               command=lambda: add_files()).pack(side="left")
    ttk.Button(top, text="Select folder…",
               command=lambda: add_folder()).pack(side="left", padx=6)
    ttk.Button(top, text="Clear", command=lambda: clear()).pack(side="left")
    ttk.Button(top, text="Cut trials\u2026",
               command=lambda: cut_trials_dialog()).pack(side="left", padx=(16, 0))
    ttk.Button(top, text="Burn subtitles\u2026",
               command=lambda: burn_subs_dialog()).pack(side="left", padx=(6, 0))

    count = ttk.Label(top, text="no files selected")
    count.pack(side="right")

    flist = ttk.Treeview(root, columns=("file", "start", "end", "len"),
                         show="headings", height=6, selectmode="extended")
    for col, head, w, anc in (("file", "file", 210, "w"),
                              ("start", "recording starts", 200, "w"),
                              ("end", "recording ends", 200, "w"),
                              ("len", "length", 70, "e")):
        flist.heading(col, text=head)
        flist.column(col, width=w, anchor=anc)
    flist.pack(fill="x", padx=10)

    opts = ttk.LabelFrame(root, text="Options", padding=10)
    opts.pack(fill="x", padx=10, pady=10)

    mode = tk.StringVar(value="srt")
    ttk.Radiobutton(opts, text="Subtitle file  (instant, no re-encode)",
                    variable=mode, value="srt").grid(row=0, column=0, sticky="w", columnspan=2)
    ttk.Radiobutton(opts, text="Burn into video  (slow, makes _ts.mp4)",
                    variable=mode, value="burn").grid(row=1, column=0, sticky="w", columnspan=2)

    preview = tk.BooleanVar(value=True)
    ttk.Checkbutton(opts, text="first 20 s only (test burn)",
                    variable=preview).grid(row=1, column=2, sticky="w", padx=10)

    gpu = tk.BooleanVar(value=False)
    ttk.Checkbutton(opts, text="NVIDIA GPU encode",
                    variable=gpu).grid(row=1, column=3, sticky="w")

    ttk.Label(opts, text="Clock shown:").grid(row=2, column=0, sticky="w", pady=(8, 0))
    tzmode = tk.StringVar(value="camera")
    tzbox = ttk.Combobox(opts, textvariable=tzmode, state="readonly", width=34,
                         values=["camera", "utc", "custom"])
    tzbox.grid(row=2, column=1, sticky="w", pady=(8, 0))
    tzcustom = tk.StringVar(value="-04:00")
    ttk.Entry(opts, textvariable=tzcustom, width=9).grid(row=2, column=2, sticky="w",
                                                        padx=10, pady=(8, 0))
    ttk.Label(opts, text="(camera = the timezone the camera was set to)").grid(
        row=2, column=3, sticky="w", pady=(8, 0))

    ttk.Label(opts, text="Time source:").grid(row=3, column=0, sticky="w", pady=(6, 0))
    srcmode = tk.StringVar(value="auto")
    ttk.Combobox(opts, textvariable=srcmode, state="readonly", width=34,
                 values=["auto", "GPS", "timecode", "file date"]).grid(
        row=3, column=1, sticky="w", pady=(6, 0))
    ttk.Label(opts, text="(auto = GPS, unless it contradicts the camera clock)").grid(
        row=3, column=3, sticky="w", pady=(6, 0))

    deep = tk.BooleanVar(value=False)
    ttk.Checkbutton(opts, text="deep scan for a GPS lock later in the clip (slow)",
                    variable=deep).grid(row=4, column=1, columnspan=3, sticky="w",
                                        pady=(6, 0))

    exp = ttk.LabelFrame(root, text="Events  (optional)", padding=10)
    exp.pack(fill="x", padx=10)

    markers = []            # [{"epoch": float, "name": str}], any order
    camtz = {"value": None}  # camera timezone, learned from the first video

    cols = ("time", "event", "ok")
    tree = ttk.Treeview(exp, columns=cols, show="headings", height=5,
                        selectmode="extended")
    tree.heading("time", text="when")
    tree.heading("event", text="event starts")
    tree.heading("ok", text="in a clip")
    tree.column("time", width=200, anchor="w")
    tree.column("event", width=210, anchor="w")
    tree.column("ok", width=60, anchor="center")
    tree.tag_configure("in", foreground="#137333")
    tree.tag_configure("out", foreground="#a06000")
    tree.tag_configure("unknown", foreground="#777777")
    marker_notes = {}       # row id -> why it has the mark it has
    tree.grid(row=0, column=0, rowspan=6, sticky="we")
    exp.columnconfigure(0, weight=1)

    btns = ttk.Frame(exp)
    btns.grid(row=0, column=1, rowspan=6, sticky="nw", padx=(10, 0))
    runtype = tk.StringVar(value="Experiment")
    ttk.Combobox(btns, textvariable=runtype, state="readonly", width=22,
                 values=list(SEQUENCE_TEMPLATES)).pack(fill="x")
    ttk.Button(btns, text="Add run from photos\u2026", width=24,
               command=lambda: add_run()).pack(fill="x", pady=(4, 0))
    ttk.Button(btns, text="Match photos to clips\u2026", width=24,
               command=lambda: match_photos()).pack(fill="x", pady=(4, 0))
    ttk.Button(btns, text="Add one event\u2026", width=24,
               command=lambda: add_marker()).pack(fill="x", pady=(4, 0))
    ttk.Button(btns, text="Edit\u2026", width=24,
               command=lambda: edit_marker()).pack(fill="x", pady=(4, 0))
    ttk.Button(btns, text="Remove", width=24,
               command=lambda: remove_markers()).pack(fill="x", pady=(4, 0))
    ttk.Button(btns, text="Clear all", width=24,
               command=lambda: clear_markers()).pack(fill="x", pady=(4, 0))

    shiftrow = ttk.Frame(exp)
    shiftrow.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
    ttk.Label(shiftrow, text="Clock shift").pack(side="left")
    pshift = tk.StringVar(value="0")
    pshift.trace_add("write", lambda *_: refresh_markers())
    ttk.Entry(shiftrow, textvariable=pshift, width=8).pack(side="left", padx=6)
    ttk.Label(shiftrow, text="s  (+/- if the photo camera's clock differs from "
                             "the GoPro's).  Each event runs until the next; "
                             "END closes the one before it.").pack(side="left")

    log = tk.Text(root, height=8, wrap="word", font=("Consolas", 9))
    log.pack(fill="both", expand=True, padx=10, pady=(10, 4))
    runbtn = ttk.Button(bottom, text="Run", command=lambda: start())
    runbtn.pack(side="right")
    stopbtn = ttk.Button(bottom, text="Stop", state="disabled", command=lambda: stop())
    stopbtn.pack(side="right", padx=6)
    status = ttk.Label(bottom, text="")
    status.pack(side="left")

    # ---- plumbing ---------------------------------------------------------
    def say(s=""):
        msgs.put(s)

    def pump():
        while True:
            try:
                s = msgs.get_nowait()
            except queue.Empty:
                break
            if isinstance(s, tuple):
                bar["value"], bar["maximum"] = s
            else:
                log.insert("end", s + "\n")
                log.see("end")
        root.after(120, pump)

    def attach_tooltip(widget, text_for):
        """Hover help. Tk has none built in, so this is a small borrowed-looking
        label in a borderless window that follows the pointer."""
        tip = {"win": None, "row": None}

        def hide(_=None):
            if tip["win"] is not None:
                tip["win"].destroy()
                tip["win"] = None
            tip["row"] = None

        def move(ev):
            row = widget.identify_row(ev.y)
            text = text_for(ev) if row else None
            if not text:
                hide()
                return
            if row == tip["row"] and tip["win"] is not None:
                tip["win"].wm_geometry(f"+{ev.x_root + 14}+{ev.y_root + 18}")
                return
            hide()
            tip["row"] = row
            win = tk.Toplevel(widget)
            win.wm_overrideredirect(True)
            win.wm_geometry(f"+{ev.x_root + 14}+{ev.y_root + 18}")
            tk.Label(win, text=text, justify="left", wraplength=380,
                     background="#ffffe0", relief="solid", borderwidth=1,
                     font=("Segoe UI", 9), padx=6, pady=4).pack()
            tip["win"] = win

        widget.bind("<Motion>", move, add="+")
        widget.bind("<Leave>", hide, add="+")

    def refresh_list():
        flist.delete(*flist.get_children())
        off = current_tz_offset()
        for i, f in enumerate(files):
            span = filespans.get(f)
            if span is None:
                start = end = length = "reading\u2026"
            elif span.get("error"):
                start, end, length = span["error"], "", ""
            else:
                start = fmt(span["epoch"], off)
                end = fmt(span["epoch"] + span["duration"], off)
                length = short_duration(span["duration"])
            flist.insert("", "end", iid=str(i),
                         values=(os.path.basename(f), start, end, length))
        count.config(text=f"{len(files)} file(s) selected" if files
                     else "no files selected")

    def scan_files():
        """Work out each clip's real start and end so you can see at a glance
        which photos belong to it. GPS is skipped here -- this is for choosing
        events, and a full telemetry scan per file would make selecting files
        feel broken. Run still uses the precise anchor."""
        for f in list(files):
            if f in filespans:
                continue
            try:
                info = container_info(f)
                a = find_anchor(f, info, 0, lambda _s: None, tz_offset=0,
                                use_gps=False)
                filespans[f] = {"epoch": a["epoch"],
                                "duration": float(info.get("Duration") or 0),
                                "grade": a["grade"]}
            except Exception as exc:
                filespans[f] = {"error": str(exc)[:40]}
            root.after(0, refresh_list)
            root.after(0, refresh_markers)

    def rescan():
        threading.Thread(target=scan_files, daemon=True).start()

    def add_files():
        picked = filedialog.askopenfilenames(
            title="Select GoPro video files",
            filetypes=[("Video", "*.mp4 *.MP4 *.mov *.MOV *.m4v"), ("All files", "*.*")])
        for f in discover(list(picked)):
            if f not in files:
                files.append(f)
        refresh_list()
        learn_camera_tz()
        rescan()
        learn_camera_tz()

    def add_folder():
        d = filedialog.askdirectory(title="Select a folder of GoPro videos")
        if not d:
            return
        for f in discover([d], recursive=True):
            if f not in files:
                files.append(f)
        refresh_list()
        learn_camera_tz()
        rescan()

    def clear():
        files.clear()
        filespans.clear()
        refresh_list()

    def current_tz_offset(info=None):
        """The offset in force right now.

        Photos are read when you add them and videos when you press Run, so
        both paths have to land on the same number or the two sets of times end
        up hours apart. In 'camera' mode that number is cached off the first
        video you select, rather than each path guessing separately.
        """
        if tzmode.get() == "utc":
            return 0
        if tzmode.get() == "custom":
            return parse_offset(tzcustom.get()) or 0
        if info:
            return camera_tz_offset(info)
        if camtz["value"] is not None:
            return camtz["value"]
        return parse_offset(tzcustom.get()) or 0

    def learn_camera_tz():
        """Read the timezone off the first video, so photos use it too."""
        if not files:
            return
        try:
            off = camera_tz_offset(container_info(files[0]))
        except Exception:
            return
        if camtz["value"] == off:
            return
        camtz["value"] = off
        tzcustom.set(tz_label_for(off).replace("UTC", "") or "+00:00")
        say(f"Camera timezone: {tz_label_for(off)} "
            f"(used for photo times as well)")
        refresh_markers()
        refresh_list()

    PHOTO_TYPES = [("Photos", "*.jpg *.JPG *.jpeg *.JPEG *.png *.PNG *.heic *.HEIC "
                              "*.dng *.DNG *.cr2 *.CR2 *.nef *.NEF *.arw *.ARW "
                              "*.raf *.RAF *.orf *.ORF"), ("All files", "*.*")]

    MARK = {"in": "\u2713", "out": "\u26a0", "unknown": "\u2013"}

    def refresh_markers():
        tree.delete(*tree.get_children())
        marker_notes.clear()
        off = current_tz_offset()
        try:
            shift = float(pshift.get() or 0)
        except ValueError:
            shift = 0.0
        for i, m in enumerate(sorted(markers, key=lambda m: m["epoch"])):
            status, note = locate_in_clips(m["epoch"] + shift, filespans)
            marker_notes[str(i)] = note
            tree.insert("", "end", iid=str(i), tags=(status,),
                        values=(fmt(m["epoch"], off), m["name"], MARK[status]))

    def run_number():
        """How many runs are already laid out, so a new one is numbered on."""
        return len(runs_from_markers(markers)) + 1

    def add_run():
        """One run = the photos marking each of its events, in time order."""
        picked = filedialog.askopenfilenames(
            title="Select this run's photos: one per event, plus one for the end",
            filetypes=PHOTO_TYPES)
        if not picked:
            return
        off = current_tz_offset()
        try:
            times = sorted(read_photo_time(f, off) for f in picked)
        except Exception as exc:
            messagebox.showerror("Photos", str(exc))
            return
        template = SEQUENCE_TEMPLATES[runtype.get()]
        n = run_number()
        suffix = "" if n == 1 else f" {n}"
        for i, t in enumerate(times):
            if i < len(template) - 1:
                name = template[i] + suffix
            elif i == len(times) - 1:
                name = "END" + suffix
            else:
                name = f"event {i + 1}{suffix}"
            markers.append({"epoch": t, "name": name})
        refresh_markers()
        say(f"Added {len(times)} events from photos"
            + (f" (run {n})" if n > 1 else "") + " — edit any name you like")
        for m in sorted(markers, key=lambda m: m["epoch"])[-len(times):]:
            say(f"    {fmt(m['epoch'], off)}  {m['name']}")

    def match_photos():
        """Pick a photo folder and show only the shots that fall inside the
        videos you have loaded, so the choice is made for you."""
        if not filespans or all(v.get("error") for v in filespans.values()):
            messagebox.showinfo("Match photos",
                                "Load your video files first -- the matching is "
                                "done against their recording periods.")
            return
        folder = filedialog.askdirectory(title="Folder holding this session's photos")
        if not folder:
            return
        off = current_tz_offset()
        say(f"Reading photo times from {folder} \u2026")
        try:
            photos, note = read_photo_times_bulk(folder, off, recursive=True,
                                                 log=say)
        except Exception as exc:
            messagebox.showerror("Match photos", str(exc))
            return
        if not photos:
            messagebox.showinfo(
                "Match photos",
                f"Nothing with a capture time was found under:\n\n{folder}\n\n"
                f"{note}.\n\nCheck that this folder holds the photos (not the "
                f"videos), and that the files still carry their EXIF data.")
            return
        try:
            shift = float(pshift.get() or 0)
        except ValueError:
            shift = 0.0
        for ph in photos:
            ph["status"], ph["note"] = locate_in_clips(ph["epoch"] + shift, filespans)
        inside = [p for p in photos if p["status"] == "in"]
        say(f"    {len(photos)} photos with times, {len(inside)} inside the "
            f"loaded videos")
        if not inside:
            span_lo = min(p["epoch"] for p in photos)
            span_hi = max(p["epoch"] for p in photos)
            say(f"    photos run {fmt(span_lo, off)} -> {fmt(span_hi, off)}")
            for f, sp in filespans.items():
                if not sp.get("error"):
                    say(f"    {os.path.basename(f)}: {fmt(sp['epoch'], off)} -> "
                        f"{fmt(sp['epoch'] + sp['duration'], off)}")

        dlg = tk.Toplevel(root)
        dlg.title("Photos taken during these videos")
        dlg.transient(root)
        dlg.geometry("860x540")
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill="both", expand=True)

        headline = (f"{len(inside)} of {len(photos)} photos fall inside the "
                    f"loaded videos. Select the ones that mark your events."
                    if inside else
                    f"None of the {len(photos)} photos were taken while the "
                    f"loaded videos were recording \u2014 showing them all so you "
                    f"can see the times. Check the log for both time ranges.")
        ttk.Label(frm, text=headline, wraplength=720, justify="left").pack(anchor="w")

        cams = sorted({ph["cam"] for ph in photos})

        filt = ttk.Frame(frm)
        filt.pack(fill="x", pady=(8, 0))
        ttk.Label(filt, text="Camera:").pack(side="left")
        camsel = tk.StringVar(value="all cameras")
        ttk.Combobox(filt, textvariable=camsel, state="readonly", width=26,
                     values=["all cameras"] + cams).pack(side="left", padx=(4, 12))
        showall = tk.BooleanVar(value=not inside)
        ttk.Checkbutton(filt, text="show photos outside the videos too",
                        variable=showall, command=lambda: fill()).pack(side="left")

        cols = ("photo", "when", "cam", "clip")
        pt = ttk.Treeview(frm, columns=cols, show="headings", height=13,
                          selectmode="extended")
        for c, h, w in (("photo", "photo", 160), ("when", "taken at", 190),
                        ("cam", "camera", 170), ("clip", "falls inside", 180)):
            pt.heading(c, text=h)
            pt.column(c, width=w, anchor="w")
        pt.pack(fill="both", expand=True, pady=(8, 0))
        pt.tag_configure("out", foreground="#a06000")

        rows = {}
        shown_count = tk.StringVar(value="")

        def fill():
            pt.delete(*pt.get_children())
            rows.clear()
            shown = [ph for ph in (photos if showall.get() else inside)
                     if camsel.get() == "all cameras" or ph["cam"] == camsel.get()]
            for i, ph in enumerate(shown):
                where = (ph["note"].split(",")[0].replace("Inside ", "")
                         if ph["status"] == "in" else "outside every video")
                pt.insert("", "end", iid=str(i),
                          tags=() if ph["status"] == "in" else ("out",),
                          values=(ph["name"], fmt(ph["epoch"], off), ph["cam"], where))
                rows[str(i)] = ph
            shown_count.set(f"{len(shown)} shown")

        camsel.trace_add("write", lambda *_: fill())
        fill()

        opts = ttk.Frame(frm)
        opts.pack(fill="x", pady=(8, 0))
        ttk.Button(opts, text="Select all shown",
                   command=lambda: pt.selection_set(pt.get_children())).pack(side="left")
        ttk.Button(opts, text="Select none",
                   command=lambda: pt.selection_remove(pt.selection())).pack(
            side="left", padx=6)
        ttk.Label(opts, textvariable=shown_count).pack(side="left", padx=8)
        ttk.Label(opts, text="(click, then Shift+click for a range; "
                             "Ctrl+click adds or drops one)",
                  foreground="#666").pack(side="left")

        def chosen():
            picked = [rows[i] for i in pt.selection()]
            if not picked:
                messagebox.showinfo("Match photos", "Select some photos first.",
                                    parent=dlg)
            return sorted(picked, key=lambda p: p["epoch"])

        def add_as_run():
            picked = chosen()
            if not picked:
                return
            n = run_number()
            suffix = "" if n == 1 else f" {n}"
            for i, ph in enumerate(picked):
                if i < len(SEQUENCE_TEMPLATE) - 1:
                    nm = SEQUENCE_TEMPLATE[i] + suffix
                elif i == len(picked) - 1:
                    nm = "END" + suffix
                else:
                    nm = f"event {i + 1}{suffix}"
                markers.append({"epoch": ph["epoch"], "name": nm})
                say(f"    {fmt(ph['epoch'], off)}  {nm}   ({ph['name']})")
            refresh_markers()
            dlg.destroy()

        def add_named():
            picked = chosen()
            if not picked:
                return
            nm = name_prompt(dlg)
            if not nm:
                return
            for ph in picked:
                markers.append({"epoch": ph["epoch"], "name": nm})
                say(f"    {fmt(ph['epoch'], off)}  {nm}   ({ph['name']})")
            refresh_markers()
            dlg.destroy()

        btn = ttk.Frame(frm)
        btn.pack(fill="x", pady=(10, 0))
        ttk.Button(btn, text="Close", command=dlg.destroy).pack(side="right")
        ttk.Button(btn, text="Add selected with one name\u2026",
                   command=add_named).pack(side="right", padx=6)
        ttk.Button(btn, text="Add selected as a run",
                   command=add_as_run).pack(side="right")
        dlg.grab_set()

    def name_prompt(parent):
        """Just the event name: preset or typed."""
        dlg = tk.Toplevel(parent)
        dlg.title("Event name")
        dlg.transient(parent)
        dlg.resizable(False, False)
        frm = ttk.Frame(dlg, padding=12)
        frm.pack()
        out = {}
        nvar = tk.StringVar(value=EVENT_PRESETS[0])
        ttk.Label(frm, text="Event").pack(anchor="w")
        box = ttk.Combobox(frm, textvariable=nvar, width=30,
                           values=list(EVENT_PRESETS) + ["custom\u2026"])
        box.pack(pady=(4, 0))

        def picked(_=None):
            if nvar.get() == "custom\u2026":
                nvar.set("")
                box.focus_set()
        box.bind("<<ComboboxSelected>>", picked)

        def ok():
            if nvar.get().strip():
                out["name"] = nvar.get().strip()
                dlg.destroy()
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(12, 0))
        ttk.Button(row, text="Cancel", command=dlg.destroy).pack(side="right", padx=4)
        ttk.Button(row, text="OK", command=ok).pack(side="right")
        dlg.bind("<Return>", lambda _: ok())
        dlg.grab_set()
        parent.wait_window(dlg)
        return out.get("name")

    def marker_dialog(title, name="", when=""):
        """Small modal: pick a preset event or type your own, set the time."""
        dlg = tk.Toplevel(root)
        dlg.title(title)
        dlg.transient(root)
        dlg.resizable(False, False)
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)
        result = {}

        ttk.Label(frm, text="Event").grid(row=0, column=0, sticky="w")
        nvar = tk.StringVar(value=name or EVENT_PRESETS[0])
        box = ttk.Combobox(frm, textvariable=nvar, width=30,
                           values=list(EVENT_PRESETS) + ["custom\u2026"])
        box.grid(row=0, column=1, columnspan=2, sticky="w", padx=6)

        def on_pick(_=None):
            if nvar.get() == "custom\u2026":
                nvar.set("")
                box.focus_set()
        box.bind("<<ComboboxSelected>>", on_pick)

        ttk.Label(frm, text="When").grid(row=1, column=0, sticky="w", pady=(8, 0))
        wvar = tk.StringVar(value=when)
        ttk.Entry(frm, textvariable=wvar, width=30).grid(row=1, column=1, sticky="w",
                                                          padx=6, pady=(8, 0))

        def from_photo():
            f = filedialog.askopenfilename(parent=dlg, title="Photo taken at that moment",
                                           filetypes=PHOTO_TYPES)
            if not f:
                return
            try:
                wvar.set(fmt(read_photo_time(f, current_tz_offset()),
                             current_tz_offset()))
            except Exception as exc:
                messagebox.showerror("Photo", str(exc), parent=dlg)
        ttk.Button(frm, text="from photo\u2026", command=from_photo).grid(
            row=1, column=2, sticky="w", pady=(8, 0))

        ttk.Label(frm, text="(YYYY-MM-DD HH:MM:SS.mmm)", foreground="#666").grid(
            row=2, column=1, sticky="w", padx=6)

        def ok():
            if not nvar.get().strip():
                messagebox.showerror("Event", "Give the event a name.", parent=dlg)
                return
            try:
                result["epoch"] = parse_moment(wvar.get(), current_tz_offset())
            except Exception as exc:
                messagebox.showerror("Event", str(exc), parent=dlg)
                return
            result["name"] = nvar.get().strip()
            dlg.destroy()

        row = ttk.Frame(frm)
        row.grid(row=3, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(row, text="Cancel", command=dlg.destroy).pack(side="right", padx=4)
        ttk.Button(row, text="OK", command=ok).pack(side="right")
        dlg.bind("<Return>", lambda _: ok())
        dlg.grab_set()
        root.wait_window(dlg)
        return result or None

    def add_marker():
        m = marker_dialog("Add an event")
        if m:
            markers.append(m)
            refresh_markers()
            say(f"Added {m['name']} at {fmt(m['epoch'], current_tz_offset())}")

    def selected_markers():
        order = sorted(markers, key=lambda m: m["epoch"])
        return [order[int(i)] for i in tree.selection()]

    def edit_marker():
        sel = selected_markers()
        if len(sel) != 1:
            messagebox.showinfo("Edit", "Select exactly one event to edit.")
            return
        old = sel[0]
        m = marker_dialog("Edit event", old["name"],
                          fmt(old["epoch"], current_tz_offset()))
        if m:
            old.update(m)
            refresh_markers()

    def remove_markers():
        for m in selected_markers():
            markers.remove(m)
        refresh_markers()

    def clear_markers():
        markers.clear()
        refresh_markers()

    def cut_trials_dialog():
        """Trim each run out of its clip, with padding, keeping the original
        untouched and carrying the subtitles across."""
        if not files:
            messagebox.showinfo("Cut trials", "Select the video files first.")
            return
        if not markers:
            messagebox.showinfo("Cut trials",
                                "Add your events first -- the cut points come "
                                "from them.")
            return

        dlg = tk.Toplevel(root)
        dlg.title("Cut trials out of the clips")
        dlg.transient(root)
        dlg.geometry("900x560")
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="One file per trial. The copy is a stream copy, so "
                            "the picture is untouched and the original is left "
                            "alone. Start the trial at the first phase you will "
                            "actually score \u2014 anything before it is not carried "
                            "into the trial file.",
                  wraplength=860, justify="left").pack(anchor="w")

        row0 = ttk.Frame(frm)
        row0.pack(fill="x", pady=(8, 0))
        ttk.Label(row0, text="Start each trial at").pack(side="left")
        names = []
        for m in sorted(markers, key=lambda m: m["epoch"]):
            b = base_event_name(m["name"])
            if b and not is_end_marker(b) and b not in names:
                names.append(b)
        cutfrom = tk.StringVar(value=(names[1] if len(names) > 1
                                      else "the run's first event"))
        ttk.Combobox(row0, textvariable=cutfrom, state="readonly", width=26,
                     values=["the run's first event"] + names).pack(side="left",
                                                                    padx=6)
        ttk.Label(row0, text="and end at the last event of the run",
                  foreground="#444").pack(side="left")

        row1 = ttk.Frame(frm)
        row1.pack(fill="x", pady=(6, 0))
        ttk.Label(row1, text="Burned copy").pack(side="left")
        cutpreset = tk.StringVar(value=BORIS_DEFAULT)
        ttk.Combobox(row1, textvariable=cutpreset, state="readonly", width=42,
                     values=[k for k in SUB_PRESETS
                             if SUB_PRESETS[k]["encode"]]).pack(side="left", padx=6)
        ttk.Label(row1, text="text").pack(side="left", padx=(10, 0))
        cutsize = tk.StringVar(value="Normal")
        ttk.Combobox(row1, textvariable=cutsize, state="readonly", width=12,
                     values=list(TEXT_SCALES)).pack(side="left", padx=4)

        top2 = ttk.Frame(frm)
        top2.pack(fill="x", pady=(6, 0))
        ttk.Label(top2, text="Padding").pack(side="left")
        padvar = tk.StringVar(value="10")
        ttk.Entry(top2, textvariable=padvar, width=6).pack(side="left", padx=4)
        ttk.Label(top2, text="s before and after").pack(side="left")
        withsubs = tk.BooleanVar(value=True)
        ttk.Checkbutton(top2, text="subtitles (made now if missing)",
                        variable=withsubs).pack(side="left", padx=(18, 0))
        makeproxy = tk.BooleanVar(value=True)
        ttk.Checkbutton(top2, text="burn a copy for scoring (slow)",
                        variable=makeproxy).pack(side="left", padx=(12, 0))

        ttk.Label(frm, text="With both ticked this is the whole job in one press: "
                            "timestamps, cut, and a proxy ready to score. Leave it "
                            "running and come back.",
                  wraplength=860, foreground="#444",
                  justify="left").pack(anchor="w", pady=(6, 0))

        cols = ("id", "clip", "when", "len")
        tv = ttk.Treeview(frm, columns=cols, show="headings", height=10,
                          selectmode="browse")
        for c, h, w in (("id", "trial ID (double-click to rename)", 240),
                        ("clip", "from clip", 190),
                        ("when", "real time covered", 300), ("len", "length", 80)):
            tv.heading(c, text=h)
            tv.column(c, width=w, anchor="w")
        tv.pack(fill="both", expand=True, pady=(8, 0))

        plan = []

        def rebuild():
            plan.clear()
            tv.delete(*tv.get_children())
            try:
                pad = float(padvar.get() or 0)
            except ValueError:
                pad = 0.0
            off = current_tz_offset()
            try:
                shift = float(pshift.get() or 0)
            except ValueError:
                shift = 0.0
            runs = runs_from_markers([{"epoch": m["epoch"] + shift,
                                       "name": m["name"]} for m in markers])
            n = 0
            for path in files:
                sp = filespans.get(path)
                if not sp or sp.get("error"):
                    continue
                c0, c1 = sp["epoch"], sp["epoch"] + sp["duration"]
                for run in runs:
                    want = (None if cutfrom.get() == "the run's first event"
                            else cutfrom.get())
                    a, b, from_name = trial_window(run, pad, want)
                    if b <= c0 or a >= c1:
                        continue
                    a, b = max(c0, a), min(c1, b)
                    n += 1
                    stem = os.path.splitext(os.path.basename(path))[0]
                    plan.append({"video": path, "start_abs": a, "end_abs": b,
                                 "clip_start": c0, "id": f"T{n:02d}",
                                 "from_name": from_name,
                                 "clipped": (a > run[0]["epoch"] - pad + 0.01
                                             or b < run[-1]["epoch"] + pad - 0.01)})
                    tv.insert("", "end", iid=str(len(plan) - 1),
                              values=(f"T{n:02d}", f"{stem}  ({from_name})",
                                      f"{fmt(a, off)[11:]}  \u2192  {fmt(b, off)[11:]}"
                                      + ("   (clipped by the clip's edge)"
                                         if plan[-1]["clipped"] else ""),
                                      short_duration(b - a)))
            if not plan:
                tv.insert("", "end", values=("no trials fall inside the loaded "
                                             "clips", "", "", ""))
        rebuild()
        padvar.trace_add("write", lambda *_: rebuild())
        cutfrom.trace_add("write", lambda *_: rebuild())

        def rename(_event=None):
            sel = tv.selection()
            if not sel or not plan:
                return
            i = int(sel[0])
            dlg2 = tk.Toplevel(dlg)
            dlg2.title("Trial ID")
            dlg2.transient(dlg)
            f2 = ttk.Frame(dlg2, padding=12)
            f2.pack()
            ttk.Label(f2, text="Trial ID (used in the file name)").pack(anchor="w")
            var = tk.StringVar(value=plan[i]["id"])
            e = ttk.Entry(f2, textvariable=var, width=32)
            e.pack(pady=(4, 0))
            e.focus_set()

            def ok():
                plan[i]["id"] = safe_name(var.get())
                vals = list(tv.item(sel[0], "values"))
                vals[0] = plan[i]["id"]
                tv.item(sel[0], values=vals)
                dlg2.destroy()
            ttk.Button(f2, text="OK", command=ok).pack(pady=(10, 0))
            dlg2.bind("<Return>", lambda _: ok())
            dlg2.grab_set()
        tv.bind("<Double-1>", rename)

        def go():
            if not plan:
                messagebox.showinfo("Cut trials", "Nothing to cut.", parent=dlg)
                return
            ids = [p["id"] for p in plan]
            if len(set(ids)) != len(ids):
                messagebox.showerror("Cut trials",
                                     "Two trials have the same ID. Rename one.",
                                     parent=dlg)
                return
            opts = {"subs": withsubs.get(), "proxy": makeproxy.get(),
                    "preset": cutpreset.get(),
                    "scale": TEXT_SCALES[cutsize.get()]}
            items = [dict(p) for p in plan]
            dlg.destroy()
            start_cut(items, opts)

        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(12, 0))
        ttk.Button(row, text="Close", command=dlg.destroy).pack(side="right")
        ttk.Button(row, text="Cut", command=go).pack(side="right", padx=6)
        dlg.grab_set()

    def start_cut(items, opts):
        if worker["thread"] and worker["thread"].is_alive():
            messagebox.showinfo("Busy", "Something is already running.")
            return
        worker["stop"] = False
        runbtn.config(state="disabled")
        stopbtn.config(state="normal")
        status.config(text="cutting\u2026")
        worker["thread"] = threading.Thread(target=lambda: cut_job(items, opts),
                                            daemon=True)
        worker["thread"].start()

    def cut_job(items, opts):
        try:
            total = len(items)
            msgs.put((0, total))
            ok = bad = 0
            manifest = []
            made_subs = set()          # only build a clip's subtitles once
            off = current_tz_offset()
            for i, it in enumerate(items, 1):
                if worker["stop"]:
                    say("Stopped.")
                    break
                video = it["video"]
                stem = os.path.splitext(video)[0]
                name = f"{os.path.basename(stem)}_{it['id']}"
                say(f"[{i}/{total}] {it['id']} from {os.path.basename(video)}")
                try:
                    want = it["start_abs"] - it["clip_start"]
                    kf = keyframe_at_or_before(video, want)
                    dur = it["end_abs"] - it["start_abs"] + (want - kf)
                    out = os.path.join(os.path.dirname(video), name + ".mp4")
                    if kf < want - 0.01:
                        say(f"    starts at the keyframe {want - kf:.2f} s earlier "
                            f"(stream copy cannot cut between keyframes)")
                    cmd = cut_command(video, kf, dur, out)
                    p = subprocess.run(cmd, capture_output=True, text=True,
                                       creationflags=NOWINDOW)
                    if p.returncode != 0:
                        raise RuntimeError("ffmpeg: "
                                           + (p.stderr.strip().splitlines() or
                                              ["failed"])[-1][:160])
                    say(f"    wrote {os.path.basename(out)}  "
                        f"({short_duration(dur)}, {os.path.getsize(out) / 1e6:.0f} MB)")

                    sub_out = None
                    if opts["subs"]:
                        sub = find_sidecar_subtitle(video)
                        if not sub and video not in made_subs:
                            say("    no subtitle file yet, making one\u2026")
                            info_v = container_info(video)
                            sub = make_subtitles(
                                video, info_v,
                                float(info_v.get("Duration") or 0))[0]
                            made_subs.add(video)
                        if sub and sub.lower().endswith(".srt"):
                            sub_out = os.path.join(os.path.dirname(video),
                                                   name + ".srt")
                            n = shift_srt(sub, sub_out, kf, dur)
                            say(f"    wrote {os.path.basename(sub_out)} "
                                f"({n} cues, shifted by {kf:.3f} s)")
                        elif sub:
                            say("    subtitle is not .srt, left alone")
                        else:
                            say("    no subtitle file beside the clip, skipped")

                    if opts["proxy"] and sub_out and not worker["stop"]:
                        info = container_info(out)
                        bcmd, bcwd, bout, tmp = build_burn_command(
                            out, sub_out, opts.get("preset", BORIS_DEFAULT), info,
                            text_scale=opts.get("scale", 1.0))
                        say(f"    encoding {os.path.basename(bout)}\u2026")
                        pb = subprocess.run(bcmd, cwd=bcwd, capture_output=True,
                                            text=True, creationflags=NOWINDOW)
                        if tmp and os.path.exists(tmp):
                            os.remove(tmp)
                        if pb.returncode != 0:
                            raise RuntimeError("proxy encode failed")
                        say(f"    wrote {os.path.basename(bout)}")

                    manifest.append({
                        "trial": it["id"], "source": os.path.basename(video),
                        "output": os.path.basename(out),
                        "starts": fmt(it["clip_start"] + kf, off),
                        "ends": fmt(it["clip_start"] + kf + dur, off),
                        "seconds_into_clip": f"{kf:.3f}",
                        "duration_s": f"{dur:.3f}"})
                    ok += 1
                except Exception as exc:
                    bad += 1
                    say(f"    !! {exc}")
                msgs.put((i, total))

            if manifest:
                mpath = os.path.join(os.path.dirname(items[0]["video"]),
                                     "trials.csv")
                try:
                    with open(mpath, "w", newline="", encoding="utf-8") as fh:
                        w = csv.DictWriter(fh, fieldnames=list(manifest[0].keys()))
                        w.writeheader()
                        w.writerows(manifest)
                    say(f"Wrote {os.path.basename(mpath)}")
                except Exception as exc:
                    say(f"could not write trials.csv: {exc}")
            say("")
            say(f"Finished cutting: {ok} ok, {bad} failed.")
        finally:
            root.after(0, finish)

    def burn_subs_dialog():
        """Everything about burning an already-checked subtitle file, in one
        place, so the main window stays about timestamps."""
        if not files:
            messagebox.showinfo("Burn subtitles",
                                "Select the video files first.")
            return

        chosen = [files[int(i)] for i in flist.selection()] or list(files)

        dlg = tk.Toplevel(root)
        dlg.title("Burn subtitles into video")
        dlg.transient(root)
        dlg.geometry("820x520")
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Each video is paired with the subtitle file of the "
                            "same name sitting beside it.",
                  wraplength=780, justify="left").pack(anchor="w")

        pairs = ttk.Treeview(frm, columns=("video", "sub"), show="headings",
                             height=7, selectmode="extended")
        pairs.heading("video", text="video")
        pairs.heading("sub", text="subtitle file")
        pairs.column("video", width=300, anchor="w")
        pairs.column("sub", width=460, anchor="w")
        pairs.pack(fill="both", expand=True, pady=(8, 0))
        pairs.tag_configure("missing", foreground="#a06000")

        found = {}

        def refresh_pairs():
            pairs.delete(*pairs.get_children())
            for i, v in enumerate(chosen):
                sub = found.get(v) or find_sidecar_subtitle(v)
                found[v] = sub
                pairs.insert("", "end", iid=str(i),
                             tags=() if sub else ("missing",),
                             values=(os.path.basename(v),
                                     os.path.basename(sub) if sub
                                     else "none found \u2014 use 'choose' below"))
        refresh_pairs()

        def choose_sub():
            sel = pairs.selection()
            if len(sel) != 1:
                messagebox.showinfo("Subtitle", "Select exactly one video first.",
                                    parent=dlg)
                return
            v = chosen[int(sel[0])]
            f = filedialog.askopenfilename(
                parent=dlg, title=f"Subtitle file for {os.path.basename(v)}",
                filetypes=[("Subtitles", "*.srt *.SRT *.ass *.ASS *.ssa *.vtt"),
                           ("All files", "*.*")])
            if f:
                found[v] = f
                refresh_pairs()

        ttk.Button(frm, text="choose a subtitle for the selected video\u2026",
                   command=choose_sub).pack(anchor="w", pady=(6, 0))

        box = ttk.LabelFrame(frm, text="Output", padding=10)
        box.pack(fill="x", pady=(10, 0))
        preset = tk.StringVar(value=BORIS_DEFAULT)
        ttk.Combobox(box, textvariable=preset, state="readonly", width=46,
                     values=list(SUB_PRESETS)).grid(row=0, column=0, columnspan=3,
                                                    sticky="w")
        hint = ttk.Label(box, text="", foreground="#666", wraplength=760,
                         justify="left")
        hint.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

        HINTS = {
            "Full resolution (best detail, slowest)":
                "Source resolution, nothing thrown away. Try this in BORIS "
                "first if fine detail matters -- if playback or frame stepping "
                "struggles, step down a size.",
            "4K 3840 px":
                "Most of the detail at a fraction of the decoding cost. The "
                "usual next stop if full resolution stutters.",
            "1080p 1920 px":
                "Comfortable everywhere, still detailed enough for most scoring.",
            "BORIS proxy 1280 px":
                "Small and smooth, with more detail than the 1024 px option.",
            "BORIS proxy 1024 px (safest for BORIS)":
                "H.264, constant frame rate, keyframe every second, 1024 px wide "
                "\u2014 what BORIS's own re-encode tool targets, and what the mpv "
                "player it uses handles most smoothly for frame-by-frame coding.",
            "No re-encode: attach subtitles as a switchable track":
                "Instant and lossless. The timestamps travel inside the file and "
                "can be switched on or off in any player, but are not in the "
                "pixels.",
        }

        def on_preset(*_):
            hint.config(text=HINTS.get(preset.get(), ""))
        preset.trace_add("write", on_preset)
        on_preset()

        ttk.Label(box, text="Text size").grid(row=3, column=0, sticky="w",
                                              pady=(8, 0))
        tsize = tk.StringVar(value="Normal")
        ttk.Combobox(box, textvariable=tsize, state="readonly", width=14,
                     values=list(TEXT_SCALES)).grid(row=3, column=1, sticky="w",
                                                    pady=(8, 0))

        half = tk.BooleanVar(value=False)
        ontop = tk.BooleanVar(value=False)
        usegpu = tk.BooleanVar(value=False)
        ttk.Checkbutton(box, text="halve the frame rate (59.94 \u2192 29.97)",
                        variable=half).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(box, text="subtitles at the top",
                        variable=ontop).grid(row=2, column=1, sticky="w",
                                             padx=12, pady=(8, 0))
        ttk.Checkbutton(box, text="NVIDIA GPU encode",
                        variable=usegpu).grid(row=2, column=2, sticky="w",
                                              pady=(8, 0))

        def go():
            ready = [(v, found[v]) for v in chosen if found.get(v)]
            missing = [v for v in chosen if not found.get(v)]
            if not ready:
                messagebox.showinfo("Burn subtitles",
                                    "No video has a subtitle file to burn.",
                                    parent=dlg)
                return
            if missing and not messagebox.askyesno(
                    "Burn subtitles",
                    f"{len(missing)} video(s) have no subtitle file and will be "
                    f"skipped. Continue with the other {len(ready)}?", parent=dlg):
                return
            opts = {"preset": preset.get(), "half": half.get(),
                    "top": ontop.get(), "gpu": usegpu.get(),
                    "scale": TEXT_SCALES[tsize.get()]}
            dlg.destroy()
            start_burn(ready, opts)

        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(12, 0))
        ttk.Button(row, text="Close", command=dlg.destroy).pack(side="right")
        ttk.Button(row, text="Burn", command=go).pack(side="right", padx=6)
        dlg.grab_set()

    def start_burn(pairs, opts):
        if worker["thread"] and worker["thread"].is_alive():
            messagebox.showinfo("Busy", "Something is already running.")
            return
        worker["stop"] = False
        runbtn.config(state="disabled")
        stopbtn.config(state="normal")
        status.config(text="burning\u2026")
        worker["thread"] = threading.Thread(
            target=lambda: burn_job(pairs, opts), daemon=True)
        worker["thread"].start()

    def burn_job(pairs, opts):
        try:
            total = len(pairs)
            msgs.put((0, total))
            ok = bad = 0
            for i, (video, sub) in enumerate(pairs, 1):
                if worker["stop"]:
                    say("Stopped.")
                    break
                say(f"[{i}/{total}] {os.path.basename(video)}")
                tmp = None
                try:
                    info = container_info(video)
                    cmd, cwd, out, tmp = build_burn_command(
                        video, sub, opts["preset"], info, gpu=opts["gpu"],
                        half_fps=opts["half"], on_top=opts["top"],
                        text_scale=opts.get("scale", 1.0))
                    say(f"    {os.path.basename(sub)} \u2192 "
                        f"{os.path.basename(out)}")
                    if SUB_PRESETS[opts["preset"]]["encode"]:
                        say("    encoding, this is the slow part\u2026")
                    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.PIPE, text=True,
                                         creationflags=NOWINDOW)
                    worker["proc"] = p
                    tail = []
                    for line in p.stderr:
                        line = line.strip()
                        if line:
                            tail = (tail + [line])[-3:]
                    p.wait()
                    worker["proc"] = None
                    if p.returncode != 0:
                        raise RuntimeError("ffmpeg failed: "
                                           + (" | ".join(tail) or "unknown"))
                    say(f"    wrote {os.path.basename(out)}")
                    ok += 1
                except Exception as exc:
                    bad += 1
                    say(f"    !! {exc}")
                finally:
                    if tmp and os.path.exists(tmp):
                        os.remove(tmp)
                msgs.put((i, total))
            say("")
            say(f"Finished burning: {ok} ok, {bad} failed.")
        finally:
            root.after(0, finish)

    def stop():
        worker["stop"] = True
        p = worker.get("proc")
        if p and p.poll() is None:
            p.terminate()
        say("Stopping after the current file…")

    def start():
        if not files:
            messagebox.showinfo("Nothing to do", "Select at least one video first.")
            return
        if tzmode.get() == "custom" and parse_offset(tzcustom.get()) is None:
            messagebox.showerror("Bad timezone", "Use the form -04:00 or +02:00.")
            return
        try:
            float(pshift.get() or 0)
        except ValueError:
            messagebox.showerror("Events", "Clock shift must be a number of seconds.")
            return
        worker["stop"] = False
        runbtn.config(state="disabled")
        stopbtn.config(state="normal")
        status.config(text="working…")
        worker["thread"] = threading.Thread(target=job, daemon=True)
        worker["thread"].start()

    def finish():
        runbtn.config(state="normal")
        stopbtn.config(state="disabled")
        status.config(text="done")

    # ---- the actual work --------------------------------------------------
    def job():
        try:
            total = len(files)
            msgs.put((0, total))
            ok = bad = 0
            for i, path in enumerate(files, 1):
                if worker["stop"]:
                    say("Stopped.")
                    break
                say(f"[{i}/{total}] {os.path.basename(path)}")
                try:
                    handle(path)
                    ok += 1
                except Exception as exc:
                    bad += 1
                    say(f"    !! {exc}")
                msgs.put((i, total))
            say("")
            say(f"Finished: {ok} ok, {bad} failed.")
        finally:
            root.after(0, finish)

    def make_subtitles(path, info, duration):
        """Anchor the clip, label it with the events, write <clip>.srt.

        Shared by Run and by the trial cutter, so a cut trial never has to
        depend on somebody having pressed Run first.
        """
        off = current_tz_offset(info)
        label = tz_label_for(off)
        anchor = find_anchor(path, info, 60, say, prefer=srcmode.get(),
                             tz_offset=off, deep=deep.get())
        if anchor.get("warn"):
            say(f"    ** {anchor['warn']}")
        note = {"ms": "millisecond grade", "frame": "frame grade",
                "second": "SECOND grade only"}[anchor["grade"]]
        say(f"    frame 0 = {fmt(anchor['epoch'], off)} {label}   <- {anchor['source']}")
        say(f"    {note}, rms {anchor['rms'] * 1000:.1f} ms")

        spans = ()
        if markers:
            try:
                shift = float(pshift.get() or 0)
            except ValueError:
                shift = 0.0
            spans = spans_from_markers(markers, anchor["epoch"], duration, shift)
            if spans:
                say(f"    {len(spans)} labelled span(s) from {len(markers)} events:")
                for t0, t1, name in spans:
                    say(f"      {srt_time(t0)} - {srt_time(t1)}  {name}")
            else:
                ts = sorted(m["epoch"] + shift for m in markers)
                say("    ** NONE of your events fall inside this clip, so no "
                    "labels were written")
                say(f"       this clip  : {fmt(anchor['epoch'], off)}"
                    f"  ->  {fmt(anchor['epoch'] + duration, off)}")
                say(f"       your events: {fmt(ts[0], off)}  ->  {fmt(ts[-1], off)}")
                gap = ((anchor["epoch"] - ts[-1]) if ts[-1] < anchor["epoch"]
                       else (anchor["epoch"] + duration - ts[0]))
                say(f"       {abs(gap):.0f} s ({abs(gap) / 3600:.2f} h) apart -- "
                    f"check the photo camera's clock and timezone first; "
                    f"Clock shift {gap:+.0f} would force them together")

        out = os.path.splitext(path)[0] + ".srt"
        n = write_srt(out, anchor["epoch"], off, label, duration, phases=spans)
        say(f"    wrote {os.path.basename(out)} ({n} cues)")
        return out, anchor, spans, off, label

    def handle(path):
        info = container_info(path)
        duration = float(info.get("Duration") or 0)
        stem = os.path.splitext(path)[0]

        if mode.get() == "srt":
            make_subtitles(path, info, duration)
            say("    open the video in VLC to see it")
            return

        off = current_tz_offset(info)
        label = tz_label_for(off)

        anchor = find_anchor(path, info, 60, say, prefer=srcmode.get(),
                             tz_offset=off, deep=deep.get())
        if anchor.get("warn"):
            say(f"    ** {anchor['warn']}")

        note = {"ms": "millisecond grade", "frame": "frame grade",
                "second": "SECOND grade only"}[anchor["grade"]]
        say(f"    frame 0 = {fmt(anchor['epoch'], off)} {label}   <- {anchor['source']}")
        say(f"    {note}, rms {anchor['rms'] * 1000:.1f} ms")

        spans = ()
        if markers:
            shift = float(pshift.get() or 0)
            spans = spans_from_markers(markers, anchor["epoch"], duration, shift)
            if spans:
                say(f"    {len(spans)} labelled span(s) from {len(markers)} events:")
                for t0, t1, name in spans:
                    say(f"      {srt_time(t0)} - {srt_time(t1)}  {name}")
            else:
                ts = sorted(m["epoch"] + shift for m in markers)
                say("    ** NONE of your events fall inside this clip, so no "
                    "labels were written")
                say(f"       this clip  : {fmt(anchor['epoch'], off)}"
                    f"  ->  {fmt(anchor['epoch'] + duration, off)}")
                say(f"       your events: {fmt(ts[0], off)}"
                    f"  ->  {fmt(ts[-1], off)}")
                gap = ((anchor["epoch"] - ts[-1]) if ts[-1] < anchor["epoch"]
                       else (anchor["epoch"] + duration - ts[0]))
                say(f"       {abs(gap):.0f} s ({abs(gap) / 3600:.2f} h) apart -- "
                    f"check the photo camera's clock and timezone first; "
                    f"Clock shift {gap:+.0f} would force them together")

        vf = build_filter(anchor["epoch"], off, label, info)
        for f in phase_filters(spans, info):
            vf += "," + f
        out = stem + ("_ts_preview.mp4" if preview.get() else "_ts.mp4")
        cmd = [TOOLS["ffmpeg"], "-hide_banner", "-v", "error", "-stats", "-y", "-i", path]
        if preview.get():
            cmd += ["-t", "20"]
        cmd += ["-vf", vf, "-c:v", "hevc_nvenc" if gpu.get() else "libx265",
                "-c:a", "copy", out]
        say(f"    encoding {os.path.basename(out)} …")
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                             text=True, creationflags=NOWINDOW)
        worker["proc"] = p
        tail = []
        for line in p.stderr:
            line = line.strip()
            if line:
                tail = (tail + [line])[-3:]
        p.wait()
        worker["proc"] = None
        if p.returncode != 0:
            raise RuntimeError("ffmpeg failed: " + (" | ".join(tail) or "unknown"))
        say(f"    wrote {os.path.basename(out)}")

    # ---- startup ----------------------------------------------------------
    attach_tooltip(tree, lambda ev: marker_notes.get(tree.identify_row(ev.y)))

    def retime(_=None):
        refresh_markers()
        refresh_list()
    tzbox.bind("<<ComboboxSelected>>", retime)

    refresh_tools()
    say(f"{APP_NAME} {VERSION}")
    say("")
    for t in ("exiftool", "ffmpeg", "ffprobe"):
        say(f"  {t:9s} {TOOLS[t] or 'NOT FOUND'}")
    say("")
    if not TOOLS["exiftool"]:
        say("!! exiftool NOT FOUND -- GPS timing is unavailable and any time")
        say("!! shown will be a coarse fallback. Put exiftool.exe (or the")
        say("!! file exactly as downloaded, exiftool(-k).exe) in this folder.")
        root.after(400, lambda: messagebox.showwarning(
            "exiftool missing",
            "exiftool was not found, so the millisecond GPS timing this tool "
            "exists for is unavailable.\n\nPut exiftool.exe -- or the file "
            "exactly as downloaded, exiftool(-k).exe, together with its "
            "exiftool_files folder -- next to this program and restart.\n\n"
            "You can continue, but timestamps will come from a coarse fallback "
            "and may be seconds out."))
    if not TOOLS["ffmpeg"]:
        say("ffmpeg is missing — subtitle output still works, burning does not.")
    say("Pick your files, choose an output, press Run.")
    say("")
    refresh_list()
    pump()

    if os.environ.get("GRT_AUTOTEST"):
        files.extend(discover(os.environ["GRT_AUTOTEST"].split(os.pathsep)))
        refresh_list()
        root.after(300, start)
        root.after(9000, root.destroy)

    root.mainloop()


if __name__ == "__main__":
    launch_gui()
