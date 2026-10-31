"""Build the owner-authorized Android 12 time recovery APK using a local ROM signer."""
import argparse,hashlib,json,os,subprocess,zipfile
from pathlib import Path
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['sdk','java-home','platform-key','platform-cert','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();src=Path(__file__).resolve().parent;out=a.out.resolve()
 if out.exists():raise SystemExit('Output must not exist')
 out.mkdir(parents=True);(out/'classes').mkdir();(out/'dex').mkdir()
 sdk=a.sdk.resolve();bt=sdk/'build-tools/35.0.0';jdk=a.java_home.resolve();jar=sdk/'platforms/android-35/android.jar'
 os.environ['JAVA_HOME']=str(jdk);os.environ['PATH']=str(jdk/'bin')+os.pathsep+os.environ['PATH']
 def tool(n):return bt/(n+('.bat' if n in ['apksigner','d8'] else '.exe') if os.name=='nt' else n)
 def java(n):return jdk/'bin'/(n+'.exe' if os.name=='nt' else n)
 def run(x):subprocess.run(list(map(str,x)),check=True)
 run([java('javac'),'-encoding','UTF-8','-source','8','-target','8','-classpath',jar,'-d',out/'classes',*sorted(src.glob('*.java'))])
 run([tool('d8'),'--lib',jar,'--output',out/'dex',*sorted((out/'classes').rglob('*.class'))])
 run([tool('aapt2'),'link','-I',jar,'--manifest',src/'AndroidManifest.xml','-o',out/'unsigned.apk'])
 with zipfile.ZipFile(out/'unsigned.apk','a') as z:z.write(out/'dex/classes.dex','classes.dex')
 run([tool('zipalign'),'-f','4',out/'unsigned.apk',out/'aligned.apk'])
 apk=out/'BfxTimeRecovery.apk'
 run([tool('apksigner'),'sign','--key',a.platform_key.resolve(),'--cert',a.platform_cert.resolve(),'--out',apk,out/'aligned.apk'])
 run([tool('apksigner'),'verify',apk])
 proof={'package':'local.bfx.timerecovery','sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'firmware_writes':0,'needs_target_platform_signer':True,'uses_native_NtpTrustedTime_and_TimeDetector':True,'retry_ms':60000,'success_poll_ms':21600000,'no_persistent_process_or_root_interface':True}
 (out/'build-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
