package com.android.tv.settings.bfx;

import android.app.*;
import android.bluetooth.*;
import android.content.*;
import android.hardware.input.InputManager;
import android.os.*;
import android.view.*;
import java.io.*;
import java.lang.reflect.Method;
import java.util.*;

/** Decode only the paired BMM-BA03's unsupported compact keyboard report. */
public final class RemoteKeyService extends Service {
    private static UUID uuid(String s){return UUID.fromString("0000"+s+"-0000-1000-8000-00805f9b34fb");}
    private final Handler main=new Handler(Looper.getMainLooper());
    private BluetoothAdapter adapter;
    private BluetoothGatt gatt;
    private BluetoothGattCharacteristic pnp,target;
    private final ArrayDeque<BluetoothGattCharacteristic> candidates=new ArrayDeque<>();
    private BluetoothGattCharacteristic candidate;
    private Object input;
    private Method inject;
    private int held=-1,presses,errors;
    private long downAt;
    private String state="starting";
    private final Runnable releaseGuard=()->release();
    private final BluetoothGattCallback callbacks=new BluetoothGattCallback() {
        @Override public void onConnectionStateChange(BluetoothGatt g,int status,int connected) {
            main.post(()->{
                if(g!=gatt)return;
                if(status!=BluetoothGatt.GATT_SUCCESS || connected==BluetoothProfile.STATE_DISCONNECTED) {
                    release();state="disconnected";return;
                }
                if(connected==BluetoothProfile.STATE_CONNECTED) {state="reading remote identity";g.discoverServices();}
            });
        }
        @Override public void onServicesDiscovered(BluetoothGatt g,int status) {
            main.post(()->{
                if(g!=gatt)return;
                if(status!=0){fail("service discovery");return;}
                BluetoothGattService device=g.getService(uuid("180a")),hid=g.getService(uuid("1812"));
                if(device==null||hid==null){fail("missing HID identity");return;}
                pnp=device.getCharacteristic(uuid("2a50"));candidates.clear();
                for(BluetoothGattCharacteristic c:hid.getCharacteristics())if(c.getUuid().equals(uuid("2a4d")) &&
                    (c.getProperties()&BluetoothGattCharacteristic.PROPERTY_NOTIFY)!=0)candidates.add(c);
                if(pnp==null||!g.readCharacteristic(pnp))fail("identity read");
            });
        }
        @Override public void onCharacteristicRead(BluetoothGatt g,BluetoothGattCharacteristic c,int status) {
            byte[] value=c.getValue()==null?null:c.getValue().clone();
            main.post(()->{
                if(g!=gatt || c!=pnp)return;
                if(status!=0 || value==null || value.length!=7 || (value[0]&255)!=1 ||
                    ((value[1]&255)|((value[2]&255)<<8))!=0x005d ||
                    ((value[3]&255)|((value[4]&255)<<8))!=0x0004) {fail("remote identity mismatch");return;}
                nextReference();
            });
        }
        @Override public void onDescriptorRead(BluetoothGatt g,BluetoothGattDescriptor d,int status) {
            byte[] value=d.getValue()==null?null:d.getValue().clone();
            main.post(()->{
                if(g!=gatt)return;
                if(status==0 && value!=null && value.length==2 && (value[0]&255)==0x80 && value[1]==1) {
                    target=d.getCharacteristic();
                    if(!g.setCharacteristicNotification(target,true)){fail("notification registration");return;}
                    BluetoothGattDescriptor cccd=target.getDescriptor(uuid("2902"));
                    if(cccd==null){fail("missing notification descriptor");return;}
                    cccd.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                    if(!g.writeDescriptor(cccd))fail("notification enable");
                } else nextReference();
            });
        }
        @Override public void onDescriptorWrite(BluetoothGatt g,BluetoothGattDescriptor d,int status) {
            main.post(()->{if(g==gatt){if(status==0)state="ready";else fail("notification status "+status);}});
        }
        @Override public void onCharacteristicChanged(BluetoothGatt g,BluetoothGattCharacteristic c) {
            byte[] b=c.getValue()==null?null:c.getValue().clone();
            main.post(()->{
                if(g!=gatt || target==null || c.getInstanceId()!=target.getInstanceId())return;
                if(yieldToNative())return;
                int key=RemoteReport.decode(b);
                if(key==RemoteReport.RELEASE)release();
                else if(key>=0)press(key);
            });
        }
    };
    @Override public void onCreate() {
        super.onCreate();adapter=getSystemService(BluetoothManager.class).getAdapter();
        try {
            Class<?> type=Class.forName("android.hardware.input.InputManager");
            input=type.getMethod("getInstance").invoke(null);
            inject=type.getMethod("injectInputEvent",InputEvent.class,int.class);
        } catch(Exception e){fail("input API unavailable");}
    }
    @Override public int onStartCommand(Intent i,int flags,int id) {
        if(yieldToNative())return START_NOT_STICKY;
        if(adapter!=null && !adapter.isEnabled()) {release();if(gatt!=null)gatt.close();gatt=null;state="Bluetooth off";}
        else connect();
        return START_STICKY;
    }
    private boolean yieldToNative() {
        try {
            Object state=Class.forName("android.os.SystemProperties")
                .getMethod("get",String.class).invoke(null,"sys.bfx.stock_remote.state");
            if(!"native-bound".equals(state)) {
                if(!"id-registered".equals(state) && !"registered-awaiting-device".equals(state))return false;
                boolean nativeInput=false;
                for(int id:InputDevice.getDeviceIds()) {
                    InputDevice d=InputDevice.getDevice(id);
                    if(d!=null && !d.isVirtual() && d.getVendorId()==0x005d && d.getProductId()==0x0004 &&
                        (d.getSources()&InputDevice.SOURCE_GAMEPAD)==InputDevice.SOURCE_GAMEPAD)nativeInput=true;
                }
                if(!nativeInput)return false;
            }
        }catch(Exception e){return false;}
        release();if(gatt!=null)gatt.close();gatt=null;
        state="stock HID driver active";stopSelf();return true;
    }
    private void connect() {
        if(gatt!=null || adapter==null || !adapter.isEnabled() || inject==null)return;
        ArrayList<BluetoothDevice> matches=new ArrayList<>();
        for(BluetoothDevice d:adapter.getBondedDevices())if(d.getName()!=null && d.getName().startsWith("BMM_BA03_"))matches.add(d);
        if(matches.size()!=1){state=matches.isEmpty()?"no paired BMM-BA03":"multiple paired BMM-BA03 remotes";return;}
        state="connecting";gatt=matches.get(0).connectGatt(this,true,callbacks,BluetoothDevice.TRANSPORT_LE);
    }
    private void nextReference() {
        while(!candidates.isEmpty()) {
            candidate=candidates.removeFirst();BluetoothGattDescriptor ref=candidate.getDescriptor(uuid("2908"));
            if(ref!=null) {if(!gatt.readDescriptor(ref))fail("report reference read");return;}
        }
        fail("compact keyboard report absent");
    }
    private boolean send(int key,int action,long start) {
        if(inject==null)return false;
        try {
            KeyEvent e=new KeyEvent(start,SystemClock.uptimeMillis(),action,key,0,0,
                KeyCharacterMap.VIRTUAL_KEYBOARD,0,KeyEvent.FLAG_FROM_SYSTEM|KeyEvent.FLAG_VIRTUAL_HARD_KEY,
                InputDevice.SOURCE_KEYBOARD);
            return Boolean.TRUE.equals(inject.invoke(input,e,0));
        }catch(Exception e){fail("input injection");return false;}
    }
    private void press(int key) {
        main.removeCallbacks(releaseGuard);
        if(held!=key) {
            release();downAt=SystemClock.uptimeMillis();
            if(!getSystemService(PowerManager.class).isInteractive()){
                send(KeyEvent.KEYCODE_WAKEUP,KeyEvent.ACTION_DOWN,downAt);send(KeyEvent.KEYCODE_WAKEUP,KeyEvent.ACTION_UP,downAt);
            }
            if(send(key,KeyEvent.ACTION_DOWN,downAt)){held=key;presses++;}else errors++;
        }
        // Lost disconnect/release packets must never leave a navigation key held.
        main.postDelayed(releaseGuard,3000);
    }
    private void release() {
        main.removeCallbacks(releaseGuard);
        if(held>=0){int key=held;held=-1;send(key,KeyEvent.ACTION_UP,downAt);}
    }
    private void fail(String reason){errors++;state=reason;}
    @Override protected void dump(FileDescriptor fd,PrintWriter out,String[] args) {
        out.println("BMM-BA03 compact keyboard compatibility");out.println("state="+state);
        out.println("presses="+presses+" errors="+errors+" keyHeld="+(held>=0));
        out.println("scope=Bluetooth 005d:0004 report 0x80; consumer/voice reports untouched");
    }
    @Override public void onDestroy() {
        release();main.removeCallbacksAndMessages(null);if(gatt!=null)gatt.close();gatt=null;super.onDestroy();
    }
    @Override public IBinder onBind(Intent i){return null;}
}
