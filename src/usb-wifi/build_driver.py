"""Offline target-checked RTL8821CU/probe build. Never installs or loads modules."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from abi_types import inventory,diff

HERE=Path(__file__).resolve().parent
def run(a,**kw):return subprocess.run(list(map(str,a)),check=True,**kw)
def config(path):
    result={}
    for line in path.read_text().splitlines():
        if m:=re.fullmatch(r'(CONFIG_\w+)=(.*)',line):result[m[1]]=m[2]
        elif m:=re.fullmatch(r'# (CONFIG_\w+) is not set',line):result[m[1]]='n'
    return result
def versions(path):
    with path.open('rb') as f:
        elf=ELFFile(f)
        if elf.elfclass!=32 or elf['e_machine']!='EM_ARM':raise ValueError('Expected ARM32 ELF')
        section=elf.get_section_by_name('__versions')
        if section is None:raise ValueError('Module lacks import version metadata')
        b=section.data()
        if len(b)%64:raise ValueError('Unsupported modversion record size')
        rows={b[i+4:i+64].split(b'\0')[0].decode():f'{int.from_bytes(b[i:i+4],"little"):08x}' for i in range(0,len(b),64)}
        if len(rows)!=len(b)//64:raise ValueError('Duplicate version records')
        return rows
def prepare_kernel(kernel,original,cross):
    target=json.loads((HERE/'reference-target.json').read_text())
    if hashlib.sha256(original.read_bytes()).hexdigest()!=target['original_config_sha256']:
        raise ValueError('Original kernel config is not the tested target; port separately')
    old=config(original)
    for name in ['sched.h','mm_types.h']:
        p=kernel/'include/linux'/name;s=p.read_text()
        pattern=r'\bu64(\s+vmacache_seqnum\s*;)'
        if len(re.findall(pattern,s))==1:s=re.sub(pattern,r'u32\1',s);p.write_text(s)
        elif len(re.findall(r'\bu32\s+vmacache_seqnum\s*;',s))!=1:
            raise ValueError('Unexpected vmacache layout in '+name)
    p=kernel/'.config'
    if p.exists() and not (kernel/'.config.before-bfx').exists():shutil.copyfile(p,kernel/'.config.before-bfx')
    shutil.copyfile(original,p)
    run([kernel/'scripts/config','--file',p,'--enable','CC_STACKPROTECTOR_STRONG_AMLOGIC'])
    make=['make','-C',kernel,'ARCH=arm','CROSS_COMPILE='+cross,'HOSTCFLAGS=-fcommon']
    run(make+['olddefconfig'])
    candidate=config(p);allowed={'CONFIG_CC_STACKPROTECTOR_STRONG_AMLOGIC','CONFIG_HAVE_ARCH_KASAN'}
    disable=[key for key,value in candidate.items() if key not in old and value!='n' and key not in allowed]
    if disable:
        command=[kernel/'scripts/config','--file',p]
        for key in disable:command+=['--disable',key.removeprefix('CONFIG_')]
        run(command)
    run(make+['olddefconfig','modules_prepare'])
    new=config(p)
    if new.get('CONFIG_AMLOGIC_VMAP','n')!='n' or new.get('CONFIG_AMLOGIC_SLAB_TRACE','n')!='n':
        raise ValueError('Unsafe source-tree stack/slab defaults remain enabled')
    if new.get('CONFIG_CC_STACKPROTECTOR_STRONG_AMLOGIC')!='y':raise ValueError('Strong stack protection missing')
    changes={k for k,v in old.items() if new.get(k,'n')!=v}
    if changes-{'CONFIG_INIT_ENV_ARG_LIMIT','CONFIG_CC_STACKPROTECTOR_STRONG','CONFIG_AMLOGIC_IRBLASTER'}:
        raise ValueError('Unreviewed configuration difference: '+str(sorted(changes)))
    if {k for k,v in new.items() if k not in old and v!='n'}-allowed:raise ValueError('New enabled defaults remain')
def patch_driver(driver):
    patches=[('os_dep/linux/ioctl_mp.c',f'sprintf(extra, "%s{suffix}", extra, {arg});',
              f'sprintf(extra + strlen(extra), "{suffix}", {arg});') for suffix,arg in
             [(',pathb=%d','txpower_inx'),(',pathc=%d','txpower_inx'),(',pathd=%d','txpower_inx'),
              (':%02x','maskfileBuffer[i]'),('\\nLoad Efuse Mask data %d hex ok\\n','count')]]
    patches.append(('core/rtw_mp.c','sprintf(data, "%s%x ", data, psd_data);','sprintf(data + strlen(data), "%x ", psd_data);'))
    for name,before,after in patches:
        p=driver/name;s=p.read_text()
        if s.count(before)==1:
            backup=p.with_suffix('.c.before-bfx')
            if not backup.exists():shutil.copyfile(p,backup)
            p.write_text(s.replace(before,after))
        elif s.count(after)!=1:raise ValueError('Unsupported upstream diagnostic source: '+name)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['kernel','driver','original-config','stock-hid','stock-usb','stock-network','out']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cross-compile',required=True);args=p.parse_args()
    if args.out.exists():raise ValueError('Output directory must not exist')
    compiler=subprocess.check_output([args.cross_compile+'gcc','--version'],text=True)
    if not re.search(r'6\.3\.1\s+20170109',compiler):raise ValueError('Use the pinned original-version compiler')
    expected=json.loads((HERE/'reference-crcs.json').read_text())
    for original in [args.stock_hid,args.stock_usb,args.stock_network]:
        if versions(original).get('module_layout')!=expected['module_layout']:raise ValueError('Original module does not match target core ABI')
    prepare_kernel(args.kernel,args.original_config,args.cross_compile);patch_driver(args.driver)
    args.out.mkdir(parents=True)
    symvers=args.out/'target.symvers'
    symvers.write_text(''.join(f'0x{crc}\t{name}\tvmlinux\tEXPORT_SYMBOL\n' for name,crc in sorted(expected.items()))+
                       '0xe007de41\tkallsyms_lookup_name\tvmlinux\tEXPORT_SYMBOL_GPL\n')
    make=['make','-j6','-C',args.kernel,'ARCH=arm','CROSS_COMPILE='+args.cross_compile,'HOSTCFLAGS=-fcommon',
          'KCFLAGS=-Wno-error -march=armv7-a','KBUILD_EXTRA_SYMBOLS='+str(symvers.resolve())]
    run(make+['M='+str(args.driver.resolve()),'CONFIG_RTL8821CU=m','CONFIG_PLATFORM_I386_PC=n','CONFIG_WIFI_MONITOR=n',
              'USER_EXTRA_CFLAGS=-DCONFIG_LITTLE_ENDIAN -DCONFIG_IOCTL_CFG80211 -DRTW_USE_CFG80211_STA_EVENT','modules'])
    candidate,ambiguous=inventory(args.driver/'core/rtw_cmd.o');evidence={}
    for label,original in [('hid',args.stock_hid),('usb',args.stock_usb),('network',args.stock_network)]:
        old,old_ambiguous=inventory(original);delta=diff(old,candidate);common=len(old.keys()&candidate.keys())
        if common<200 or delta or ambiguous or old_ambiguous:raise ValueError('Inline layout mismatch: '+label+' '+str(list(delta)))
        evidence[label]={'common_types':common,'differences':0}
    if versions(args.driver/'8821cu.ko')!=expected:raise ValueError('All target imports must match before packaging')
    probe=args.out/'probe';probe.mkdir();shutil.copyfile(HERE/'bfx_wifi_abi_probe.c',probe/'bfx_wifi_abi_probe.c');shutil.copyfile(HERE/'Makefile',probe/'Makefile')
    run(make+['M='+str(probe.resolve()),'modules'])
    probe_versions=versions(probe/'bfx_wifi_abi_probe.ko')
    if set(probe_versions)-set(expected)-{'kallsyms_lookup_name'}:raise ValueError('Unexpected probe import')
    if any(crc!=dict(expected,kallsyms_lookup_name='e007de41').get(name) for name,crc in probe_versions.items()):raise ValueError('Probe import mismatch')
    for original,name in [(args.driver/'8821cu.ko','8821cu.ko'),(probe/'bfx_wifi_abi_probe.ko','wifi-abi-probe.ko')]:
        run([args.cross_compile+'strip','--strip-debug','-o',args.out/name,original])
    (args.out/'abi-evidence.json').write_text(json.dumps({'module_versions':len(expected),'actual_command_object_layouts':evidence,
        'stack_base_thread_info':True,'no_force_flags':True,'hardware_runtime_tested':False},indent=2)+'\n')
    print('Offline build and layout checks passed. No driver was loaded and no device was written.')
if __name__=='__main__':main()
