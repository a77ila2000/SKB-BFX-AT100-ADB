"""Regress the actual shell loop: late wake, re-enumeration and probe rejection."""
from pathlib import Path
import os
import subprocess
import tempfile
import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src/stock-remote/bfx-stock-remote.sh"
pytestmark = pytest.mark.skipif(os.name == "nt", reason="Run POSIX shell/sysfs fixtures in Linux/WSL")

def run_case(mode, source=None):
    text = (source or SOURCE).read_text()
    if "last_state=id-registered" in text:
        body = text[text.index("last_state=id-registered"):]
    else:
        # Allows the exact pre-fix 60-second script to be checked as a negative control.
        body = text.split("setprop sys.bfx.stock_remote.state id-registered\n", 1)[1]
    with tempfile.TemporaryDirectory(prefix="bfx-watch-test-") as folder:
        root = Path(folder)
        devices = root / "sys/bus/hid/devices"
        devices.mkdir(parents=True)
        for name in ["skbrm", "hid-generic"]:
            (root / "sys/bus/hid/drivers" / name).mkdir(parents=True)
        (root / "owner").mkdir()
        (root / "report").touch()
        prefix = f'root={folder}\nmode={mode}\n' + r'''
driver="$root/sys/bus/hid/drivers/skbrm"
report="$root/report"
clock=0
phase=0
setprop() { echo "$2" >> "$root/props"; }
fail() { setprop sys.bfx.stock_remote.state "$1"; exit 1; }
write_driver_key() {
 case "$1" in
  */hid-generic/unbind) rm "$root/sys/bus/hid/devices/$2/driver" ;;
  */skbrm/bind)
   echo "$2" >> "$root/attempts"
   [ "$mode" != probe-failure ] || return 1
   ln -s "$root/sys/bus/hid/drivers/skbrm" "$root/sys/bus/hid/devices/$2/driver" ;;
  */hid-generic/bind)
   ln -s "$root/sys/bus/hid/drivers/hid-generic" "$root/sys/bus/hid/devices/$2/driver" ;;
  *) exit 9 ;;
 esac
}
sleep() {
 clock=$((clock+$1))
 if [ "$phase" = 0 ] && [ "$clock" -ge 80 ]; then
  mkdir "$root/sys/bus/hid/devices/0005:005D:0004.0001"
  ln -s "$root/sys/bus/hid/drivers/hid-generic" "$root/sys/bus/hid/devices/0005:005D:0004.0001/driver"
  phase=1
 fi
 if [ "$mode" = late-and-reconnect ]; then
  if [ "$phase" = 1 ] && [ "$clock" -ge 90 ]; then
   rm "$root/sys/bus/hid/devices/0005:005D:0004.0001/driver"
   rmdir "$root/sys/bus/hid/devices/0005:005D:0004.0001"
   phase=2
  fi
  if [ "$phase" = 2 ] && [ "$clock" -ge 96 ]; then
   mkdir "$root/sys/bus/hid/devices/0005:005D:0004.0002"
   ln -s "$root/sys/bus/hid/drivers/hid-generic" "$root/sys/bus/hid/devices/0005:005D:0004.0002/driver"
   phase=3
  fi
 fi
 [ "$clock" -lt 110 ] || touch "$root/owner/bfx-stock-remote.disable"
}
'''
        trial = body.replace("/sys/", folder + "/sys/")
        trial = trial.replace("/data/local/tmp/", folder + "/owner/")
        script = root / "trial.sh"
        script.write_text(prefix + trial)
        run = subprocess.run(["sh", str(script)], capture_output=True, text=True, timeout=5)
        assert run.returncode == 1, (mode, run.returncode, run.stderr)
        states = (root / "props").read_text().splitlines()
        attempts = (root / "attempts").read_text().splitlines()
        if mode == "late-and-reconnect":
            assert states.count("native-bound") == 2, states
            assert len(attempts) == 2 and attempts[0] != attempts[1], attempts
        else:
            assert len(attempts) == 1, attempts
            assert "generic-restored" in states, states
            assert (devices / "0005:005D:0004.0001/driver").resolve().name == "hid-generic"
        assert states[-1] == "owner-disabled", states


def test_connection_after_80_seconds_and_reconnect():
    run_case("late-and-reconnect")


def test_rejected_probe_restores_generic_without_retry_storm():
    run_case("probe-failure")


def test_builder_rejects_unknown_module_before_creating_output(tmp_path):
    import importlib.util
    script = SOURCE.parent / "build_overlay.py"
    spec = importlib.util.spec_from_file_location("stock_remote_builder", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = tmp_path / "unknown.ko"
    original.write_bytes(b"not-the-supported-original-module")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Unsupported original HID module"):
        module.build(original, output)
    assert not output.exists()
