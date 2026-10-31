package com.android.tv.settings.bfx;
public final class RemoteReportTest {
    public static void main(String[] args) {
        int[][] samples={{2,3},{0x46,23},{0x49,19},{0x4a,20},{0x4b,21},{0x4c,22},{0x4e,4}};
        for(int[] s:samples)if(RemoteReport.decode(new byte[]{0,(byte)s[0],0})!=s[1])throw new AssertionError();
        for(int digit=0;digit<=9;digit++)
            if(RemoteReport.decode(new byte[]{0,(byte)(0x20+digit),0})!=7+digit)throw new AssertionError("digit "+digit);
        if(RemoteReport.decode(new byte[]{0,-1,-1})!=RemoteReport.RELEASE)throw new AssertionError();
        for(byte[] b:new byte[][]{null,new byte[0],new byte[]{0,2},new byte[]{1,2,0},new byte[]{0,2,1},new byte[]{0,0x3a,0}})
            if(RemoteReport.decode(b)!=RemoteReport.IGNORE)throw new AssertionError();
        System.out.println("PASS: observed compact keys, release, unknown and malformed reports");
    }
}
