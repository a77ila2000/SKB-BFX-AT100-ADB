"""Rename the OEM Settings FileProvider without recompiling resources or code."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from zipfile import ZipFile
import zlib


def prepare(source, destination):
    old = "com.android.settings.files"
    new = "com.android.settings.ftvfs"
    assert len(old) == len(new)
    if destination.exists() or source.resolve() == destination.resolve():
        raise ValueError("Output must be a new file")
    changes = []
    with ZipFile(source) as original, ZipFile(destination, "x") as output:
        for entry in original.infolist():
            if entry.filename.startswith("META-INF/") and entry.filename.endswith((".RSA", ".SF", ".MF")):
                continue  # The derived APK is signed separately with the running GSI's test certificate.
            data = original.read(entry)
            before = data
            if entry.filename == "AndroidManifest.xml":
                for encoding in ("utf-8", "utf-16le"):
                    data = data.replace(old.encode(encoding), new.encode(encoding))
                if data == before:
                    raise ValueError("Expected manifest authority was not found")
            elif entry.filename.startswith("classes") and entry.filename.endswith(".dex") and old.encode() in data:
                if not data.startswith(b"dex\n") or struct.unpack_from("<I", data, 32)[0] != len(data):
                    raise ValueError("Unexpected DEX header")
                if hashlib.sha1(data[32:]).digest() != data[12:32] or zlib.adler32(data[12:]) & 0xffffffff != struct.unpack_from("<I", data, 8)[0]:
                    raise ValueError("Original DEX integrity check failed")
                # DEX string IDs must stay sorted; a different package prefix cannot be patched in place.
                count, table = struct.unpack_from("<II", data, 56)
                strings = []
                for index in range(count):
                    offset = struct.unpack_from("<I", data, table + index * 4)[0]
                    while data[offset] & 0x80:
                        offset += 1
                    offset += 1
                    strings.append(data[offset:data.index(b"\0", offset)])
                hits = [i for i, value in enumerate(strings) if value == old.encode()]
                if len(hits) != 1 or data.count(old.encode()) != 1:
                    raise ValueError("Expected exactly one complete DEX authority string")
                index = hits[0]
                if (index and strings[index - 1] >= new.encode()) or (index + 1 < count and new.encode() >= strings[index + 1]):
                    raise ValueError("Replacement would break DEX string ordering")
                data = bytearray(data.replace(old.encode(), new.encode()))
                data[12:32] = hashlib.sha1(data[32:]).digest()
                struct.pack_into("<I", data, 8, zlib.adler32(data[12:]) & 0xffffffff)
                data = bytes(data)
            if data != before:
                if len(data) != len(before):
                    raise ValueError("A same-length patch changed entry size")
                changes.append({"entry": entry.filename, "before": hashlib.sha256(before).hexdigest(), "after": hashlib.sha256(data).hexdigest()})
            output.writestr(entry, data)
    if not any(x["entry"].endswith(".dex") for x in changes):
        raise ValueError("Expected LicenseActivity DEX authority reference was not found")
    with ZipFile(source) as original, ZipFile(destination) as output:
        changed = {x["entry"] for x in changes}
        for name in output.namelist():
            if name not in changed and output.read(name) != original.read(name):
                raise ValueError("An unrelated APK entry changed: " + name)
    return {"source": str(source), "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(), "destination": str(destination), "authority": new, "changes": changes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination), indent=2))
