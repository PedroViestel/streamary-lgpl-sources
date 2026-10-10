#!/usr/bin/env python3
"""Lists the contrib packages linked into the libVLC files Streamary ships (runs in the build container).

Input: keep-plugins.txt (plugin paths relative to plugins/), the install tree (/build/out-win64) and the contrib tree
(/build/vlc/contrib). For libvlccore and every kept plugin it reads the libtool archive's dependency_libs, follows each
library through pkg-config --static (static libraries bring their own dependencies) and maps each library file back to
the contrib package whose build tree produced it. Prints JSON: {"packages": {name: [libs]}, "unmapped": [libs]}.
"""
import glob, json, os, re, subprocess, sys

KEEP = sys.argv[1] if len(sys.argv) > 1 else '/src/keep-plugins.txt'
# Windows defaults; Android sets CONTRIB, PREFIX, TREE, BUILD and passes "all" as KEEP (every plugin built goes
# into libvlc.so there, except libvlcjni's blacklist, which only makes the list longer than what ships).
OUT = os.environ.get('OUT', '/build/out-win64')
CONTRIB = os.environ.get('CONTRIB', '/build/vlc/contrib')
PREFIX = os.environ.get('PREFIX', CONTRIB + '/x86_64-w64-mingw32')
BUILDTREE = os.environ.get('TREE', CONTRIB + '/contrib-win64')
# Windows system libraries and the toolchain's own runtime: not contribs.
SYSTEM = set('ole32 oleaut32 uuid user32 gdi32 advapi32 ws2_32 iphlpapi bcrypt secur32 crypt32 shlwapi shell32 kernel32 '
             'winmm dxguid dxgi d3d11 d3d9 dxva2 mfplat mfuuid strmiids psapi usp10 comdlg32 comctl32 version setupapi imm32 '
             'opengl32 dwrite d2d1 windowscodecs ksuser mf mfreadwrite propsys ntdll dbghelp rpcrt4 normaliz wsock32 '
             'pthread m stdc++ gcc gcc_s ssp mingwex mingw32 msvcrt ucrt moldname '
             # Android system libraries
             'c dl log android OpenSLES EGL GLESv2 GLESv3 mediandk jnigraphics aaudio c++_shared c++_static c++abi unwind'.split())

def la_libs(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r"^dependency_libs='(.*)'", text, re.M)
    return m.group(1).split() if m else []

def pc_for_lib(name):
    """The .pc file that provides -l<name>: named after it, else the one whose Libs line starts with it (a .pc that
    merely lists it as a dependency must not count, or every user of zlib would claim -lz)."""
    pcdir = PREFIX + '/lib/pkgconfig/'
    for candidate in (name, 'lib' + name, name.replace('lib', '', 1)):
        if os.path.exists(pcdir + candidate + '.pc'):
            return candidate
    for pc in glob.glob(pcdir + '*.pc'):
        text = open(pc, encoding='utf-8', errors='replace').read()
        m = re.search(r'^Libs:(.*)$', text, re.M)
        own = [t[2:] for t in (m.group(1).split() if m else []) if t.startswith('-l')]
        if own and own[0] == name:
            return os.path.basename(pc)[:-3]
    return None

def static_libs(pc):
    env = dict(os.environ, PKG_CONFIG_LIBDIR=PREFIX + '/lib/pkgconfig', PKG_CONFIG_PATH='')
    out = subprocess.run(['pkg-config', '--static', '--libs-only-l', pc], capture_output=True, text=True, env=env).stdout
    return [t[2:] for t in out.split() if t.startswith('-l')]

def package_for(lib):
    """The contrib package whose build tree holds lib<name>.a (or the .la's name)."""
    for pattern in ('/*/**/lib%s.a' % lib, '/*/**/%s.a' % lib, '/*/**/lib%s.la' % lib):
        hits = glob.glob(BUILDTREE + pattern, recursive=True)
        if hits:
            return os.path.relpath(hits[0], BUILDTREE).split(os.sep)[0]
    return None

BUILD = os.environ.get('BUILD', '/build/vlc/win64')
if KEEP == 'all':
    keep = sorted(os.path.relpath(p, BUILD + '/modules').replace('.la', '.dll') for p in glob.glob(BUILD + '/modules/**/lib*_plugin.la', recursive=True))
    keep = [os.path.basename(k) for k in keep]
else:
    keep = [l.strip() for l in open(KEEP, encoding='utf-8') if l.strip() and not l.startswith('#')]

def make_value(directory, variable):
    """A variable of the configured build, fully expanded (libtool archives leave out the static libraries a plugin
    links itself, so the Makefiles are the source)."""
    probe = '/tmp/print-variable.mk'
    with open(probe, 'w') as f:
        f.write('print-variable:\n\t@echo $(%s)\n' % variable)
    out = subprocess.run(['make', '-s', '-C', directory, '-f', 'Makefile', '-f', probe, 'print-variable'], capture_output=True, text=True).stdout
    return out.split()

def add_tokens(tokens, libs):
    for token in tokens:
        if token.startswith('-l'):
            libs.add(token[2:])
        elif token.endswith(('.la', '.a')) and '/contrib/' in token:
            libs.add(re.sub(r'^lib', '', re.sub(r'\.(la|a)$', '', os.path.basename(token))))

libs = set()
for variable in ('libvlccore_la_LIBADD', 'libvlccore_la_LDFLAGS'):
    add_tokens(make_value(BUILD + '/src', variable), libs)
for plugin in keep:
    name = re.sub(r'\.dll$', '', os.path.basename(plugin))
    for variable in (name + '_la_LIBADD', name + '_la_LDFLAGS'):
        add_tokens(make_value(BUILD + '/modules', variable), libs)
    for token in la_libs(OUT + '/lib/vlc/plugins/' + re.sub(r'\.dll$', '.la', plugin)) if os.path.exists(OUT + '/lib/vlc/plugins/' + re.sub(r'\.dll$', '.la', plugin)) else []:
        add_tokens([token], libs)

# Follow static dependencies.
queue = list(libs)
while queue:
    lib = queue.pop()
    pc = pc_for_lib(lib)
    if not pc:
        continue
    for dep in static_libs(pc):
        if dep not in libs:
            libs.add(dep)
            queue.append(dep)

packages, unmapped = {}, []
for lib in sorted(libs - SYSTEM):
    pkg = package_for(lib)
    if pkg:
        packages.setdefault(pkg, []).append(lib)
    else:
        unmapped.append(lib)
print(json.dumps({'packages': packages, 'unmapped': unmapped}, indent=1))
