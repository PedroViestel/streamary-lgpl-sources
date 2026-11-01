#!/bin/sh
# Builds libVLC for Windows x64 with LGPL 2.1 code only (ai-plan/CONTEXT.md, licence decision 2026-10-03).
# Runs inside VideoLAN's own 3.0 build image; see Tools/vlc-lgpl/README.md for the docker command.
#
# What differs from VideoLAN's release build:
# - contribs (FFmpeg and the other third-party libraries) are configured with --disable-gpl --disable-gnuv3:
#   FFmpeg is LGPL (no --enable-gpl / postproc / lame), GPL-only libraries (a52, dca, libmpeg2, mad, faad2, dvdread,
#   x264, x265, ...) are not built, and gnutls is dropped (its nettle/gmp need LGPLv3), so VLC opens http only;
# - libVLC only (-z: no vlc.exe, Qt or skins);
# - dvdread is not forced on (build.sh passes --enable-dvdread, which fails without the GPL libdvdread);
# - SourceForge downloads go through SourceForge's redirector (the mirror VLC 3.0 names is gone);
# - patches/: the deinterlace plugin without its GPL yadif modes (the rest of it is LGPL).
# VLC's own plugins are then limited to Plugins/VlcMedia/ThirdParty/vlc/Win64/keep-plugins.txt (all LGPL in source)
# by Tools/TrimVlcRuntime.py.
set -e

VLC_TAG="${VLC_TAG:-3.0.23}"
OUT="${OUT:-/build/out-win64}"

cd /build
if [ ! -d vlc ]; then
    git clone --depth 1 --branch "$VLC_TAG" https://code.videolan.org/videolan/vlc.git vlc
fi
cd vlc
git describe --tags --exact-match

# Our patches to VLC (Tools/vlc-lgpl/patches), each applied once.
for patch in /src/patches/*.patch; do
    tr -d '\r' < "$patch" > /tmp/patch.patch  # a Windows checkout may have CRLF
    if git apply --reverse --check /tmp/patch.patch 2>/dev/null; then echo "already applied: $patch"; else git apply /tmp/patch.patch; fi
done

sed -i 's/--enable-dvdread //' extras/package/win32/build.sh
# The contribs' fixed SourceForge mirror no longer resolves; SourceForge's own redirector serves the same files
# (checksums are still checked against contrib/src/*/SHA512SUMS).
sed -i 's|^SF := https://netcologne.dl.sourceforge.net/|SF := https://downloads.sourceforge.net/project/|' contrib/src/main.mak

# Codec patents (ai-plan/CONTEXT.md, 2026-10-03; step 25d): H.264, HEVC, AAC and E-AC3 are decoded by the platform
# (Media Foundation / MediaCodec, patches 0002/0003), so FFmpeg is built without its decoders for them (hardware
# wrappers included). Parsers stay (they read headers, they don't decode).
FFMPEG_NO_DECODERS="aac,aac_fixed,aac_latm,aac_at,aac_mediacodec,eac3,eac3_at,h264,h264_amf,h264_crystalhd,h264_cuvid,h264_mediacodec,h264_mmal,h264_oh,h264_qsv,h264_rkmpp,h264_v4l2m2m,hevc,hevc_amf,hevc_cuvid,hevc_mediacodec,hevc_oh,hevc_qsv,hevc_rkmpp,hevc_v4l2m2m"
FFMPEG_RULES=contrib/src/ffmpeg/rules.mak
if ! grep -q "Streamary: patented formats" "$FFMPEG_RULES"; then
    echo "# Streamary: patented formats are decoded by the platform" >> "$FFMPEG_RULES"
    echo "FFMPEGCONF += --disable-decoder=$FFMPEG_NO_DECODERS" >> "$FFMPEG_RULES"
fi

# asdcplib (digital cinema packages) pulls in nettle and gmp, which are LGPLv3: off with them.
# --enable-ad-clauses lets FreeType (subtitle text) build under the FreeType License, a permissive licence with a
# credit clause (the notices carry the credit), instead of its GPLv2 option. It gates FreeType only.
export CONTRIBFLAGS="--disable-gpl --disable-gnuv3 --disable-asdcplib --disable-nettle --disable-gmp --enable-ad-clauses"
# configure.sh forces live555 (RTSP; LGPLv3, not built) and faad (GPL, not built) on: off.
export CONFIGFLAGS="--disable-live555 --disable-faad"
# -r release, -z libVLC only, -i none: no installer, install the tree into $OUT instead.
extras/package/win32/build.sh -r -z -a x86_64 -i none -o "$OUT"

# The licence the contribs were configured for, and FFmpeg's own view of it.
grep -h "LICENSE\|GPL" contrib/contrib-win64/config.mak || true
