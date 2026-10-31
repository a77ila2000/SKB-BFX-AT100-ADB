#!/system/bin/sh
/system/bin/setprop sys.bfx.wifi_abi.state reading
# Expected ENODEV after read-only logging; the probe intentionally never stays loaded.
/system/bin/insmod /system/lib/modules/bfx/wifi-abi-probe.ko
/system/bin/dmesg | /system/bin/grep -oE 'BFX_WIFI_ABI:[a-zA-Z0-9_]+=[0-9a-f]{8}' |
while read -r record; do
    pair=${record#BFX_WIFI_ABI:}
    /system/bin/setprop "sys.bfx.wifi_crc.${pair%=*}" "${pair##*=}"
done
count=$(/system/bin/dmesg | /system/bin/grep -c 'BFX_WIFI_ABI:')
if [ "$count" = 205 ]; then
    /system/bin/setprop sys.bfx.wifi_abi.state exported
else
    /system/bin/setprop sys.bfx.wifi_abi.state unavailable
fi
