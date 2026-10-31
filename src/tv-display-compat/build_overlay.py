"""Compile the resource-only TV overlay using the target ROM's local signer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['sdk', 'java-home', 'platform-key', 'platform-cert', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    output = args.out.resolve()
    if output.exists():
        raise SystemExit('Output directory must not exist')
    sdk = args.sdk.resolve(); java = args.java_home.resolve()
    key = args.platform_key.resolve(); cert = args.platform_cert.resolve()
    if not key.is_file() or not cert.is_file():
        raise SystemExit('Supply your ROM platform signing inputs locally')
    os.environ['JAVA_HOME'] = str(java)
    os.environ['PATH'] = str(java / 'bin') + os.pathsep + os.environ['PATH']
    tools = sdk / 'build-tools/35.0.0'
    def tool(name):
        return tools / (name + ('.bat' if name == 'apksigner' else '.exe')
                        if os.name == 'nt' else name)
    output.mkdir(parents=True)
    apk = output / 'BfxTvDisplayOverlay.apk'
    commands = [
        [tool('aapt2'), 'compile', '--dir', source / 'res', '-o', output / 'resources.zip'],
        [tool('aapt2'), 'link', '-I', sdk / 'platforms/android-35/android.jar',
         '--manifest', source / 'AndroidManifest.xml', '-o', output / 'unsigned.apk',
         output / 'resources.zip'],
        [tool('zipalign'), '-f', '4', output / 'unsigned.apk', output / 'aligned.apk'],
        [tool('apksigner'), 'sign', '--key', key, '--cert', cert, '--out', apk,
         output / 'aligned.apk'],
        [tool('apksigner'), 'verify', apk],
    ]
    for command in commands:
        subprocess.run(list(map(str, command)), check=True)
    proof = {'package': 'local.bfx.tvdisplay.overlay',
             'installation': 'Optional runtime data RRO, initially disabled; not an early system overlay',
             'cold_boot_playback_not_established': True,
             'tested_as_manual_runtime_workaround_only': True,
             'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
             'resource_only_no_google_or_vendor_binary': True,
             'platform_signer_must_match_target': True, 'writes_to_device': False}
    (output / 'build-verification.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof, indent=2))

if __name__ == '__main__':
    main()
