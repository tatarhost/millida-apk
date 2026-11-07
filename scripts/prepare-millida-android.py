#!/usr/bin/env python3
"""Apply the first Android build adaptation to a pinned Millida Launcher checkout.

This script deliberately keeps the original Millida React frontend and Rust engine.
It only replaces desktop-only integrations with Android-safe stubs so the Android
target can be compiled and its remaining platform blockers discovered.
"""
from pathlib import Path
import subprocess
import sys

EXPECTED = "a9cec042ad1515a495a4f7c550e71f7423b65812"

def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match for {old[:90]!r}, got {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare-millida-android.py <millida-launcher-checkout>")
    root = Path(sys.argv[1]).resolve()
    actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if actual != EXPECTED:
        raise SystemExit(f"Unexpected Millida source revision {actual}; expected {EXPECTED}")

    cargo = root / "src-tauri/Cargo.toml"
    text = cargo.read_text(encoding="utf-8")

    # Tauri core is used on every target; desktop-only features and integrations
    # are activated only for Windows/macOS/Linux.
    replace_once(cargo, 'tauri = { version = "2", features = ["protocol-asset", "tray-icon", "macos-private-api"] }',
                 'tauri = { version = "2", features = ["protocol-asset"] }')
    desktop_deps = """[target.'cfg(not(target_os = "android"))'.dependencies]
tauri = { version = "2", features = ["tray-icon", "macos-private-api"] }
tauri-plugin-updater = "2"
tauri-plugin-autostart = "~2.5.1"
tauri-plugin-single-instance = { version = "2", features = ["deep-link"] }
tauri-plugin-global-shortcut = "2.3.2"
discord-rich-presence = "0.2"

"""
    marker = "[target.'cfg(windows)'.dependencies]"
    if text.count(marker) != 1:
        raise SystemExit("Cargo.toml: could not find the Windows target dependency section")
    text = text.replace(marker, desktop_deps + marker, 1)
    for line in [
        'tauri-plugin-updater = "2"\n',
        'tauri-plugin-autostart = "~2.5.1"\n',
        'tauri-plugin-single-instance = { version = "2", features = ["deep-link"] }\n',
        'discord-rich-presence = "0.2"\n',
        'tauri-plugin-global-shortcut = "2.3.2"\n',
    ]:
        if text.count(line) != 1:
            raise SystemExit(f"Cargo.toml: expected one dependency line {line.strip()!r}")
        text = text.replace(line, "", 1)
    cargo.write_text(text, encoding="utf-8")

    src = root / "src-tauri/src"
    # Use real desktop modules unchanged off Android. Android gets adapters for
    # features that do not exist on a phone.
    lib = src / "lib.rs"
    for old, new in [
        ("mod app_icon;\n", '#[cfg(not(target_os = "android"))]\nmod app_icon;\n#[cfg(target_os = "android")]\n#[path = "app_icon_mobile.rs"]\nmod app_icon;\n'),
        ("mod discord;\n", '#[cfg(not(target_os = "android"))]\nmod discord;\n#[cfg(target_os = "android")]\n#[path = "discord_mobile.rs"]\nmod discord;\n'),
        ("pub mod tray;\n", '#[cfg(not(target_os = "android"))]\npub mod tray;\n#[cfg(target_os = "android")]\n#[path = "tray_mobile.rs"]\npub mod tray;\n'),
        ("mod overlay;\n", '#[cfg(not(target_os = "android"))]\nmod overlay;\n#[cfg(target_os = "android")]\n#[path = "overlay_mobile.rs"]\nmod overlay;\n'),
    ]:
        replace_once(lib, old, new)

    # Builder plugins not supported by the mobile target stay on desktop.
    old_chain = """.plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {
            cli::forward_second_start(app, &argv);
            tray::show_main(app);
        }))
        .plugin(navguard::init())
        .plugin(tauri_plugin_deep_link::init())
        // Tauri auto-update plugin. The address and the public signing key are in tauri.conf.json. Our own signature check code is in engine/core/selfupdate.rs.
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        // Only one global hotkey is registered: the overlay hotkey (Alt+M by default), see overlay.rs.
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        // Запуск вместе с системой (06.10.2026): лаунчер живёт в трее, и
        // напоминания о сундуке и серии есть кому показать.
        // Autostart with the system. The user turns it on with a switch in settings.
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec![commands::system::AUTOSTART_ARG]),
        ))
        .setup(|app| {"""
    new_chain = """.plugin(navguard::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_clipboard_manager::init());
    #[cfg(not(target_os = "android"))]
    let builder = builder
        .plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {
            cli::forward_second_start(app, &argv);
            tray::show_main(app);
        }))
        // Desktop updater, process control, global hotkeys and autostart.
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec![commands::system::AUTOSTART_ARG]),
        ));
    builder.setup(|app| {"""
    replace_once(lib, "    tauri::Builder::default()\n        .plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {\n            cli::forward_second_start(app, &argv);\n            tray::show_main(app);\n        }))\n        .plugin(navguard::init())\n        .plugin(tauri_plugin_deep_link::init())\n        // Tauri auto-update plugin. The address and the public signing key are in tauri.conf.json. Our own signature check code is in engine/core/selfupdate.rs.\n        .plugin(tauri_plugin_updater::Builder::new().build())\n        .plugin(tauri_plugin_process::init())\n        .plugin(tauri_plugin_clipboard_manager::init())\n        // Only one global hotkey is registered: the overlay hotkey (Alt+M by default), see overlay.rs.\n        .plugin(tauri_plugin_global_shortcut::Builder::new().build())\n        // Запуск вместе с системой (06.10.2026): лаунчер живёт в трее, и\n        // напоминания о сундуке и серии есть кому показать.\n        // Autostart with the system. The user turns it on with a switch in settings.\n        .plugin(tauri_plugin_autostart::init(\n            tauri_plugin_autostart::MacosLauncher::LaunchAgent,\n            Some(vec![commands::system::AUTOSTART_ARG]),\n        ))\n        .setup(|app| {",
        "    let builder = tauri::Builder::default()\n        .plugin(navguard::init())\n        .plugin(tauri_plugin_deep_link::init())\n        .plugin(tauri_plugin_clipboard_manager::init());\n    #[cfg(not(target_os = \\"android\\"))]\n    let builder = builder\n        .plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {\n            cli::forward_second_start(app, &argv);\n            tray::show_main(app);\n        }))\n        // Desktop updater, process control, global hotkeys and autostart.\n        .plugin(tauri_plugin_updater::Builder::new().build())\n        .plugin(tauri_plugin_process::init())\n        .plugin(tauri_plugin_global_shortcut::Builder::new().build())\n        .plugin(tauri_plugin_autostart::init(\n            tauri_plugin_autostart::MacosLauncher::LaunchAgent,\n            Some(vec![commands::system::AUTOSTART_ARG]),\n        ));\n    builder.setup(|app| {")
    # The exact block above is anchored separately, so verify no unpatched desktop chain remains.
    patched = lib.read_text(encoding="utf-8")
    if "tauri::Builder::default()\n        .plugin(tauri_plugin_single_instance" in patched:
        raise SystemExit("lib.rs: desktop plugin chain was not replaced")

    # Desktop-only startup helpers are gated; mobile still attaches its one main window.
    replace_once(lib, "            update_start::run(app.handle(), shown_after_update);",
                 "            #[cfg(not(target_os = \\"android\\"))]\n            update_start::run(app.handle(), shown_after_update);")
    replace_once(lib, "    packdrop::watch(app);\n    display::watch(app);",
                 "    #[cfg(not(target_os = \\"android\\"))]\n    {\n        packdrop::watch(app);\n        display::watch(app);\n    }")

    # rfd dialogs are still desktop-only for this first compile pass. The Android
    # picker/SAF implementation is a separate adapter, not a desktop path shim.
    system = src / "commands/system.rs"
    for fn_name, signature, stub in [
        ("autostart_state",
         "pub fn autostart_state(app: tauri::AppHandle) -> Result<bool, String> {",
         "pub fn autostart_state(_app: tauri::AppHandle) -> Result<bool, String> { Ok(false) }"),
        ("autostart_set",
         "pub fn autostart_set(app: tauri::AppHandle, on: bool) -> Result<bool, String> {",
         "pub fn autostart_set(_app: tauri::AppHandle, _on: bool) -> Result<bool, String> { Ok(false) }"),
    ]:
        text = system.read_text(encoding="utf-8")
        if text.count(signature) != 1:
            raise SystemExit(f"system.rs: cannot find {fn_name}")
        # Keep the original full desktop function, prepend cfg to its command attribute.
        text = text.replace("#[tauri::command]\n" + signature,
                            "#[cfg(not(target_os = \\"android\\"))]\n#[tauri::command]\n" + signature, 1)
        # Append mobile stub after the end of this function by using the next stable section marker.
        marker = "/// Hardware and OS facts only, nothing identifying the user." if fn_name == "autostart_set" else "/// Включить или выключить запуск вместе с системой; ответ — что вышло на деле."
        if fn_name == "autostart_state":
            # Insert stub immediately before the following autostart_set docs.
            insertion = "#[cfg(target_os = \\"android\\")]\n#[tauri::command]\n" + stub + "\n\n"
            text = text.replace(marker, insertion + marker, 1)
        else:
            # Insert stub before DeviceSpecs, after the desktop function.
            marker2 = "/// Hardware and OS facts only, nothing identifying the user."
            insertion = "#[cfg(target_os = \\"android\\")]\n#[tauri::command]\n" + stub + "\n\n"
            text = text.replace(marker2, insertion + marker2, 1)
        system.write_text(text, encoding="utf-8")

    write(src / "app_icon_mobile.rs", """use tauri::AppHandle;\n\n#[tauri::command]\npub fn set_app_icon(_app: AppHandle, _id: String) -> Result<(), String> { Ok(()) }\n\n#[cfg(debug_assertions)]\npub fn apply_from_env(_app: &AppHandle) {}\n""")

    write(src / "discord_mobile.rs", r'''use serde::Serialize;

#[derive(Clone, Default)]
pub struct Presence {
    pub details: String,
    pub state: String,
    pub playing: bool,
    pub large_image: String,
    pub large_text: String,
    pub join_url: String,
    pub profile_slug: String,
}

#[derive(Clone, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DiscordStatus {
    pub connected: bool,
    pub app_id: String,
    pub last_error: String,
    pub last_activity: String,
    #[serde(rename = "userId")]
    pub user_id: String,
}

pub fn status() -> DiscordStatus { DiscordStatus::default() }
pub async fn set_activity(_presence: Presence) {}
pub async fn reconnect() {}
pub async fn clear() {}
''')

    write(src / "tray_mobile.rs", r'''use tauri::AppHandle;

pub const LAST_BUILD_PREF: &str = "tray-last-build";
pub fn available() -> bool { false }
pub fn relabel() {}
pub fn set_status(_status: Option<&'static str>) {}
pub fn set_update(_version: Option<&str>) {}
pub fn set_last_build(_build: &str) -> Result<(), String> { Ok(()) }
pub fn show_main(app: &AppHandle) { if let Some(w) = app.get_webview_window("main") { let _ = w.show(); let _ = w.set_focus(); } }
pub fn set_restore_on_exit(_on: bool) {}
pub fn restore_after_game(app: &AppHandle) { show_main(app); }
pub fn main_visible(app: &AppHandle) -> bool { app.get_webview_window("main").is_some_and(|w| w.is_visible().unwrap_or(false)) }
pub fn hide_main(app: &AppHandle) { if let Some(w) = app.get_webview_window("main") { let _ = w.hide(); } }
pub fn init(_app: &AppHandle) {}
''')

    write(src / "overlay_mobile.rs", r'''use serde_json::Value;
use tauri::{AppHandle, Emitter};

pub const LABEL: &str = "overlay";
pub const DEFAULT_HOTKEY: &str = "";
pub const RELAY_EVENT: &str = "realtime-relay";
pub const DEFAULT_CARD_MS: u64 = 9_000;
pub const MIN_CARD_MS: u64 = 3_000;
pub const MAX_CARD_MS: u64 = 30_000;

pub fn enabled() -> bool { false }
pub fn toasts_enabled() -> bool { true }
pub fn clamp_card_ms(ms: u64) -> u64 { ms.clamp(MIN_CARD_MS, MAX_CARD_MS) }
pub fn card_ms() -> u64 { DEFAULT_CARD_MS }
pub fn set_card_ms(_ms: u64) -> Result<(), String> { Ok(()) }
pub fn hotkey() -> String { String::new() }
pub fn set_hit_areas(_rects: Vec<[f64; 4]>) {}
pub fn show(_app: &AppHandle, _interactive: bool) -> Result<bool, String> { Ok(false) }
pub fn hide(_app: &AppHandle) {}
pub fn cleared(_seq: u64) {}
pub fn drain_pending(_app: &AppHandle) {}
pub async fn notify(_app: &AppHandle, _payload: Value) -> Result<(), String> { Ok(()) }
pub fn rebind_hotkey(_app: &AppHandle) {}
pub fn open_card(app: &AppHandle, payload: Value, _to_launcher: bool) -> Result<(), String> {
    app.emit("overlay-open", payload).map_err(|e| e.to_string())
}
pub fn main_unloaded(_app: &AppHandle) {}
pub fn toggle(app: &AppHandle) { if let Some(w) = app.get_webview_window("main") { let _ = w.show(); let _ = w.set_focus(); } }
pub fn relay_realtime(app: &AppHandle, payload: Value) { let _ = app.emit(RELAY_EVENT, payload); }
pub fn relay_state(_app: &AppHandle) -> (bool, bool) { (false, true) }
''')

    # Capabilities: desktop window/tray and updater APIs are not granted to Android.
    default_cap = root / "src-tauri/capabilities/default.json"
    default = default_cap.read_text(encoding="utf-8")
    if '"platforms"' not in default:
        default = default.replace('"identifier": "default",',
                                  '"identifier": "default",\n  "platforms": ["windows", "linux", "macOS"],', 1)
    default_cap.write_text(default, encoding="utf-8")
    overlay_cap = root / "src-tauri/capabilities/overlay.json"
    overlay = overlay_cap.read_text(encoding="utf-8")
    if '"platforms"' not in overlay:
        overlay = overlay.replace('"identifier": "overlay",',
                                  '"identifier": "overlay",\n  "platforms": ["windows", "linux", "macOS"],', 1)
    overlay_cap.write_text(overlay, encoding="utf-8")
    write(root / "src-tauri/capabilities/mobile.json", """{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "mobile",
  "description": "Millida Launcher main Android window",
  "platforms": ["android"],
  "windows": ["main"],
  "permissions": [
    "core:event:allow-listen",
    "core:event:allow-unlisten",
    "clipboard-manager:allow-write-text",
    "deep-link:allow-get-current",
    "main-commands"
  ]
}
""")

    # A mobile window uses the same frontend bundle, without desktop dimensions.
    write(root / "src-tauri/tauri.android.conf.json", """{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "Launcher Android Port",
  "version": "2.2.0",
  "identifier": "net.tatarhost.millida.android",
  "app": {
    "windows": [
      {
        "label": "main",
        "title": "Launcher Android Port",
        "width": 420,
        "height": 900,
        "resizable": true,
        "fullscreen": false
      }
    ]
  },
  "bundle": {
    "active": true,
    "android": {
      "minSdkVersion": 24
    }
  }
}
""")

    print("Prepared pinned Millida source for the first Android Tauri compile.")
    print("The original React frontend and Rust engine remain the application; desktop tray/overlay/Discord are mobile stubs.")
    print("Minecraft Java launch and Android SAF are not implemented by this compile adapter yet.")

if __name__ == "__main__":
    main()
