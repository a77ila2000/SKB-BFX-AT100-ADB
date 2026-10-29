#!/bin/bash
# Offline image construction only. No device nodes are written by this script.
set -euo pipefail
if [[ $# != 2 ]]; then echo "Usage: $0 ORIGINAL_GSI.img NEW_OUTPUT_DIRECTORY" >&2; exit 2; fi
: "${AVBTOOL:?Set the pinned Android 12 avbtool.py path}"
: "${SIGNING_KEY:?Set a locally supplied, accepted signing key path}"
: "${STOCK_VBMETA:?Set the locally backed-up original vbmeta image path}"
: "${STOCK_PARTS_DIR:?Set the directory of your verified original boot/recovery/vendor/product/dtbo/dtb images}"
: "${AUDIO_LIBRARY:?Set the original vendor audio.primary.amlogic.so path}"
repo=$(cd "$(dirname "$0")/.." && pwd)
source=$(realpath "$1")
out=$(realpath -m "$2")
for path in "$repo" "$source" "$out" "$AVBTOOL" "$SIGNING_KEY" "$STOCK_VBMETA" "$STOCK_PARTS_DIR" "$AUDIO_LIBRARY" "${ADB_PUBLIC_KEY:-}"; do
    if [[ "$path" =~ [[:space:]] || "$path" == *'"'* || "$path" == *\\* ]]; then
        echo 'Use paths without whitespace, quotes or backslashes for debugfs.' >&2; exit 2
    fi
done
for path in "$source" "$AVBTOOL" "$SIGNING_KEY" "$STOCK_VBMETA" "$AUDIO_LIBRARY"; do
    [[ -f "$path" ]] || { echo 'A required local regular file is missing.' >&2; exit 2; }
done
[[ ! -e "$out" ]] || { echo 'Output directory must not exist.' >&2; exit 2; }
for part in boot recovery vendor product dtbo dtb; do
    [[ -f "$STOCK_PARTS_DIR/$part.img" ]] || { echo "Missing original $part image." >&2; exit 2; }
done
echo '62b68f4c8f7e01497e02628f05e2a5ec0a0328ef98c8262be143c3ee90f2bc1b  '"$source" | sha256sum -c -
echo 'a9ec360fc5395db9b72d36c03af59ff984f4eefcc349dc32a556de7f8ed892ab  '"$AVBTOOL" | sha256sum -c -
mkdir "$out"
cp "$source" "$out/system.img"
python3 "$AVBTOOL" erase_footer --image "$out/system.img"
debugfs -R "dump /system/lib/libbootanimation.so $out/libbootanimation.original.so" "$out/system.img" > "$out/debugfs.log" 2>&1
python3 "$repo/src/patch_libraries.py" bootanimation "$out/libbootanimation.original.so" "$out/libbootanimation.so"
python3 "$repo/src/patch_libraries.py" audio "$AUDIO_LIBRARY" "$out/audio.primary.amlogic.so"
debugfs -R "dump /system/build.prop $out/build.prop.original" "$out/system.img" >> "$out/debugfs.log" 2>&1
python3 - "$out/build.prop.original" "$out/build.prop" <<'PY'
from pathlib import Path
import sys
source, output = map(Path, sys.argv[1:])
data = source.read_bytes()
if b'ro.adb.secure=0' not in data:
    raise SystemExit('Expected pinned GSI ADB property was not found')
data = data.replace(b'ro.adb.secure=0', b'ro.adb.secure=1')
if any(line.startswith(b'ro.adb.secure=') and line != b'ro.adb.secure=1' for line in data.splitlines()):
    raise SystemExit('Unexpected ADB authentication property')
with output.open('xb') as stream:
    stream.write(data)
PY
printf 'u:object_r:rootfs:s0\0' > "$out/label-rootfs"
printf 'u:object_r:system_file:s0\0' > "$out/label-system"
printf 'u:object_r:system_lib_file:s0\0' > "$out/label-system-lib"
printf 'u:object_r:vendor_file:s0\0' > "$out/label-vendor"
cat > "$out/requests.txt" <<EOF
mkdir /system/etc/bfx-compat
set_inode_field /system/etc/bfx-compat mode 040755
set_inode_field /system/etc/bfx-compat uid 0
set_inode_field /system/etc/bfx-compat gid 0
ea_set -f $out/label-system /system/etc/bfx-compat security.selinux
EOF
files=("$repo/overlay/fstab.bfx_gsi" "$out/libbootanimation.so" "$out/audio.primary.amlogic.so" "$out/build.prop" "$repo/overlay/bfx-audio-compat.sh" "$repo/overlay/bfx-audio-compat.rc" "$repo/overlay/bfx-diagnostics.rc")
targets=(/fstab.bfx_gsi /system/lib/libbootanimation.so /system/etc/bfx-compat/audio.primary.amlogic.so /system/build.prop /system/bin/bfx-audio-compat.sh /system/etc/init/bfx-audio-compat.rc /system/etc/init/bfx-diagnostics.rc)
labels=(rootfs system-lib vendor system system system system)
if [[ -n "${ADB_PUBLIC_KEY:-}" ]]; then
    [[ -f "$ADB_PUBLIC_KEY" ]] || { echo 'Public ADB key file is missing.' >&2; exit 2; }
    if grep -q 'PRIVATE KEY' "$ADB_PUBLIC_KEY"; then echo 'Do not supply a private ADB key.' >&2; exit 2; fi
    python3 - "$ADB_PUBLIC_KEY" <<'PY'
import base64, sys
from pathlib import Path
lines = Path(sys.argv[1]).read_text().splitlines()
if len(lines) != 1 or not lines[0].split():
    raise SystemExit('Expected one Android ADB public key')
if len(base64.b64decode(lines[0].split()[0], validate=True)) != 524:
    raise SystemExit('Unexpected Android ADB public-key length')
PY
    printf 'u:object_r:adb_keys_file:s0\0' > "$out/label-adb"
    printf 'on post-fs-data\n    setprop service.adb.tcp.port 5555\n    start adbd\n' > "$out/bfx-local-adb.rc"
    files+=("$ADB_PUBLIC_KEY" "$out/bfx-local-adb.rc")
    targets+=(/adb_keys /system/etc/init/bfx-local-adb.rc)
    labels+=(adb system)
fi
for i in "${!targets[@]}"; do
    target=${targets[$i]}
    cat >> "$out/requests.txt" <<EOF
rm $target
write ${files[$i]} $target
set_inode_field $target mode 0100644
set_inode_field $target uid 0
set_inode_field $target gid 0
ea_set -f $out/label-${labels[$i]} $target security.selinux
EOF
done
debugfs -w -f "$out/requests.txt" "$out/system.img" >> "$out/debugfs.log" 2>&1
mkdir "$out/private-readback"
for i in "${!targets[@]}"; do
    debugfs -R "dump ${targets[$i]} $out/private-readback/$i" "$out/system.img" >> "$out/debugfs.log" 2>&1
    cmp "${files[$i]}" "$out/private-readback/$i"
    debugfs -R "stat ${targets[$i]}" "$out/system.img" >> "$out/metadata.txt" 2>&1
    debugfs -R "ea_list ${targets[$i]}" "$out/system.img" >> "$out/metadata.txt" 2>&1
done
e2fsck -fn "$out/system.img" > "$out/e2fsck.txt" 2>&1
python3 "$AVBTOOL" add_hashtree_footer --image "$out/system.img" --partition_name system \
    --partition_size 1551892480 --algorithm SHA256_RSA2048 --key "$SIGNING_KEY" \
    --hash_algorithm sha256 --salt 770a1e8dd4d0f051709b6264af0b628ff3aecff43d8cd72cfc5a2104f07860f1 \
    --do_not_generate_fec --rollback_index 0 \
    --prop com.android.build.system.os_version:12 --prop com.android.build.system.security_patch:2022-07-05
python3 "$repo/src/build_vbmeta.py" --avbtool "$AVBTOOL" --key "$SIGNING_KEY" --stock "$STOCK_VBMETA" \
    --system "$out/system.img" --output "$out/vbmeta.img" \
    --extra-cmdline 'androidboot.android_dt_dir=/proc/device-tree/firmware/bfx_gsi/ androidboot.fstab_suffix=bfx_gsi androidboot.boot_devices=ffe07000.emmc' > "$out/vbmeta-report.json"
cp "$out/vbmeta.img" "$out/flash-vbmeta.img"
truncate -s 2097152 "$out/flash-vbmeta.img"
python3 "$AVBTOOL" verify_image --image "$out/system.img" > "$out/system-avb.txt"
for part in boot recovery vendor product dtbo dtb; do
    ln -s "$(realpath "$STOCK_PARTS_DIR/$part.img")" "$out/$part.img"
done
python3 "$AVBTOOL" verify_image --image "$out/vbmeta.img" > "$out/vbmeta-avb.txt"
sha256sum "$out/system.img" "$out/flash-vbmeta.img" > "$out/image-sha256.txt"
echo 'Offline images built and reread-verified. No device was written. If ADB_PUBLIC_KEY was set, keep the personalized output private.'
