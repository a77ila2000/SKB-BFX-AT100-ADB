#!/system/bin/sh
# Register one confirmed BA03 ID with the original, unchanged ARM32 SKB driver.
# No module replacement, CRC patch, new su interface or NUGU application.
setprop sys.bfx.stock_remote.state checking
fail() { echo "state=$1"; setprop sys.bfx.stock_remote.state "$1"; exit 1; }
[ "$(getprop ro.product.vendor.model)" = BFX-AT100 ] || fail wrong-model
[ "$(uname -r)" = 4.9.113 ] || fail wrong-kernel
grep -q "#71 SMP PREEMPT" /proc/version || fail wrong-kernel-build
[ ! -e /data/local/tmp/bfx-stock-remote.disable ] || fail owner-disabled
module=/vendor/lib/hid-skbrm.ko
expected=81972bf616a5f7ee798b5fce40019f46691f7bd21766b11c2a219fb23e243e1c
actual=$(sha256sum "$module" | cut -d' ' -f1)
[ "$actual" = "$expected" ] || fail different-stock-module
[ -d /sys/module/hid_skbrm ] || fail module-not-loaded
driver=/sys/bus/hid/drivers/skbrm
[ -w "$driver/new_id" ] || fail registration-unavailable
guard=/data/misc/bfx-stock-remote
[ ! -L "$guard" ] || fail invalid-trial-guard
mkdir -p "$guard" || fail no-trial-guard
[ "$(stat -c %u "$guard")" = 0 ] || fail invalid-trial-owner
chmod 0700 "$guard"
chown root:shell "$guard"
chmod 0750 "$guard"
chcon u:object_r:shell_data_file:s0 "$guard"
report="$guard/registration.txt"
[ ! -L "$report" ] || fail invalid-report
: > "$report" || fail report-unavailable
chown root:shell "$report"
chmod 0640 "$report"
chcon u:object_r:shell_data_file:s0 "$report"
exec >> "$report" 2>&1
echo "trial=late-connect-watch-v4"
id
ls -ldZ "$driver" "$driver/new_id"
if [ -f "$guard/attempted-v3" ] && [ ! -e /data/local/tmp/bfx-stock-remote.confirm ]; then
    fail trial-awaiting-confirmation
fi
: > "$guard/attempted-v3" || fail trial-guard-write
sync
# Toybox printf writes literal characters separately; sysfs requires one complete write.
echo '0005 005d 0004 0' > "$driver/new_id" || fail registration-rejected
setprop sys.bfx.stock_remote.state id-registered
# Generic HID may claim a late/reconnected remote before this dynamic ID.
# Watch every enumeration; bind once per path and restore generic on rejection.
write_driver_key() { echo "$2" > "$1"; }
last_state=id-registered
mark() {
    [ "$last_state" = "$1" ] && return
    [ "$(stat -c %s "$report")" -le 65536 ] || : > "$report"
    echo "state=$1"
    setprop sys.bfx.stock_remote.state "$1"
    last_state="$1"
}
failed_path=
while :; do
    [ ! -e /data/local/tmp/bfx-stock-remote.disable ] || fail owner-disabled
    found=
    matches=0
    for path in /sys/bus/hid/devices/0005:005D:0004.*; do
        [ -d "$path" ] || continue
        found="$path"
        matches=$((matches+1))
    done
    [ "$matches" -le 1 ] || fail multiple-remotes
    if [ -z "$found" ]; then
        failed_path=
        mark registered-awaiting-device
        sleep 2
        continue
    fi
    current=$(basename "$(readlink "$found/driver")")
    if [ "$current" = skbrm ]; then
        failed_path=
        mark native-bound
        sleep 2
        continue
    fi
    if [ "$current" != hid-generic ]; then
        mark waiting-for-driver
        sleep 2
        continue
    fi
    # A failed probe is not retried until the device is re-enumerated.
    if [ "$failed_path" = "$found" ]; then
        sleep 5
        continue
    fi
    device=$(basename "$found")
    if ! write_driver_key /sys/bus/hid/drivers/hid-generic/unbind "$device"; then
        failed_path="$found"
        mark unbind-rejected
        sleep 5
        continue
    fi
    if write_driver_key "$driver/bind" "$device"; then
        if [ "$(basename "$(readlink "$found/driver")")" = skbrm ]; then
            mark native-bound
            sleep 2
            continue
        fi
    fi
    failed_path="$found"
    if [ ! -d "$found" ]; then
        mark registered-awaiting-device
    elif write_driver_key /sys/bus/hid/drivers/hid-generic/bind "$device"; then
        mark generic-restored
    else
        mark generic-restore-failed
    fi
    sleep 5
done
