"""Prepare a local offline overlay from checked local binaries. No device access."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from build_driver import versions

HERE=Path(__file__).resolve().parent
TARGET='/system/lib/hw/bfx-wifi'
PLATFORM_LIBS={'libc.so','libm.so','libdl.so','libdl_android.so','liblog.so','libvndksupport.so','libcgrouprc.so'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def needed(p):
    with p.open('rb') as f:
        elf=ELFFile(f)
        if elf.elfclass!=32 or elf['e_machine']!='EM_ARM':raise ValueError('Expected ARM32 ELF: '+p.name)
        return [t.needed for t in elf.get_section_by_name('.dynamic').iter_tags() if t.entry.d_tag=='DT_NEEDED']
def run(args):subprocess.run(list(map(str,args)),check=True)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['driver-build','userspace','vndk30','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cross-compile',required=True);args=p.parse_args()
    if args.out.exists():raise ValueError('Output directory must not exist')
    expected=json.loads((HERE/'reference-crcs.json').read_text())
    if versions(args.driver_build/'8821cu.ko')!=expected:raise ValueError('Driver import versions do not match target')
    proof=json.loads((args.driver_build/'abi-evidence.json').read_text())
    if not proof['stack_base_thread_info'] or not proof['no_force_flags']:raise ValueError('Missing build evidence')
    if set(proof['actual_command_object_layouts'])!={'hid','usb','network'} or any(v['differences'] or v['common_types']<200 for v in proof['actual_command_object_layouts'].values()):raise ValueError('Missing original-module layout comparisons')
    probe_versions=versions(args.driver_build/'wifi-abi-probe.ko')
    if any(crc!=dict(expected,kallsyms_lookup_name='e007de41').get(name) for name,crc in probe_versions.items()):raise ValueError('Probe import versions do not match')
    roots={name:args.userspace/name for name in ['bfx-wifi-hal','bfx-wpa-supplicant','libwifi-hal-aml.so',
        'libkeystore-wifi-hidl.so','libkeystore-engine-wifi-hidl.so']}
    hashes=json.loads((HERE/'reference-userspace-sha256.json').read_text());closure=dict(roots);queue=list(roots.values());platform=set()
    while queue:
        origin=queue.pop()
        if hashes.get(origin.name)!=sha(origin):raise ValueError('Unsupported userspace version: '+origin.name)
        for name in needed(origin):
            if Path(name).name!=name:raise ValueError('Invalid library dependency path')
            if name in closure:continue
            if name in PLATFORM_LIBS:platform.add(name);continue
            dependency=args.vndk30/name
            if name not in hashes or not dependency.is_file():raise ValueError('Missing matching VNDK30 library: '+name)
            closure[name]=dependency;queue.append(dependency)
    args.out.mkdir(parents=True);files={}
    def add(origin,target,mode='0644',label='system_file'):
        output=args.out/target.lstrip('/');output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin,output)
        files[target]={'source':output.relative_to(args.out).as_posix(),'mode':mode,'selinux_type':label}
        return output
    shim=args.out/'libbfx-usb-wifi-driver.so'
    run([args.cross_compile+'gcc','-shared','-fPIC','-nostdlib','-fno-stack-protector','-fno-builtin',
         '-mfloat-abi=softfp','-march=armv7-a','-Wl,-soname,libbfx-usb-wifi-driver.so','-Wl,--hash-style=both',
         '-Wl,-z,global','-o',shim,HERE/'usb_wifi_driver.c'])
    closure[shim.name]=shim
    for name,origin in closure.items():
        executable=name in ('bfx-wifi-hal','bfx-wpa-supplicant')
        target='/system/bin/hw/'+name if executable else TARGET+'/'+name
        label='hal_wifi_default_exec' if name=='bfx-wifi-hal' else 'hal_wifi_supplicant_default_exec' if executable else 'vendor_file'
        output=add(origin,target,'0755' if executable else '0644',label)
        run(['patchelf','--set-rpath',TARGET,output])
        if name=='bfx-wifi-hal':run(['patchelf','--add-needed',shim.name,output])
        with output.open('rb') as f:
            tags=list(ELFFile(f).get_section_by_name('.dynamic').iter_tags())
            if not any(t.entry.d_tag=='DT_RUNPATH' and t.runpath==TARGET for t in tags):raise ValueError('Private runpath missing')
            if name==shim.name and not any(t.entry.d_tag=='DT_FLAGS_1' and t.entry.d_val&2 for t in tags):raise ValueError('Driver shim is not global')
    add(args.driver_build/'8821cu.ko','/system/lib/modules/bfx/8821cu.ko')
    add(args.driver_build/'wifi-abi-probe.ko','/system/lib/modules/bfx/wifi-abi-probe.ko')
    for name,target in [('bfx-usb-wifi.rc','/system/etc/init/bfx-usb-wifi.rc'),('bfx-wifi-probe.rc','/system/etc/init/bfx-wifi-probe.rc'),
        ('bfx-usb-wifi-load.sh','/system/etc/bfx-usb-wifi-load.sh'),('bfx-wifi-probe.sh','/system/etc/bfx-wifi-probe.sh'),
        ('bfx-usb-wifi.xml','/system/etc/vintf/manifest/bfx-usb-wifi.xml'),('wpa_supplicant.conf','/system/etc/wifi/wpa_supplicant.conf')]:
        add(HERE/'overlay'/name,target)
    expected_path=args.out/'expected-crcs.txt';expected_path.write_text(''.join(n+' '+v+'\n' for n,v in sorted(expected.items())))
    add(expected_path,'/system/etc/bfx-usb-wifi-expected-crcs.txt')
    for target,row in files.items():row['sha256']=sha(args.out/row['source'])
    manifest={'files':files,'platform_dependencies':sorted(platform),'no_device_access':True,'no_credentials_included':True,
        'kernel_vendor_dtb_tee_unchanged':True,'hardware_runtime_tested':False,
        'instruction':'Merge offline with inode/shared-block preservation and regenerate/verify full AVB; this directory is not an OTA or flash installer.'}
    (args.out/'overlay-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Prepared checked offline overlay. No image or device partition was written.')
if __name__=='__main__':main()
