"""Offline guards for the public module builder; never opens a device."""
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src/usb-wifi"
sys.path.insert(0, str(SOURCE))
if importlib.util.find_spec("elftools"):
    from build_driver import versions, prepare_kernel, patch_driver
else:
    versions = None


def module_bytes(rows, machine=40):
    names = b"\0.shstrtab\0__versions\0"
    data = b"".join(struct.pack("<I", crc) + name.encode().ljust(60, b"\0") for name, crc in rows)
    table = 52 + len(names) + len(data)
    header = b"\x7fELF\x01\x01\x01" + bytes(9)
    header += struct.pack("<HHIIIIIHHHHHH", 1, machine, 1, 0, 0, table, 0, 52, 0, 0, 40, 3, 1)
    sections = bytes(40)
    sections += struct.pack("<IIIIIIIIII", 1, 3, 0, 0, 52, len(names), 0, 0, 1, 0)
    sections += struct.pack("<IIIIIIIIII", 11, 1, 0, 0, 52 + len(names), len(data), 0, 0, 4, 0)
    return header + names + data + sections


@unittest.skipUnless(versions, "Install src/usb-wifi/requirements.txt for ELF guard checks")
class ConnectivityBuildGuards(unittest.TestCase):
    def test_version_table_accepts_arm_and_rejects_duplicates_or_wrong_architecture(self):
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory) / "fixture.ko"
            module.write_bytes(module_bytes([("module_layout", 0x12345678), ("usb_register_driver", 0xAABBCCDD)]))
            self.assertEqual(versions(module), {"module_layout": "12345678", "usb_register_driver": "aabbccdd"})
            for rows, machine in [([("module_layout", 1), ("module_layout", 2)], 40),
                                  ([("module_layout", 1)], 183)]:
                module.write_bytes(module_bytes(rows, machine))
                with self.assertRaises(ValueError):
                    versions(module)

    def test_unrecognized_config_is_rejected_before_source_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.config"
            original.write_text("CONFIG_UNRELATED=y\n")
            with self.assertRaises(ValueError):
                prepare_kernel(root / "absent-kernel", original, "absent-compiler-")
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["original.config"])

    def test_unknown_driver_source_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "os_dep/linux/ioctl_mp.c"
            source.parent.mkdir(parents=True)
            source.write_text("unrelated upstream revision\n")
            with self.assertRaises(ValueError):
                patch_driver(root)
            self.assertEqual(source.read_text(), "unrelated upstream revision\n")


if __name__ == "__main__":
    unittest.main()
