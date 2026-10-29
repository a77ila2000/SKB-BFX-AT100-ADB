import hashlib
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

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


class DistributionHelpers(unittest.TestCase):
    def load(self, name):
        spec = importlib.util.spec_from_file_location(name, ROOT / ("src/" + name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_usb_script_checksums_and_no_persistent_writes(self):
        module = self.load("make_usb_script")
        source = (ROOT / "src/uboot-console.cmd").read_bytes()
        image = module.build(source)
        header = bytearray(image[:64])
        values = struct.unpack(">7I4B32s", header)
        self.assertEqual(values[0], 0x27051956)
        struct.pack_into(">I", header, 4, 0)
        self.assertEqual(values[1], zlib.crc32(header) & 0xffffffff)
        self.assertEqual(values[3], len(image) - 64)
        self.assertEqual(values[6], zlib.crc32(image[64:]) & 0xffffffff)
        self.assertEqual(image[72:], source)
        for command in (b"saveenv\n", b"store write system 0 0 1\n", b"erase all\n"):
            with self.assertRaises(ValueError):
                module.build(command)

    def test_boot_flags_preserve_other_device_data_and_refuse_bad_crc(self):
        module = self.load("prepare_boot_flags")
        env = bytearray(8388608)
        block = bytearray(65536)
        fields = b"own_device=KEEP\0upgrade_step=3\0boot_part=boot\0active_slot=normal\0wipe_data=successful\0wipe_cache=successful\0\0"
        block[4:4 + len(fields)] = fields
        struct.pack_into("<I", block, 0, zlib.crc32(block[4:]) & 0xffffffff)
        env[:65536] = block
        env[65536:131072] = block
        env[200000:200004] = b"KEEP"
        misc = bytearray(8388608)
        misc[:13] = b"boot-recovery"
        misc[64:73] = b"recovery\n"
        misc[3000:3004] = b"KEEP"
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "env-before.img").write_bytes(env)
            (folder / "misc-before.img").write_bytes(misc)
            result = module.prepare(folder)
            new_env = (folder / "env-normal-prefix.bin").read_bytes() + env[131072:]
            new_misc = (folder / "misc-clear-bcb.bin").read_bytes() + misc[2048:]
            self.assertEqual(hashlib.sha256(new_env).hexdigest(), result["envAfterSha256"])
            self.assertEqual(hashlib.sha256(new_misc).hexdigest(), result["miscAfterSha256"])
            self.assertEqual(new_env[200000:200004], b"KEEP")
            self.assertEqual(new_misc[3000:3004], b"KEEP")
            self.assertEqual(new_env.count(b"upgrade_step=1"), 2)
            for start in (0, 65536):
                current = new_env[start:start + 65536]
                self.assertEqual(struct.unpack_from("<I", current)[0], zlib.crc32(current[4:]) & 0xffffffff)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            env[0] ^= 1
            (folder / "env-before.img").write_bytes(env)
            (folder / "misc-before.img").write_bytes(misc)
            with self.assertRaises(ValueError):
                module.prepare(folder)
            self.assertFalse((folder / "env-normal-prefix.bin").exists())


if __name__ == "__main__":
    unittest.main()
