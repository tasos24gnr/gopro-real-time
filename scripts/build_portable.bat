@echo off
REM ===================================================================
REM  Builds a fully portable GoPro Real Time for Windows.
REM
REM  Produces:  dist\GoProRealTime\           the whole program
REM             GoProRealTime_portable.zip    send this to anyone
REM
REM  The person you send it to needs NOTHING installed. They unzip it
REM  and double-click. No Python, no ffmpeg, no exiftool, no PATH.
REM
REM  You only need to do this once, on a Windows PC that has Python.
REM  Run it from the repository root, or from scripts\ inside it. Add:
REM      ffmpeg.exe   ffprobe.exe   exiftool.exe   exiftool_files\
REM  (these are not in the repository; see the README for where to get them)
REM ===================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Work from wherever GoProRealTime.pyw actually is: beside this script, or
REM one level up when the script is run from scripts\ in the repository.
if not exist GoProRealTime.pyw if exist "..\GoProRealTime.pyw" cd ..
if exist assets\scallop.ico if not exist scallop.ico copy /y assets\scallop.ico scallop.ico >nul

echo.
echo === Checking what is in this folder =========================
set STOP=0
if not exist GoProRealTime.pyw (
  echo   MISSING: GoProRealTime.pyw
  set STOP=1
) else ( echo   found: GoProRealTime.pyw )

for %%F in (ffmpeg.exe ffprobe.exe) do (
  if not exist %%F ( echo   MISSING: %%F & set STOP=1 ) else ( echo   found: %%F )
)

set HAVEXIF=0
if exist exiftool.exe        ( echo   found: exiftool.exe & set HAVEXIF=1 )
if exist "exiftool(-k).exe"  ( echo   found: exiftool^(-k^).exe & set HAVEXIF=1 )
if "!HAVEXIF!"=="0" ( echo   MISSING: exiftool.exe & set STOP=1 )
if not exist exiftool_files ( echo   MISSING: exiftool_files folder & set STOP=1 ) else ( echo   found: exiftool_files\ )

if "!STOP!"=="1" (
  echo.
  echo Something above is missing. Get them from:
  echo   ffmpeg + ffprobe : https://www.gyan.dev/ffmpeg/builds/  ^(essentials build, look in bin\^)
  echo   exiftool         : https://exiftool.org  ^(Windows package: keep exiftool_files next to the exe^)
  echo.
  pause & exit /b 1
)

echo.
echo === Building ================================================
py -m pip install --upgrade --quiet pyinstaller || goto :err
copy /y GoProRealTime.pyw grt_main.py >nul

set ICON=
if exist scallop.ico set ICON=--icon scallop.ico

REM --noupx: compressed executables trip antivirus scanners for no gain here.
py -m PyInstaller --noconfirm --clean --windowed --noupx ^
   --name GoProRealTime %ICON% grt_main.py || goto :err

echo.
echo === Bundling the helper programs ============================
REM They sit BESIDE the exe rather than inside it: the app looks in its own
REM folder first, the build stays small, and startup is instant.
for %%F in (ffmpeg.exe ffprobe.exe exiftool.exe) do (
  if exist %%F copy /y %%F dist\GoProRealTime\ >nul & echo   + %%F
)
if exist "exiftool(-k).exe" if not exist exiftool.exe (
  copy /y "exiftool(-k).exe" dist\GoProRealTime\exiftool.exe >nul
  echo   + exiftool^(-k^).exe  ^(copied in as exiftool.exe^)
)
if exist exiftool_files xcopy /e /i /y /q exiftool_files dist\GoProRealTime\exiftool_files >nul & echo   + exiftool_files\
if exist README_FIRST.txt copy /y README_FIRST.txt dist\GoProRealTime\ >nul
if exist README.md copy /y README.md dist\GoProRealTime\ >nul
if exist LICENSE copy /y LICENSE dist\GoProRealTime\ >nul
if exist docs xcopy /e /i /y /q docs dist\GoProRealTime\docs >nul

echo.
echo === Zipping =================================================
if exist GoProRealTime_portable.zip del GoProRealTime_portable.zip
powershell -nologo -command ^
  "Compress-Archive -Path 'dist\GoProRealTime\*' -DestinationPath 'GoProRealTime_portable.zip' -CompressionLevel Optimal" || goto :err

del grt_main.py >nul 2>&1
for %%A in (GoProRealTime_portable.zip) do set ZIPMB=%%~zA
set /a ZIPMB=!ZIPMB!/1048576

echo.
echo === Done ====================================================
echo   Folder : dist\GoProRealTime\GoProRealTime.exe
echo   Zip    : GoProRealTime_portable.zip  (!ZIPMB! MB)
echo.
echo Send the zip. They unzip it anywhere and double-click
echo GoProRealTime.exe. Nothing to install.
echo.
echo First launch on each PC shows "Windows protected your PC".
echo That is SmartScreen reacting to an unsigned program:
echo click More info, then Run anyway.
echo.
pause
exit /b 0

:err
del grt_main.py >nul 2>&1
echo.
echo Build failed. Check that Python is installed:  py --version
pause
exit /b 1
