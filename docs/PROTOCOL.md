# Protocol

Field procedure, analysis procedure, and methods text suitable for adaptation into a paper or thesis.

---

## 1. Before recording

### Set every camera from one source

Camera clocks drift independently and their timezone settings are not synchronised by anything. Set them all, from one reference, at the start of each shoot day.

- The GoPro Quik app pushes the phone's time **and** timezone when it connects.
- [GoPro Labs' Precision Date and Time](https://gopro.github.io/labs/control/precisiontime/) applies the same values to every camera from a single animated QR code, with no pairing step that can silently fail.

Either way, apply the same setting to every body, including any camera used for the marker photographs.

### Verify by recording, not by reading the menu

A sync you performed and a sync that landed are different claims. Record two seconds on each camera and read the result back:

```powershell
exiftool -T -FileName -CameraSerialNumber -TimeZone -CreationDate "E:\test\*.MP4"
```

Every row should show the same offset. This takes a minute and catches a mis-set camera while it can still be fixed. See [TIMEZONES.md](TIMEZONES.md) for what the values mean.

### Film a time reference

Where absolute timing matters, record a few seconds of a millisecond clock — [time.is](https://time.is), or any NTP-disciplined display — on every camera at the start of each session.

This is the single step that makes timing claims defensible rather than assumed. It is an independent reference captured *in the data*, so a clock error found later becomes measurable instead of fatal. It also removes any dependence on GPS lock, which is unreliable indoors and under cover.

If a reference was not filmed, an independent contemporaneous record — times written into a lab notebook or spreadsheet, even to the minute — still resolves the one-hour class of error, which is the one that actually occurs.

### Enable GPS, and wait for lock

Absolute timing to the millisecond requires a GPS fix. A cold start outdoors takes 30–90 seconds; indoors or under structure the receiver may never lock. A camera that is powered but unlocked still writes telemetry, with a placeholder date and a dilution-of-precision value of 99.99 — the application rejects these, but they cannot be turned into a usable time after the fact.

---

## 2. During the session

Photograph the start of each phase. One photograph per boundary, plus one to close the final phase:

| Photograph | Marks |
|---|---|
| 1 | Habituation begins |
| 2 | Exposure begins (habituation ends) |
| 3 | Post-exposure begins (exposure ends) |
| 4 | End of trial |

Each event runs until the next, so *n* photographs define *n − 1* labelled phases. For control trials the same four photographs are taken and the procedure mimicked without the treatment; phases are then named *Sham exposure* and *Sham post-exposure*.

Start and stop the video recording per trial where practical. A trial contained within a single clip needs no concatenation and no reasoning about chapter boundaries.

Record the clock time of each phase in a notebook or spreadsheet as well. It costs seconds and is the cross-check that later validates the metadata.

### After a battery change

A battery swap is the realistic risk to the clock. Re-verify, and if a time reference is in use, film it again. Sleep and power-off do not affect the clock; the real-time clock runs from the main battery.

---

## 3. Analysis

### Extract the metadata

One pass over the session folder, both file types, producing the table that documents the analysis:

```powershell
exiftool -csv -FileName -FileType -CameraSerialNumber ^
         -CreationDate -CreateDate -DateTimeOriginal -SubSecTimeOriginal ^
         -TimeZone -Duration -r -ext MP4 -ext JPG "D:\Session\2026-08-18" > session.csv
```

Retain `session.csv` with the data. It is the record that timing was verified rather than assumed.

### Compute phase positions

For each file, convert its own local time to UTC using **its own** recorded offset:

- video start = `CreationDate` + `TimeZone`, or equivalently `CreateDate`, which is already UTC
- photograph time = `DateTimeOriginal` (+ `SubSecTimeOriginal`) + `TimeZone`

Then:

> **position in video = photograph time − video start time**

Converting both sides with the same offset makes any timezone error cancel out, provided both files come from the same camera. This is the reason phase alignment survives the timezone inconsistencies described in [TIMEZONES.md](TIMEZONES.md) — and the reason the one protocol rule is: **do not mix sessions or cameras within a single alignment.**

### In the application

1. **Select video files** — confirm each clip's recording window.
2. **Match photos to clips…** — select the session's photograph folder; only those taken during the loaded recordings are offered. Add them as a run.
3. Confirm every event shows ✓ in the *in a clip* column. A ⚠ means the event falls outside every loaded clip; hovering gives the reason and the size of the gap.
4. **Cut trials…** — set the first phase to include and the padding, then run.

Verify before committing to a batch: open one clip with its subtitle file and check that the displayed clock matches the contemporaneous record, and that phase boundaries fall where expected.

---

## 4. Methods text

Adapt as appropriate. Fill in the bracketed values from your own `session.csv`.

> **Video timing and phase annotation.** Continuous video was recorded at 5.3K/59.94 fps (GoPro HERO13 Black). The start and end of each experimental phase were marked by a still photograph. Phase boundaries were recovered from file metadata rather than by manual review of the footage.
>
> Timestamps were extracted with ExifTool [version]: `DateTimeOriginal` (with `SubSecTimeOriginal` where recorded) for photographs, and `CreationDate` with `TimeZone` for video files. All timestamps were converted to UTC using each file's own recorded offset, removing any dependence on per-camera regional settings. The position of each phase boundary within a recording was computed as the difference between the photograph's timestamp and the video's start time.
>
> Boundaries were verified by inspection: a timestamp overlay derived from the video's own metadata was rendered as a subtitle track and checked against the photographic record and contemporaneous written records of clock time. Trial clips were then extracted by lossless stream copy with [10] s of padding at each boundary; original recordings were retained unmodified. A manifest recording the mapping from each trial clip to its source file, offset and duration was generated automatically and is archived with the data.
>
> [*Where GPS lock was achieved:*] Absolute recording times were derived from GPS-disciplined UTC timestamps in the camera's GPMF telemetry track, fitted by least squares against the video timeline over the full clip (residual RMS [x] ms).
>
> [*Where it was not:*] GPS lock was not achieved during recording, so absolute times derive from each camera's internal clock and are accurate to approximately ±1 s. Relative timing within and between recordings from the same camera is unaffected, as it derives from the video's presentation timestamps. Camera-reported timezone offsets were found to vary between bodies ([−03:00, −04:00, −05:00]), reflecting differing regional settings rather than any variation in local civil time; all times were therefore normalised to UTC and converted using a single fixed offset of [−04:00], verified against contemporaneous written records.
>
> **Behavioural scoring.** Trial clips were transcoded to [1024]-px-wide H.264 proxies with the timestamp and phase label rendered into the image, and scored in BORIS [version] (Friard & Gamba, 2016). Because observations in BORIS are timed relative to the start of the media file, absolute times were recovered by adding each trial's start time as recorded in the trial manifest.

---

## 5. What to archive

| | |
|---|---|
| Original recordings | Unmodified, as written by the camera |
| Marker photographs | Unmodified |
| `session.csv` | Metadata of every file in the session |
| `trials.csv` | Mapping of every trial clip to its source, offset and duration |
| `<video>.srt` | Timestamp and phase track for each source recording |
| Contemporaneous records | The notebook or spreadsheet times |

Trial clips and scoring proxies are reproducible from the originals plus these tables, so they need not be archived if storage is constrained — but the tables must be.
