"""End-to-end tests against doubletake's built-in test receiver (no Apple TV).
Set DOUBLETAKE_BIN_DIR to a folder holding doubletake + doubletake-test-receiver."""
import os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import pytest

BIN = os.environ.get("DOUBLETAKE_BIN_DIR")
pytestmark = pytest.mark.skipif(not BIN, reason="DOUBLETAKE_BIN_DIR not set")


@pytest.fixture()
def app(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("APPDATA", tmp)
    monkeypatch.setenv("PATH", BIN + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("DOUBLETAKE_CAPTURE", "ffmpeg")
    monkeypatch.setenv("DOUBLETAKE_AUDIO", "ffmpeg")
    monkeypatch.setenv("DOUBLETAKE_FFMPEG_INPUT", "-re -f lavfi -i testsrc2=size=1280x720:rate=30")
    monkeypatch.setenv("DOUBLETAKE_FFMPEG_AUDIO_INPUT", "-re -f lavfi -i sine=frequency=440:sample_rate=44100")
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import importlib, castapp
    importlib.reload(castapp)
    recv = subprocess.Popen([str(Path(BIN) / "doubletake-test-receiver"), "-listen", "127.0.0.1:7123",
                             "-profile", "modern", "-auth", "pin", "-code", "4321", "-stats-interval", "1s"],
                            stderr=subprocess.PIPE, text=True)
    time.sleep(0.5)
    yield castapp, recv
    recv.terminate()


def test_pair_then_cast_then_stop(app):
    castapp, recv = app
    dt = castapp.find_tool("doubletake")
    ok, out = castapp.run_pairing(dt, "127.0.0.1", lambda: "4321", port=7123)
    assert ok, out
    assert castapp.CREDS.exists()

    cfg = {"address": "127.0.0.1", "port": 7123}
    msgs, done = [], []
    c = castapp.Caster(cfg)
    c.start(msgs.append, lambda: done.append(1))
    time.sleep(8)
    assert any("Casting" in m for m in msgs), msgs
    c.stop()
    time.sleep(1)
    assert done and c.proc is None, msgs
    log = castapp.LOG.read_text()
    assert "mirror session ready" in log and "stream ended" in log
