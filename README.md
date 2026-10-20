# Apple TV Cast (free)

One big button: **Cast to Apple TV**. It sends your PC screen and sound to your Apple TV over Wi-Fi.

**Be aware:** the TV shows things about **3–8 seconds late**. That's fine for videos, photos and slides. It's not good for games or for moving the mouse. True real-time mirroring like AirParrot uses Apple's locked encryption (FairPlay), and no free open-source program can send that today.

## How it works (plain terms)
1. The free tool ffmpeg records your screen and sound into small video chunks.
2. A tiny web server on your PC serves those chunks over your home Wi-Fi.
3. The app asks the Apple TV (using AirPlay, via the free pyatv library) to play that address.

## One-time Apple TV settings
Settings → AirPlay and HomeKit → Allow Access: **Everyone on the same network** (or "Anyone on the same network"). The first time you click **Set up Apple TV**, the TV shows a 4-digit PIN. Type it into the app. This only happens once.

## PC sound
Windows needs a "recording" device that captures what the speakers play. Do one of these:
- Turn on **Stereo Mix**: Sound settings → More sound settings → Recording → right-click → Show disabled devices → Enable Stereo Mix. Or
- Install the free "screen-capture-recorder" (it adds `virtual-audio-capturer`).
Then put its name in `%APPDATA%\AppleTVCast\config.json` as `"audio_device": "Stereo Mix (Realtek(R) Audio)"`. To list the names, run: `ffmpeg -list_devices true -f dshow -i dummy`.

## Install (Windows)
See INSTALL_WINDOWS.md.

## Status
- Tested on Linux: the video-chunk pipeline, the web server, and the pyatv functions are present.
- **Not tested yet:** a real Apple TV, PIN pairing, Windows screen and sound capture, and the exe build.
