#!/usr/bin/env python3
"""Copies the licence files of the packages a libVLC build links into a bundle (runs in the build container).

    python3 collect_licences.py <linked.json> <bundle folder>

Environment: CONTRIB (the contrib folder), TREE (its build tree, contrib-<host>), VLC (the VLC source).
The bundle has one folder per package with version.txt and the package's own licence files (COPYING, LICENSE, ...),
and vlc/ with COPYING.LIB, AUTHORS and version.txt. make_notices.py turns bundles into THIRD-PARTY-NOTICES.txt.
"""
import glob, json, os, re, shutil, sys

CONTRIB = os.environ.get('CONTRIB', '/build/vlc/contrib')
TREE = os.environ.get('TREE', CONTRIB + '/contrib-win64')
VLC = os.environ.get('VLC', '/build/vlc')
# Packages whose tree carries licences that don't apply to this build: FFmpeg ships GPL and LGPLv3 texts beside the
# LGPL 2.1 one, and is configured for LGPL 2.1 (the binary says "LGPL version 2.1 or later").
# IJG libjpeg keeps its licence in README ("LEGAL ISSUES").
FILES = {'ffmpeg': ['COPYING.LGPLv2.1', 'LICENSE.md'], 'jpeg': ['README']}

def version_of(package):
    """From the tarball the contrib fetched (libogg-1.3.5.tar.xz -> 1.3.5)."""
    names = [package, package.replace('lib', '', 1), 'lib' + package]
    for tarball in sorted(glob.glob(CONTRIB + '/tarballs/*')):
        base = os.path.basename(tarball)
        for name in names:
            m = re.match(r'^%s[-_]v?([0-9][0-9A-Za-z.\-_]*?)\.(tar|zip|tgz)' % re.escape(name), base, re.I)
            if m:
                return m.group(1)
    return ''

def licence_files(directory):
    package = os.path.basename(directory)
    if package in FILES:
        return [directory + '/' + name for name in FILES[package] if os.path.exists(directory + '/' + name)]
    files = []
    for path in sorted(glob.glob(directory + '/*')):
        base = os.path.basename(path).upper()
        if os.path.isfile(path) and re.match(r'^(COPYING|LICEN[CS]E|COPYRIGHT|NOTICE)', base) and not base.endswith(('.IN', '.AM', '.SH', '.PY', '.C', '.H')):
            files.append(path)
    return files

def main(linked, bundle):
    data = json.load(open(linked))
    shutil.rmtree(bundle, ignore_errors=True)
    os.makedirs(bundle + '/vlc')
    configure = open(VLC + '/configure.ac', encoding='utf-8', errors='replace').read()
    m = re.search(r'AC_INIT\(\[?vlc\]?,\s*\[?([0-9.]+)', configure)
    open(bundle + '/vlc/version.txt', 'w').write(m.group(1) if m else '')
    for name in ('COPYING.LIB', 'AUTHORS'):
        shutil.copy(VLC + '/' + name, bundle + '/vlc/' + name)
    missing = []
    for package in data['packages']:
        files = licence_files(TREE + '/' + package)
        if not files:
            missing.append(package)
            continue
        os.makedirs(bundle + '/' + package)
        open(bundle + '/' + package + '/version.txt', 'w').write(version_of(package))
        for path in files:
            shutil.copy(path, bundle + '/' + package + '/' + os.path.basename(path))
    if missing:
        sys.exit('no licence file: ' + ', '.join(missing))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
