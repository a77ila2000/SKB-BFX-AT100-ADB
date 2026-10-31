package com.android.tv.settings.bfx;
import android.hardware.usb.*;

/** Only the known Realtek installer interface receives the standard SCSI eject command. */
final class UsbModeSwitch {
    static boolean installer(UsbDevice d) {return d.getVendorId()==0x0bda&&d.getProductId()==0x1a2b;}
    static synchronized void eject(UsbManager usb,UsbDevice d) throws Exception {
        if(!installer(d)||!usb.hasPermission(d))throw new IllegalArgumentException();
        if(!usb.getDeviceList().containsKey(d.getDeviceName()))return;
        UsbInterface selected=null;UsbDeviceConnection c=null;
        try {
            for(int i=0;i<d.getInterfaceCount();i++) {
                UsbInterface x=d.getInterface(i);
                if(x.getInterfaceClass()==8&&x.getInterfaceSubclass()==6&&x.getInterfaceProtocol()==80){selected=x;break;}
            }
            if(selected==null)throw new IllegalStateException();
            UsbEndpoint in=null,out=null;
            for(int i=0;i<selected.getEndpointCount();i++) {
                UsbEndpoint e=selected.getEndpoint(i);
                if(e.getType()==UsbConstants.USB_ENDPOINT_XFER_BULK) {
                    if(e.getDirection()==UsbConstants.USB_DIR_IN)in=e;else out=e;
                }
            }
            if(in==null||out==null)throw new IllegalStateException();c=usb.openDevice(d);
            if(c==null||!c.claimInterface(selected,true))throw new IllegalStateException();
            for(int stage=0;stage<2;stage++) {
                int tag=0x51+stage;byte[] command=new byte[31];
                command[0]=0x55;command[1]=0x53;command[2]=0x42;command[3]=0x43;
                command[4]=(byte)tag;command[14]=6;command[15]=(byte)(stage==0?0x1e:0x1b);command[19]=(byte)(stage==0?0:2);
                if(c.bulkTransfer(out,command,31,2500)!=31)throw new IllegalStateException();
                byte[] r=new byte[13];int count=c.bulkTransfer(in,r,13,2500);
                if(count<0&&stage==1)break; // Device may disconnect immediately after successful eject.
                if(count!=13||r[0]!=0x55||r[1]!=0x53||r[2]!=0x42||r[3]!=0x53||
                   (r[4]&255)!=tag||r[5]!=0||r[6]!=0||r[7]!=0||
                   !(r[12]==0||(stage==0&&r[12]==1)))throw new IllegalStateException();
            }
        } finally {if(c!=null){if(selected!=null)c.releaseInterface(selected);c.close();}}
    }
}
