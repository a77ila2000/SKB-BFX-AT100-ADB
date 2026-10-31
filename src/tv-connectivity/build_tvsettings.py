"""Add TV USB Wi-Fi settings while retaining the existing signed TV settings code."""
from pathlib import Path
import hashlib,json,os,re,subprocess,zipfile
from loguru import logger
logger.remove()
from androguard.core.apk import APK
from androguard.core.axml import AXMLPrinter
from lxml import etree as ET

import argparse,ssl,importlib.util
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--base-apk',type=Path,required=True)
p.add_argument('--sdk',type=Path,required=True)
p.add_argument('--java-home',type=Path,required=True)
p.add_argument('--platform-key',type=Path,required=True)
p.add_argument('--platform-cert',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--version-code',type=int,default=1021)
args=p.parse_args()
w=Path(__file__).resolve().parent
sdk=args.sdk.resolve();bt=sdk/'build-tools/35.0.0';jdk=args.java_home.resolve();jar=sdk/'platforms/android-35/android.jar'
key=args.platform_key.resolve();cert=args.platform_cert.resolve();old=args.base_apk.resolve()
supplied_sha=hashlib.sha256(old.read_bytes()).hexdigest()
stock_sha='a0809d1280325da87cbeac69c2a98dd54ac21ed26cf9f34cb1a317fce5cb9d36'
if supplied_sha not in (stock_sha,'5ade308905d3be7d8acbe3f60fbb000d887954450a87c370fa69735d90b644ea'):
    raise SystemExit('Unsupported TV Settings base. Do not patch a stock SKB or a different APK.')
if args.version_code<2:raise SystemExit('version-code must be >= 2')
build=args.out.resolve()
if build.exists():raise SystemExit('Output directory must not exist')
if not key.is_file() or not cert.is_file():raise SystemExit('Supply locally held platform signing inputs')
os.environ['JAVA_HOME']=str(jdk);os.environ['PATH']=str(jdk/'bin')+os.pathsep+os.environ['PATH']
def jtool(name):return jdk/'bin'/(name+('.exe' if os.name=='nt' else ''))
def sdktool(name):return bt/(name+('.bat' if name in ('d8','apksigner') else '.exe') if os.name=='nt' else name)
cert_digest=hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest()
verified=subprocess.check_output([str(sdktool('apksigner')),'verify','--print-certs',str(old)],text=True)
if supplied_sha!=stock_sha and not re.search(r'certificate SHA-256 digest: '+cert_digest+r'(?:\s|$)',verified,re.I):
    raise SystemExit('Signing certificate must match the pinned system APK/platform signer')
build.mkdir(parents=True)
if supplied_sha==stock_sha:
    spec=importlib.util.spec_from_file_location('provider_fix',w.parent/'prepare_tvsettings.py')
    provider_fix=importlib.util.module_from_spec(spec);spec.loader.exec_module(provider_fix)
    unsigned=build/'provider-fixed-unsigned.apk';provider_fix.prepare(old,unsigned)
    aligned=build/'provider-fixed-aligned.apk';old=build/'provider-fixed.apk'
    subprocess.run([str(sdktool('zipalign')),'-f','4',str(unsigned),str(aligned)],check=True)
    subprocess.run([str(sdktool('apksigner')),'sign','--key',str(key),'--cert',str(cert),'--out',str(old),str(aligned)],check=True)
    subprocess.run([str(sdktool('apksigner')),'verify',str(old)],check=True)
apk=APK(str(old));resources=apk.get_android_resources();ns='{http://schemas.android.com/apk/res/android}'
def run(a):subprocess.run(list(map(str,a)),check=True)
def normalize(root):
    for e in root.iter():
        for k,v in list(e.attrib.items()):
            if re.fullmatch(r'@[0-9A-Fa-f]{8}',v):
                name=resources.get_resource_xml_name(int(v[1:],16));assert name,v;e.set(k,name)
            if k==ns+'configChanges' and v.startswith('0x'):
                flags={1:'mcc',2:'mnc',4:'locale',8:'touchscreen',16:'keyboard',32:'keyboardHidden',64:'navigation',128:'orientation',256:'screenLayout',512:'uiMode',1024:'screenSize',2048:'smallestScreenSize',4096:'density',8192:'layoutDirection',16384:'colorMode',0x40000000:'fontScale'}
                bits=int(v,16);assert bits & ~sum(flags)==0;e.set(k,'|'.join(n for bit,n in flags.items() if bits&bit))
            if k==ns+'launchMode' and v.isdigit():e.set(k,['standard','singleTop','singleTask','singleInstance'][int(v)])
            if k==ns+'persistableMode' and v.isdigit():e.set(k,['persistRootOnly','persistNever','persistAcrossReboots'][int(v)])
            if e.get(k) in ('@01030007','@android:01030007'):e.set(k,'@android:style/Theme.NoTitleBar.Fullscreen')
            if e.get(k) in ('@01030055','@android:01030055'):e.set(k,'@android:style/Theme.NoDisplay')
    return root
root=normalize(apk.get_android_manifest_xml());root.set(ns+'versionCode',str(args.version_code));root.set(ns+'versionName','1.0.11-bfx-tv-compat-public')
app=root.find('application')
for permission in ['android.permission.BLUETOOTH_CONNECT','android.permission.BLUETOOTH_PRIVILEGED','android.permission.HDMI_CEC','android.permission.MODIFY_AUDIO_ROUTING']:
    if not any(e.get(ns+'name')==permission for e in root.findall('uses-permission')):ET.SubElement(root,'uses-permission',{ns+'name':permission})
for a in app.findall('activity'):
    for f in a.findall('intent-filter'):
        for action in f.findall('action'):
            if action.get(ns+'name')=='android.settings.WIFI_SETTINGS':f.remove(action)
        if not f.findall('action'):a.remove(f)
network_activity=next(a for a in app.findall('activity') if a.get(ns+'name')=='com.android.tv.settings.connectivity.NetworkActivity')
activity=ET.SubElement(app,'activity',{ns+'name':'com.android.tv.settings.bfx.UsbWifiActivity',ns+'exported':'true',ns+'label':'Wi-Fi',ns+'theme':network_activity.get(ns+'theme')})
f=ET.SubElement(activity,'intent-filter',{ns+'priority':'150'});ET.SubElement(f,'action',{ns+'name':'android.settings.WIFI_SETTINGS'});ET.SubElement(f,'category',{ns+'name':'android.intent.category.DEFAULT'})
ET.SubElement(app,'receiver',{ns+'name':'com.android.tv.settings.bfx.HdmiVolumeReceiver',ns+'exported':'true',ns+'permission':'android.permission.DUMP'})
ET.SubElement(app,'service',{ns+'name':'com.android.tv.settings.bfx.RemoteKeyService',ns+'exported':'false'})
ET.SubElement(app,'service',{ns+'name':'com.android.tv.settings.bfx.UsbWifiStartupService',ns+'exported':'false'})
startup=ET.SubElement(app,'receiver',{ns+'name':'com.android.tv.settings.bfx.RemoteStartupReceiver',ns+'exported':'true'})
f=ET.SubElement(startup,'intent-filter')
for action in ['android.intent.action.BOOT_COMPLETED','android.intent.action.MY_PACKAGE_REPLACED','android.bluetooth.adapter.action.STATE_CHANGED','android.bluetooth.input.profile.action.CONNECTION_STATE_CHANGED','android.bluetooth.device.action.BOND_STATE_CHANGED']:ET.SubElement(f,'action',{ns+'name':action})
ET.SubElement(f,'action',{ns+'name':'android.hardware.usb.action.USB_DEVICE_ATTACHED'})
manifest=build/'AndroidManifest.xml';ET.ElementTree(root).write(str(manifest),encoding='utf-8',xml_declaration=True)
patched={}
with zipfile.ZipFile(old) as z:
    for name in ['main_prefs.xml','main_prefs_vendor.xml','main_prefs_x.xml','network.xml','network_compat.xml','network_x.xml']:
        path='res/xml/'+name;r=normalize(ET.fromstring(AXMLPrinter(z.read(path)).get_xml()))
        pref=ET.Element('Preference',{ns+'key':'bfx_usb_wifi',ns+'title':'USB Wi-Fi',ns+'summary':'수신기 연결 및 무선 네트워크 설정'})
        ET.SubElement(pref,'intent',{ns+'targetPackage':'com.android.tv.settings',ns+'targetClass':'com.android.tv.settings.bfx.UsbWifiActivity'})
        network=next((e for e in r.iter() if e.get(ns+'key')=='network'),None)
        if network is not None:network.getparent().insert(network.getparent().index(network)+1,pref)
        else:r.insert(0,pref)
        dest=build/'res/xml'/name;dest.parent.mkdir(parents=True,exist_ok=True);ET.ElementTree(r).write(str(dest),encoding='utf-8',xml_declaration=True);patched[path]=None
classes=build/'classes';classes.mkdir(exist_ok=True);dex=build/'dex';dex.mkdir(exist_ok=True)
stubs=build/'compile-stubs';stubs.mkdir(exist_ok=True)
run([jtool('javac'),'-encoding','UTF-8','-source','8','-target','8','-classpath',jar,'-d',stubs,*sorted((w/'compile-stubs').rglob('*.java'))])
run([jtool('javac'),'-encoding','UTF-8','-source','8','-target','8','-classpath',str(jar)+os.pathsep+str(stubs),'-d',classes,*sorted((w/'source').glob('*.java'))])
run([jtool('javac'),'-encoding','UTF-8','-classpath',classes,'-d',build/'test-classes',w/'RemoteReportTest.java'])
run([jtool('java'),'-cp',str(classes)+os.pathsep+str(build/'test-classes'),'com.android.tv.settings.bfx.RemoteReportTest'])
run([jtool('javac'),'-encoding','UTF-8','-classpath',str(classes)+os.pathsep+str(jar),'-d',build/'test-classes',w/'WifiSecurityTest.java'])
run([jtool('java'),'-cp',str(classes)+os.pathsep+str(build/'test-classes'),'com.android.tv.settings.bfx.WifiSecurityTest'])
stub_jar=build/'compile-stubs.jar'
with zipfile.ZipFile(stub_jar,'w') as z:
    for p in stubs.rglob('*.class'):z.write(p,p.relative_to(stubs).as_posix())
run([sdktool('d8'),'--lib',jar,'--classpath',stub_jar,'--output',dex,*classes.rglob('*.class')])
compiled=build/'resources.zip';run([sdktool('aapt2'),'compile','--dir',build/'res','-o',compiled])
linked=build/'linked.apk';run([sdktool('aapt2'),'link','-I',jar,'-I',old,'--manifest',manifest,'-o',linked,compiled])
def pack(link,output,extra=True,base_apk=old):
    unsigned=build/(output.stem+'-unsigned.apk');aligned=build/(output.stem+'-aligned.apk')
    with zipfile.ZipFile(base_apk) as original,zipfile.ZipFile(link) as new,zipfile.ZipFile(unsigned,'w') as out:
        for item in original.infolist():
            if item.filename.startswith('META-INF/'):continue
            changed=item.filename=='AndroidManifest.xml' or (extra and item.filename in patched)
            out.writestr(item,new.read(item.filename) if changed else original.read(item))
        if extra:
            assert 'classes2.dex' not in original.namelist();out.write(dex/'classes.dex','classes2.dex')
    run([sdktool('zipalign'),'-f','4',unsigned,aligned]);run([sdktool('apksigner'),'sign','--key',key,'--cert',cert,'--out',output,aligned]);run([sdktool('apksigner'),'verify',output])
    with zipfile.ZipFile(base_apk) as a,zipfile.ZipFile(output) as b:
        retained=[n for n in a.namelist() if not n.startswith('META-INF/') and n!='AndroidManifest.xml' and not(extra and n in patched)]
        assert all(a.read(n)==b.read(n) for n in retained)
    return len(retained)
out=build/'TvSettings-connectivity.apk';count=pack(linked,out)
# Preserve the supplied pre-update system app as a higher-version recovery APK.
rollback_root=normalize(apk.get_android_manifest_xml())
rollback_root.set(ns+'versionCode',str(args.version_code+1));rollback_root.set(ns+'versionName','pre-connectivity-rollback')
rollback_manifest=build/'rollback/AndroidManifest.xml';rollback_manifest.parent.mkdir();ET.ElementTree(rollback_root).write(str(rollback_manifest),encoding='utf-8',xml_declaration=True)
rollback_linked=build/'rollback-linked.apk';run([sdktool('aapt2'),'link','-I',jar,'-I',old,'--manifest',rollback_manifest,'-o',rollback_linked])
pack(rollback_linked,build/'TvSettings-connectivity-rollback.apk',False)
proof={'supplied_base_sha256':supplied_sha,'base_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'new_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
       'original_zip_entries_byte_identical':count,'original_dex_and_resources_table_preserved':True,
       'modified_preference_xml':list(patched),'same_platform_signer':supplied_sha!=stock_sha,
       'local_signer_must_match_running_gsi':True,'diagnostic_receivers_included':False,
       'public_rebuild_hardware_tested':False, 'hdmi_volume_receiver_permission':'android.permission.DUMP', 'native_driver_yield_included':True}
(build/'build-verification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
