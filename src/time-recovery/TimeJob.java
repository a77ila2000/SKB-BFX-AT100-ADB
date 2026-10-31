package local.bfx.timerecovery;
import android.app.job.*;
import android.content.*;
import android.net.*;
import android.os.*;
import android.util.Log;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
public final class TimeJob extends JobService {
 private final ConcurrentHashMap<Integer,AtomicBoolean> running=new ConcurrentHashMap<>();
 public boolean onStartJob(final JobParameters p){
  final AtomicBoolean stopped=new AtomicBoolean(false);running.put(p.getJobId(),stopped);
  new Thread(()->{
   boolean success=false;String result="not-attempted";long epoch=0,reference=0,delta=0;
   try{
    if(!Scheduler.target()||!Scheduler.automatic(this)){result="automatic-time-disabled";return;}
    ConnectivityManager cm=getSystemService(ConnectivityManager.class);
    if(cm.getActiveNetwork()==null)throw new IllegalStateException("NoDefaultNetwork");
    Class<?> trusted=Class.forName("android.util.NtpTrustedTime");Object ntp=trusted.getMethod("getInstance",Context.class).invoke(null,this);
    if(!Boolean.TRUE.equals(trusted.getMethod("forceRefresh").invoke(ntp)))throw new IllegalStateException("NoNtpResponse");
    Object fix=trusted.getMethod("getCachedTimeResult").invoke(ntp);if(fix==null)throw new IllegalStateException("NoNtpFix");
    epoch=(Long)fix.getClass().getMethod("getTimeMillis").invoke(fix);reference=(Long)fix.getClass().getMethod("getElapsedRealtimeMillis").invoke(fix);
    if(SystemClock.elapsedRealtime()-reference<0||SystemClock.elapsedRealtime()-reference>15000)throw new IllegalStateException("StaleNtpFix");
    if(stopped.get()||!Scheduler.automatic(this))return;
    Class<?> stamp=Class.forName("android.os.TimestampedValue"),suggestion=Class.forName("android.app.timedetector.NetworkTimeSuggestion");
    Object s=suggestion.getConstructor(stamp).newInstance(stamp.getConstructor(long.class,Object.class).newInstance(reference,Long.valueOf(epoch)));
    Object detector=getSystemService("time_detector");if(detector==null)throw new IllegalStateException("NoTimeDetector");
    delta=epoch+(SystemClock.elapsedRealtime()-reference)-System.currentTimeMillis();
    Class.forName("android.app.timedetector.TimeDetector").getMethod("suggestNetworkTime",suggestion).invoke(detector,s);
    success=true;result="network-suggestion-submitted";
   }catch(Throwable e){Throwable cause=e instanceof java.lang.reflect.InvocationTargetException?e.getCause():e;result=cause.getClass().getSimpleName()+":"+String.valueOf(cause.getMessage());if(result.length()>180)result=result.substring(0,180);}
   finally{
    if(!stopped.get()){
     android.content.SharedPreferences pref=Scheduler.prefs(this);long failures=success?0:pref.getLong("consecutive_failures",0)+(Scheduler.automatic(this)?1:0);
     android.content.SharedPreferences.Editor ed=pref.edit().putString("last_result",result).putLong("last_attempt_elapsed",SystemClock.elapsedRealtime()).putLong("consecutive_failures",failures).putBoolean("last_suggestion_submitted",success);
     if(success)ed.putLong("last_network_epoch",epoch).putLong("last_network_reference",reference).putLong("last_adjustment_ms",delta);
     ed.commit();Log.i("BfxTimeRecovery",result+" failures="+failures);
     // Alternate fixed IDs: scheduling must not cancel the job that is finishing.
     boolean scheduled=false;
     try{Scheduler.schedule(this,p.getJobId()==Scheduler.FIRST?Scheduler.SECOND:Scheduler.FIRST,success?21600000L:60000L);scheduled=true;}
     catch(Exception e){Log.e("BfxTimeRecovery","schedule failed; OS retry retained",e);}
     jobFinished(p,!scheduled);
    }
    running.remove(p.getJobId(),stopped);
   }
  },"BfxTimeRecovery").start();return true;
 }
 public boolean onStopJob(JobParameters p){AtomicBoolean flag=running.remove(p.getJobId());if(flag!=null)flag.set(true);return true;}
}
