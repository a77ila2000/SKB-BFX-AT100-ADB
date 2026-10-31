package com.android.tv.settings.bfx;
import android.net.wifi.WifiConfiguration;
public final class WifiSecurityTest {
    public static void main(String[] args) {
        if(WifiSecurity.type("[WEP][ESS]")!=-1)throw new AssertionError("WEP classified as open");
        if(WifiSecurity.type("[OWE][ESS]")!=WifiConfiguration.SECURITY_TYPE_OWE)throw new AssertionError();
        if(WifiSecurity.type("[WPA2-PSK+SAE-CCMP]")!=WifiConfiguration.SECURITY_TYPE_PSK)throw new AssertionError();
        if(WifiSecurity.validPassword("1234567",WifiConfiguration.SECURITY_TYPE_PSK))throw new AssertionError();
        if(!WifiSecurity.validPassword("12345678",WifiConfiguration.SECURITY_TYPE_PSK))throw new AssertionError();
        if(!WifiSecurity.rawPsk(new String(new char[64]).replace('\0','a')))throw new AssertionError();
        if(WifiSecurity.rawPsk(new String(new char[64]).replace('\0','z')))throw new AssertionError();
        System.out.println("Wi-Fi security classification and password checks passed");
    }
}
