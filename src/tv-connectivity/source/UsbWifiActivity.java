package com.android.tv.settings.bfx;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.net.*;
import android.view.WindowManager;
import androidx.fragment.app.Fragment;
import com.android.tv.settings.overlay.FlavorUtils;

/** Uses the same TV settings host and pane factory as the stock network screen. */
public final class UsbWifiActivity extends com.android.tv.settings.connectivity.NetworkActivity {
    private ConnectivityManager connectivity;
    private final ConnectivityManager.NetworkCallback setupNetwork=new ConnectivityManager.NetworkCallback() {};
    private boolean requested;
    @Override public void onCreate(Bundle b) {
        super.onCreate(b);getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);setTurnScreenOn(true);
        connectivity=getSystemService(ConnectivityManager.class);
        // Ethernet can satisfy all default requests. Keep a Wi-Fi request during this setup
        // activity (including its stock password child), without changing the default route.
        try {
            connectivity.requestNetwork(new NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET).build(),setupNetwork);
            requested=true;
        }catch(SecurityException e){android.util.Log.e("BfxUsbWifi","Wi-Fi setup network request denied");}
        try {getPackageManager().setComponentEnabledSetting(new ComponentName("com.android.settings",
            "com.android.settings.Settings$WifiSettingsActivity"),PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
            PackageManager.DONT_KILL_APP);} catch(SecurityException ignored) {}
    }
    @Override public void onDestroy() {
        if(requested){connectivity.unregisterNetworkCallback(setupNetwork);requested=false;}
        super.onDestroy();
    }
    @Override protected Fragment createSettingsFragment() {
        return FlavorUtils.getFeatureFactory(this).getSettingsFragmentProvider()
            .newSettingsFragment(UsbWifiFragment.class.getName(),null);
    }
}
