#!/bin/sh
# Builds libvlc.so for Android with LGPL 2.1 code only (ai-plan/CONTEXT.md, licence decision 2026-10-03).
# Runs inside VideoLAN's Android 3.0 build image; see Tools/vlc-lgpl/README.md for the docker command.
#
# Same libVLC as VideoLAN's libvlc-all 3.7.7 AAR (libvlcjni at the commit vlc-android tag libvlc-3.7.7 tests, VLC
# 3.0.25 with libvlcjni's patches), with these differences:
# - contribs built with libvlcjni's own "--license a" (LGPL 2.1 + ad-clauses: --disable-gpl --disable-gnuv3
#   --enable-ad-clauses), so FFmpeg is LGPL and no GPL-only library (libpostproc, a52, faad2, x264...) is linked;
# - VLC's own plugins whose source is GPL (Tools/vlc-lgpl/module_licences.py over this exact tree) are added to
#   libvlcjni's module blacklist, so they are not linked into libvlc.so;
# - patches/: the deinterlace plugin without its GPL yadif modes; MediaCodec for memory output (0003);
# - FFmpeg without its H.264, HEVC, AAC and E-AC3 decoders (the platform decodes them).
set -e

LIBVLCJNI_HASH="${LIBVLCJNI_HASH:-0b8dc65efb203c86a0476bc337ddd99ecf1c0ef6}"
ABIS="${ABIS:-arm64-v8a x86_64}"
OUT="${OUT:-/build/out-android}"

cd /build
if [ ! -d libvlcjni ]; then
    git clone --single-branch --branch libvlcjni-3.x https://code.videolan.org/videolan/libvlcjni.git libvlcjni
fi
cd libvlcjni
git reset -q --hard "$LIBVLCJNI_HASH"
git log --oneline -1

# Our VLC patches go after libvlcjni's (get-vlc.sh applies libvlc/patches/*.patch with git am).
for patch in /src/patches/*.patch; do
    cp "$patch" "libvlc/patches/9$(basename "$patch")"
done
if [ ! -d vlc ]; then
    ./buildsystem/get-vlc.sh
fi
# A patch added after the checkout was made (get-vlc.sh runs once) goes on top with git am, in order, as a fresh
# checkout would have it (the Windows-only ones too: they change modules Android doesn't build).
for patch in /src/patches/*.patch; do
    tr -d '\r' < "$patch" > /tmp/patch.patch
    if ! git -C vlc apply --reverse --check /tmp/patch.patch 2>/dev/null; then
        echo "applying: $patch"
        git -C vlc -c user.name=Streamary -c user.email=noreply@streamary.invalid am /tmp/patch.patch
    fi
done
(cd vlc && git log --oneline -3)

# Codec patents (ai-plan/CONTEXT.md, 2026-10-03; step 25d): H.264, HEVC, AAC and E-AC3 are decoded by the platform
# (Media Foundation / MediaCodec, patches 0002/0003), so FFmpeg is built without its decoders for them (hardware
# wrappers included). Parsers stay (they read headers, they don't decode).
FFMPEG_NO_DECODERS="aac,aac_fixed,aac_latm,aac_at,aac_mediacodec,eac3,eac3_at,h264,h264_amf,h264_crystalhd,h264_cuvid,h264_mediacodec,h264_mmal,h264_oh,h264_qsv,h264_rkmpp,h264_v4l2m2m,hevc,hevc_amf,hevc_cuvid,hevc_mediacodec,hevc_oh,hevc_qsv,hevc_rkmpp,hevc_v4l2m2m"
FFMPEG_RULES=vlc/contrib/src/ffmpeg/rules.mak
if ! grep -q "Streamary: patented formats" "$FFMPEG_RULES"; then
    echo "# Streamary: patented formats are decoded by the platform" >> "$FFMPEG_RULES"
    echo "FFMPEGCONF += --disable-decoder=$FFMPEG_NO_DECODERS" >> "$FFMPEG_RULES"
fi

# VLC's GPL plugins stay out of libvlc.so.
GPL_MODULES=$(python3 /tmp/module_licences.py vlc --gpl-names | tr '\n' ' ')
echo "GPL plugins excluded: $GPL_MODULES"
python3 - "$GPL_MODULES" <<'EOF'
import sys
path = 'buildsystem/compile-libvlc.sh'
text = open(path).read()
marker = 'VLC_MODULE_BLACKLIST="\n'
extra = ''.join('    %s\n' % name for name in sys.argv[1].split())
if '# Streamary: GPL plugins' not in text:
    text = text.replace(marker, marker + '    # Streamary: GPL plugins\n' + extra, 1)
open(path, 'w').write(text)
EOF

mkdir -p "$OUT"
for abi in $ABIS; do
    ./buildsystem/compile-libvlc.sh -a "$abi" --release --license a
done

# libvlc.so per ABI, and the licence the contribs were configured for.
for dir in libvlc/jni/libs/*; do
    abi=$(basename "$dir")
    mkdir -p "$OUT/$abi"
    cp "$dir/libvlc.so" "$OUT/$abi/"
    [ -f "$dir/libc++_shared.so" ] && cp "$dir/libc++_shared.so" "$OUT/$abi/"
done
ls -l "$OUT"/*
grep -h "LICENSE\|GPL" vlc/contrib/contrib-android-*/config.mak 2>/dev/null || true
