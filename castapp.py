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


def cast_cmd(dt, address, cfg):
    cmd = [dt, "-target", address, "-port", str(cfg.get("port", 7000)), "-creds", str(CREDS),
           "-quit-on-stdin-eof",
           "-fps", str(cfg.get("fps", 30))]
    if cfg.get("no_audio"):
        cmd.append("-no-audio")
    if cfg.get("extra_args"):
        cmd += list(cfg["extra_args"])
    return cmd


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
        self.cfg, self.proc = cfg, None

    def start(self, status, on_exit):
        dt = find_tool("doubletake")
        if not dt:
            return status("doubletake.exe is missing. Put it next to AppleTVCast.exe.")
        APPDIR.mkdir(parents=True, exist_ok=True)
        log = open(LOG, "w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(cast_cmd(dt, self.cfg["address"], self.cfg),
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, env=tool_env(), creationflags=NO_WINDOW)
        proc = self.proc

        def watch():
            last = ""
            for raw in proc.stdout:
                line = raw.decode("utf-8", "replace")
                log.write(line); log.flush()
                if line.strip():
                    last = line.strip()
                if "mirror session ready" in line:
                    status("Casting! Your screen should be on the TV now.")
                elif "audio capture started" in line:
                    status("Casting with sound.")
            proc.wait(); log.close()
            if self.proc is proc:
                self.proc = None
                status("Stopped." if proc.returncode == 0 else
                       f"Casting stopped with a problem. Details in {LOG}\n{last[-200:]}")
            on_exit()
        threading.Thread(target=watch, daemon=True).start()

    def stop(self):
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

    btn = tk.Button(root, text="Cast to Apple TV", font=("Segoe UI", 20, "bold"), width=18, height=2, command=toggle)
    btn.pack(padx=20, pady=15)
    tk.Button(root, text="Set up Apple TV", command=setup).pack()
    tk.Label(root, textvariable=status, wraplength=380, justify="left").pack(pady=10)
    root.protocol("WM_DELETE_WINDOW", lambda: (caster.stop(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    gui()
