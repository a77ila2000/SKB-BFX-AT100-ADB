package com.android.tv.settings.bfx;
import android.net.wifi.WifiConfiguration;
final class WifiSecurity {
    static int type(String caps) {
        if(caps==null)return -1;
        if(caps.contains("WEP")||caps.contains("WAPI"))return -1;
        if(caps.contains("EAP"))return WifiConfiguration.SECURITY_TYPE_EAP;
        if(caps.contains("PSK"))return WifiConfiguration.SECURITY_TYPE_PSK;
        if(caps.contains("SAE"))return WifiConfiguration.SECURITY_TYPE_SAE;
        if(caps.contains("OWE"))return WifiConfiguration.SECURITY_TYPE_OWE;
        return WifiConfiguration.SECURITY_TYPE_OPEN;
    }
    static boolean rawPsk(String value){return value.matches("[0-9a-fA-F]{64}");}
    static boolean validPassword(String value,int type) {
        if(type==WifiConfiguration.SECURITY_TYPE_SAE)return value.length()>=1&&value.length()<=63;
        return value.length()>=8&&value.length()<=63||rawPsk(value);
    }
}
