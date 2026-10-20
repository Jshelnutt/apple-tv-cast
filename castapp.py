"""Apple TV Cast - free PC-to-Apple TV casting (HLS + AirPlay play_url via pyatv).
Delayed casting (~3-8 s), NOT real-time mirroring."""
import asyncio, json, os, shutil, socket, subprocess, sys, tempfile, threading
import functools, http.server
from pathlib import Path

CONFIG = Path(os.environ.get("APPDATA", Path.home())) / "AppleTVCast" / "config.json"
PORT = 8765


def load_cfg():
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def save_cfg(cfg):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2))


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
    finally:
        s.close()


def ffmpeg_cmd(outdir, audio_device=None, test_source=False, fps=30, ffmpeg="ffmpeg"):
    """Build ffmpeg command: screen (+system audio) -> H.264/AAC HLS."""
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-y"]
    if test_source:
        cmd += ["-re", "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate={fps}",
                "-f", "lavfi", "-i", "sine=frequency=440"]
    else:
        cmd += ["-f", "gdigrab", "-framerate", str(fps), "-i", "desktop"]
        if audio_device:
            cmd += ["-f", "dshow", "-i", f"audio={audio_device}"]
    has_audio = test_source or bool(audio_device)
    cmd += ["-vf", "scale='min(1920,iw)':-2,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-g", str(fps), "-keyint_min", str(fps), "-sc_threshold", "0", "-b:v", "6M"]
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "160k", "-ar", "48000"]
    cmd += ["-f", "hls", "-hls_time", "1", "-hls_list_size", "6",
            "-hls_flags", "delete_segments+independent_segments",
            str(Path(outdir) / "live.m3u8")]
    return cmd


def start_http(directory, port=PORT):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    h.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


async def discover():
    import pyatv
    from pyatv.const import Protocol
    found = await pyatv.scan(asyncio.get_running_loop(), timeout=5)
    return [d for d in found if d.get_service(Protocol.AirPlay)]


async def pair(identifier, pin_cb):
    import pyatv
    from pyatv.const import Protocol
    loop = asyncio.get_running_loop()
    conf = (await pyatv.scan(loop, identifier=identifier, timeout=5))[0]
    p = await pyatv.pair(conf, Protocol.AirPlay, loop)
    await p.begin()
    if p.device_provides_pin:
        p.pin(int(await loop.run_in_executor(None, pin_cb)))
    await p.finish()
    creds = p.service.credentials if p.has_paired else None
    await p.close()
    return creds


async def play(identifier, creds, url):
    import pyatv
    from pyatv.const import Protocol
    loop = asyncio.get_running_loop()
    conf = (await pyatv.scan(loop, identifier=identifier, timeout=5))[0]
    if creds:
        conf.set_credentials(Protocol.AirPlay, creds)
    atv = await pyatv.connect(conf, loop)
    try:
        await atv.stream.play_url(url)  # blocks until playback ends
    finally:
        atv.close()


class Caster:
    def __init__(self, cfg):
        self.cfg, self.proc, self.srv, self.thread = cfg, None, None, None

    def start(self, status):
        out = Path(tempfile.mkdtemp(prefix="atvcast_"))
        ff = shutil.which("ffmpeg") or str(Path(sys.argv[0]).parent / "ffmpeg.exe")
        self.proc = subprocess.Popen(ffmpeg_cmd(out, self.cfg.get("audio_device"), ffmpeg=ff),
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.srv = start_http(out)
        url = f"http://{local_ip()}:{PORT}/live.m3u8"
        def run():
            import time
            for _ in range(30):  # wait for first segments
                if (out / "live.m3u8").exists(): break
                time.sleep(0.5)
            time.sleep(3)
            try:
                status("Casting... (picture is a few seconds behind)")
                asyncio.run(play(self.cfg["device_id"], self.cfg.get("credentials"), url))
                status("Stopped.")
            except Exception as e:
                status(f"Problem: {e}")
            finally:
                self.stop()
        self.thread = threading.Thread(target=run, daemon=True); self.thread.start()

    def stop(self):
        if self.proc: self.proc.terminate(); self.proc = None
        if self.srv: self.srv.shutdown(); self.srv = None


def gui():
    import tkinter as tk
    from tkinter import simpledialog, messagebox
    cfg = load_cfg(); root = tk.Tk(); root.title("Apple TV Cast")
    status = tk.StringVar(value="Ready." if cfg.get("device_id") else "First run: click Set up Apple TV.")
    caster = Caster(cfg)
    say = lambda m: root.after(0, status.set, m)

    def setup():
        status.set("Looking for Apple TVs...")
        def work():
            devs = asyncio.run(discover())
            if not devs: return say("No Apple TV found. Same Wi-Fi? Apple TV awake?")
            d = devs[0]
            ask = lambda: root_call(lambda: simpledialog.askstring("PIN", f"Type the PIN shown on {d.name}:"))
            try:
                creds = asyncio.run(pair(d.identifier, ask))
            except Exception as e:
                return say(f"Pairing problem: {e}")
            cfg.update(device_id=d.identifier, device_name=d.name, credentials=creds); save_cfg(cfg)
            say(f"Paired with {d.name}. Click Cast!")
        threading.Thread(target=work, daemon=True).start()

    def root_call(fn):
        box, ev = {}, threading.Event()
        root.after(0, lambda: (box.setdefault("v", fn()), ev.set())); ev.wait(); return box["v"]

    def toggle():
        if caster.proc: caster.stop(); btn.config(text="Cast to Apple TV"); status.set("Stopped.")
        elif not cfg.get("device_id"): messagebox.showinfo("Apple TV Cast", "Click 'Set up Apple TV' first.")
        else: caster.start(say); btn.config(text="Stop"); status.set("Starting...")

    btn = tk.Button(root, text="Cast to Apple TV", font=("Segoe UI", 20, "bold"), width=18, height=2, command=toggle)
    btn.pack(padx=20, pady=15)
    tk.Button(root, text="Set up Apple TV", command=setup).pack()
    tk.Label(root, textvariable=status, wraplength=380).pack(pady=10)
    root.protocol("WM_DELETE_WINDOW", lambda: (caster.stop(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    gui()
