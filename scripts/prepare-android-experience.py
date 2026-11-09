#!/usr/bin/env python3
"""Prepare an Android-first CHEATLAB fork of the pinned Millida launcher source."""
from pathlib import Path
import json
import math
import struct
import subprocess
import sys
import zlib

EXPECTED = "a9cec042ad1515a495a4f7c550e71f7423b65812"

def replace_once(source: str, old: str, new: str, where: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{where}: expected one anchor, found {count}: {old[:120]!r}")
    return source.replace(old, new, 1)

def put(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)

def make_icon(path: Path, size: int = 1024, transparent: bool = False) -> None:
    pixels = bytearray(size * size * 4)
    cx = cy = size / 2
    radius = size * 0.62
    for y in range(size):
        for x in range(size):
            if transparent:
                continue
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radius
            glow = max(0.0, 1.0 - d) * 9.0
            i = (y * size + x) * 4
            pixels[i:i+4] = bytes((int(13 + glow * 0.45), int(20 + glow * 0.75), int(16 + glow * 0.5), 255))

    # Original CHEATLAB "C" mark; no upstream Millida artwork is reused.
    polygon = [
        (770, 270), (770, 400), (440, 400), (350, 470),
        (350, 554), (440, 624), (770, 624), (770, 754),
        (388, 754), (210, 600), (210, 424), (388, 270),
    ]
    scale = size / 1024
    polygon = [(round(x * scale), round(y * scale)) for x, y in polygon]
    min_y = min(p[1] for p in polygon)
    max_y = max(p[1] for p in polygon)
    for y in range(min_y, max_y):
        crossings = []
        for n in range(len(polygon)):
            x1, y1 = polygon[n]
            x2, y2 = polygon[(n + 1) % len(polygon)]
            if (y1 <= y < y2) or (y2 <= y < y1):
                crossings.append(int(x1 + (y - y1) * (x2 - x1) / (y2 - y1)))
        crossings.sort()
        for j in range(0, len(crossings) - 1, 2):
            left, right = crossings[j], crossings[j + 1]
            for x in range(left, right):
                i = (y * size + x) * 4
                pixels[i:i+4] = bytes((142, 232, 168, 255))

    rows = []
    stride = size * 4
    for y in range(size):
        rows.append(b"\x00" + pixels[y * stride:(y + 1) * stride])
    raw = b"".join(rows)
    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    data += png_chunk(b"IDAT", zlib.compress(raw, 9))
    data += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare-android-experience.py <millida-checkout>")
    root = Path(sys.argv[1]).resolve()
    rev = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if rev != EXPECTED:
        raise SystemExit(f"Unexpected source revision {rev}; expected {EXPECTED}")

    # This is a separately branded fork, not an official Millida distribution.
    config_path = root / "src-tauri/tauri.android.conf.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["productName"] = "CHEATLAB Launcher"
    config["identifier"] = "fun.cheatlab.launcher"
    config["app"]["windows"][0]["title"] = "CHEATLAB Launcher"
    config["plugins"] = {
        "deep-link": {
            "mobile": [
                {"scheme": ["tatarlauncher"], "appLink": False}
            ]
        }
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    icon_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="15" fill="#0d1410"/>
  <path d="M49 13H31L13 28v8l18 15h18V40H34l-8-7 8-7h15z" fill="#8ee8a8"/>
</svg>
"""
    put(root / "public/cheatlab-logo.svg", icon_svg)
    put(root / "public/favicon.svg", icon_svg)
    make_icon(root / "src-tauri/icons/icon.png")
    for density, base in [("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)]:
        folder = root / "src-tauri/icons/android" / f"mipmap-{density}"
        make_icon(folder / "ic_launcher.png", base)
        make_icon(folder / "ic_launcher_round.png", base)
        make_icon(folder / "ic_launcher_foreground.png", int(base * 2.25), transparent=True)
    put(root / "src-tauri/icons/android/values/ic_launcher_background.xml",
        '<resources><color name="ic_launcher_background">#0D1410</color></resources>\n')

    index_path = root / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = replace_once(index, 'content="width=device-width, initial-scale=1"', 'content="width=device-width, initial-scale=1, viewport-fit=cover"', "index viewport")
    index = replace_once(index, "<title>Millida Launcher</title>", "<title>CHEATLAB Launcher · based on Millida</title>", "index title")
    index = replace_once(index, 'src="/millida-logo.svg"', 'src="/cheatlab-logo.svg"', "boot logo")
    index_path.write_text(index, encoding="utf-8")

    # Replace the original Millida-only web login with the user's CHEATLAB
    # device approval flow. Game-account login (Microsoft / offline) remains
    # a separate step and continues to use the upstream game-account UI.
    put(root / "src/components/CheatLabLogin.tsx", r'''import { useEffect, useRef, useState } from 'react'
import { Icon } from './Icon'
import { useT } from '../i18n'
import {
  cheatLabDeviceInit,
  cheatLabDevicePoll,
  cheatLabKeyLoginStart,
  cheatLabKeyLoginVerify,
  cheatLabSessionStatus,
} from '../ipc/cheatlab'
import { openUrl } from '../ipc/commands'

type Mode = 'site' | 'key'
type KeyChallenge = { challengeId: string; email?: string; expiresAt?: number }

export function CheatLabLogin({ onAuthenticated }: { onAuthenticated: () => void }) {
  const t = useT()
  const [mode, setMode] = useState<Mode>('site')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('Войди или зарегистрируйся на cheatlab.fun — приложение вернётся сюда автоматически.')
  const [verifyUrl, setVerifyUrl] = useState('')
  const [key, setKey] = useState('')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [challenge, setChallenge] = useState<KeyChallenge | null>(null)
  const deviceRef = useRef<string>('')
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    const checkSession = () => {
      void cheatLabSessionStatus().then((user) => {
        if (alive.current && user) onAuthenticated()
      }).catch(() => {})
    }
    const onResume = () => checkSession()
    checkSession()
    window.addEventListener('cheatlab:resume', onResume)
    return () => {
      alive.current = false
      window.removeEventListener('cheatlab:resume', onResume)
    }
  }, [])

  const startSiteLogin = async () => {
    setBusy(true)
    setStatus('Создаём защищённую ссылку CHEATLAB…')
    try {
      const init = await cheatLabDeviceInit()
      deviceRef.current = init.deviceCode
      setVerifyUrl(init.verificationUrl)
      setStatus('Открой ссылку, войди или зарегистрируйся на CHEATLAB. После подтверждения приложение подключится само.')
      await openUrl(init.verificationUrl)
      const deadline = Date.now() + Math.max(30, init.expiresInSec || 300) * 1000
      const poll = async (): Promise<void> => {
        if (!alive.current) return
        if (Date.now() > deadline) {
          setBusy(false)
          setStatus('Ссылка истекла. Нажми кнопку ещё раз, чтобы создать новую.')
          return
        }
        try {
          const result = await cheatLabDevicePoll(deviceRef.current)
          if (!alive.current) return
          if (result.status === 'ok') {
            setStatus('CHEATLAB подключён. Открываем выбор игрового аккаунта…')
            setBusy(false)
            onAuthenticated()
            return
          }
          if (result.status === 'expired' || result.status === 'denied') {
            setBusy(false)
            setStatus(result.status === 'expired' ? 'Время ссылки истекло. Создай новую.' : 'Подключение отменено на сайте.')
            return
          }
        } catch (error) {
          if (!alive.current) return
          setStatus(String(error))
        }
        window.setTimeout(() => { void poll() }, 1900)
      }
      window.setTimeout(() => { void poll() }, 1200)
    } catch (error) {
      setBusy(false)
      setStatus('Не удалось открыть CHEATLAB: ' + String(error))
    }
  }

  const startKeyLogin = async () => {
    if (!key.trim()) {
      setStatus('Вставь ключ аккаунта CHEATLAB.')
      return
    }
    setBusy(true)
    setStatus('Проверяем ключ и отправляем код подтверждения…')
    try {
      const result = await cheatLabKeyLoginStart(key.trim(), email.trim() || undefined)
      if (result.verificationRequired && result.challengeId) {
        setChallenge({ challengeId: result.challengeId, email: result.email, expiresAt: result.expiresAt })
        setStatus(result.email ? 'Код отправлен на ' + result.email : 'Код отправлен на почту аккаунта.')
      } else if (result.user) {
        setBusy(false)
        onAuthenticated()
      } else {
        setStatus('Сервер не вернул подтверждение входа.')
      }
    } catch (error) {
      setStatus(String(error))
      setBusy(false)
    }
  }

  const verifyKeyLogin = async () => {
    if (!challenge || !code.trim()) {
      setStatus('Введи код из письма.')
      return
    }
    setBusy(true)
    setStatus('Подтверждаем вход…')
    try {
      await cheatLabKeyLoginVerify(challenge.challengeId, code.trim())
      setChallenge(null)
      setBusy(false)
      onAuthenticated()
    } catch (error) {
      setStatus(String(error))
      setBusy(false)
    }
  }

  return (
    <section className="login-form lg2-card cl-login-card">
      <div className="cl-login-brand"><span className="cl-login-mark">C</span><span>CHEATLAB</span></div>
      <h1>{t('Вход в CHEATLAB')}</h1>
      <p className="sub">Аккаунт сайта сохраняется в приложении. Для игры Minecraft затем отдельно подключи Microsoft или офлайн-ник.</p>
      <div className="cl-login-tabs">
        <button className={'btn sm ' + (mode === 'site' ? 'primary' : 'secondary')} onClick={() => { setMode('site'); setChallenge(null); }}>
          По ссылке
        </button>
        <button className={'btn sm ' + (mode === 'key' ? 'primary' : 'secondary')} onClick={() => { setMode('key'); setChallenge(null); }}>
          По ключу
        </button>
      </div>
      {mode === 'site' ? (
        <>
          <button className="btn lg primary lg2-main" disabled={busy} onClick={() => void startSiteLogin()}>
            <Icon id="i-shield" /> {busy ? 'Ожидаем подтверждение…' : 'Войти или зарегистрироваться на сайте'}
          </button>
          {verifyUrl ? <button className="btn sm secondary" onClick={() => void openUrl(verifyUrl)}>Открыть ссылку снова</button> : null}
          <a className="cl-login-link" href="https://cheatlab.fun" onClick={(e) => { e.preventDefault(); void openUrl('https://cheatlab.fun'); }}>Открыть cheatlab.fun</a>
        </>
      ) : (
        <>
          {challenge ? (
            <>
              <label className="cl-login-label">Код из письма</label>
              <input className="input" value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="Код подтверждения" />
              <button className="btn lg primary lg2-main" disabled={busy} onClick={() => void verifyKeyLogin()}>Подтвердить ключ</button>
            </>
          ) : (
            <>
              <label className="cl-login-label">Ключ аккаунта CHEATLAB</label>
              <textarea className="input cl-login-key" rows={3} value={key} onChange={(e) => setKey(e.target.value)} placeholder="clab2-…" autoCapitalize="none" autoCorrect="off" />
              <label className="cl-login-label">Почта (только если сайт попросит)</label>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} inputMode="email" autoComplete="email" placeholder="name@example.com" />
              <button className="btn lg primary lg2-main" disabled={busy} onClick={() => void startKeyLogin()}>Продолжить по ключу</button>
              <a className="cl-login-link" href="https://cheatlab.fun/launcher-key.html" onClick={(e) => { e.preventDefault(); void openUrl('https://cheatlab.fun/launcher-key.html'); }}>Создать ключ на сайте</a>
            </>
          )}
        </>
      )}
      <div className="cl-login-status" role="status" aria-live="polite">{status}</div>
      <div className="cl-login-trust"><Icon id="i-shield" /> Пароль вводится только на cheatlab.fun. Приложение хранит отдельную зашифрованную сессию.</div>
    </section>
  )
}
''')

    # Mobile launcher account API stays native: bearer tokens are stored in the
    # existing encrypted Rust vault and are never returned to React.
    put(root / "src-tauri/src/commands/cheatlab.rs", r'''use crate::secrets;
use reqwest::Method;
use serde_json::{json, Value};
use std::time::Duration;

const API: &str = "https://cheatlab.tatarhost.workers.dev";
const CLIENT_KEY: &str = "cheatlab-client-id";
const SESSION_KEY: &str = "cheatlab-session";

fn app_client_id() -> Result<String, String> {
    if let Some(id) = secrets::get(CLIENT_KEY) {
        if id.len() >= 16 && id.len() <= 64 && id.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-') {
            return Ok(id);
        }
    }
    let id = uuid::Uuid::new_v4().simple().to_string();
    secrets::set_many(vec![(CLIENT_KEY.to_string(), id.clone())])?;
    Ok(id)
}

async fn request(
    method: Method,
    path: &str,
    body: Option<Value>,
    session: Option<&str>,
) -> Result<Value, String> {
    let client_id = app_client_id()?;
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(18))
        .user_agent(concat!("CHEATLAB-Launcher/", env!("CARGO_PKG_VERSION")))
        .build()
        .map_err(|e| e.to_string())?;
    let mut req = client
        .request(method, format!("{API}{path}"))
        .header("x-cheatlab-client", client_id);
    if let Some(token) = session {
        req = req.header("x-cheatlab-session", token);
    }
    if let Some(value) = body {
        req = req.json(&value);
    }
    let response = req.send().await.map_err(|e| format!("CHEATLAB: {e}"))?;
    let status = response.status();
    let bytes = response.bytes().await.map_err(|e| e.to_string())?;
    let value: Value = serde_json::from_slice(&bytes)
        .map_err(|_| format!("CHEATLAB API вернул не JSON (HTTP {status})"))?;
    if !status.is_success() {
        return Err(value["error"].as_str().unwrap_or("ошибка CHEATLAB API").to_string());
    }
    Ok(value)
}

fn store_session(value: &Value) -> Result<(), String> {
    let token = value["token"].as_str().filter(|s| s.len() >= 20)
        .ok_or_else(|| "CHEATLAB не вернул токен сессии".to_string())?;
    secrets::set_many(vec![(SESSION_KEY.to_string(), token.to_string())])
}

#[tauri::command]
#[tauri::command]
pub async fn cheatlab_device_init() -> Result<Value, String> {
    let value = request(Method::POST, "/api/app-auth/init", Some(json!({})), None).await?;
    let code = value["deviceCode"].as_str().filter(|s| s.len() >= 20)
        .ok_or_else(|| "CHEATLAB не вернул код устройства".to_string())?;
    secrets::set_many(vec![(PENDING_KEY.to_string(), code.to_string())])?;
    Ok(value)
}

async fn resume_pending_device_login() -> Result<Value, String> {
    let Some(code) = secrets::get(PENDING_KEY) else {
        return Ok(json!({ "user": null }));
    };
    let value = request(
        Method::POST,
        "/api/app-auth/poll",
        Some(json!({ "deviceCode": code })),
        None,
    ).await?;
    if value["token"].is_string() {
        store_session(&value)?;
        secrets::delete(PENDING_KEY)?;
        return Ok(json!({ "user": value["user"] }));
    }
    if value["status"] == "expired" || value["status"] == "denied" {
        let _ = secrets::delete(PENDING_KEY);
    }
    Ok(json!({ "user": null }))
}

#[tauri::command]
pub async fn cheatlab_device_poll(device_code: String) -> Result<Value, String> {
    let value = request(
        Method::POST,
        "/api/app-auth/poll",
        Some(json!({ "deviceCode": device_code })),
        None,
    ).await?;
    if value["token"].is_string() {
        store_session(&value)?;
        secrets::delete(PENDING_KEY)?;
        return Ok(json!({ "status": "ok", "user": value["user"] }));
    }
    if value["status"] == "expired" || value["status"] == "denied" {
        let _ = secrets::delete(PENDING_KEY);
    }
    Ok(value)
}

#[tauri::command]
pub async fn cheatlab_session_status() -> Result<Value, String> {
    if let Some(token) = secrets::get(SESSION_KEY) {
        let value = request(Method::GET, "/api/auth/me", None, Some(&token)).await?;
        if !value["user"].is_null() {
            return Ok(json!({ "user": value["user"] }));
        }
        let _ = secrets::delete(SESSION_KEY);
    }
    resume_pending_device_login().await
}
#[tauri::command]
pub async fn cheatlab_key_login_start(key: String, email: Option<String>) -> Result<Value, String> {
    request(
        Method::POST,
        "/api/auth/keylogin",
        Some(json!({ "key": key, "email": email.unwrap_or_default() })),
        None,
    ).await
}

#[tauri::command]
pub async fn cheatlab_key_login_verify(challenge_id: String, code: String) -> Result<Value, String> {
    let value = request(
        Method::POST,
        "/api/auth/login/verify",
        Some(json!({ "challengeId": challenge_id, "code": code })),
        None,
    ).await?;
    store_session(&value)?;
    Ok(json!({ "user": value["user"] }))
}

#[tauri::command]
pub async fn cheatlab_logout() -> Result<(), String> {
    if let Some(token) = secrets::get(SESSION_KEY) {
        let _ = request(Method::POST, "/api/auth/logout", Some(json!({})), Some(&token)).await;
    }
    secrets::delete(SESSION_KEY)
}
''')

    # Add the native commands to the Tauri command registry.
    cargo_path = root / "src-tauri/Cargo.toml"
    cargo = cargo_path.read_text(encoding="utf-8")
    cargo = replace_once(
        cargo,
        'semver = "1"\n',
        'semver = "1"\nuuid = { version = "1", features = ["v4"] }\n',
        "uuid dependency",
    )
    cargo_path.write_text(cargo, encoding="utf-8")

    mod_path = root / "src-tauri/src/commands/mod.rs"
    mod = mod_path.read_text(encoding="utf-8")
    mod = replace_once(mod, "pub mod accounts;\n", "pub mod accounts;\npub mod cheatlab;\n", "CHEATLAB command module")
    mod_path.write_text(mod, encoding="utf-8")

    lib_path = root / "src-tauri/src/lib.rs"
    lib = lib_path.read_text(encoding="utf-8")
    lib = replace_once(
        lib,
        "            commands::accounts::millida_login_poll,\n",
        """            commands::cheatlab::cheatlab_device_init,
            commands::cheatlab::cheatlab_device_poll,
            commands::cheatlab::cheatlab_session_status,
            commands::cheatlab::cheatlab_key_login_start,
            commands::cheatlab::cheatlab_key_login_verify,
            commands::cheatlab::cheatlab_logout,
            commands::accounts::millida_login_poll,
""",
        "CHEATLAB invoke handler",
    )
    lib_path.write_text(lib, encoding="utf-8")

    # The CHEATLAB IPC bridge is a separate lazy chunk; it keeps the
    # Android-only account implementation out of the initial UI bundle.
    put(root / "src/ipc/cheatlab.ts", r'''import { tauri } from './tauri'

const invoke = <T>(command: string, args?: Record<string, unknown>): Promise<T> => {
  const bridge = tauri()
  if (!bridge) return Promise.reject(new Error('no tauri'))
  return bridge.core.invoke<T>(command, args)
}

export interface CheatLabDeviceInit {
  deviceCode: string
  verificationUrl: string
  expiresInSec: number
}
export const cheatLabDeviceInit = () => invoke<CheatLabDeviceInit>('cheatlab_device_init')
export const cheatLabDevicePoll = (deviceCode: string) =>
  invoke<{status: 'pending' | 'expired' | 'denied' | 'ok'; user?: {id: string; nick: string}}>('cheatlab_device_poll', { deviceCode })
export const cheatLabSessionStatus = async () => {
  const result = await invoke<{user: {id: string; nick: string} | null}>('cheatlab_session_status')
  return result.user
}
export const cheatLabKeyLoginStart = (key: string, email?: string) =>
  invoke<{verificationRequired?: boolean; challengeId?: string; email?: string; expiresAt?: number; user?: {id: string; nick: string}}>('cheatlab_key_login_start', { key, email: email || null })
export const cheatLabKeyLoginVerify = (challengeId: string, code: string) =>
  invoke<{user: {id: string; nick: string}}>('cheatlab_key_login_verify', { challengeId, code })
export const cheatLabLogout = () => invoke<void>('cheatlab_logout')
''')

        # Add the native CHEATLAB login only to Android; the desktop source remains
    # as it was. The user then chooses a Microsoft or offline game account.
    login_path = root / "src/screens/Login.tsx"
    login = login_path.read_text(encoding="utf-8")
    login = replace_once(
        login,
        "import { useEffect, useRef, useState } from 'react'\n",
        "import { lazy, Suspense, useEffect, useRef, useState } from 'react'\n",
        "Android lazy-login React imports",
    )
    login = replace_once(
        login,
        "import { PixelField } from '../components/lobby/PixelField'\n",
        "import { PixelField } from '../components/lobby/PixelField'\nimport { hasTauri } from '../ipc/tauri'\nimport { startGameStep } from '../state/firstRun'\nimport { enterApp } from '../lib/session'\n",
        "Android login imports",
    )
    login = replace_once(
        login,
        "const SAFETY_URL = 'https://millida.net/launcher/bezopasnost'\n",
        "const SAFETY_URL = 'https://millida.net/launcher/bezopasnost'\nconst CheatLabLogin = lazy(() => import('../components/CheatLabLogin').then((m) => ({ default: m.CheatLabLogin })))\n",
        "Lazy-load CHEATLAB login screen",
    )
    login = replace_once(login, "function GameAccountStep() {",
                         "function GameAccountStep({ androidAutoEnter = false }: { androidAutoEnter?: boolean }) {",
                         "Android game account step props")
    login = replace_once(
        login,
        "  useEffect(() => {\n    if (added) finishFirstRun()\n  }, [added])",
        "  useEffect(() => {\n    if (added) { finishFirstRun(); if (androidAutoEnter) enterApp() }\n  }, [added, androidAutoEnter])",
        "Android game account completion",
    )
    login = replace_once(
        login,
        "        {step ? (\n          <GameAccountStep />\n        ) : (\n        <div className=\"login-form lg2-card\">",
        """        {step ? (
          <GameAccountStep androidAutoEnter={hasTauri() && /Android/i.test(navigator.userAgent)} />
        ) : hasTauri() && /Android/i.test(navigator.userAgent) ? (
          <Suspense fallback={null}>
            <CheatLabLogin onAuthenticated={() => startGameStep()} />
          </Suspense>
        ) : (
        <div className="login-form lg2-card">""",
        "Android login screen",
    )
    login_path.write_text(login, encoding="utf-8")

    # Replace every visible upstream launcher mark with the fork's own brand.
    brand_edits = {
        "src/components/Titlebar.tsx": [
            ('src="/millida-logo.svg"', 'src="/cheatlab-logo.svg"'),
            ("MILLIDA LAUNCHER", "CHEATLAB LAUNCHER"),
        ],
        "src/components/BootUpdate.tsx": [
            ('src="/millida-logo.svg"', 'src="/cheatlab-logo.svg"'),
            ("'Millida Launcher'", "'CHEATLAB Launcher'"),
        ],
        "src/components/Welcome.tsx": [
            ('src="/millida-logo.svg"', 'src="/cheatlab-logo.svg"'),
            ("t('в Millida')", "t('в CHEATLAB Launcher')"),
        ],
        "src/modals/Onboarding.tsx": [
            ('src="/millida-logo.svg"', 'src="/cheatlab-logo.svg"'),
            ("переедут в Millida целиком", "переедут в CHEATLAB Launcher целиком"),
        ],
        "src/modals/Settings.tsx": [
            ('src="/millida-logo.svg"', 'src="/cheatlab-logo.svg"'),
            ("<b>Millida Launcher</b>", "<b>CHEATLAB Launcher</b>"),
        ],
        "src/screens/HostingManage.tsx": [
            ("'/millida-logo.svg'", "'/cheatlab-logo.svg'"),
        ],
        "src/styles/12-pixel.css": [
            ("img[src$='/millida-logo.svg']", "img[src$='/cheatlab-logo.svg']"),
        ],
    }
    for relative, edits in brand_edits.items():
        target = root / relative
        source = target.read_text(encoding="utf-8")
        for before, after in edits:
            source = replace_once(source, before, after, f"CHEATLAB branding: {relative}")
        target.write_text(source, encoding="utf-8")

    # Android boot checks the encrypted CHEATLAB session instead of attempting
    # to sign into the upstream Millida service.
    app_path = root / "src/App.tsx"
    app = app_path.read_text(encoding="utf-8")
    app = replace_once(
        app,
        "import { gameStepPending, hasGameAccount, useFirstRun } from './state/firstRun'\n",
        "import { gameStepPending, hasGameAccount, useFirstRun, startGameStep } from './state/firstRun'\n",
        "Android boot first-run import",
    )
    app = replace_once(
        app,
        "import { loadProfileSettings } from './ipc/commands'\n",
        "import { loadProfileSettings } from './ipc/commands'\n",
        "Android boot CHEATLAB status import",
    )
    app = replace_once(
        app,
        "    const decide = (check: SessionCheck, rechecks: number) => {\n      const acc = getAccount()\n",
        """    let androidAuthStarted = false
    const decide = (check: SessionCheck, rechecks: number) => {
      if (!preview && hasTauri() && /Android/i.test(navigator.userAgent)) {
        if (androidAuthStarted) return
        androidAuthStarted = true
        void import('./ipc/cheatlab').then(({ cheatLabSessionStatus }) => cheatLabSessionStatus()).then((user) => {
          if (user && hasGameAccount()) {
            enterApp()
          } else {
            useUi.getState().setLogged(false)
            if (user) startGameStep()
            else useFirstRun.setState({ open: false })
          }
        }).catch(() => {
          useUi.getState().setLogged(false)
          useFirstRun.setState({ open: false })
        })
        return
      }
      const acc = getAccount()
""",
        "Android CHEATLAB startup gate",
    )
    app_path.write_text(app, encoding="utf-8")

    # Keep the existing responsive layout; add the CHEATLAB login-card details.
    main_path = root / "src/main.tsx"
    main = main_path.read_text(encoding="utf-8")
    main = replace_once(
        main,
        "import './styles/13-lite.css'\n",
        "import './styles/13-lite.css'\nimport './styles/android.css'\n",
        "Android responsive stylesheet import",
    )
    main_path.write_text(main, encoding="utf-8")

    put(root / "src/components/AndroidBottomNav.tsx", r'''import { Icon } from './Icon'
import { useT } from '../i18n'
import { useUi, setScreen, type ScreenId } from '../state/ui'

export function AndroidBottomNav() {
  const t = useT()
  const screen = useUi((s) => s.screen)
  const items: { id: ScreenId; label: string; icon: string }[] = [
    { id: 'play', label: t('Играть'), icon: 'i-play' },
    { id: 'builds', label: t('Сборки'), icon: 'i-box' },
    { id: 'mods', label: t('Каталог'), icon: 'i-blocks' },
    { id: 'servers', label: t('Серверы'), icon: 'i-server' },
    { id: 'friends', label: t('Друзья'), icon: 'i-users' },
  ]
  return (
    <nav className="android-bottom-nav" aria-label={t('Основная навигация')}>
      {items.map((item) => {
        const active = screen === item.id || (item.id === 'friends' && screen === 'chat')
          || (item.id === 'builds' && screen === 'playhub')
        return (
          <button key={item.id} type="button" className={'android-bottom-nav__item' + (active ? ' is-active' : '')}
            aria-current={active ? 'page' : undefined}
            onClick={() => { if (item.id === 'mods') void import('../state/mods').then(({ useMods }) => useMods.getState().scopeTo(null)); setScreen(item.id); document.querySelector<HTMLElement>('.content')?.scrollTo(0, 0) }}>
            <Icon id={item.icon} /><span>{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
''')

    app = app_path.read_text(encoding="utf-8")
    app = replace_once(app, "  AccountAddModal,\n",
                       "  AndroidBottomNav,\n  AccountAddModal,\n",
                       "Add lazy Android nav to host imports")
    app = replace_once(app, "          </main>\n        </div>\n\n        {instanceMounted",
                       "          </main>\n          <AndroidBottomNav screen={screen} />\n        </div>\n\n        {instanceMounted",
                       "App Android nav mount")
    app_path.write_text(app, encoding="utf-8")

    hosts_path = root / "src/components/hosts.tsx"
    hosts = hosts_path.read_text(encoding="utf-8")
    hosts = replace_once(
        hosts,
        "export const MilliDock = lateMount(() => import('./milli/MilliDock').then((m) => ({ default: m.MilliDock })), 700)\\n",
        "export const MilliDock = lateMount(() => import('./milli/MilliDock').then((m) => ({ default: m.MilliDock })), 700)\\nexport const AndroidBottomNav = lateMount(() => import('./AndroidBottomNav').then((m) => ({ default: m.AndroidBottomNav })), 200)\\n",
        "Android bottom navigation lazy host",
    )
    hosts_path.write_text(hosts, encoding="utf-8")

    put(root / "src/styles/android.css", r'''/* Android-first layout; desktop CSS is unchanged outside phone widths. */
.android-bottom-nav { display: none; }
.cl-login-card { width: min(100%, 480px); }
.cl-login-brand { display:flex; align-items:center; gap:10px; margin:0 0 22px; font-weight:950; letter-spacing:.1em; color:#f3f8f4; }
.cl-login-mark { display:grid; place-items:center; width:38px; height:38px; background:#8ee8a8; color:#09130d; font-size:23px; font-weight:950; }
.cl-login-tabs { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:0 0 14px; }
.cl-login-label { display:block; margin:10px 0 6px; font-size:12px; color:var(--m-fg-muted); font-weight:750; }
.cl-login-key { width:100%; resize:vertical; overflow-wrap:anywhere; font-family:ui-monospace,monospace; }
.cl-login-status { margin-top:14px; min-height:46px; padding:12px; color:#c6d4ca; background:#101b14; border:1px solid #2b4433; font-size:12px; line-height:1.5; overflow-wrap:anywhere; }
.cl-login-link { display:block; margin:12px auto 0; color:#91e8a8; font-size:13px; text-align:center; text-decoration:underline; }
.cl-login-trust { display:flex; gap:8px; align-items:flex-start; margin-top:16px; color:var(--m-fg-subtle); font-size:11px; line-height:1.4; }
.cl-login-trust svg { width:16px; height:16px; flex:none; }

@media (max-width: 760px) {
  html, body, #root, .window { width:100%; height:100%; min-height:100%; overflow:hidden; }
  .window { height:100dvh; min-height:100dvh; max-height:100dvh; }
  .titlebar { display:none !important; }
  #scr-app.app { display:flex; flex-direction:column; width:100%; height:100dvh; min-width:0; min-height:0; max-height:100dvh; padding:0 !important; gap:0 !important; overflow:hidden; }
  #scr-app.app > .sidebar { display:none !important; }
  #scr-app.app > .content { flex:1 1 auto; width:100%; min-width:0; min-height:0; height:100%; overflow-x:hidden; overflow-y:auto; overscroll-behavior:contain; -webkit-overflow-scrolling:touch; padding:12px 10px calc(88px + env(safe-area-inset-bottom)) !important; }
  #scr-app:has(> .topbar.is-lobby) > .content { padding-top:calc(64px + env(safe-area-inset-top)) !important; }
  #scr-app .screen { width:100%; max-width:none; min-width:0; margin-inline:0; }
  #scr-app > .topbar:not(.is-lobby) { position:sticky; top:0; z-index:60; flex:0 0 auto; width:100%; min-width:0; min-height:50px; height:auto; padding:6px 10px; gap:6px; box-sizing:border-box; }
  #scr-app > .topbar.is-lobby { position:absolute; top:calc(env(safe-area-inset-top) + 8px); right:8px; left:auto; z-index:70; width:auto; height:auto; padding:0; background:transparent; box-shadow:none; }
  .topbar.is-lobby .lb-btns { gap:5px; }
  .topbar.is-lobby .lb-btn { height:42px; min-width:42px; padding:0 5px; }
  .topbar.is-lobby .lb-btn > svg { width:20px; height:20px; }
  .topbar.is-lobby .lb-heads .lb-head { width:25px; height:25px; }
  .topbar.is-lobby .lb-txt, .topbar.is-lobby .lb-acc-txt, .topbar.is-lobby .lb-btn.lb-fb { display:none !important; }
  .topbar.is-lobby .lb-btn.lb-acc { width:42px; min-width:42px; padding:0; justify-content:center; }
  .topbar.is-lobby .lb-btn.lb-acc .ava { width:34px; height:34px; }
  .topbar.is-lobby .lb-vol .lb-quick-pop { right:0; left:auto; }
  .topbar .btn, .topbar button { min-height:40px; }

  .android-bottom-nav { position:fixed; z-index:1500; left:8px; right:8px; bottom:0; display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); align-items:stretch; gap:3px; box-sizing:border-box; min-height:66px; padding:5px 5px calc(5px + env(safe-area-inset-bottom)); background:rgba(15,20,17,.96); border:1px solid rgba(130,232,164,.20); box-shadow:0 -8px 28px rgba(0,0,0,.24); backdrop-filter:blur(18px); -webkit-backdrop-filter:blur(18px); border-radius:14px 14px 0 0; }
  .android-bottom-nav__item { display:flex; min-width:0; min-height:50px; flex-direction:column; justify-content:center; align-items:center; gap:3px; padding:4px 1px; color:#a7b3aa; background:transparent; border:0; border-radius:9px; font:700 10px/1.15 var(--m-font,system-ui); -webkit-tap-highlight-color:transparent; touch-action:manipulation; }
  .android-bottom-nav__item svg { width:21px; height:21px; flex:none; }
  .android-bottom-nav__item span { display:block; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .android-bottom-nav__item.is-active { color:#101a13; background:#8ce9a8; }
  .android-bottom-nav__item:active { transform:scale(.97); }

  #scr-login.lg2 { min-height:100dvh; }
  #scr-login.lg2 .lg2-wrap { display:grid; grid-template-columns:minmax(0,1fr); align-items:center; justify-items:center; width:100%; min-height:100dvh; height:auto; box-sizing:border-box; padding:calc(22px + env(safe-area-inset-top)) 12px calc(22px + env(safe-area-inset-bottom)); }
  #scr-login.lg2 .lg2-card { width:100%; max-width:460px; box-sizing:border-box; padding:22px 18px 20px; }
  #scr-login.lg2 .lg2-card h1 { font-size:clamp(25px,7vw,32px); }
  #scr-login.lg2 .lg2-art { display:none !important; }
  #scr-login.lg2 .lg2-lang { top:12px; right:12px; }
  .modal { box-sizing:border-box; width:calc(100vw - 20px) !important; max-width:calc(100vw - 20px) !important; max-height:calc(100dvh - 24px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); overflow:auto; overscroll-behavior:contain; }
  button, .btn, [role="button"] { touch-action:manipulation; }
  input, textarea, select, [contenteditable="true"] { font-size:16px !important; }
  :where(.screen,.modal,.content) { min-width:0; }
  img, video, canvas { max-width:100%; }
  .screen :is(.grid,.cards,.card-grid,.skin-cards,.build-cards,.mod-cards) { min-width:0; max-width:100%; }
}
@media (max-width:390px) {
  .android-bottom-nav { left:4px; right:4px; gap:1px; }
  .android-bottom-nav__item { font-size:9px; }
  .android-bottom-nav__item svg { width:19px; height:19px; }
  #scr-app.app > .content { padding-left:8px !important; padding-right:8px !important; }
}
@media (max-width:760px) and (max-height:520px) {
  .android-bottom-nav { min-height:48px; }
  .android-bottom-nav__item { min-height:38px; }
  .android-bottom-nav__item span { display:none; }
  #scr-app.app > .content { padding-bottom:calc(58px + env(safe-area-inset-bottom)) !important; }
}
@media (prefers-reduced-motion:reduce) { .android-bottom-nav__item { transition:none !important; } }
''')

    deep_path = root / "src/lib/deeplink.ts"
    deep = deep_path.read_text(encoding="utf-8")
    deep = replace_once(deep, "if (url.protocol !== 'millida:') return", "if (url.protocol !== 'tatarlauncher:') return", "Android deep-link scheme")
    deep = replace_once(
        deep,
        "  const q = url.searchParams\\n",
        "  const q = url.searchParams\\n  if (action === 'auth' && rest === 'success') { window.dispatchEvent(new Event('cheatlab:resume')); return }\\n",
        "CHEATLAB login return deep link",
    )
    deep_path.write_text(deep, encoding="utf-8")

    print("Applied CHEATLAB branding, website device authorization, encrypted native session storage and Android touch layout.")
    print("Game-account sign-in (Microsoft/offline) stays separate from the CHEATLAB website account.")
    print("Minecraft Java/JNI runtime and Android Storage Access Framework still require separate implementation.")

if __name__ == "__main__":
    main()
