# Streamary: LGPL source code

[Streamary](https://streamary.app) is a video player for your own IPTV playlists, for Windows, Android phones and tablets, and Android TV. It uses **libVLC** and the libraries it bundles (FFmpeg and others), built by us under the **GNU Lesser General Public License, version 2.1 only** (no GPL or LGPLv3 parts). This repository is how we meet that licence:

- **the exact source code** of every libVLC build we ship, with our changes and the scripts that build it (see *Releases*);
- **how to rebuild it** (`build-kit/`);
- **how to replace libVLC in Streamary** with your own build (below).

Streamary's own code is not here; it isn't covered by the LGPL. The licence texts and the list of libraries are also in the app (About > licences) and at [streamary.app/en/licenses](https://streamary.app/en/licenses/).

## Which source matches which app version

Each [release](../../releases) of this repository names the Streamary versions it applies to and carries:

| File | What it is |
|---|---|
| `vlc-<version>-<commit>.tar.gz` | VLC's source at the exact commit we built (from `git archive`) |
| `*-local-changes.diff` | every change to that source made by our build (our patches in `build-kit/patches` and the build script's edits) |
| `contrib-tarballs-<platform>.tar` | the source archives of every third-party library VLC's build downloaded (FFmpeg, and the others listed in the app's notices) |
| `libvlcjni-<commit>.tar.gz` + diff | Android: VideoLAN's libvlcjni build system at the exact commit, and our change to it |
| `SHA256SUMS` | checksums of all the above |

**Release `libvlc-2026-10`** applies to Streamary 0.3 to 0.13 (and later versions until a newer release is listed):

- **Windows x64:** VLC 3.0.23 (commit `578d28f6c9f2379164516e689418f92ac74a3445`), built in VideoLAN's image `registry.videolan.org/vlc-debian-win64-3.0:20251208092116` (`sha256:ef9cab24b7f16cf223c0562b21f7a5f5f62294dcb88b0b704ef3d3c8682918f4`).
- **Android (arm64-v8a, x86_64):** libvlcjni commit `0b8dc65efb203c86a0476bc337ddd99ecf1c0ef6` with VLC `3.0.24-37-gaec0d4b715` (commit `aec0d4b715e55a799a8618749a66744a492404e8`), built in VideoLAN's image `registry.videolan.org/vlc-debian-android:20260611225331` (`sha256:5f041ff50465aea803b93855d463f4b98f1d9f3be6628e304af2bf3fded6f98e`).

We keep every release here for at least three years after the last Streamary version that used it was distributed. If a file is ever missing, write to **suporte@streamary.app** and we will send it at no charge beyond the cost of delivery.

## Rebuilding

`build-kit/README.md` explains the whole build (Docker, the configure options that keep it LGPL 2.1 only, the patches, stripping, and the licence notices). In short:

- `build-kit/build-win64.sh`: Windows x64 in VideoLAN's win64 image;
- `build-kit/build-android.sh`: Android with libvlcjni in VideoLAN's Android image;
- `build-kit/patches/`: our three patches (deinterlacing without yadif, Media Foundation platform decoders on Windows, MediaCodec output to memory on Android).

The scripts expect the source archives above, or download the same versions themselves.

## Replacing libVLC in Streamary

The LGPL lets you run Streamary with a modified libVLC. The libraries are separate files in the app:

| Platform | Files |
|---|---|
| Windows | `Streamary\Plugins\VlcMedia\ThirdParty\vlc\Win64\libvlc.dll`, `libvlccore.dll` and the `plugins\` folder next to them |
| Android | `lib/arm64-v8a/libvlc.so` (and `lib/x86_64/libvlc.so`) inside the APK |

Your build must keep libVLC 3.0's programming interface (the app calls it as a shared library).

### Windows (Microsoft Store version)

Store apps install into a read-only, signed folder, so you run your own copy instead:

1. Turn on **Developer Mode** (Settings > System > For developers).
2. Copy Streamary's installation folder (`C:\Program Files\WindowsApps\PedroViestel.Streamary_<version>_x64__<id>`; you may need to take ownership of `WindowsApps` to read it) to a folder of your own, for example `C:\Streamary-custom`.
3. In the copy, delete `AppxSignature.p7x`, `AppxBlockMap.xml` and `AppxMetadata\` (if present), then replace `libvlc.dll`, `libvlccore.dll` and `plugins\` with your build.
4. Uninstall the Store version (your Lists and settings in `%LOCALAPPDATA%` are kept), then in PowerShell: `Add-AppxPackage -Register C:\Streamary-custom\AppxManifest.xml`.

Store purchases are tied to the Store's signed package; a self-registered copy runs the free version. If you'd rather not copy from `WindowsApps`, ask us at suporte@streamary.app for the unsigned package of the version you have.

### Android (Google Play version)

1. Get the installed APKs: `adb shell pm path com.streamary.app`, then `adb pull` each path (a base APK and split APKs).
2. In the split that contains `lib/<abi>/libvlc.so`, replace that file with your build (an APK is a ZIP file; keep the library uncompressed and page-aligned with `zipalign -p 4`).
3. Re-sign **all** the APKs with the same key of your own (`apksigner sign --ks <your key> <apk>`).
4. Uninstall the Play version, then `adb install-multiple <all the APKs>`.

A copy signed with your key can't use Google Play purchases or Google sign-in (both check the app's signature), so it runs as the free version without Drive sync.

## Licence of this repository

The patches in `build-kit/patches/` change LGPL code and are under the GNU LGPL 2.1 or later, like the files they change. Our build scripts are under the MIT licence. The source archives in the releases keep their own licences, as stated inside them.
