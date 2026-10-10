#!/usr/bin/env python3
"""Lists VLC's own plugins whose source is GPL (not LGPL), from a VLC source tree.

    python3 module_licences.py <vlc source> [--gpl-names]

Each plugin's sources come from the Makefile.am files (lib<name>_plugin_la_SOURCES); a plugin is GPL when any of its
own .c/.cpp/.h files carries a GPL header without the "Lesser" one. --gpl-names prints just the names (one per line),
for the Android build's module blacklist; otherwise a summary.
"""
import glob, os, re, sys

def plugin_sources(root):
    plugins = {}
    for makefile in glob.glob(os.path.join(root, 'modules', '**', 'Makefile.am'), recursive=True):
        directory = os.path.dirname(makefile)
        text = open(makefile, encoding='utf-8', errors='replace').read().replace('\\\n', ' ')
        for name, value in re.findall(r'^lib(\w+)_plugin_la_SOURCES\s*\+?=\s*(.*)$', text, re.M):
            files = [f for f in value.split() if not f.startswith('$') and f.endswith(('.c', '.cpp', '.h', '.hpp', '.m'))]
            # modules/Makefile.am includes the subfolders' files, so paths are relative to modules/ (or to the folder).
            for f in files:
                local = os.path.normpath(os.path.join(directory, f))
                top = os.path.normpath(os.path.join(root, 'modules', f))
                plugins.setdefault(name, []).append(local if os.path.exists(local) else top)
    return plugins

def licence(path):
    try:
        head = open(path, encoding='utf-8', errors='replace').read(4000)
    except OSError:
        return None
    if re.search(r'GNU\s+Lesser\s+General\s+Public', head) or re.search(r'\bLGPL', head):
        return 'LGPL'
    if re.search(r'GNU\s+General\s+Public', head):
        return 'GPL'
    return None

def main():
    root = sys.argv[1]
    names_only = '--gpl-names' in sys.argv
    gpl = {}
    for name, files in sorted(plugin_sources(root).items()):
        own = [f for f in files if os.path.exists(f)]
        bad = [os.path.relpath(f, root) for f in own if licence(f) == 'GPL']
        if bad:
            gpl[name] = bad
    if names_only:
        print('\n'.join(sorted(gpl)))
    else:
        for name, files in sorted(gpl.items()):
            print('%-28s %s' % (name, ', '.join(files[:3])))
        print('%d GPL plugins' % len(gpl))

if __name__ == '__main__':
    main()
