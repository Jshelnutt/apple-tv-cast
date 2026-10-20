import sys, time, subprocess, tempfile, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import castapp

def test_cmd_has_hls_and_audio():
    c = castapp.ffmpeg_cmd("x", audio_device="Stereo Mix")
    assert "gdigrab" in c and "dshow" in c and "aac" in c and c[-1].endswith("live.m3u8")

def test_cmd_no_audio():
    assert "aac" not in castapp.ffmpeg_cmd("x")

def test_hls_end_to_end():
    out = Path(tempfile.mkdtemp())
    p = subprocess.Popen(castapp.ffmpeg_cmd(out, test_source=True))
    srv = castapp.start_http(out, 8799)
    try:
        time.sleep(6)
        body = urllib.request.urlopen("http://127.0.0.1:8799/live.m3u8").read().decode()
        assert "#EXTM3U" in body and ".ts" in body
    finally:
        p.terminate(); srv.shutdown()

def test_pyatv_api():
    import pyatv
    from pyatv.interface import Stream
    assert hasattr(Stream, "play_url") and hasattr(pyatv, "pair")
