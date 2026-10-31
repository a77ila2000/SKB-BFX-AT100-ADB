#!/system/bin/sh
# The OEM kernel warns but does not reject version mismatches. Fail closed here.
# The expected file must be generated from genuine compiler output and every value
# must match the separate read-only ABI probe before any Wi-Fi driver is loaded.
/system/bin/setprop sys.bfx.usb_wifi_driver loading
if [ ! -r /system/etc/bfx-usb-wifi-expected-crcs.txt ] || [ "$(/system/bin/getprop sys.bfx.wifi_abi.state)" != exported ]; then
    /system/bin/setprop sys.bfx.usb_wifi_driver abi-unverified
    exit 1
fi
count=0
while read -r name expected; do
    actual=$(/system/bin/getprop "sys.bfx.wifi_crc.$name")
    if [ "$actual" != "$expected" ]; then
        /system/bin/setprop sys.bfx.usb_wifi_driver abi-mismatch
        exit 1
    fi
    count=$((count+1))
done < /system/etc/bfx-usb-wifi-expected-crcs.txt
if [ "$count" != 205 ]; then
    /system/bin/setprop sys.bfx.usb_wifi_driver abi-incomplete
    exit 1
fi
# This USB driver has no dedicated P2P-device interface. Keep wlan0 in the STA map.
# Append only this non-secret flag; retain the existing file, owner and network contents.
config=/data/vendor/wifi/wpa/wpa_supplicant.conf
if [ -L "$config" ]; then
    /system/bin/setprop sys.bfx.usb_wifi_driver config-rejected
    exit 1
fi
if [ -f "$config" ] && ! /system/bin/grep -qx 'p2p_disabled=1' "$config"; then
    printf '\np2p_disabled=1\n' >> "$config" || exit 1
fi
if /system/bin/insmod /system/lib/modules/bfx/8821cu.ko rtw_drv_log_level=1; then
    /system/bin/setprop sys.bfx.usb_wifi_driver loaded
else
    /system/bin/setprop sys.bfx.usb_wifi_driver rejected
fi
/system/bin/dmesg | /system/bin/grep -E '8821cu|disagrees about version|Unknown symbol' |
while read -r line; do
    /system/bin/log -p e -t BfxUsbWifi "$line"
done
