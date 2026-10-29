"""Read-only release and original-partition verification. Requires Linux/WSL."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zlib

ORIGINAL_VBMETA = "8645abe07d046688991ddd4d2bbcba81a444e444eb83884b264fb4aff707b91d"
AVBTOOL = "a9ec360fc5395db9b72d36c03af59ff984f4eefcc349dc32a556de7f8ed892ab"
SIZES = {"system.img": 1551892480, "vbmeta.img": 2097152}


def digest(path):
    value, crc = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while data := stream.read(8 * 1024 * 1024):
            value.update(data)
            crc = zlib.crc32(data, crc)
    return value.hexdigest(), f"{crc & 0xffffffff:08x}"


def verify(release, originals, avbtool):
    release, originals, avbtool = map(lambda p: Path(p).resolve(), (release, originals, avbtool))
    if not avbtool.is_file() or digest(avbtool)[0] != AVBTOOL:
        raise ValueError("Supply the pinned Android 12 avbtool.py")
    stock = originals / "vbmeta.img"
    if not stock.is_file():
        raise ValueError("Your complete original partition backups are required")
    with stock.open("rb") as stream:
        if hashlib.sha256(stream.read(4096)).hexdigest() != ORIGINAL_VBMETA:
            raise ValueError("Original vbmeta is incompatible; do not install this release")
    manifest = json.loads((release / "BUILDINFO.json").read_text())
    rows = manifest["images"]
    if len(rows) != 2 or {row["name"] for row in rows} != set(SIZES):
        raise ValueError("Unexpected release manifest")
    for row in rows:
        path = release / row["name"]
        if not path.is_file() or path.stat().st_size != SIZES[row["name"]] or row["bytes"] != path.stat().st_size:
            raise ValueError("Image is missing, truncated, or the wrong size")
        if digest(path) != (row["sha256"], row["crc32"]):
            raise ValueError("Image SHA-256 or CRC32 mismatch")
    import sys
    with tempfile.TemporaryDirectory(prefix="bfx-release-check-") as temporary:
        folder = Path(temporary)
        for name in ("boot", "recovery", "vendor", "product", "dtbo", "dtb"):
            source = originals / (name + ".img")
            if not source.is_file():
                raise ValueError("Missing original " + name + " image")
            (folder / source.name).symlink_to(source)
        for name in SIZES:
            (folder / name).symlink_to(release / name)
        subprocess.run([sys.executable, str(avbtool), "verify_image", "--image", str(folder / "vbmeta.img")], check=True)
    print("PASS: image hashes, original vbmeta, and all preserved AVB partition descriptors. No device was accessed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("originals", type=Path)
    parser.add_argument("--avbtool", type=Path, required=True)
    args = parser.parse_args()
    verify(args.release, args.originals, args.avbtool)
