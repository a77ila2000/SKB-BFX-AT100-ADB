package local.bfx.timerecovery;
import android.content.*;
import org.json.JSONObject;
public final class ControlReceiver extends BroadcastReceiver {
 public void onReceive(Context c,Intent i){
  try{
   if("local.bfx.timerecovery.SYNC".equals(i.getAction()))Scheduler.start(c);
   else if(!"local.bfx.timerecovery.STATUS".equals(i.getAction()))throw new IllegalArgumentException("Unknown action");
   JSONObject o=new JSONObject(Scheduler.prefs(c).getAll());o.put("auto_time",Scheduler.automatic(c));setResultCode(0);setResultData(o.toString());
  }catch(Exception e){setResultCode(1);setResultData(e.getClass().getSimpleName());}
 }
}
