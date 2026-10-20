# Windows install (PowerShell, normal user)
```powershell
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
winget install -e --id Git.Git
# open a NEW PowerShell window so PATH updates
cd $HOME; git clone https://github.com/Jshelnutt/apple-tv-cast.git; cd apple-tv-cast
py -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt pyinstaller
.\build.bat
```
(The repo is private, so git asks you to sign in to GitHub. Or download the ZIP instead.)

Allow Windows Firewall access for **Private networks** when it asks. The Apple TV must be able to reach port 8765.

`build.bat` creates `dist\AppleTVCast.exe` and puts an **Apple TV Cast** shortcut on the Desktop. ffmpeg must be on PATH, or you can copy `ffmpeg.exe` next to the exe.
