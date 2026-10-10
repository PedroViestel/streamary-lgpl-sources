# libVLC, LGPL 2.1 only

Streamary ships libVLC and the libraries it bundles (FFmpeg and others) under the **GNU LGPL 2.1 only**
(`ai-plan/CONTEXT.md`, licence decision 2026-10-03). VideoLAN's own Windows and Android builds include GPL code
(FFmpeg configured with `--enable-gpl`, libpostproc, GPL-only decoders), so we build libVLC ourselves with GPL and
LGPLv3 code turned off. This folder holds everything needed to repeat that build, and it is part of what the
LGPL source offer publishes.

## What is different from VideoLAN's build

| | VideoLAN release | Streamary |
|---|---|---|
| Third-party libraries (`contrib/bootstrap`) | GPL on | `--disable-gpl --disable-gnuv3` (+ `--disable-asdcplib --disable-nettle --disable-gmp`; `--enable-ad-clauses` so FreeType builds under the FreeType License, a permissive licence with a credit clause, not GPLv2) |
| FFmpeg | `--enable-gpl --enable-postproc --enable-libmp3lame` | LGPL configuration, no postproc, no encoders |
| GPL-only libraries (a52, dca, libmpeg2, mad, faad2, dvdread, x264, x265, ...) | built | not built |
| TLS (gnutls, which needs LGPLv3 nettle/gmp) | built | not built: VLC opens `http` only; HTTPS goes through the app's loopback proxy |
| VLC's own plugins | all | `Plugins/VlcMedia/ThirdParty/vlc/Win64/keep-plugins.txt` (all LGPL in source), applied by `Tools/TrimVlcRuntime.py` |
| Programs | vlc.exe, Qt, skins | libVLC only |

Build-script changes, applied by `build-win64.sh` with `sed` and listed there: `--enable-dvdread` is not forced,
and SourceForge downloads go through `downloads.sourceforge.net` (the mirror VLC 3.0 names is gone).

## Windows x64

VideoLAN's build image for 3.0 (from `extras/ci/gitlab-ci.yml` of the tag), Docker on Windows or Linux:

```sh
docker pull registry.videolan.org/vlc-debian-win64-3.0:20251208092116
docker volume create vlclgpl
docker run --rm -u root -v vlclgpl:/build registry.videolan.org/vlc-debian-win64-3.0:20251208092116 chown -R 499:499 /build
docker run --name vlclgpl-win64 -v vlclgpl:/build -v "<repo>/Tools/vlc-lgpl:/src:ro" \
    registry.videolan.org/vlc-debian-win64-3.0:20251208092116 \
    sh -c "tr -d '\r' < /src/build-win64.sh > /tmp/b.sh && sh /tmp/b.sh"
```

From Git Bash, set `MSYS_NO_PATHCONV=1` first, or `/build` becomes a Windows path. The first build compiles every
library from source (a few hours); a rerun reuses the volume (after a new patch it re-runs configure and recompiles
VLC itself, not the libraries). The result is in `/build/out-win64`. Strip it into `/build/stage-win64` first (the DLLs
in the repository are stripped; same sizes as this produces):

```sh
docker run --rm -u 499 -v vlclgpl:/build registry.videolan.org/vlc-debian-win64-3.0:20251208092116 sh -c \
  'rm -rf /build/stage-win64 && cp -r /build/out-win64 /build/stage-win64 &&
   find /build/stage-win64 -name "*.dll" -exec x86_64-w64-mingw32-strip --strip-unneeded {} +'
```

Copy `/build/stage-win64` out of the volume; `install_win64.py` copies it into `Plugins/VlcMedia/ThirdParty/vlc/Win64`,
trims it to `keep-plugins.txt` and writes the notices. A rebuild changes every DLL (build timestamps) even where the
source didn't change; to keep Git LFS small, put back the unchanged ones (`git checkout`) and regenerate the SHA-256
list in `BUILD-INFO.txt` for what ships (as done for patch 0002).

## Android (arm64-v8a, x86_64)

The same libVLC as VideoLAN's `libvlc-all` 3.7.7 AAR (libvlcjni at the commit vlc-android's tag `libvlc-3.7.7`
tests, VLC 3.0.25 with libvlcjni's patches), built with libvlcjni's own `--license a` (LGPL 2.1 + ad-clauses),
with VLC's GPL plugins (found by `module_licences.py` in that exact tree) added to libvlcjni's module blacklist and
our patches applied after libvlcjni's. The image is the one VideoLAN's libvlcjni CI uses for 64-bit ABIs
(`VLC_ANDROID4_IMAGE`, NDK 29; the 3.0 image has NDK 21, which builds 32-bit only).

```sh
docker pull registry.videolan.org/vlc-debian-android:20260611225331
docker volume create vlclgpl-android
docker run --rm -u root -v vlclgpl-android:/build registry.videolan.org/vlc-debian-android:20260611225331 chown -R 499:499 /build
docker run --name vlclgpl-android -v vlclgpl-android:/build -v "<repo>/Tools/vlc-lgpl:/src:ro" \
    registry.videolan.org/vlc-debian-android:20260611225331 \
    sh -c "tr -d '\r' < /src/module_licences.py > /tmp/module_licences.py && tr -d '\r' < /src/build-android.sh > /tmp/b.sh && sh /tmp/b.sh"
```

`libvlc.so` per ABI lands in `/build/out-android/<abi>`; it replaces the one in
`Plugins/VlcMedia/ThirdParty/vlc/Android/<abi>` (with `libc++_shared.so`, the NDK's C++ runtime).

## Patches

`patches/*.patch` (`git format-patch --thread` form, which libvlcjni's `git am` requires; the Windows build uses
`git apply`):

- `0001-deinterlace-without-yadif.patch`: the deinterlace plugin without its yadif modes, whose code comes from FFmpeg
  under the GPL. The default mode (`auto`, which is `x`) and the other modes stay.
- `0002-mft-platform-decoders.patch`: the Media Foundation decoder (`mft`, Windows only) decodes H.264, HEVC, AAC and
  E-AC3 with Windows' own decoders, which carry the patent licences, and declines every other format (step 25,
  `ai-plan/steps/25-platform-decoders.md`). It fixes H.264/HEVC from MP4/MKV (parameter sets never sent), takes every
  ready output, adds HEVC (refused until the frame size is known: Windows' HEVC decoder crashes without it), E-AC3, a
  flush on seek, low-latency mode, and reads the output planes with the decoder's padded layout (`MF_MT_FRAME_SIZE`,
  e.g. 1088 lines for 1080p H.264; before, the chroma sat below the luma). The probes it was found with are in
  `Tools/codec-probe`; colour checks use `VLCHARNESS_DUMP` and the colour-bar fixture `10.mkv`.
- `0003-mediacodec-memory-output.patch`: the MediaCodec decoder (`mediacodec`, Android only) for Streamary's
  memory-output mode (`--no-mediacodec-dr`, vmem): configured with the input picture size (it sent 0x0, which decoders
  refuse); limited to H.264, HEVC, AAC and E-AC3 (other formats stay with FFmpeg/mpg123); E-AC3/AC3 decoders found
  despite a stream profile; the codec search names a decoder Android has no capabilities for; the output format is
  logged as debug, not as an error (step 25c). A fresh build applies 0001-0003 in order with `git am` (checked on
  3.0.25 with libvlcjni's patches; 0002 touches only the Windows module).

## Decoders (step 25)

H.264, HEVC, AAC and E-AC3 are decoded only by the platform: Media Foundation on Windows (patch 0002, `--codec=mft,any`)
and MediaCodec on Android (patch 0003). Both build scripts add `--disable-decoder=` for FFmpeg's decoders of those
formats (hardware wrappers included) to `contrib/src/ffmpeg/rules.mak`; FFmpeg keeps MPEG-2, MP2/MP3, AC3, Opus,
Vorbis, FLAC, PCM, VP9, DTS and VC-1, and the parsers. The platform modules open a live stream before its picture size
(or AAC configuration) is known and start when VLC restarts them on the packetizer's "input format change"; FFmpeg
used to cover that moment. Check a build: FFmpeg's generated `libavcodec/codec_list.c` in the contrib build folder
lists none of `ff_h264*`, `ff_hevc*`, `ff_aac*`, `ff_eac3*` decoders, and `Tools/codec-probe/vlcharness` with
`--codec=avcodec,none` decodes nothing for them ("VLC could not decode the format").

## Checking a build

- `module_licences.py <vlc source>`: VLC's own plugins with GPL source files (none may ship).
- `linked_packages.py`: the contrib packages linked into what ships (for the notices).
- `make_notices.py`: `THIRD-PARTY-NOTICES.txt` from those packages' own licence files; it stops on a GPL or
  LGPLv3 one.
- FFmpeg names its own licence inside the binary: `LGPL version 2.1 or later` is right; `GPL` is not.

## Replacing the libraries

The libraries stay separate files next to the app (`libvlc.dll`, `libvlccore.dll`, `plugins/`), so a user can
build their own (for example with this script, changed) and put them in place of ours.
