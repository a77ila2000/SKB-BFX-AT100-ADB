package com.android.tv.settings.bfx;
import android.app.IntentService;
import android.content.Intent;
import android.hardware.usb.*;
import android.net.wifi.WifiManager;
import android.provider.Settings;
import android.util.Log;
import java.net.NetworkInterface;

/** A bounded USB-mode preparation at boot/attach; no resident polling or credentials. */
public final class UsbWifiStartupService extends IntentService {
    public UsbWifiStartupService(){super("bfx-usb-wifi-startup");}
    static boolean hasStation() {
        try {return NetworkInterface.getByName("wlan0")!=null;}catch(Exception e){return false;}
    }
    @Override protected void onHandleIntent(Intent intent) {
        int desired=Settings.Global.getInt(getContentResolver(),"wifi_on",0);
        UsbManager usb=getSystemService(UsbManager.class);boolean recognized=false;
        for(UsbDevice d:usb.getDeviceList().values()) {
            if(d.getVendorId()==0x0bda&&d.getProductId()==0xc820)recognized=true;
            if(!UsbModeSwitch.installer(d))continue;
            recognized=true;
            try {UsbModeSwitch.eject(usb,d);}
            catch(Exception e){Log.w("BfxUsbWifi","USB mode preparation failed");}
        }
        Log.i("BfxUsbWifi","Boot/attach preparation: adapter="+recognized+" desired="+desired+" station="+hasStation());
        if(recognized||desired==1||desired==2)for(int i=0;i<80&&!hasStation();i++) {
            try {Thread.sleep(750);}catch(InterruptedException e){Thread.currentThread().interrupt();return;}
        }
        desired=Settings.Global.getInt(getContentResolver(),"wifi_on",0);
        boolean airplane=Settings.Global.getInt(getContentResolver(),Settings.Global.AIRPLANE_MODE_ON,0)!=0;
        if(hasStation()&&((desired==1&&!airplane)||desired==2)) {
            WifiManager wifi=getSystemService(WifiManager.class);
            try {
                // The gated loader restarts the early HAL after wlan0 exists.
                Thread.sleep(2000);
                for(int i=0;i<10&&wifi.getWifiState()==WifiManager.WIFI_STATE_ENABLING;i++)Thread.sleep(500);
                if(!wifi.isWifiEnabled()) {
                    wifi.setWifiEnabled(false);Thread.sleep(1000);
                    if(Settings.Global.getInt(getContentResolver(),Settings.Global.AIRPLANE_MODE_ON,0)==0||desired==2)
                        Log.i("BfxUsbWifi","Restore saved Wi-Fi state: accepted="+wifi.setWifiEnabled(true));
                }
            }catch(InterruptedException e){Thread.currentThread().interrupt();return;}
        }
        Log.i("BfxUsbWifi","Boot/attach preparation finished: station="+hasStation());
    }
}
