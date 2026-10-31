package com.android.tv.settings.bfx;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.media.AudioDeviceInfo;

/** Explicit HDMI volume routing control; manifest restricts callers to DUMP. */
public final class HdmiVolumeReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (!"com.android.tv.settings.bfx.SET_CEC_VOLUME".equals(intent.getAction())
                || !intent.hasExtra("enabled")) { setResultCode(1); return; }
        try {
            boolean forwarding = intent.getBooleanExtra("enabled", false);
            Object hdmi = context.getSystemService("hdmi_control");
            if (hdmi == null) throw new IllegalStateException("HDMI control unavailable");
            hdmi.getClass().getMethod("setHdmiCecVolumeControlEnabled", int.class)
                    .invoke(hdmi, forwarding ? 1 : 0);
            Class<?> type = Class.forName("android.media.AudioDeviceAttributes");
            Object output = type.getConstructor(int.class, int.class, String.class)
                    .newInstance(2, AudioDeviceInfo.TYPE_HDMI, "");
            Object audio = context.getSystemService(android.media.AudioManager.class);
            audio.getClass().getMethod("setDeviceVolumeBehavior", type, int.class)
                    .invoke(audio, output, forwarding ? 1 : 0);
            setResultCode(0);
        } catch (Exception error) {
            android.util.Log.e("BfxLocalVolume", "HDMI volume routing unavailable", error);
            setResultCode(1);
        }
    }
}
