#!/system/bin/sh
# Mount the verified error-return fix before the vendor audio HAL starts.
src=/system/etc/bfx-compat/audio.primary.amlogic.so
target=/vendor/lib/hw/audio.primary.amlogic.so
fail() {
    setprop sys.bfx.audio_patch failed
    echo "BFX_AUDIO_PATCH_GUARD_FAILED $1" > /dev/kmsg
    exit 0
}
expected=$(cat /system/etc/bfx-compat/device-serial 2>/dev/null)
[ -n "$expected" ] && [ "$(getprop ro.serialno)" = "$expected" ] || fail serial
[ "$(sha256sum "$src" | cut -c 1-64)" = 918c4e5600a1632d2127eb026b26f0339999c611f46bfb7b4e031c6fc79a9db1 ] || fail source
current=$(sha256sum "$target" | cut -c 1-64)
if [ "$current" = 27eb4b859d7366cefdd352e785d7f036e0ab3d0773c62d448a569005dac1105b ]; then
    mount -o bind "$src" "$target" || fail mount
elif [ "$current" != 918c4e5600a1632d2127eb026b26f0339999c611f46bfb7b4e031c6fc79a9db1 ]; then
    fail target
fi
[ "$(sha256sum "$target" | cut -c 1-64)" = 918c4e5600a1632d2127eb026b26f0339999c611f46bfb7b4e031c6fc79a9db1 ] || fail readback
setprop sys.bfx.audio_patch ready
echo BFX_AUDIO_PATCH_READY > /dev/kmsg
