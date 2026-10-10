#!/usr/bin/env python3
"""Writes THIRD-PARTY-NOTICES.txt from the licence bundles of the libVLC builds Streamary ships (runs anywhere).

    python make_notices.py Windows=<bundle> Android=<bundle> > THIRD-PARTY-NOTICES.txt

A bundle comes from collect_licences.py. Each library is listed once, with the platforms it ships on, its version(s)
and its licence, named from the licence text. Long licence texts (the LGPL appears in about a dozen packages) are
printed once at the end and referred to by name. A package whose licence is GPL or LGPLv3 stops the script: the
builds must not contain one.
"""
import glob, os, sys

SHARED_TEXT_CHARS = 6000
LABEL_ORDER = ['LGPL 2.1', 'LGPL 2.0 (Library GPL)']

def read(path):
    return open(path, encoding='utf-8', errors='replace').read().replace('\r\n', '\n').strip()

def label(text):
    # One line, single spaces: licence names are often wrapped.
    t = ' '.join(text.upper().split())
    # GNU licences by their heading or opening notice only: the GPLv3 text itself mentions the Lesser GPL near its end.
    head = t[:700]
    if 'THE FREETYPE PROJECT LICENSE' in t or 'FREETYPE LICENSE' in head: return 'FreeType License (FTL)'
    if 'INDEPENDENT JPEG GROUP' in t and 'LEGAL ISSUES' in t: return 'IJG License ("This software is based in part on the work of the Independent JPEG Group.")'
    if 'GNU LESSER GENERAL PUBLIC LICENSE' in head:
        if 'VERSION 3' in head: return 'LGPL 3'
        return 'LGPL 2.1'
    if 'GNU LIBRARY GENERAL PUBLIC LICENSE' in head: return 'LGPL 2.0 (Library GPL)'
    if 'GNU GENERAL PUBLIC LICENSE' in head: return 'GPL'
    if 'PNG REFERENCE LIBRARY' in t or 'LIBPNG' in head: return 'libpng License'
    if "PROVIDED 'AS-IS'" in t and 'ALTERED SOURCE VERSIONS' in t: return 'zlib License'
    if 'PERMISSION IS HEREBY GRANTED, FREE OF CHARGE' in t: return 'MIT License'
    if 'OLD MIT' in t or 'PERMISSION IS HEREBY GRANTED, WITHOUT WRITTEN AGREEMENT' in t: return 'MIT-style License ("Old MIT")'
    if 'PERMISSION TO USE, COPY, MODIFY, DISTRIBUTE, AND SELL' in t: return 'MIT-style License (HPND)'
    if 'PERMISSION TO USE, COPY, MODIFY, AND/OR DISTRIBUTE' in t or 'PERMISSION TO USE, COPY, MODIFY, AND DISTRIBUTE' in t: return 'ISC-style License'
    if 'REDISTRIBUTION AND USE IN SOURCE AND BINARY FORMS' in t or 'BSD' in t: return 'BSD License'
    if 'IN THE PUBLIC DOMAIN' in t: return 'Public domain'
    # A preamble before the licence itself (mpg123).
    if 'GNU LESSER GENERAL PUBLIC LICENSE VERSION 2.1' in t: return 'LGPL 2.1'
    return ''

def main(args):
    bundles = [arg.split('=', 1) for arg in args]
    # package -> {'platforms': [...], 'versions': {platform: v}, 'files': {name: text}}
    packages = {}
    for platform, folder in bundles:
        for directory in sorted(glob.glob(folder + '/*')):
            name = os.path.basename(directory)
            entry = packages.setdefault(name, {'platforms': [], 'versions': {}, 'files': {}})
            entry['platforms'].append(platform)
            entry['versions'][platform] = read(directory + '/version.txt') if os.path.exists(directory + '/version.txt') else ''
            for path in sorted(glob.glob(directory + '/*')):
                if os.path.basename(path) != 'version.txt':
                    entry['files'].setdefault(os.path.basename(path), read(path))

    shared, problems, sections = {}, [], []
    def shared_name(lab, text):
        key = ' '.join(text.split())
        if key not in shared:
            same = sum(1 for (name, _) in shared.values() if name.startswith(lab))
            shared[key] = (lab + (' (variant %d)' % (same + 1) if same else ''), text)
        return shared[key][0]

    def describe(title, entry, url=''):
        versions = sorted(set(v for v in entry['versions'].values() if v))
        labelled = [(name, text, label(text)) for name, text in entry['files'].items()]
        # LGPL texts over a GPL file shipped beside them (gettext-style trees).
        if any(l not in ('GPL',) for _, _, l in labelled):
            labelled = [x for x in labelled if x[2] != 'GPL']
        labels = sorted({l for _, _, l in labelled if l})
        if set(labels) & {'GPL', 'LGPL 3'}:
            problems.append('%s: %s' % (title, ', '.join(labels)))
        lines = [title + (' ' + ' / '.join(versions) if versions else ''),
                 'Licence: ' + (', '.join(labels) if labels else 'see text below'),
                 'Ships on: ' + ', '.join(entry['platforms'])]
        if url:
            lines.append('Source: ' + url)
        for name, text, lab in labelled:
            if len(text) > SHARED_TEXT_CHARS:
                lines += ['', '--- %s: full text under "%s" in Licence texts below ---' % (name, shared_name(lab or name, text))]
            else:
                lines += ['', '--- ' + name + ' ---', text]
        return '\n'.join(lines)

    vlc = packages.pop('vlc')
    vlc_entry = {'platforms': vlc['platforms'], 'versions': vlc['versions'],
                 'files': {'COPYING.LIB': 'Copyright (C) 1996-2025 VLC authors and VideoLAN. Licensed under the GNU Lesser General Public '
                                          'License, version 2.1 or later (full text in LGPL-2.1.txt).'}}
    sections.append(describe('libVLC and libVLCcore (VideoLAN)', vlc_entry, 'https://code.videolan.org/videolan/vlc'))
    for name in sorted(packages, key=str.lower):
        sections.append(describe(name, packages[name]))
    sections.append('\n'.join(['Toolchain runtime libraries', 'Ships on: ' + ', '.join(p for p, _ in bundles), '',
        'Windows: parts of the MinGW-w64 runtime (winpthreads: MIT License; CRT: public domain and ZPL) and of the GCC runtime',
        '(libgcc, libssp, libatomic: GPL 3 with the GCC Runtime Library Exception, which allows use in any program) are linked',
        'into the libraries. Android: libc++_shared.so is LLVM libc++ from the Android NDK (Apache License 2.0 with LLVM',
        'Exceptions).']))

    out = ['THIRD-PARTY NOTICES', '===================', '',
           'Streamary uses the libraries below. They ship as separate files next to the app (Windows: libvlc.dll,',
           'libvlccore.dll and the plugins folder; Android: libvlc.so), and you may replace them with your own builds.',
           'They were built from source without GPL or LGPLv3 code; the exact sources, our changes and the build scripts',
           'are available as the About screen says. FFmpeg is built without its H.264, HEVC, AAC and E-AC3 decoders: those',
           'formats are decoded by the operating system or device (Media Foundation on Windows, MediaCodec on Android).', '']
    for section in sections:
        out += ['-' * 78, section, '']
    # The app's own third-party assets (not libraries): the player's icons (step 24).
    out += ['-' * 78, '
'.join([
        'Material Symbols (Google)',
        'Licence: Apache License 2.0 (full text in Apache-2.0.txt)',
        'Ships on: all platforms',
        'Source: https://github.com/google/material-design-icons',
        "The player's icons are drawn from Material Symbols paths by Tools/MakePlayerIcons.py."]), '']
    out += ['=' * 78, 'Licence texts', '=' * 78, '']
    for name, text in sorted(shared.values()):
        out += ['-' * 78, name, '', text, '']
    out += ['=' * 78, 'VLC authors', '=' * 78, '', vlc['files'].get('AUTHORS', ''), '']
    # UTF-8 whatever the console's code page (author names, licence texts).
    sys.stdout.buffer.write(('\n'.join(out) + '\n').encode('utf-8'))
    if problems:
        sys.stderr.write('PROBLEMS:\n' + '\n'.join(problems) + '\n')
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
