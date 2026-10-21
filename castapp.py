"""Apple TV Cast - free real-time PC-to-Apple TV screen mirroring.

The window is a thin front end for doubletake.exe (Jshelnutt/doubletake,
Windows port of omarroth/doubletake), which speaks the AirPlay mirroring
protocol: picture via ffmpeg desktop capture + H.264, sound via WASAPI
loopback. pyatv is only used to find the Apple TV on the network.
"""
import asyncio, json, os, re, shutil, subprocess, sys, threading
from pathlib import Path

APPDIR = Path(os.environ.get("APPDATA", Path.home())) / "AppleTVCast"
CONFIG = APPDIR / "config.json"
CREDS = APPDIR / "doubletake-credentials.json"
LOG = APPDIR / "cast.log"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def load_cfg():
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def save_cfg(cfg):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2))


def _search_dirs():
    dirs = [Path(sys.argv[0]).resolve().parent, Path(__file__).resolve().parent]
    if hasattr(sys, "_MEIPASS"):
        dirs.insert(0, Path(sys._MEIPASS))
    return dirs


def find_tool(name):
    """Find doubletake/ffmpeg next to the app (or bundled), then on PATH."""
    exe = name + (".exe" if os.name == "nt" else "")
    for d in _search_dirs():
        if (d / exe).exists():
            return str(d / exe)
    return shutil.which(name)


def tool_env():
    env = dict(os.environ)
    ff = find_tool("ffmpeg")
    if ff:
        env["DOUBLETAKE_FFMPEG"] = ff
    return env


def pair_cmd(dt, address, port=7000):
    return [dt, "-target", address, "-port", str(port), "-creds", str(CREDS),
            "-pair", "-pair-only", "-no-audio"]


def homepod_mode(cfg):
    return bool(cfg.get("speaker_id"))


def cast_cmd(dt, address, cfg):
    cmd = [dt, "-target", address, "-port", str(cfg.get("port", 7000)), "-creds", str(CREDS),
           "-quit-on-stdin-eof",
           "-fps", str(cfg.get("fps", 30))]
    if cfg.get("no_audio") or homepod_mode(cfg):
        # tvOS does not forward screen-mirroring sound to HomePods that are the
        # Apple TV's audio output, so in HomePod mode sound goes to them directly.
        cmd.append("-no-audio")
    if homepod_mode(cfg) and cfg.get("video_delay_ms", 1800):
        # Hold the picture back so it lines up with the HomePods' ~2 s buffer.
        cmd += ["-target-latency-ms", str(cfg.get("video_delay_ms", 1800))]
    if cfg.get("extra_args"):
        cmd += list(cfg["extra_args"])
    return cmd


def pcm_cmd(dt):
    return [dt, "-pcm-stdout"]


def mp3_cmd(ff):
    return [ff, "-hide_banner", "-loglevel", "error", "-probesize", "32", "-analyzeduration", "0", "-fflags", "nobuffer",
            "-f", "s16le", "-ar", "44100", "-ac", "2",
            "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", "320k", "-f", "mp3", "-flush_packets", "1", "pipe:1"]


async def discover_speakers():
    import pyatv
    from pyatv.const import Protocol
    found = await pyatv.scan(asyncio.get_running_loop(), timeout=5)
    return [d for d in found if d.get_service(Protocol.RAOP)]


class SpeakerStream:
    """System sound -> doubletake -pcm-stdout -> ffmpeg MP3 -> pyatv RAOP (HomePods).
    Everything (incl. pyatv's own debug log) goes to %APPDATA%/AppleTVCast/speaker.log.
    If the stream ends while casting it is restarted with back-off."""

    MAX_RESTARTS = 5

    def __init__(self, cfg, status):
        self.cfg, self.status = cfg, status
        self.loop = self.task = self.pcm = self.enc = None
        self.thread = None
        self.stopped = False

    def start(self):
        dt, ff = find_tool("doubletake"), find_tool("ffmpeg")
        if not (dt and ff):
            return self.status("Sound to HomePods needs doubletake.exe and ffmpeg.exe next to the app.")
        self.thread = threading.Thread(target=self._run, args=(dt, ff), daemon=True)
        self.thread.start()

    def _logger(self):
        import logging
        APPDIR.mkdir(parents=True, exist_ok=True)
        self.logf = open(APPDIR / "speaker.log", "a", encoding="utf-8", errors="replace")
        h = logging.StreamHandler(self.logf)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        lg = logging.getLogger("pyatv")
        lg.setLevel(logging.DEBUG if self.cfg.get("speaker_debug", True) else logging.INFO)
        lg.handlers = [h]
        app = logging.getLogger("atvcast.speaker"); app.setLevel(logging.INFO); app.handlers = [h]
        return app

    def _run(self, dt, ff):
        import time
        log = self._logger()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        restarts = 0
        while not self.stopped:
            started = time.time()
            try:
                self.task = self.loop.create_task(self._stream(dt, ff, log))
                self.loop.run_until_complete(self.task)
                log.warning("stream_file returned (HomePod ended the stream)")
            except asyncio.CancelledError:
                log.info("speaker stream cancelled")
            except Exception as e:
                log.exception("speaker stream failed: %r", e)
            finally:
                self._kill()
            if self.stopped:
                break
            if time.time() - started > 60:
                restarts = 0
            restarts += 1
            if restarts > self.MAX_RESTARTS:
                self.status(f"Sound to {self.cfg.get('speaker_name')} keeps stopping. Details in {APPDIR / 'speaker.log'}")
                break
            wait = min(2 * restarts, 10)
            log.info("restarting speaker stream in %ss (attempt %d/%d)", wait, restarts, self.MAX_RESTARTS)
            self.status(f"Sound to {self.cfg.get('speaker_name')} dropped; reconnecting ({restarts})...")
            time.sleep(wait)
        log.info("speaker stream thread exit")
        self.logf.close()

    async def _stream(self, dt, ff, log):
        import pyatv
        from pyatv.const import Protocol
        from pyatv.interface import MediaMetadata
        loop = asyncio.get_running_loop()
        confs = await pyatv.scan(loop, identifier=self.cfg["speaker_id"], timeout=5)
        if not confs:
            raise RuntimeError(f"{self.cfg.get('speaker_name', 'HomePod')} ({self.cfg['speaker_id']}) not found")
        conf = confs[0]
        try:
            log.info("speaker %s at %s; services: %s", getattr(conf, "name", "?"), getattr(conf, "address", "?"),
                     [(str(sv.protocol), sv.port) for sv in conf.services])
        except Exception:
            pass
        if self.cfg.get("speaker_raop_only", True) and hasattr(conf, "_services"):
            # Stream with plain RAOP; ignore the HomePod's AirPlay/Companion
            # services so pyatv doesn't try to control the home-theater group.
            for sv in list(conf.services):
                if sv.protocol not in (Protocol.RAOP,):
                    try:
                        conf._services.pop(sv.protocol, None)  # best effort
                    except Exception:
                        pass
        self.pcm = subprocess.Popen(pcm_cmd(dt), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=self.logf, env=tool_env(), creationflags=NO_WINDOW)
        self.enc = await asyncio.create_subprocess_exec(*mp3_cmd(ff), stdin=self.pcm.stdout,
                                                        stdout=asyncio.subprocess.PIPE, stderr=self.logf,
                                                        creationflags=NO_WINDOW)
        atv = await pyatv.connect(conf, loop)
        log.info("connected; starting stream_file")
        self.status(f"Casting! Sound goes to {self.cfg.get('speaker_name')} (about 2 s behind; picture is delayed to match).")
        try:
            await atv.stream.stream_file(self.enc.stdout, metadata=MediaMetadata(title="PC sound", artist="Apple TV Cast"))
        finally:
            log.info("closing speaker connection (pcm rc=%s, mp3 rc=%s)",
                     self.pcm.poll() if self.pcm else None, self.enc.returncode if self.enc else None)
            atv.close()

    def _kill(self):
        for p in (self.pcm, self.enc):
            try:
                if p and (getattr(p, "returncode", None) is None):
                    p.kill()
            except Exception:
                pass
        self.pcm = self.enc = None

    def stop(self):
        self.stopped = True
        if self.loop and self.task and not self.task.done():
            self.loop.call_soon_threadsafe(self.task.cancel)
        self._kill()


async def discover():
    import pyatv
    from pyatv.const import Protocol
    found = await pyatv.scan(asyncio.get_running_loop(), timeout=5)
    return [d for d in found if d.get_service(Protocol.AirPlay)]


def run_pairing(dt, address, ask_pin, timeout=90, port=7000):
    """Run doubletake -pair-only, answering its PIN prompt. Returns (ok, log)."""
    APPDIR.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(pair_cmd(dt, address, port), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, env=tool_env(), creationflags=NO_WINDOW)
    out, asked = "", False
    timer = threading.Timer(timeout, p.kill); timer.start()
    try:
        while True:
            chunk = p.stdout.read1(4096) if hasattr(p.stdout, "read1") else p.stdout.read(1)
            if not chunk:
                break
            out += chunk.decode("utf-8", "replace")
            if not asked and re.search(r"Enter the (PIN|code|receiver)", out):
                asked = True
                pin = ask_pin()
                if not pin:
                    p.kill(); break
                p.stdin.write((pin.strip() + "\n").encode()); p.stdin.flush()
        p.wait()
    finally:
        timer.cancel()
    return p.returncode == 0 and "pairing complete" in out, out


class Caster:
    def __init__(self, cfg):
        self.cfg, self.proc, self.speaker = cfg, None, None

    MIRROR_RETRIES = 3

    def start(self, status, on_exit):
        dt = find_tool("doubletake")
        if not dt:
            return status("doubletake.exe is missing. Put it next to AppleTVCast.exe.")
        APPDIR.mkdir(parents=True, exist_ok=True)
        self.stopping = False
        log = open(LOG, "w", encoding="utf-8", errors="replace")

        def launch():
            return subprocess.Popen(cast_cmd(dt, self.cfg["address"], self.cfg),
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=tool_env(), creationflags=NO_WINDOW)
        self.proc = launch()

        def watch():
            import time
            attempt, last, proc = 1, "", self.proc
            while True:
                ready = False
                for raw in proc.stdout:
                    line = raw.decode("utf-8", "replace")
                    log.write(line); log.flush()
                    if line.strip():
                        last = line.strip()
                    if "mirror session ready" in line and not ready:
                        ready = True
                        if homepod_mode(self.cfg):
                            # Start the HomePod stream only once the Apple TV
                            # session is up, so the two AirPlay setups don't race.
                            status(f"Casting! Connecting sound to {self.cfg.get('speaker_name')}...")
                            self.speaker = SpeakerStream(self.cfg, status)
                            self.speaker.start()
                        else:
                            status("Casting! Your screen should be on the TV now.")
                    elif "audio capture started" in line and not homepod_mode(self.cfg):
                        status("Casting with sound.")
                proc.wait()
                if self.speaker:
                    self.speaker.stop(); self.speaker = None
                retry = (not ready and not self.stopping and self.proc is proc and proc.returncode != 0
                         and attempt < self.MIRROR_RETRIES)
                if not retry:
                    break
                attempt += 1
                log.write(f"--- mirror setup failed; retry {attempt}/{self.MIRROR_RETRIES} in 3 s ---\n"); log.flush()
                status(f"Apple TV didn't accept the connection; retrying ({attempt}/{self.MIRROR_RETRIES})...")
                time.sleep(3)
                if self.stopping:
                    break
                proc = self.proc = launch()
            log.close()
            if self.proc is proc:
                self.proc = None
                status("Stopped." if proc.returncode == 0 else
                       f"Casting stopped with a problem. Details in {LOG}\n{last[-200:]}")
            on_exit()
        threading.Thread(target=watch, daemon=True).start()

    def stop(self):
        self.stopping = True
        if self.speaker:
            self.speaker.stop(); self.speaker = None
        proc, self.proc = self.proc, None
        if not proc:
            return
        try:
            proc.stdin.close()  # doubletake shuts down cleanly on stdin EOF
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def gui():
    import tkinter as tk
    from tkinter import simpledialog, messagebox
    cfg = load_cfg(); root = tk.Tk(); root.title("Apple TV Cast")
    ready = cfg.get("address") and CREDS.exists()
    status = tk.StringVar(value=f"Ready to cast to {cfg.get('device_name', 'Apple TV')}." if ready
                          else "First run: click Set up Apple TV.")
    caster = Caster(cfg)
    say = lambda m: root.after(0, status.set, m)
    reset_btn = lambda: root.after(0, btn.config, {"text": "Cast to Apple TV"})

    def root_call(fn):
        box, ev = {}, threading.Event()
        root.after(0, lambda: (box.setdefault("v", fn()), ev.set())); ev.wait(); return box["v"]

    def setup():
        dt = find_tool("doubletake")
        if not dt:
            return messagebox.showerror("Apple TV Cast", "doubletake.exe is missing. Put it next to AppleTVCast.exe.")
        status.set("Looking for Apple TVs...")

        def work():
            try:
                devs = asyncio.run(discover())
            except Exception as e:
                return say(f"Search problem: {e}")
            if not devs:
                return say("No Apple TV found. Same Wi-Fi? Apple TV awake?")
            d = devs[0]
            if len(devs) > 1:
                names = "\n".join(f"{i+1}. {x.name}" for i, x in enumerate(devs))
                pick = root_call(lambda: simpledialog.askinteger("Apple TV Cast", f"Which one?\n{names}",
                                                                minvalue=1, maxvalue=len(devs)))
                if not pick:
                    return say("Setup cancelled.")
                d = devs[pick - 1]
            address = str(d.address)
            say(f"Pairing with {d.name}... a code should appear on the TV.")
            ok, out = run_pairing(dt, address, lambda: root_call(
                lambda: simpledialog.askstring("PIN", f"Type the 4-digit code shown on {d.name}:")))
            APPDIR.mkdir(parents=True, exist_ok=True)
            (APPDIR / "pair.log").write_text(out, encoding="utf-8")
            if not ok:
                return say(f"Pairing didn't finish. Details in {APPDIR / 'pair.log'}")
            cfg.update(device_id=d.identifier, device_name=d.name, address=address,
                       doubletake_credentials=str(CREDS))
            cfg.pop("credentials", None)  # old pyatv play_url credentials, no longer used
            save_cfg(cfg)
            say(f"Paired with {d.name}. Click Cast!")
        threading.Thread(target=work, daemon=True).start()

    def toggle():
        if caster.proc:
            caster.stop(); btn.config(text="Cast to Apple TV"); status.set("Stopped.")
        elif not (cfg.get("address") and CREDS.exists()):
            messagebox.showinfo("Apple TV Cast", "Click 'Set up Apple TV' first.")
        else:
            caster.start(say, reset_btn); btn.config(text="Stop"); status.set("Connecting...")

    def pick_sound():
        status.set("Looking for HomePods and AirPlay speakers...")

        def work():
            try:
                spk = asyncio.run(discover_speakers())
            except Exception as e:
                return say(f"Search problem: {e}")
            spk = [d for d in spk if d.identifier != cfg.get("device_id")]
            names = "\n".join(f"{i+1}. {x.name}" for i, x in enumerate(spk))
            pick = root_call(lambda: simpledialog.askinteger(
                "Sound output", "Where should the PC's sound play?\n0. Apple TV (TV/projector speakers)\n" + names,
                minvalue=0, maxvalue=len(spk)))
            if pick is None:
                return say("No change.")
            if pick == 0:
                cfg.pop("speaker_id", None); cfg.pop("speaker_name", None)
                save_cfg(cfg); return say("Sound will go to the Apple TV.")
            d = spk[pick - 1]
            delay = root_call(lambda: simpledialog.askinteger(
                "Picture delay", "Delay the picture to match the speakers (milliseconds, 0-2000):",
                initialvalue=cfg.get("video_delay_ms", 1800), minvalue=0, maxvalue=2000))
            cfg.update(speaker_id=d.identifier, speaker_name=d.name,
                       video_delay_ms=1800 if delay is None else delay)
            save_cfg(cfg); say(f"Sound will go to {d.name}.")
        threading.Thread(target=work, daemon=True).start()

    btn = tk.Button(root, text="Cast to Apple TV", font=("Segoe UI", 20, "bold"), width=18, height=2, command=toggle)
    btn.pack(padx=20, pady=15)
    tk.Button(root, text="Set up Apple TV", command=setup).pack()
    tk.Button(root, text="Sound output...", command=pick_sound).pack(pady=(6, 0))
    tk.Label(root, textvariable=status, wraplength=380, justify="left").pack(pady=10)
    root.protocol("WM_DELETE_WINDOW", lambda: (caster.stop(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    gui()
