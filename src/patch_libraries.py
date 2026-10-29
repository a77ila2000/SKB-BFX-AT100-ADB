"""Patch exact, locally supplied libraries; never read or write a device."""
import argparse
import hashlib
import json
from pathlib import Path

PATCHES = {
    "bootanimation": {
        "bytes": 70016,
        "source_sha256": "a20d786b330c203501a2843783932f22bc5e3dea74bba112bbecad4fcb54875f",
        "output_sha256": "6a07de02e94c8014317fa47fbddb731c55f4d17f3754fd0067986b792273b6b6",
        "offset": 0x91CE,
        "before": "daf89c004968",
        "after": "002959d007e0",
    },
    "audio": {
        "bytes": 226232,
        "source_sha256": "27eb4b859d7366cefdd352e785d7f036e0ab3d0773c62d448a569005dac1105b",
        "output_sha256": "918c4e5600a1632d2127eb026b26f0339999c611f46bfb7b4e031c6fc79a9db1",
        "offset": 0xE442,
        "before": "c0490620c04ac04b79447a447b44",
        "after": "11990020086016204042c3e000bf",
    },
}


def apply_patch(data, spec):
    if len(data) != spec["bytes"] or hashlib.sha256(data).hexdigest() != spec["source_sha256"]:
        raise ValueError("Unsupported source library: size or SHA-256 mismatch")
    start = spec["offset"]
    before, after = bytes.fromhex(spec["before"]), bytes.fromhex(spec["after"])
    if start < 0 or len(before) != len(after) or start + len(before) > len(data):
        raise ValueError("Invalid patch range")
    if data[start:start + len(before)] != before:
        raise ValueError("Original instruction bytes mismatch")
    result = data[:start] + after + data[start + len(before):]
    if len(result) != len(data) or hashlib.sha256(result).hexdigest() != spec["output_sha256"]:
        raise ValueError("Patched output digest mismatch")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=PATCHES)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not args.source.is_file() or args.source.resolve() == args.output.resolve():
        parser.error("Supply a regular source file and a separate, new output")
    result = apply_patch(args.source.read_bytes(), PATCHES[args.kind])
    with args.output.open("xb") as stream:
        stream.write(result)
    print(json.dumps({"kind": args.kind, "bytes": len(result),
                      "sha256": hashlib.sha256(result).hexdigest(), "device_write": False}))


if __name__ == "__main__":
    main()
