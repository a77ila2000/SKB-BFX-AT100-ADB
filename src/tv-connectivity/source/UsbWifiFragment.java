package com.android.tv.settings.bfx;

import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.hardware.usb.*;
import android.net.*;
import android.net.wifi.*;
import android.os.*;
import android.text.InputType;
import android.view.*;
import android.widget.*;
import androidx.preference.*;
import java.net.NetworkInterface;
import java.util.*;

/** TV controls around Android's Wi-Fi service. Passwords stay in the Android Wi-Fi store. */
public final class UsbWifiFragment extends com.android.tv.settings.SettingsPreferenceFragment {
    private WifiManager wifi;
    private UsbManager usb;
    private ConnectivityManager connectivity;
    private PreferenceScreen screen;
    private PreferenceCategory rows;
    private Preference status,scan;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private boolean switching, enabling, enableTried, resumed;
    private int switchedDeviceId=-1;
    private int interfaceWaits;
    private final BroadcastReceiver changes=new BroadcastReceiver() {
        @Override public void onReceive(Context c, Intent i) {
            String action=i.getAction();
            if(UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(action)||UsbManager.ACTION_USB_DEVICE_DETACHED.equals(action)) {
                interfaceWaits=0;enableTried=false;
            }
            if (WifiManager.SCAN_RESULTS_AVAILABLE_ACTION.equals(action)) renderResults();
            else update();
        }
    };
    private final ConnectivityManager.NetworkCallback networks=new ConnectivityManager.NetworkCallback() {
        @Override public void onCapabilitiesChanged(Network n, NetworkCapabilities caps) { handler.post(()->update()); }
        @Override public void onLost(Network n) { handler.post(()->update()); }
    };

    @Override public void onCreatePreferences(Bundle b,String rootKey) {
        Context context=requireContext();
        wifi=context.getSystemService(WifiManager.class);usb=context.getSystemService(UsbManager.class);
        connectivity=context.getSystemService(ConnectivityManager.class);
        screen=getPreferenceManager().createPreferenceScreen(context);screen.setTitle("Wi-Fi");setPreferenceScreen(screen);
        status=new Preference(context);status.setTitle("USB Wi-Fi 수신기");status.setSelectable(false);screen.addPreference(status);
        scan=button("다시 검색",v->{interfaceWaits=0;enableTried=false;requestScan();});screen.addPreference(scan);
        rows=new PreferenceCategory(context);rows.setTitle("사용 가능한 네트워크");screen.addPreference(rows);
        screen.addPreference(button("네트워크 추가",v->startActivity(new Intent().setClassName(context.getPackageName(),
            "com.android.tv.settings.connectivity.AddWifiNetworkActivity"))));
        screen.addPreference(button("유선 연결 설정",v->startActivity(new Intent().setClassName(context.getPackageName(),
            "com.android.tv.settings.connectivity.NetworkActivity"))));
    }
    private Preference button(String title,View.OnClickListener listener) {
        Preference p=new Preference(requireContext());p.setTitle(title);
        p.setOnPreferenceClickListener(value->{listener.onClick(null);return true;});return p;
    }
    @Override public void onResume() {
        super.onResume(); resumed=true;
        IntentFilter f=new IntentFilter();
        for(String action:new String[]{UsbManager.ACTION_USB_DEVICE_ATTACHED,UsbManager.ACTION_USB_DEVICE_DETACHED,
            WifiManager.WIFI_STATE_CHANGED_ACTION,WifiManager.NETWORK_STATE_CHANGED_ACTION,
            WifiManager.SCAN_RESULTS_AVAILABLE_ACTION,WifiManager.SUPPLICANT_STATE_CHANGED_ACTION})f.addAction(action);
        requireContext().registerReceiver(changes,f);
        connectivity.registerNetworkCallback(new NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_WIFI).build(),networks);update();
    }
    @Override public void onPause() {
        resumed=false; handler.removeCallbacksAndMessages(null); requireContext().unregisterReceiver(changes);
        connectivity.unregisterNetworkCallback(networks); super.onPause();
    }
    private boolean hasStation() {
        try {
            Enumeration<NetworkInterface> list=NetworkInterface.getNetworkInterfaces();
            while(list!=null && list.hasMoreElements()) {
                String n=list.nextElement().getName();
                if(n.startsWith("wlan")||n.startsWith("mlan")||n.startsWith("ra0"))return true;
            }
        } catch(Exception ignored) {} return false;
    }
    private boolean candidate(UsbDevice d) {
        int v=d.getVendorId(),p=d.getProductId();
        if(v==0x0bda && p==0x1a2b)return true;
        if(v==0x0bda && (p==0x8152||p==0x8153||p==0x8156))return false;
        if(v!=0x0bda && v!=0x148f && v!=0x0e8d && v!=0x0cf3 && v!=0x2357 && v!=0x2001)return false;
        for(int i=0;i<d.getInterfaceCount();i++)if(d.getInterface(i).getInterfaceClass()==255)return true;
        return false;
    }
    private void empty(String message) {
        status.setSummary(message);scan.setTitle("수신기 다시 확인");scan.setEnabled(true);rows.removeAll();
    }
    private void update() {
        if(!resumed)return;
        ArrayList<UsbDevice> devices=new ArrayList<>();
        for(UsbDevice d:usb.getDeviceList().values())if(candidate(d))devices.add(d);
        if(devices.isEmpty() && !hasStation()) { empty("USB Wi-Fi 수신기를 연결하세요.\n연결하면 주변 Wi-Fi를 검색합니다.");return; }
        if(switching) {status.setSummary("USB Wi-Fi 수신기를 준비하고 있습니다…");return;}
        for(UsbDevice d:devices)if(d.getVendorId()==0x0bda && d.getProductId()==0x1a2b) {
            if(switchedDeviceId==d.getDeviceId()) {empty("수신기 준비가 완료되지 않았습니다. USB 수신기를 다시 연결해 주세요.");return;}
            if(!usb.hasPermission(d)) {empty("USB 수신기 접근 권한을 확인할 수 없습니다. 수신기를 다시 연결해 주세요.");return;}
            switchMode(d); return;
        }
        if(!hasStation()) {
            if(interfaceWaits++<40) {
                status.setSummary("USB Wi-Fi 수신기를 확인하고 있습니다…");handler.postDelayed(()->update(),1500);return;
            }
            empty("USB 수신기는 인식됐지만 Wi-Fi를 시작할 수 없습니다.\n수신기를 다시 연결한 뒤 확인해 주세요.");return;
        }
        interfaceWaits=0;scan.setTitle("다시 검색");
        if(!wifi.isWifiEnabled()) {
            if(!enabling) {
                if(enableTried){empty("Wi-Fi를 시작하지 못했습니다. 다시 검색을 눌러 재시도해 주세요.");return;}
                enableTried=true;enabling=true; status.setSummary("Wi-Fi를 켜고 있습니다…");
                if(!wifi.setWifiEnabled(true)) {enabling=false;empty("Wi-Fi를 시작하지 못했습니다. 수신기의 지원 여부를 확인해 주세요.");return;}
                handler.postDelayed(()->{
                    if(!resumed)return;
                    if(!wifi.isWifiEnabled()){empty("USB 수신기는 연결됐지만 Wi-Fi를 시작하지 못했습니다.\n수신기의 지원 여부를 확인해 주세요.");enabling=false;}
                    else requestScan();
                },8000);
            }
            return;
        }
        enabling=false;
        if(!connectionSummary())status.setSummary("사용할 Wi-Fi를 선택하세요.");
        if(rows.getPreferenceCount()==0)requestScan();
    }
    private boolean connectionSummary() {
        WifiInfo info=wifi.getConnectionInfo();
        if(info!=null && info.getSupplicantState()==android.net.wifi.SupplicantState.COMPLETED) {
            String ssid=unquote(info.getSSID()); boolean validated=false;
            for(Network n:connectivity.getAllNetworks()) {
                NetworkCapabilities c=connectivity.getNetworkCapabilities(n);
                if(c!=null && c.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                    if(c.hasCapability(NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL)) {
                        status.setSummary(ssid+"에 연결됐습니다. 네트워크 로그인이 필요합니다.");
                        rows.removeAll();rows.addPreference(button("네트워크 로그인",v->openPortal(n)));return true;
                    }
                    validated|=c.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
                }
            }
            status.setSummary(ssid+"에 연결됨"+(validated?" · 인터넷 연결됨":" · 인터넷 연결 확인 중"));
            return true;
        }return false;
    }
    private void openPortal(Network n) {
        try {ConnectivityManager.class.getMethod("startCaptivePortalApp",Network.class).invoke(connectivity,n);}
        catch(Exception e) {status.setSummary("네트워크 로그인 화면을 열지 못했습니다. 네트워크 설정에서 다시 시도해 주세요.");}
    }
    @SuppressWarnings("deprecation") private void requestScan() {
        if(!resumed)return;
        if(!wifi.isWifiEnabled()) {enabling=false;enableTried=false;update();return;}
        status.setSummary("주변 Wi-Fi를 검색하고 있습니다…");
        try {
            boolean started=wifi.startScan();
            if(!started) {renderResults();if(rows.getPreferenceCount()==0)status.setSummary("검색을 시작하지 못했습니다. 잠시 후 다시 검색해 주세요.");}
        } catch(SecurityException e) {empty("Wi-Fi 검색 권한을 확인할 수 없습니다.");}
    }
    private static String unquote(String s) {return s!=null && s.length()>1 && s.startsWith("\"") && s.endsWith("\"")?s.substring(1,s.length()-1):String.valueOf(s);}
    @SuppressWarnings("deprecation") private void renderResults() {
        if(!resumed || !wifi.isWifiEnabled())return;
        List<ScanResult> scans;
        try {scans=new ArrayList<>(wifi.getScanResults());}catch(SecurityException e){empty("Wi-Fi 검색 권한을 확인할 수 없습니다.");return;}
        WifiInfo info=wifi.getConnectionInfo();String connected=info!=null&&info.getSupplicantState()==SupplicantState.COMPLETED?unquote(info.getSSID()):null;
        scans.sort((a,b)->{int current=Boolean.compare(Objects.equals(b.SSID,connected),Objects.equals(a.SSID,connected));return current!=0?current:Integer.compare(b.level,a.level);});
        LinkedHashMap<String,ScanResult> unique=new LinkedHashMap<>();
        for(ScanResult s:scans)if(s.SSID!=null && !s.SSID.isEmpty())unique.putIfAbsent(s.SSID+"|"+WifiSecurity.type(s.capabilities),s);
        rows.removeAll();
        for(ScanResult s:unique.values()) {
            String label=s.SSID+(s.SSID.equals(connected)?"  · 연결됨":WifiSecurity.type(s.capabilities)!=WifiConfiguration.SECURITY_TYPE_OPEN?"  · 보안 네트워크":"");
            Preference p=button(label,v->select(s));p.setKey("wifi:"+s.SSID+"|"+WifiSecurity.type(s.capabilities));rows.addPreference(p);
        }
        if(!connectionSummary())status.setSummary(unique.isEmpty()?"주변 Wi-Fi를 찾지 못했습니다. 다시 검색해 주세요.":"사용할 Wi-Fi를 선택하세요.");
        // Native TV preference navigation retains the current D-pad focus.
    }
    private void select(ScanResult s) {
        int type=WifiSecurity.type(s.capabilities);
        if(type<0) {
            new AlertDialog.Builder(requireContext()).setMessage("이 네트워크의 보안 방식은 지원하지 않습니다.")
                .setPositiveButton("확인",null).show();return;
        }
        // Reuse the stock TV guided keyboard, saved-network, error and connection flow.
        int nativeSecurity=type==WifiConfiguration.SECURITY_TYPE_PSK?2:
            type==WifiConfiguration.SECURITY_TYPE_SAE?5:type==WifiConfiguration.SECURITY_TYPE_OWE?4:
            type==WifiConfiguration.SECURITY_TYPE_EAP?3:0;
        startActivity(new Intent().setClassName(requireContext().getPackageName(),
            "com.android.tv.settings.connectivity.WifiConnectionActivity")
            .putExtra("wifi_ssid",s.SSID).putExtra("wifi_security_name",nativeSecurity));
    }
    private void switchMode(UsbDevice d) {
        switching=true;switchedDeviceId=d.getDeviceId();status.setSummary("USB Wi-Fi 수신기를 준비하고 있습니다…");
        new Thread(()->{
            String error=null;
            try {
                UsbModeSwitch.eject(usb,d);
            }catch(Exception e){error="USB Wi-Fi 수신기를 준비하지 못했습니다. 다시 연결해 주세요.";}
            final String message=error;handler.postDelayed(()->{switching=false;if(!resumed)return;if(message!=null&&!hasStation())empty(message);else update();},1500);
        },"bfx-usb-wifi-mode").start();
    }
}
