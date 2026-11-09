# Android build status — CHEATLAB Launcher

The build uses the real upstream React/TypeScript and Rust/Tauri source from `millida/launcher`, pinned to `a9cec042ad1515a495a4f7c550e71f7423b65812`. It does not use Amethyst or Pojav as a substitute.

## Android-specific changes

- CHEATLAB app name, package ID, custom SVG/PNG icon and Android mipmap assets.
- Phone layout with bottom navigation, safe-area spacing, scrollable content and touch-friendly controls.
- CHEATLAB website device authorization at `https://cheatlab.fun/app-authorize.html`.
- Optional `clab2-…` account-key login with email OTP.
- Session tokens remain in the native encrypted Rust vault and are not exposed to React state/localStorage.
- Microsoft/offline Minecraft account selection remains a separate step.

The CHEATLAB Worker device authorization endpoints and D1 migration are deployed from the `tatarhost/cheatlab` repository. Site pages are served from `cheatlab.fun`.

## Important limitation

A successful APK build proves the Android app shell compiles; it does **not** prove Minecraft can launch. Upstream still uses desktop Java process startup via `std::process::Command`. Android ARM64 JVM/JNI, graphics surface/backend, Android Storage Access Framework and in-game touch controls remain unimplemented. Do not describe this build as a fully playable Minecraft Android launcher until those parts are implemented and tested on a physical device.

## Signing

Current CI uses a temporary test keystore to produce an installable APK. It is suitable for an installation smoke test, but its signing identity changes from build to build. A stable public release needs a persistent release keystore stored only in GitHub Secrets.

## Trademark / license

The upstream source is GPL-3.0-only, but its name, logo and branding are not covered by GPL. The public fork therefore uses the distinct CHEATLAB Launcher name, package ID and artwork, and identifies itself as based on Millida rather than as an official Millida build. See upstream [TRADEMARK.md](https://github.com/millida/launcher/blob/main/TRADEMARK.md).
