"""Build a legacy ARM U-Boot script container; no device is accessed."""
import argparse
from pathlib import Path
import re
import struct
import zlib


def build(source):
    text = source.decode("ascii").replace("\r\n", "\n")
    if re.search(r"\b(saveenv|erase|fatwrite)\b|\b(store|mmc)\s+write\b", text, re.I):
        raise ValueError("USB console script must not contain persistent writes")
    data = text.encode("ascii")
    payload = struct.pack(">II", len(data), 0) + data
    values = [0x27051956, 0, 0, len(payload), 0, 0, zlib.crc32(payload) & 0xffffffff, 5, 2, 6, 0, b"BFX UART console".ljust(32, b"\0")]
    header = struct.pack(">7I4B32s", *values)
    values[1] = zlib.crc32(header) & 0xffffffff
    return struct.pack(">7I4B32s", *values) + payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    image = build(args.source.read_bytes())
    with args.output.open("xb") as stream:
        stream.write(image)
