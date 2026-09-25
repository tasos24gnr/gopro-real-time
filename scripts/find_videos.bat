@echo off
REM ===================================================================
REM  find_videos.bat - list videos recorded in a given time window
REM
REM  Searches by the time INSIDE each file (the camera's own CreationDate),
REM  not by the Windows file dates. Windows rewrites those when you copy
REM  from an SD card, so they say when the copy happened, not when you shot.
REM
REM  Default: 27 August 2026, 09:30 to 11:30, under "D:\Lab Tests"
REM
REM  Usage:
REM    find_videos.bat
REM    find_videos.bat 2026:08:27 09:30 11:30 "D:\Lab Tests"
REM
REM  Needs exiftool.exe beside this file, or on PATH.
REM ===================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "DAY=%~1"
set "FROM=%~2"
set "TO=%~3"
set "ROOT=%~4"
if "%DAY%"==""  set "DAY=2026:08:27"
if "%FROM%"=="" set "FROM=09:30"
if "%TO%"==""   set "TO=11:30"
if "%ROOT%"=="" set "ROOT=D:\Lab Tests"

REM --- find exiftool -------------------------------------------------
set "ET="
if exist "exiftool.exe" set "ET=exiftool.exe"
if not defined ET if exist "exiftool(-k).exe" set "ET=exiftool(-k).exe"
if not defined ET (
  where exiftool.exe >nul 2>&1 && set "ET=exiftool.exe"
)
if not defined ET (
  echo Could not find exiftool.exe. Put it in this folder, together with
  echo its exiftool_files folder, and run this again.
  pause & exit /b 1
)

if not exist "%ROOT%" (
  echo Folder not found: %ROOT%
  pause & exit /b 1
)

set "START=%DAY% %FROM%:00"
set "END=%DAY% %TO%:59"
set "TAG=%DAY::=%_%FROM::=%-%TO::=%"
set "OUT=videos_%TAG%.csv"

echo.
echo Searching : %ROOT%   (including subfolders)
echo Window    : %START%  to  %END%
echo Source    : the recording time stored inside each file
echo.

REM -d forces a plain date format, so a trailing timezone offset cannot
REM upset the comparison. -r searches subfolders.
"%ET%" -r -q -ext MP4 -ext MOV -ext LRV ^
  -d "%%Y:%%m:%%d %%H:%%M:%%S" ^
  -if "$CreationDate ge '%START%' and $CreationDate le '%END%'" ^
  -T -FileName -CreationDate -TimeZone -Duration -CameraSerialNumber ^
  "%ROOT%"

"%ET%" -r -q -ext MP4 -ext MOV -ext LRV ^
  -d "%%Y:%%m:%%d %%H:%%M:%%S" ^
  -if "$CreationDate ge '%START%' and $CreationDate le '%END%'" ^
  -csv -FileName -Directory -CreationDate -CreateDate -TimeZone -Duration ^
  -ImageWidth -ImageHeight -VideoFrameRate -CameraSerialNumber ^
  "%ROOT%" > "%OUT%"

set HITS=0
for /f %%A in ('find /c /v "" ^< "%OUT%"') do set /a HITS=%%A-1
if !HITS! LSS 0 set HITS=0

echo.
echo %HITS% file(s) matched. Full details written to %OUT%
echo.

if !HITS! GTR 0 (
  choice /m "Copy the matching files into a subfolder here"
  if not errorlevel 2 (
    set "DEST=%~dp0matched_%TAG%"
    mkdir "!DEST!" 2>nul
    for /f "usebackq skip=1 tokens=1,2 delims=," %%A in ("%OUT%") do (
      if exist "%%~A" copy /y "%%~A" "!DEST!\" >nul
    )
    echo Copied into !DEST!
  )
)

echo.
echo If nothing matched, try widening the window, or check the date:
echo   "%ET%" -r -q -ext MP4 -T -FileName -CreationDate "%ROOT%"
echo which lists every video with its recorded time.
echo.
pause
exit /b 0
