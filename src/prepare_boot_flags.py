"""Prepare minimal normal-boot changes from the user's own env/misc backups, offline."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib


def prepare(directory):
    env = (directory / "env-before.img").read_bytes()
    misc = (directory / "misc-before.img").read_bytes()
    outputs = [directory / name for name in ("env-normal-prefix.bin", "misc-clear-bcb.bin", "boot-flags-plan.json")]
    if any(path.exists() for path in outputs):
        raise ValueError("Output files must not already exist")
    if len(env) != 8388608 or len(misc) != 8388608:
        raise ValueError("Two complete original 8MiB env/misc backups are required")
    changed, offsets = bytearray(env), []
    for start in (0, 65536):
        block = bytearray(env[start:start + 65536])
        if struct.unpack_from("<I", block)[0] != zlib.crc32(block[4:]) & 0xffffffff:
            raise ValueError("Invalid original environment checksum")
        fields = dict(record.split(b"=", 1) for record in bytes(block[4:]).split(b"\0\0", 1)[0].split(b"\0"))
        expected = {b"upgrade_step": b"3", b"boot_part": b"boot", b"active_slot": b"normal", b"wipe_data": b"successful", b"wipe_cache": b"successful"}
        if any(fields.get(key) != value for key, value in expected.items()):
            raise ValueError("Unsupported boot state; no generic environment reset is performed")
        needle = b"\0upgrade_step=3\0"
        if block.count(needle) != 1:
            raise ValueError("Expected one upgrade-step record in each environment copy")
        index = block.index(needle) + len(needle) - 2
        block[index] = ord("1")
        struct.pack_into("<I", block, 0, zlib.crc32(block[4:]) & 0xffffffff)
        changed[start:start + 65536] = block
        offsets.append(start + index)
    if misc[:32].rstrip(b"\0") != b"boot-recovery" or not misc[64:832].startswith(b"recovery\n"):
        raise ValueError("Expected a standard pending recovery request")
    allowed = set(range(4)) | set(range(65536, 65540)) | set(offsets)
    differences = {index for index, pair in enumerate(zip(env, changed)) if pair[0] != pair[1]}
    if not differences <= allowed or changed[131072:] != env[131072:]:
        raise ValueError("An unrelated environment byte changed")
    sha = lambda data: hashlib.sha256(data).hexdigest()
    result = {"envBeforeSha256": sha(env), "envAfterSha256": sha(changed), "envWriteBytes": 131072,
              "envPrefixSha256": sha(changed[:131072]), "miscBeforeSha256": sha(misc),
              "miscAfterSha256": sha(bytes(2048) + misc[2048:]), "miscWriteBytes": 2048,
              "miscPrefixSha256": sha(bytes(2048)), "changedEnvOffsets": sorted(differences),
              "scope": "Own device only; preserve environment tail and misc bytes after the BCB"}
    for path, data in zip(outputs[:2], (changed[:131072], bytes(2048))):
        with path.open("xb") as stream:
            stream.write(data)
    with outputs[2].open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.directory), indent=2))
