import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("patches", ROOT / "src/patch_libraries.py")
patches = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patches)


class PatchGuards(unittest.TestCase):
    def test_exact_patch_and_all_guards(self):
        data = b"prefix-OLD-suffix"
        expected = b"prefix-NEW-suffix"
        item = {"bytes": len(data), "source_sha256": hashlib.sha256(data).hexdigest(),
                "output_sha256": hashlib.sha256(expected).hexdigest(),
                "offset": 7, "before": b"OLD".hex(), "after": b"NEW".hex()}
        self.assertEqual(patches.apply_patch(data, item), expected)
        for field, value in {"bytes": 1, "source_sha256": "0" * 64, "output_sha256": "0" * 64,
                             "offset": -1, "before": "000000", "after": "00"}.items():
            with self.subTest(field=field), self.assertRaises(ValueError):
                patches.apply_patch(data, dict(item, **{field: value}))

    def test_production_patches_reject_unknown_input(self):
        for item in patches.PATCHES.values():
            with self.assertRaises(ValueError):
                patches.apply_patch(bytes(item["bytes"]), item)

    def test_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "existing.so"
            target.write_bytes(b"preserve")
            result = subprocess.run([shutil.which("python3") or "python", str(ROOT / "src/patch_libraries.py"),
                                     "audio", str(target), str(target)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_bytes(), b"preserve")


@unittest.skipUnless(shutil.which("cc"), "C compiler required")
class Range64(unittest.TestCase):
    def test_offsets_above_four_gib_and_short_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            binary = folder / "read-range64"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2",
                            str(ROOT / "src/read-range64.c"), "-o", str(binary)], check=True)
            source = folder / "sparse.bin"
            mib = 1048576
            with source.open("wb") as stream:
                stream.truncate(7169 * mib)
                for offset in [0, 2048, 4096, 7168]:
                    stream.seek(offset * mib)
                    stream.write(f"marker-{offset}".encode())
            for offset in [0, 2048, 4096, 7168]:
                output = subprocess.run([str(binary), str(source), str(offset), "1"],
                                        check=True, capture_output=True).stdout
                with source.open("rb") as stream:
                    stream.seek(offset * mib)
                    self.assertEqual(output, stream.read(mib))
            for offset, count in [(8192, 1), (-1, 1), (0, 0)]:
                result = subprocess.run([str(binary), str(source), str(offset), str(count)], capture_output=True)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
