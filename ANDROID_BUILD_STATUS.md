# Android port build status

This repository's Android build job checks the **real upstream source** from `millida/launcher`, pinned to commit `a9cec042ad1515a495a4f7c550e71f7423b65812`. It does not use Amethyst or Pojav as a substitute.

The first CI run is a compatibility/build probe. A successful Tauri APK build would prove only that the Millida application shell compiles for Android; it would **not** prove Minecraft can launch. The upstream Rust launcher currently starts desktop Java with `std::process::Command`, so Minecraft-on-Android still requires a separate Android JVM/JNI and graphics integration.

The workflow intentionally uploads an APK only if the real upstream Android build succeeds. It does not publish a GitHub Release or claim runtime compatibility.

## Legal/branding boundary

The upstream project is GPL-3.0-only, but its name, logos, icons, art, service credentials and infrastructure are not granted by the code license. Public forks must use a distinct product name, application ID, icons and service registrations, and must not present themselves as official Millida builds. See upstream [TRADEMARK.md](https://github.com/millida/launcher/blob/main/TRADEMARK.md).

## Next engineering gates

1. Make the upstream Tauri/Rust core compile on Android by gating desktop-only plugins and OS integrations.
2. Replace desktop file dialogs and absolute-path assumptions with Android Storage Access Framework and app-private storage.
3. Integrate a supported ARM64 Java runtime through JNI and an Android graphics/input backend.
4. Test Vanilla first, then individual loader families and content types on a physical Android device.
