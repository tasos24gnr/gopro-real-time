# Camera clocks and timezones

Why files from the same day report different UTC offsets, what it does and does not affect, and how to make it stop.

## The short version

A timezone offset is a **legal constant for a region**, not a measurement. It changes twice a year, at 02:00 on a defined Sunday, for an entire zone at once. It does not vary between morning and afternoon, and a camera cannot change it by itself.

The offset stored in a file is therefore not an observation of anything. **It is a copy of a setting inside that camera at the moment recording started.** When files disagree, the cameras disagree — or something changed one of them.

## The tags, and which to trust

Every GoPro MP4 stores the same instant twice:

| Tag | Meaning |
|---|---|
| `CreateDate` | **UTC.** The absolute moment. |
| `CreationDate` + `TimeZone` | The same moment as local civil time, plus the camera's claimed offset. |
| `File Modification/Creation Date` | Filesystem dates. **Rewritten when you copy from an SD card** — they record the copy, not the recording. |

`CreateDate` is the record. `TimeZone` is a label attached to it. A wrong label shifts the description, never the underlying time — which is why a mis-set camera loses nothing that cannot be recovered.

> **Note on `-n`.** With ExifTool's numeric flag, `TimeZone` comes back as **minutes** (`-240`) rather than `-04:00`. Both forms are parsed by this application; a parser that only handles the second form will silently fall back to UTC.

## What makes them diverge

Only three things realistically write that setting:

**A phone connecting via the Quik app.** The app pushes the phone's time and timezone on connect. Different phones, or one phone at different moments, produce different values. A camera that did not pair that day silently keeps its old setting, with no confirmation either way — which is why *"I synced them all"* and *"they all got synced"* are different statements.

**Someone in Preferences → Regional.** Ten seconds, easy to forget.

**A daylight-saving flag, where the model has one.** On cameras with a separate DST switch, the zone and the flag add together:

| Zone setting | DST | Recorded offset | |
|---|---|---|---|
| UTC−05:00 | off | −05:00 | DST forgotten |
| UTC−05:00 | on | **−04:00** | correct for EDT |
| UTC−04:00 | on | −03:00 | DST applied twice |

That is the signature of a spread like −05/−04/−03 across cameras in a single location: not drift, but the same correct intent expressed through two settings that different bodies combine differently. Newer models may fold DST into the timezone list, in which case the spread comes directly from the `Time Zone` value alone.

## What it affects

**Phase alignment: not affected.** The position of a phase inside a video is a subtraction — photograph time minus video start time. Convert both with the same offset and the offset cancels. Provided the photograph and the video come from the same camera, or from cameras that agree, the result is exact regardless of whether the offset is right.

**The displayed clock: not affected.** The application derives a UTC anchor and formats it back to local time with the same offset, so the two cancel. The clock shown is the camera's local clock — the time you would have read off a watch. Only the suffix after it reflects the camera's belief.

**Absolute UTC claims: affected.** A time displayed as `10:47:20 UTC-0300` when the camera was in fact at UTC−04:00 implies a UTC moment one hour earlier than reality. Anyone converting the displayed time using the printed suffix lands an hour off.

**Combining cameras: affected.** Two cameras an hour apart will place the same real moment an hour apart. Nothing in the metadata reveals which is right, because each is internally consistent. Only an external reference — a filmed clock, or a contemporaneous written record — resolves it.

## Auditing a set of files

```powershell
exiftool -T -FileName -CameraSerialNumber -CreationDate -CreateDate -TimeZone ^
         -r -ext MP4 -ext JPG "D:\Session" > audit.tsv
```

Open in a spreadsheet and sort by serial, then by date.

- **Each serial holds one consistent value, values differ between serials** → the cameras were never set the same. Expected, and harmless within a session.
- **One serial shows two values on the same day** → something touched that camera mid-session. The clip where it flips shows when.

## Fixing it

Set every camera identically, then **verify by recording**, not by reading the menu:

```powershell
exiftool -T -FileName -CameraSerialNumber -TimeZone -CreationDate "E:\test\*.MP4"
```

Every row should read the same offset. Either convention works provided it is consistent:

- Zone **−05:00**, DST **on** → records −04:00 ✓ (survives the November change if the camera handles it)
- Zone **−04:00**, DST **off** → records −04:00 ✓ (simpler; must be changed manually in November)

[GoPro Labs' Precision Date and Time](https://gopro.github.io/labs/control/precisiontime/) applies timezone and DST to every camera from one animated QR code, which removes both the pairing step that can silently fail and the menu that can be set inconsistently.

## Reporting it

If a spread has already occurred in collected data, it is documentable rather than disqualifying:

> Camera-reported timezone offsets varied between bodies (UTC−03:00, −04:00, −05:00), reflecting differing per-camera regional settings rather than any variation in local civil time; the study region observed EDT (UTC−04:00) throughout the study period. All timestamps were normalised to UTC and converted using a single fixed offset of −04:00, verified against contemporaneous written records of clock time.
