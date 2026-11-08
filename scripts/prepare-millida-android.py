#!/usr/bin/env python3
"""Patch a pinned Millida Launcher checkout for the first Tauri Android compile."""
from pathlib import Path
import re
import subprocess
import sys

EXPECTED = "a9cec042ad1515a495a4f7c550e71f7423b65812"

def once(text: str, old: str, new: str, where: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{where}: expected one source anchor, found {count}: {old[:100]!r}")
    return text.replace(old, new, 1)

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def gate_command(source: str, signature: str, mobile_stub: str, where: str) -> str:
    if source.count(signature) != 1:
        raise SystemExit(f"{where}: command signature not found exactly once")
    fn_start = source.index(signature)
    attr_start = source.rfind("#[tauri::command]", 0, fn_start)
    if attr_start < 0 or source[attr_start:fn_start].strip().splitlines()[0] != "#[tauri::command]":
        raise SystemExit(f"{where}: command attribute not found")
    start = attr_start
    end = source.index("\n}\n", fn_start) + 3
    original = source[start:end]
    mobile = (
        "#[cfg(target_os = \"android\")]\n"
        "#[tauri::command]\n"
        + mobile_stub + "\n"
    )
    return source[:start] + "#[cfg(not(target_os = \"android\"))]\n" + original + "\n" + mobile + source[end:]

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare-millida-android.py <millida-launcher-checkout>")
    root = Path(sys.argv[1]).resolve()
    actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if actual != EXPECTED:
        raise SystemExit(f"Unexpected Millida source revision {actual}; expected {EXPECTED}")

    cargo = root / "src-tauri/Cargo.toml"
    c = cargo.read_text(encoding="utf-8")
    c = once(
        c,
        'tauri = { version = "2", features = ["protocol-asset", "tray-icon", "macos-private-api"] }',
        'tauri = { version = "2", features = ["protocol-asset"] }',
        "Cargo.toml",
    )
    desktop_lines = [
        'tauri-plugin-updater = "2"\n',
        'tauri-plugin-process = "2"\n',
        'tauri-plugin-autostart = "~2.5.1"\n',
        'tauri-plugin-single-instance = { version = "2", features = ["deep-link"] }\n',
        'tauri-plugin-global-shortcut = "2.3.2"\n',
        'discord-rich-presence = "0.2"\n',
        'rfd = "0.15"\n',
    ]
    for line in desktop_lines:
        c = once(c, line, "", "Cargo.toml desktop dependency move")
    desktop_block = """[target.'cfg(not(target_os = "android"))'.dependencies]
tauri = { version = "2", features = ["tray-icon", "macos-private-api"] }
""" + "".join(desktop_lines) + "\n"
    c = once(c, "[target.'cfg(windows)'.dependencies]", desktop_block + "[target.'cfg(windows)'.dependencies]", "Cargo.toml")
    cargo.write_text(c, encoding="utf-8")

    src = root / "src-tauri/src"
    lib_path = src / "lib.rs"
    lib = lib_path.read_text(encoding="utf-8")
    module_pairs = [
        ("mod app_icon;\n", '#[cfg(not(target_os = "android"))]\nmod app_icon;\n#[cfg(target_os = "android")]\n#[path = "app_icon_mobile.rs"]\nmod app_icon;\n'),
        ("mod discord;\n", '#[cfg(not(target_os = "android"))]\nmod discord;\n#[cfg(target_os = "android")]\n#[path = "discord_mobile.rs"]\nmod discord;\n'),
        ("pub mod tray;\n", '#[cfg(not(target_os = "android"))]\npub mod tray;\n#[cfg(target_os = "android")]\n#[path = "tray_mobile.rs"]\npub mod tray;\n'),
        ("mod overlay;\n", '#[cfg(not(target_os = "android"))]\nmod overlay;\n#[cfg(target_os = "android")]\n#[path = "overlay_mobile.rs"]\nmod overlay;\n'),
        ("mod update_start;\n", '#[cfg(not(target_os = "android"))]\nmod update_start;\n'),
    ]
    for old, new in module_pairs:
        lib = once(lib, old, new, "lib.rs module selection")

    old_builder = """    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {
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
    new_builder = """    let builder = tauri::Builder::default()
        .plugin(navguard::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_clipboard_manager::init());
    #[cfg(not(target_os = "android"))]
    let builder = builder
        .plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {
            cli::forward_second_start(app, &argv);
            tray::show_main(app);
        }))
        // Desktop-only updater, process control, global hotkeys and autostart.
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec![commands::system::AUTOSTART_ARG]),
        ));
    builder.setup(|app| {"""
    lib = once(lib, old_builder, new_builder, "lib.rs plugin builder")
    lib = once(
        lib,
        "            update_start::run(app.handle(), shown_after_update);",
        '            #[cfg(not(target_os = "android"))]\n            update_start::run(app.handle(), shown_after_update);',
        "lib.rs updater setup",
    )
    lib = once(
        lib,
        "    packdrop::watch(app);\n    display::watch(app);",
        '#[cfg(not(target_os = "android"))]\n    {\n        packdrop::watch(app);\n        display::watch(app);\n    }',
        "lib.rs attach_main desktop hooks",
    )
    lib = once(
        lib,
        "            uiwatch::watch(app.handle());\n            overlay::rebind_hotkey(app.handle());",
        '#[cfg(not(target_os = "android"))]\n            {\n                uiwatch::watch(app.handle());\n                overlay::rebind_hotkey(app.handle());\n            }',
        "lib.rs desktop watchers",
    )
    lib_path.write_text(lib, encoding="utf-8")

    # These modules are nested under engine::core, not the crate root.
    core_dir = src / "engine/core"
    core_mod_path = core_dir / "mod.rs"
    core_mod = core_mod_path.read_text(encoding="utf-8")
    core_mod = once(core_mod, "mod selfheal;\n", '#[cfg(not(target_os = "android"))]\nmod selfheal;\n#[cfg(target_os = "android")]\n#[path = "selfheal_mobile.rs"]\nmod selfheal;\n', "engine/core/mod.rs selfheal module")
    core_mod = once(core_mod, "mod dialogs;\n", '#[cfg(not(target_os = "android"))]\nmod dialogs;\n#[cfg(target_os = "android")]\n#[path = "dialogs_mobile.rs"]\nmod dialogs;\n', "engine/core/mod.rs dialogs module")
    core_mod_path.write_text(core_mod, encoding="utf-8")

    # Autostart is not a launcher setting on Android; expose the same commands
    # to the original UI but return a truthful disabled state.
    system_path = src / "commands/system.rs"
    system = system_path.read_text(encoding="utf-8")
    system = gate_command(
        system,
        "pub fn autostart_state(app: tauri::AppHandle) -> Result<bool, String> {",
        "pub fn autostart_state(_app: tauri::AppHandle) -> Result<bool, String> { Ok(false) }",
        "autostart_state",
    )
    system = gate_command(
        system,
        "pub fn autostart_set(app: tauri::AppHandle, on: bool) -> Result<bool, String> {",
        "pub fn autostart_set(_app: tauri::AppHandle, _on: bool) -> Result<bool, String> { Ok(false) }",
        "autostart_set",
    )
    system_path.write_text(system, encoding="utf-8")

    # Android has no desktop global shortcuts. Keep the Windows implementation
    # intact and compile a no-op binder on mobile (rewind itself is unsupported there).
    rewind_path = src / "engine/rewind/mod.rs"
    rewind = rewind_path.read_text(encoding="utf-8")
    rewind = once(
        rewind,
        "fn bind_hotkey(app: &AppHandle) {",
        '#[cfg(not(target_os = "android"))]\\nfn bind_hotkey(app: &AppHandle) {',
        "rewind desktop hotkey binder",
    )
    rewind = once(
        rewind,
        "/// Recording of one running game; dropping it stops the capture.",
        '#[cfg(target_os = "android")]\\nfn bind_hotkey(_app: &AppHandle) {}\\n\\n/// Recording of one running game; dropping it stops the capture.',
        "rewind Android hotkey binder",
    )
    rewind_path.write_text(rewind, encoding="utf-8")

    # Android cannot minimize/center native desktop webviews. External links are
    # handed to Android's URL handler instead of creating a second Tauri window.
    external_path = src / "engine/core/external.rs"
    external = external_path.read_text(encoding="utf-8")
    external = once(external, "fn open_in_app(app: &AppHandle, url: &url::Url) -> Result<(), String> {", '#[cfg(not(target_os = "android"))]\\nfn open_in_app(app: &AppHandle, url: &url::Url) -> Result<(), String> {', "external desktop window")
    external = once(external, "#[cfg(not(windows))]\\nfn open_resolved", '#[cfg(target_os = "android")]\\nfn open_in_app(_app: &AppHandle, url: &url::Url) -> Result<(), String> {\\n    tauri_plugin_opener::open_url(url.as_str(), None::<&str>).map_err(|e| e.to_string())\\n}\\n\\n#[cfg(not(windows))]\\nfn open_resolved', "external Android URL handler")
    external_path.write_text(external, encoding="utf-8")

    # Android is Unix-like but has no Linux machine-id file. The per-install
    # random device.key already provides the secret entropy; add a stable app
    # namespace so the vault key derivation has an Android-specific binding.
    secrets_path = src / "secrets.rs"
    secrets = secrets_path.read_text(encoding="utf-8")
    secrets = once(secrets, "#[cfg(windows)]\\nfn machine_binding() -> Vec<u8> {", '#[cfg(target_os = "android")]\\nfn machine_binding() -> Vec<u8> {\\n    b"net.tatarhost.millida.android".to_vec()\\n}\\n\\n#[cfg(windows)]\\nfn machine_binding() -> Vec<u8> {', "Android machine binding")
    secrets_path.write_text(secrets, encoding="utf-8")

    # rfd has no Android backend. These stubs preserve the core API surface;
    # Storage Access Framework integration remains a separate implementation task.
    write(core_dir / "dialogs_mobile.rs", """use std::path::{Path, PathBuf};
use tauri::AppHandle;

#[derive(Clone, Default)]
pub struct MobileDialog;
impl MobileDialog {
    pub fn add_filter<T: AsRef<str>, U: AsRef<str>>(self, _name: T, _extensions: &[U]) -> Self { self }
    pub fn set_title<T: AsRef<str>>(self, _title: T) -> Self { self }
    pub fn set_directory<T: AsRef<Path>>(self, _path: T) -> Self { self }
    pub fn set_file_name<T: AsRef<str>>(self, _name: T) -> Self { self }
}
pub fn arm_dialogs(_app: &AppHandle) {}
pub fn dialog() -> MobileDialog { MobileDialog }
pub async fn pick_file(_dialog: MobileDialog) -> Option<PathBuf> { None }
pub async fn pick_files(_dialog: MobileDialog) -> Option<Vec<PathBuf>> { None }
pub async fn pick_folder(_dialog: MobileDialog) -> Option<PathBuf> { None }
pub async fn save_file(_dialog: MobileDialog) -> Option<PathBuf> { None }
""")

    write(core_dir / "selfheal_mobile.rs", """use tauri::AppHandle;
pub fn mark_frontend_ready() {}
pub fn arm_selfheal(_app: &AppHandle) {}
""")

    # Native confirmation dialogs are not available in the first Android probe.
    hooks_path = src / "engine/game/launch_hooks.rs"
    hooks = hooks_path.read_text(encoding="utf-8")
    hooks = once(hooks, "pub async fn set_launch_hooks(profile: String, hooks: LaunchHooks) -> Result<bool, String> {", '#[cfg(not(target_os = "android"))]\npub async fn set_launch_hooks(profile: String, hooks: LaunchHooks) -> Result<bool, String> {', "launch_hooks desktop function")
    hooks = once(hooks, "\nfn hook_command(line: &str, game_dir: &Path, profile: &str) -> Option<Command> {", '\n#[cfg(target_os = "android")]\npub async fn set_launch_hooks(_profile: String, _hooks: LaunchHooks) -> Result<bool, String> {\n    Err("Подтверждение системным диалогом пока недоступно на Android".into())\n}\n\nfn hook_command(line: &str, game_dir: &Path, profile: &str) -> Option<Command> {', "launch_hooks Android function")
    hooks_path.write_text(hooks, encoding="utf-8")

    write(src / "app_icon_mobile.rs", """use tauri::AppHandle;

#[tauri::command]
pub fn set_app_icon(_app: AppHandle, _id: String) -> Result<(), String> { Ok(()) }

#[cfg(debug_assertions)]
pub fn apply_from_env(_app: &AppHandle) {}
""")

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

    write(src / "tray_mobile.rs", r'''use tauri::{AppHandle, Manager};

pub const LAST_BUILD_PREF: &str = "tray-last-build";
pub fn available() -> bool { false }
pub fn relabel() {}
pub fn set_status(_status: Option<&'static str>) {}
pub fn set_update(_version: Option<&str>) {}
pub fn set_last_build(_build: &str) -> Result<(), String> { Ok(()) }
pub fn show_main(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.set_focus();
    }
}
pub fn set_restore_on_exit(_on: bool) {}
pub fn restore_after_game(app: &AppHandle) { show_main(app); }
pub fn main_visible(app: &AppHandle) -> bool {
    app.get_webview_window("main").is_some_and(|w| w.is_visible().unwrap_or(false))
}
pub fn hide_main(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") { let _ = w.hide(); }
}
pub fn init(_app: &AppHandle) {}
''')

    write(src / "overlay_mobile.rs", r'''use serde_json::Value;
use tauri::{AppHandle, Emitter, Manager};

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
pub fn toggle(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.set_focus();
    }
}
pub fn relay_realtime(app: &AppHandle, payload: Value) { let _ = app.emit(RELAY_EVENT, payload); }
pub fn relay_state(_app: &AppHandle) -> (bool, bool) { (false, true) }
''')

    # Desktop-only capabilities must not grant updater/overlay permissions to
    # an Android webview. The existing main-commands set is kept unchanged.
    default_cap = root / "src-tauri/capabilities/default.json"
    default = default_cap.read_text(encoding="utf-8")
    if '"platforms"' not in default:
        default = once(default, '"identifier": "default",',
                       '"identifier": "default",\n  "platforms": ["windows", "linux", "macOS"],',
                       "default capability")
    default_cap.write_text(default, encoding="utf-8")

    overlay_cap = root / "src-tauri/capabilities/overlay.json"
    overlay = overlay_cap.read_text(encoding="utf-8")
    if '"platforms"' not in overlay:
        overlay = once(overlay, '"identifier": "overlay",',
                       '"identifier": "overlay",\n  "platforms": ["windows", "linux", "macOS"],',
                       "overlay capability")
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

    # The mobile shell keeps the upstream web frontend. Bundle identity is
    # distinct because the upstream trademark policy forbids redistributing a
    # third-party build as the official Millida Launcher.
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

    print("Prepared pinned Millida React/Rust source for Android Tauri compilation.")
    print("Desktop tray, Discord RPC, secondary overlay and desktop updater startup are excluded/stubbed.")
    print("Android SAF and in-process Minecraft Java/JNI are not implemented by this first compile adapter.")

if __name__ == "__main__":
    main()
