# Windows install (PowerShell, normal user)
```powershell
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
winget install -e --id Git.Git
# open a NEW PowerShell window so PATH updates
cd $HOME; git clone https://github.com/Jshelnutt/apple-tv-cast.git; cd apple-tv-cast
# put doubletake.exe in this folder (see below), then:
py -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt pyinstaller
.\build.bat
```
**doubletake.exe**: build it from the `windows` branch of Jshelnutt/doubletake
(`GOOS=windows go build -o doubletake.exe ./cmd/doubletake`), or copy a ready-built one,
and drop it into the `apple-tv-cast` folder. `build.bat` bundles it, plus ffmpeg.exe if
it finds one, into `dist\AppleTVCast.exe` and makes the **Apple TV Cast** Desktop shortcut.

On the Apple TV, set Settings > AirPlay and HomeKit > Allow Access to "Everyone on the
same network". When Windows asks about the firewall, allow **Private networks**.
Run **Set up Apple TV** once (it pairs again with doubletake; the old pairing isn't reused).
