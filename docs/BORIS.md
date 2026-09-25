# Preparing footage for BORIS

[BORIS](https://www.boris.unito.it) is free, open-source event-logging software for behavioural coding (Friard & Gamba, 2016). This describes how to get GoPro footage into a state where it plays and frame-steps reliably there.

## What BORIS needs

From version 8 onward, BORIS plays video through the **mpv** library. Its own FAQ is direct about the consequence: to be used with BORIS, a video must play well in mpv. So "will it work in BORIS" is really "will mpv decode it smoothly and step frames reliably".

Native GoPro footage is the hard case — 5.3K HEVC, 10-bit, 59.94 fps, ~120 Mbps. It is legal, it is not corrupt, and it will still make frame-by-frame coding painful on most machines, because the decoding cost per frame is enormous.

BORIS ships its own re-encode tool (**Tools → Re-encode/resize video**) which resizes to a default of 1024 px wide for exactly this reason. The presets here target the same thing, with the timestamp and phase label already rendered in.

## The presets

Every burned preset produces the same container and codec settings, differing only in resolution:

- **H.264 High profile**, not HEVC — mpv decodes it faster and more universally
- **`yuv420p`**, not 10-bit — the widest-compatibility pixel format
- **Constant frame rate** — variable frame rate is the usual cause of frame-stepping drifting out of sync
- **Keyframe every second** (`-g` = fps, `-sc_threshold 0`) — makes seeking and stepping backwards responsive
- **`+faststart`** — the index is at the front of the file

| Preset | Width | When |
|---|---|---|
| Full resolution | source | Fine-scale behaviour where detail is the constraint. Try it first; step down if playback struggles. |
| 4K | 3840 px | Most of the detail, far cheaper to decode. The usual next stop. |
| 1080p | 1920 px | Comfortable on any machine. |
| BORIS proxy | 1280 px | Small and smooth, more detail than 1024. |
| BORIS proxy | 1024 px | Matches BORIS's own target. The safest choice. |

There is no need to guess: burn one trial, open it in BORIS, and try frame-stepping. If it is smooth, use that preset for the batch.

## Timing inside BORIS

BORIS codes relative to the start of the media file. With one file per trial, `t = 0` is the start of the trial, which is usually what you want — every observation starts at zero and elapsed times are directly comparable between trials.

To recover absolute time, add the trial's start time from `trials.csv`, which the cutter writes alongside the clips:

```
trial,source,output,starts,ends,seconds_into_clip,duration_s
T01,GX010113.MP4,GX010113_T01.mp4,2026-08-18 10:47:10.000,2026-08-18 10:53:32.000,368.000,382.000
```

Because the timestamp is also rendered into the image, the absolute time of any frame can be read directly off the screen as a cross-check.

## Why the overlay is burned in rather than a sidecar

For scoring, the timestamp needs to be in the pixels. A subtitle track can be switched off, may not survive a copy, and will not appear in a screenshot or a figure. Burning it in means the frame carries its own ground truth: a clip taken out of context is still self-documenting, and anyone reviewing the scoring can verify a timestamp rather than trusting a filename.

The sidecar `.srt` remains the better format for *reviewing* footage — instant to produce, lossless, toggleable — which is why the application writes both.

## Speed

Encoding a proxy is dominated by **decoding the source**, not by producing the output. Measured on a 5.3K HEVC clip, single core:

| Step | Time for 5 s of footage |
|---|---|
| Decoding alone | 20.7 s |
| Decode + scale + subtitles + H.264 encode | 25.0 s |
| Same, at half frame rate | 24.2 s |
| Encoding alone, from a 1024p source | 1.8 s |

Decoding is ~83% of the work. Three consequences:

**GPU encoding helps less than expected.** It targets the 7% that is already fast. Tick it if you have an NVIDIA card, but do not expect it to transform the runtime.

**Halving the frame rate barely helps either** — every frame is still decoded before being discarded. It is still worth ticking for BORIS's sake, because it halves what BORIS must decode during scoring.

**Cutting first is a speed feature.** `-ss` placed before `-i` seeks without decoding what it skips, so a trial starting eight minutes into a clip costs nothing for those eight minutes. Cutting trials before burning, which is what *Cut trials…* does, removes that work entirely.

## If the source is too slow to transcode

Two options worth knowing about:

**LRV proxies.** GoPro writes a low-resolution proxy beside every clip (`GX013784.MP4` → `GL013784.LRV`). Burning onto that instead of the original was ~29× faster in testing, because the decode is trivial. Two caveats: the resolution varies by model and may be far too low for scoring, and the files only appear when the SD card is read directly — they are not exposed when the camera is connected over USB.

**GoPro Labs proxy support.** With the [Proxy File Support](https://gopro.github.io/labs/control/proxies/) extension enabled, the camera writes editing-grade proxies during capture, into a `Proxies` folder. The transcoding step then disappears entirely. The trade-off is stated in GoPro's own documentation: with the feature enabled, the absence of LRVs means the Quik app cannot preview video on the camera.

## Citation

> Friard, O. & Gamba, M. (2016). BORIS: a free, versatile open-source event-logging software for video/audio coding and live observations. *Methods in Ecology and Evolution*, 7(11), 1325–1330. <https://doi.org/10.1111/2041-210X.12584>
