"""Prepare project-authored files only, gated by the owner's original module."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXPECTED = '81972bf616a5f7ee798b5fce40019f46691f7bd21766b11c2a219fb23e243e1c'

def build(module, output):
    if hashlib.sha256(module.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError('Unsupported original HID module; do not force-load another module')
    if output.exists():
        raise ValueError('Output directory must not exist')
    source = Path(__file__).resolve().parent
    files = {
        '/system/etc/bfx-stock-remote.sh': 'bfx-stock-remote.sh',
        '/system/etc/init/bfx-stock-remote.rc': 'bfx-stock-remote.rc',
        '/system/usr/keylayout/Vendor_005d_Product_0004.kl': 'Vendor_005d_Product_0004.kl',
        '/system/usr/idc/Vendor_005d_Product_0004.idc': 'Vendor_005d_Product_0004.idc',
    }
    output.mkdir(parents=True)
    records = {}
    for target, name in files.items():
        destination = output / name
        shutil.copyfile(source / name, destination)
        records[target] = {
            'source': name, 'mode': '0100755' if name.endswith('.sh') else '0100644',
            'label': 'system_file',
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        }
    manifest = {'files': records, 'model': 'BFX-AT100', 'kernel_release': '4.9.113',
                'kernel_build_marker': '#71 SMP PREEMPT', 'original_hid_sha256': EXPECTED,
                'vendor_binary_copied': False, 'nugu_included': False,
                'requires_existing_phh_loader_domain': 'phhsu_daemon',
                'writes_to_device': False}
    (output / 'overlay-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock-hid', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.stock_hid, args.out), indent=2))
