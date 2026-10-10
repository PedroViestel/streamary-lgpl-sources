"""Puts the LGPL-only libVLC build into Plugins/VlcMedia/ThirdParty/vlc/Win64 (run on Windows, from the repository).

    python Tools/vlc-lgpl/install_win64.py <stage folder> <notices file>

<stage folder>: the build's install tree, stripped (see README.md: /build/stage-win64 copied out of the volume).
<notices file>: THIRD-PARTY-NOTICES.txt from make_notices.py.
Copies libvlc.dll, libvlccore.dll and the plugins listed in keep-plugins.txt (nothing else), replaces VideoLAN's GPL
COPYING.txt with the LGPL text, writes BUILD-INFO.txt, and puts the notices into Content/Licenses.
"""
import datetime, hashlib, os, shutil, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
WIN64 = os.path.join(ROOT, 'Plugins', 'VlcMedia', 'ThirdParty', 'vlc', 'Win64')
LICENSES = os.path.join(ROOT, 'Content', 'Licenses')

def main(stage, notices):
    keep = [l.strip() for l in open(os.path.join(WIN64, 'keep-plugins.txt'), encoding='utf-8') if l.strip() and not l.startswith('#')]
    plugins = os.path.join(stage, 'lib', 'vlc', 'plugins')
    missing = [k for k in keep if not os.path.exists(os.path.join(plugins, k))]
    if missing:
        sys.exit('Not in the build: ' + ', '.join(missing))

    shutil.rmtree(os.path.join(WIN64, 'plugins'), ignore_errors=True)
    for plugin in keep:
        target = os.path.join(WIN64, 'plugins', plugin)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(os.path.join(plugins, plugin), target)
    for name in ('libvlc.dll', 'libvlccore.dll'):
        shutil.copy2(os.path.join(stage, 'bin', name), os.path.join(WIN64, name))

    # VideoLAN's package carries the GPL (for vlc.exe); this build is the libraries only, under the LGPL.
    lgpl = os.path.join(LICENSES, 'LGPL-2.1.txt')
    if os.path.exists(os.path.join(WIN64, 'COPYING.txt')):
        os.remove(os.path.join(WIN64, 'COPYING.txt'))
    shutil.copy2(lgpl, os.path.join(WIN64, 'COPYING.LIB.txt'))
    shutil.copy2(notices, os.path.join(LICENSES, 'THIRD-PARTY-NOTICES.txt'))
    shutil.copy2(notices, os.path.join(WIN64, 'THIRD-PARTY-NOTICES.txt'))

    lines = ['libVLC for Streamary: LGPL 2.1 only (Tools/vlc-lgpl).',
             'Installed: ' + datetime.date.today().isoformat(),
             'Source: VLC tag 3.0.23 (https://code.videolan.org/videolan/vlc), built by Tools/vlc-lgpl/build-win64.sh',
             'Build image: registry.videolan.org/vlc-debian-win64-3.0:20251208092116', '', 'SHA-256:']
    files = ['libvlc.dll', 'libvlccore.dll'] + ['plugins/' + k for k in keep]
    total = 0
    for name in files:
        path = os.path.join(WIN64, name.replace('/', os.sep))
        total += os.path.getsize(path)
        lines.append('%s  %s' % (hashlib.sha256(open(path, 'rb').read()).hexdigest(), name))
    open(os.path.join(WIN64, 'BUILD-INFO.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('Installed %d plugins, %.1f MB.' % (len(keep), total / 1e6))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
