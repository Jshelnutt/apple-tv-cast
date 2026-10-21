# Apple TV Cast (unofficial)

Free, real-time mirroring of a Windows PC's screen **and sound** to an Apple TV,
with one big **Cast to Apple TV** button.

> **Unofficial.** This project is not affiliated with, authorized, sponsored or
> endorsed by Apple Inc. AirPlay, Apple TV and HomePod are trademarks of Apple Inc.,
> registered in the U.S. and other countries. They are used here only to describe
> what the software works with.

> **No warranty.** This software is provided "AS IS", without warranty of any kind,
> express or implied. Use it at your own risk. See [LICENSE](LICENSE).

> **No support.** This is a personal project shared as-is. The author can't offer
> help, and issues or questions may not be answered. A future Apple software update
> may stop it from working at any time.

## Setup (Windows 10/11)

1. Download `AppleTVCast.zip` from the [latest release](../../releases/latest).
2. Unzip it into a folder (right-click > **Extract All**). Keep `AppleTVCast.exe`
   and `ffmpeg.exe` together in the same folder.
3. Run `AppleTVCast.exe`. If Windows SmartScreen warns you, choose
   **More info > Run anyway** (the app isn't code-signed). Allow it through the
   Windows firewall on private networks.
4. Click **Set up Apple TV**, pick your Apple TV, and type the code shown on the TV.
   Then click **Cast to Apple TV**.

**Using HomePods for sound?** While casting, set the Apple TV's Audio Output
(Apple TV Settings > Video and Audio > Audio Output) to something other than the
HomePods, for example the TV's own speakers. If the Apple TV is sending its sound
to the HomePods, it closes the mirror as soon as the PC connects to them. You can
switch it back when you're done casting.

The PC and the Apple TV must be on the same home network.

## Known limitations

* Windows only. Tested with one Apple TV 4K setup; other models are untested.
* Built on reverse-engineered AirPlay. Apple could break it with any update.
* Delay is usually under a second, but not zero. It's fine for slides and video,
  not ideal for fast games.
* Sending sound directly to HomePods adds a fixed picture delay to keep them in
  sync, and requires the Apple TV audio-output change described above.
* Sound through ordinary TV speakers (via the Apple TV) should work but has had
  little testing.
* Protected video (some streaming apps or DRM content) may show black.
* The app is not code-signed, so Windows may warn the first time you run it.

## How it works

The window (`castapp.py`, Python/Tk, built into `AppleTVCast.exe` with PyInstaller)
is a front end for **doubletake.exe**, from
[Jshelnutt/doubletake](https://github.com/Jshelnutt/doubletake/tree/windows)
(branch `windows`), a Windows port of the open-source AirPlay mirroring sender
[omarroth/doubletake](https://github.com/omarroth/doubletake).

* **Set up Apple TV** finds the Apple TV (pyatv), then pairs with
  `doubletake.exe -target <ip> -pair -pair-only`. Pairing keys are saved in
  `%APPDATA%\AppleTVCast\doubletake-credentials.json`, settings in
  `%APPDATA%\AppleTVCast\config.json`.
* **Cast / Stop** starts and stops `doubletake.exe`. The log is written to
  `%APPDATA%\AppleTVCast\cast.log`.
* The picture is captured with `ffmpeg.exe` (ddagrab/gdigrab, GPU H.264 encoder when
  available). Sound comes from Windows' speaker loopback (WASAPI).
* Optional HomePod mode sends PC sound straight to HomePods with pyatv (RAOP).

Build: see `build.bat` and [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md).
Tests: `DOUBLETAKE_BIN_DIR=<folder with doubletake + doubletake-test-receiver> pytest tests`.

## Credits

This app would not exist without these open-source projects:

* [doubletake](https://github.com/omarroth/doubletake) by Omar Roth and contributors
  (LGPL-3.0): the AirPlay mirroring sender.
* [pyatv](https://github.com/postlund/pyatv) by Pierre Ståhl and contributors (MIT):
  Apple TV discovery and HomePod audio.
* [FFmpeg](https://ffmpeg.org) (the bundled build is GPL-3.0, from
  [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)): screen capture and video encoding.
* [Python](https://www.python.org) (PSF License) and
  [PyInstaller](https://pyinstaller.org) (GPL-2.0 with bootloader exception).

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for license details and how to
get the source code of the bundled components.

## License

Apple TV Cast is free software under the [GNU General Public License v3.0 or later](LICENSE).
