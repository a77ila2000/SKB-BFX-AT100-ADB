#!/system/bin/sh
# The stock 4.9 wakeup_sources read spins in kernel under Android 12's battery stats reader.
# Preserve real wake-lock/suspend control; replace only the read-only legacy statistics view.
[ "$(getprop ro.product.vendor.model)" = BFX-AT100 ] || exit 1
src=/system/etc/bfx-compat/wakeup_sources-safe.txt
target=/sys/kernel/debug/wakeup_sources
fail() { setprop sys.bfx.wakelock_stats_compat failed; echo "BFX_WAKELOCK_STATS_COMPAT_FAILED $1" > /dev/kmsg; exit 1; }
[ -f "$src" ] || fail source
[ -e "$target" ] || { setprop sys.bfx.wakelock_stats_compat pending; exit 0; }
if grep -q ' /system/etc/bfx-compat/wakeup_sources-safe.txt /sys/kernel/debug/wakeup_sources ' /proc/self/mountinfo; then
    setprop sys.bfx.wakelock_stats_compat ready
    exit 0
fi
mount -o bind "$src" "$target" || fail mount
grep -q ' /system/etc/bfx-compat/wakeup_sources-safe.txt /sys/kernel/debug/wakeup_sources ' /proc/self/mountinfo || fail readback
setprop sys.bfx.wakelock_stats_compat ready
echo BFX_WAKELOCK_STATS_COMPAT_READY > /dev/kmsg
