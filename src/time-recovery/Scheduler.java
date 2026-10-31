package local.bfx.timerecovery;
import android.app.job.*;
import android.content.*;
import android.os.*;
import android.provider.Settings;
final class Scheduler {
 static final int FIRST=0x42465801, SECOND=0x42465802;
 static boolean automatic(Context c){return Settings.Global.getInt(c.getContentResolver(),Settings.Global.AUTO_TIME,0)==1;}
 static boolean target(){try{return "BFX-AT100".equals(Class.forName("android.os.SystemProperties").getMethod("get",String.class).invoke(null,"ro.product.vendor.model"))&&Build.VERSION.SDK_INT==32;}catch(Exception e){return false;}}
 static android.content.SharedPreferences prefs(Context c){return c.createDeviceProtectedStorageContext().getSharedPreferences("status",0);}
 static void schedule(Context c,int id,long delay){
  if(!target())return;
  JobScheduler j=c.getSystemService(JobScheduler.class);ComponentName component=new ComponentName(c,TimeJob.class);
  JobInfo old=j.getPendingJob(id);if(old!=null&&!component.equals(old.getService()))throw new IllegalStateException("Job ID collision; existing job preserved");
  int result=j.schedule(new JobInfo.Builder(id,component).setPersisted(true).setMinimumLatency(delay).setOverrideDeadline(delay+30000).setBackoffCriteria(60000,JobInfo.BACKOFF_POLICY_LINEAR).build());
  if(result!=JobScheduler.RESULT_SUCCESS)throw new IllegalStateException("Job scheduling rejected");
  prefs(c).edit().putLong("next_delay_ms",delay).putInt("next_job_id",id).apply();
 }
 static void start(Context c){
  if(!target())return;
  JobScheduler j=c.getSystemService(JobScheduler.class);ComponentName own=new ComponentName(c,TimeJob.class);
  for(int id:new int[]{FIRST,SECOND}){JobInfo p=j.getPendingJob(id);if(p!=null&&own.equals(p.getService()))j.cancel(id);}
  schedule(c,FIRST,1000);
 }
}
