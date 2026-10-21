# Third-party notices

The release download (`AppleTVCast.zip`) contains `AppleTVCast.exe` and `ffmpeg.exe`.
They include or run the following third-party software. Each component stays under
its own license; full texts are at the links below.

## doubletake (bundled inside AppleTVCast.exe as doubletake.exe)

* Upstream: https://github.com/omarroth/doubletake, Copyright Omar Roth and contributors
* Windows port used here: https://github.com/Jshelnutt/doubletake/tree/windows
* License: GNU Lesser General Public License v3.0 (LICENSE, together with the GNU GPL v3
  in COPYING.GPL), included in that repository:
  https://github.com/Jshelnutt/doubletake/blob/windows/LICENSE
* Source code: the complete source of the exact version shipped is the `windows`
  branch of https://github.com/Jshelnutt/doubletake. Build with
  `GOOS=windows go build ./cmd/doubletake`.

## FFmpeg (ffmpeg.exe)

* Project: https://ffmpeg.org
* Build: Windows "full" build from https://www.gyan.dev/ffmpeg/builds/, configured with
  `--enable-gpl --enable-version3` (includes libx264 and other GPL libraries).
* License: GNU General Public License v3.0: https://www.gnu.org/licenses/gpl-3.0.html
  (FFmpeg legal info: https://ffmpeg.org/legal.html)
* Source code: FFmpeg source is at https://ffmpeg.org/download.html and
  https://git.ffmpeg.org/ffmpeg.git. The build's exact source and build configuration
  are published by gyan.dev (https://www.gyan.dev/ffmpeg/builds/, linking to
  https://github.com/GyanD/codexffmpeg). If you can't obtain the corresponding source
  for the ffmpeg.exe shipped in a release of this project, open an issue on this
  repository requesting it; this written offer is valid for three years from the date
  of that release.

## pyatv (bundled inside AppleTVCast.exe)

* Project: https://github.com/postlund/pyatv, Copyright Pierre Ståhl and contributors
* License: MIT: https://github.com/postlund/pyatv/blob/master/LICENSE.md
* pyatv's own dependencies (for example aiohttp, cryptography, protobuf, zeroconf,
  srptools, chacha20poly1305-reuseable) are under permissive licenses (MIT, BSD,
  Apache-2.0, LGPL for zeroconf); see each project's page on https://pypi.org.

## Python and PyInstaller

* Python: PSF License, https://docs.python.org/3/license.html
* Tcl/Tk (used by the window): BSD-style license, https://www.tcl.tk/software/tcltk/license.html
* PyInstaller: GPL-2.0 with a bootloader exception that allows distributing built
  apps under any license, https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt

## Trademarks

AirPlay, Apple TV and HomePod are trademarks of Apple Inc. This project is not
affiliated with or endorsed by Apple Inc.
