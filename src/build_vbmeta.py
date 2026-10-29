"""Construct offline GSI trial metadata; never open or write a device."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--avbtool", required=True, type=Path)
parser.add_argument("--stock", required=True, type=Path)
parser.add_argument("--key", required=True, type=Path)
parser.add_argument("--system", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--extra-cmdline", default="")
args = parser.parse_args()
if not __debug__:
    raise SystemExit("Do not disable assertions for this verification tool")
stock, key, gsi, output = args.stock, args.key, args.system, args.output
for path in (args.avbtool, stock, key, gsi):
    if not path.is_file():
        parser.error("All input paths must be existing regular local files")
if output.exists() or output.with_suffix(".json").exists():
    parser.error("Output image and report must not already exist")
spec = importlib.util.spec_from_file_location("avbtool", args.avbtool)
avbtool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(avbtool)
avb = avbtool.Avb()

expected_key_sha = "22de3994532196f61c039e90260d78a93a4c57362c7e789be928036e80b77c8c"

assert hashlib.sha256(stock.read_bytes()[:4096]).hexdigest() == (
    "8645abe07d046688991ddd4d2bbcba81a444e444eb83884b264fb4aff707b91d"
)
_, old_header, old_descriptors, _ = avb._parse_image(
    avbtool.ImageHandler(str(stock), read_only=True)
)
footer, gsi_header, gsi_descriptors, _ = avb._parse_image(
    avbtool.ImageHandler(str(gsi), read_only=True)
)
assert old_header.flags == old_header.rollback_index == 0
assert old_header.rollback_index_location == 0
assert old_header.public_key_metadata_size == 0
assert avbtool.verify_vbmeta_signature(old_header, stock.read_bytes())
with gsi.open("rb") as stream:
    stream.seek(footer.vbmeta_offset)
    gsi_vbmeta = stream.read(footer.vbmeta_size)
assert avbtool.verify_vbmeta_signature(gsi_header, gsi_vbmeta)

def public_key_sha(header, blob):
    offset = header.SIZE + header.authentication_data_block_size + header.public_key_offset
    return hashlib.sha256(blob[offset:offset + header.public_key_size]).hexdigest()

assert public_key_sha(old_header, stock.read_bytes()) == expected_key_sha
assert public_key_sha(gsi_header, gsi_vbmeta) == expected_key_sha
old_commands = [d for d in old_descriptors if isinstance(d, avbtool.AvbKernelCmdlineDescriptor)]
assert len(old_commands) == 2
assert all("ANDROID_SYSTEM_PARTUUID" in d.kernel_cmdline for d in old_commands)
old_partitions = {d.partition_name: d for d in old_descriptors if hasattr(d, "partition_name")}
assert set(old_partitions) == {"product", "vendor", "recovery", "boot", "system", "dtbo", "dtb"}
gsi_system = [d for d in gsi_descriptors if isinstance(d, avbtool.AvbHashtreeDescriptor)]
assert len(gsi_system) == 1 and gsi_system[0].partition_name == "system"
preserved = [d for d in old_descriptors if d not in old_commands and getattr(d, "partition_name", None) != "system"]
properties = [d for d in gsi_descriptors if isinstance(d, avbtool.AvbPropertyDescriptor)]
descriptors = preserved + gsi_system + properties
if args.extra_cmdline:
    extra = avbtool.AvbKernelCmdlineDescriptor()
    extra.kernel_cmdline = args.extra_cmdline
    descriptors.append(extra)
blob = avb._generate_vbmeta_blob(
    algorithm_name="SHA256_RSA2048", key_path=str(key),
    public_key_metadata_path=None, descriptors=descriptors,
    chain_partitions=None, rollback_index=0, flags=0, rollback_index_location=0,
    props=None, props_from_file=None, kernel_cmdlines=None,
    setup_rootfs_from_kernel=None, ht_desc_to_setup=gsi_system[0],
    include_descriptors_from_image=None, signing_helper=None,
    signing_helper_with_files=None, release_string=None,
    append_to_release_string=None, required_libavb_version_minor=0,
)
new_header = avbtool.AvbVBMetaHeader(blob[:256])
assert avbtool.verify_vbmeta_signature(new_header, blob)
assert public_key_sha(new_header, blob) == expected_key_sha
assert new_header.rollback_index == new_header.flags == 0
offset = 256 + new_header.authentication_data_block_size + new_header.descriptors_offset
new_descriptors = avbtool.parse_descriptors(blob[offset:offset + new_header.descriptors_size])
new_partitions = {d.partition_name: d for d in new_descriptors if hasattr(d, "partition_name")}
assert set(new_partitions) == set(old_partitions)
for name in set(old_partitions) - {"system"}:
    assert new_partitions[name].encode() == old_partitions[name].encode(), name
assert new_partitions["system"].encode() == gsi_system[0].encode()
new_commands = [d for d in new_descriptors if isinstance(d, avbtool.AvbKernelCmdlineDescriptor)]
assert len(new_commands) == 2 + bool(args.extra_cmdline)
root_commands = [d for d in new_commands if d.flags == 1]
assert len(root_commands) == 1
root_cmdline = root_commands[0].kernel_cmdline
assert gsi_system[0].root_digest.hex() in root_cmdline
assert old_partitions["system"].root_digest.hex() not in root_cmdline
if args.extra_cmdline:
    assert [d.kernel_cmdline for d in new_commands if d.flags == 0] == [args.extra_cmdline]
assert len(blob) <= 4096
padded = blob + bytes(4096 - len(blob))
with output.open("xb") as stream:
    stream.write(padded)
record = {
    "purpose": "Offline reconstruction only; no device is accessed",
    "flash_ready": False, "bytes": len(padded), "vbmeta_bytes": len(blob),
    "sha256": hashlib.sha256(padded).hexdigest(),
    "signature_verified": True, "public_key_sha256": expected_key_sha,
    "flags": new_header.flags, "rollback_index": new_header.rollback_index,
    "required_libavb": [new_header.required_libavb_version_major, new_header.required_libavb_version_minor],
    "preserved_descriptor_bytes": sorted(set(old_partitions) - {"system"}),
    "system_descriptor_matches_candidate": True,
    "root_cmdline": root_cmdline,
    "extra_cmdline": args.extra_cmdline,
    "candidate_embedded_rollback_index_not_imported": gsi_header.rollback_index,
}
output.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record, indent=2))
