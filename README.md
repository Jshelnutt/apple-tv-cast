# Apple TV Cast

Free, real-time mirroring of a Windows PC's screen **and sound** to an Apple TV,
with one big **Cast to Apple TV** button.

The window (`castapp.py`, Python/Tk, built into `AppleTVCast.exe` with PyInstaller)
is a front end for **doubletake.exe**, from
[Jshelnutt/doubletake](https://github.com/Jshelnutt/doubletake/tree/windows) (branch
`windows`), a Windows port of the open-source AirPlay mirroring sender
[omarroth/doubletake](https://github.com/omarroth/doubletake) (LGPL-3.0).

* **Set up Apple TV** finds the Apple TV (pyatv), then runs
  `doubletake.exe -target <ip> -pair -pair-only` and asks for the code shown on the TV.
  The pairing keys are saved in `%APPDATA%\AppleTVCast\doubletake-credentials.json`.
  The TV's name and address go in `%APPDATA%\AppleTVCast\config.json`.
* **Cast / Stop** starts and stops `doubletake.exe -target <ip> -creds ... -quit-on-stdin-eof`.
  The log is written to `%APPDATA%\AppleTVCast\cast.log`.
* The picture is captured with `ffmpeg.exe` (ddagrab/gdigrab, GPU H.264 encoder when available).
  Sound comes from Windows' own speaker loopback (WASAPI), so no Stereo Mix is needed.

Expected delay is well under a second, not the 3-8 s of the old HLS version.

Tests: `DOUBLETAKE_BIN_DIR=<folder with doubletake + doubletake-test-receiver> pytest tests`
(pairs, casts and stops against doubletake's built-in fake Apple TV).
