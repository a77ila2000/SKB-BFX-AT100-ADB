package com.android.tv.settings.bfx;
import android.content.*;
public final class RemoteStartupReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context c,Intent i) {
        String a=i.getAction();
        if(Intent.ACTION_BOOT_COMPLETED.equals(a)||Intent.ACTION_MY_PACKAGE_REPLACED.equals(a)||
           android.hardware.usb.UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(a))
            c.startService(new Intent(c,UsbWifiStartupService.class));
        if(Intent.ACTION_BOOT_COMPLETED.equals(a)||Intent.ACTION_MY_PACKAGE_REPLACED.equals(a)||
           "android.bluetooth.adapter.action.STATE_CHANGED".equals(a)||
           "android.bluetooth.input.profile.action.CONNECTION_STATE_CHANGED".equals(a)||
           "android.bluetooth.device.action.BOND_STATE_CHANGED".equals(a))
            c.startService(new Intent(c,RemoteKeyService.class));
    }
}
