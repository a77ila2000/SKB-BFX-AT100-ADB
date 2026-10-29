import android.os.IBinder;

/** Read the Ethernet configuration without persisting settings. */
public class BfxEthernetConfig {
    public static void main(String[] args) throws Exception {
        if (args.length != 0) {
            System.err.println(
                "Read-only: static IP persistence crashes this ROM's EthernetService at the next boot. Use DHCP.");
            System.exit(2);
            return;
        }
        Class<?> manager = Class.forName("android.net.IEthernetManager");
        IBinder binder = (IBinder) Class.forName("android.os.ServiceManager").getMethod("getService", String.class).invoke(null, "ethernet");
        Object service = Class.forName("android.net.IEthernetManager$Stub").getMethod("asInterface", IBinder.class).invoke(null, binder);
        Object old = manager.getMethod("getConfiguration", String.class).invoke(service, "eth0");
        System.out.println(old);
    }
}
