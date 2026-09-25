GoPro Real Time 1.0
===================

Recovers the true recording time of GoPro footage, labels the phases of an
experiment, and cuts trial clips ready for behavioural scoring.


GETTING STARTED
---------------
Double-click GoProRealTime.exe. There is nothing to install.

The first time you run it on a PC, Windows shows "Windows protected your PC".
Click "More info", then "Run anyway". That warning appears for any program
without a paid code-signing certificate; it is not specific to this one.

Keep the contents of this folder together. The program uses the ffmpeg.exe,
ffprobe.exe and exiftool.exe sitting beside it, and will not work if the .exe
is moved out on its own. Moving or copying the whole folder is fine, including
onto a USB stick.


WHAT IT DOES
------------
1. Select your video files. The table shows when each recording really
   started and ended.

2. Add events - the moments each phase of the experiment began. "Match photos
   to clips" reads a folder of photographs and offers only those taken while
   the loaded videos were recording.

3. "Run" writes a subtitle file next to each video. Open the video in VLC or
   mpv and the real clock appears, labelled with the phase.

4. "Cut trials" makes one file per trial, with padding either side, and can
   burn the timestamp into a copy for scoring. With both boxes ticked this is
   the whole job in one press; leave it running and come back.

Original recordings are never modified. Everything is written as new files
alongside them.


A NOTE ON TIME
--------------
The clock shown comes from the camera's own metadata. If a camera's timezone
setting is wrong, the time displayed is still the local clock time it recorded,
but the UTC label after it will be wrong by that amount. Timing within a
recording, and between recordings from the same camera, is unaffected.

The log reports how precise each file's timestamp is: "millisecond grade" means
GPS-disciplined time, "frame grade" the camera's timecode track, and "SECOND
grade only" the file's creation date.


MORE
----
Full documentation is in the docs folder and in README.md:

  PROTOCOL.md          field and analysis procedure, and methods text
  BORIS.md             preparing footage for behavioural scoring
  TIMEZONES.md         why camera clocks disagree, and how to fix them
  TROUBLESHOOTING.md   what the messages mean
