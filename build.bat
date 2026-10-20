@echo off
rem Needs doubletake.exe in this folder (from Jshelnutt/doubletake, branch windows).
if not exist doubletake.exe (echo doubletake.exe is missing from this folder & exit /b 1)
set FF=
for /f "delims=" %%F in ('where ffmpeg 2^>nul') do if not defined FF set FF=%%F
if exist ffmpeg.exe set FF=%CD%\ffmpeg.exe
set ADD=--add-binary "doubletake.exe;."
if defined FF set ADD=%ADD% --add-binary "%FF%;."
.\.venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name AppleTVCast --collect-all pyatv %ADD% castapp.py
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Apple TV Cast.lnk');$s.TargetPath='%CD%\dist\AppleTVCast.exe';$s.Save()"
echo Done. Look for "Apple TV Cast" on your Desktop.
