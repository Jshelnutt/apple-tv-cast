@echo off
.\.venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name AppleTVCast --collect-all pyatv castapp.py
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Apple TV Cast.lnk');$s.TargetPath='%CD%\dist\AppleTVCast.exe';$s.Save()"
echo Done. Look for "Apple TV Cast" on your Desktop.
