package com.android.tv.settings.bfx;

/** Compact report 0x80 used by BMM-BA03 (005d:0004), not its normal consumer keys. */
final class RemoteReport {
    static final int IGNORE=-2, RELEASE=-1;
    static int decode(byte[] b) {
        if(b==null || b.length!=3 || b[0]!=0)return IGNORE;
        int code=b[1]&255,tail=b[2]&255;
        if(code==255 && tail==255)return RELEASE;
        if(tail!=0)return IGNORE;
        if(code>=0x20 && code<=0x29)return 7+code-0x20; // Physically captured digits 0..9 -> KEYCODE_0..9.
        switch(code) {
            case 0x02:return 3;  // HOME
            case 0x46:return 23; // DPAD_CENTER
            case 0x49:return 19;
            case 0x4a:return 20;
            case 0x4b:return 21;
            case 0x4c:return 22;
            case 0x4e:return 4;  // BACK
            default:return IGNORE;
        }
    }
}
