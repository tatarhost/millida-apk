#!/usr/bin/env python3
"""Apply an Android-first shell to the pinned Tauri desktop source tree."""
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

def make_icon(path: Path, size: int = 1024) -> None:
    pixels = bytearray(size * size * 4)
    cx = cy = size / 2
    radius = size * 0.62
    for y in range(size):
        for x in range(size):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radius
            glow = max(0.0, 1.0 - d) * 9.0
            i = (y * size + x) * 4
            pixels[i:i+4] = bytes((int(13 + glow * 0.45), int(20 + glow * 0.75), int(16 + glow * 0.5), 255))

    # Abstract pixel mountain / M mark. It is original artwork, not the upstream logo.
    polygon = [
        (215, 755), (215, 285), (340, 285), (512, 485),
        (684, 285), (809, 285), (809, 755), (672, 755),
        (672, 505), (512, 690), (352, 505), (352, 755),
    ]
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
                pixels[i:i+4] = bytes((122, 231, 160, 255))

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

    # The derived app must not reuse the upstream project's protected brand.
    config_path = root / "src-tauri/tauri.android.conf.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["productName"] = "TatarHost Launcher"
    config["identifier"] = "net.tatarhost.launcher"
    config["app"]["windows"][0]["title"] = "TatarHost Launcher"
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
  <path d="M13 48V17h9l10 12 10-12h9v31h-9V31L32 43 22 31v17z" fill="#7ae7a0"/>
  <path d="M13 48h9V35l-9-10zM51 48h-9V35l9-10z" fill="#b0f5c4" opacity=".45"/>
</svg>
"""
    put(root / "public/tatarhost-logo.svg", icon_svg)
    put(root / "public/favicon.svg", icon_svg)
    make_icon(root / "src-tauri/icons/icon.png")

    index_path = root / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = replace_once(index, 'content="width=device-width, initial-scale=1"', 'content="width=device-width, initial-scale=1, viewport-fit=cover"', "index viewport")
    index = replace_once(index, "<title>Millida Launcher</title>", "<title>TatarHost Launcher</title>", "index title")
    index = replace_once(index, 'src="/millida-logo.svg"', 'src="/tatarhost-logo.svg"', "boot logo")
    index_path.write_text(index, encoding="utf-8")

    login_path = root / "src/screens/Login.tsx"
    login = login_path.read_text(encoding="utf-8")
    login = replace_once(login, 'src="/millida-logo.svg"', 'src="/tatarhost-logo.svg"', "login logo")
    login_path.write_text(login, encoding="utf-8")

    # The official site uses its own millida:// protocol. This fork registers a
    # distinct scheme and accepts only links addressed to this application.
    deep_path = root / "src/lib/deeplink.ts"
    deep = deep_path.read_text(encoding="utf-8")
    deep = replace_once(deep, "if (url.protocol !== 'millida:') return", "if (url.protocol !== 'tatarlauncher:') return", "mobile deep-link scheme")
    deep_path.write_text(deep, encoding="utf-8")

    # Millida's account API and brand are not licensed to third-party Android forks.
    # Do not silently send device-code requests to the official service.
    login_state_path = root / "src/state/login.ts"
    login_state = login_state_path.read_text(encoding="utf-8")
    guard = """  if (/Android/i.test(navigator.userAgent)) {
    const reason = 'Вход через аккаунт Millida в этой сторонней Android-сборке недоступен без отдельного разрешения владельцев сервиса. Поэтому код и ссылка авторизации не запрашиваются.';
    resetLogin(reason);
    showToast(reason, 'error');
    return;
  }
"""
    login_state = replace_once(
        login_state,
        "  if (!hasTauri()) {\n    showToast(t('Вход через аккаунт Millida доступен только в приложении лаунчера'), 'error')",
        guard + "  if (!hasTauri()) {\n    showToast(t('Вход через аккаунт Millida доступен только в приложении лаунчера'), 'error')",
        "Android Millida login permission guard",
    )
    login_state_path.write_text(login_state, encoding="utf-8")

    # A persistent five-item bottom rail replaces desktop navigation on phones.
    put(root / "src/components/AndroidBottomNav.tsx", r'''import { Icon } from './Icon'
import { useT } from '../i18n'
import { setScreen, type ScreenId } from '../state/ui'
import { useMods } from '../state/mods'

export function AndroidBottomNav({ screen }: { screen: ScreenId }) {
  const t = useT()
  const items: { id: ScreenId; label: string; icon: string }[] = [
    { id: 'play', label: t('Играть'), icon: 'i-play' },
    { id: 'builds', label: t('Сборки'), icon: 'i-box2' },
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
          <button
            key={item.id}
            type="button"
            className={'android-bottom-nav__item' + (active ? ' is-active' : '')}
            aria-current={active ? 'page' : undefined}
            onClick={() => {
              if (item.id === 'mods') useMods.getState().scopeTo(null)
              setScreen(item.id)
              document.querySelector<HTMLElement>('.content')?.scrollTo(0, 0)
            }}
          >
            <Icon id={item.icon} />
            <span>{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
''')

    app_path = root / "src/App.tsx"
    app = app_path.read_text(encoding="utf-8")
    app = replace_once(
        app,
        "import { SvgSprite } from './components/SvgSprite'\n",
        "import { SvgSprite } from './components/SvgSprite'\nimport { AndroidBottomNav } from './components/AndroidBottomNav'\n",
        "App Android nav import",
    )
    app = replace_once(
        app,
        "          </main>\n        </div>\n\n        {instanceMounted",
        "          </main>\n          <AndroidBottomNav screen={screen} />\n        </div>\n\n        {instanceMounted",
        "App Android nav mount",
    )
    app_path.write_text(app, encoding="utf-8")

    main_path = root / "src/main.tsx"
    main = main_path.read_text(encoding="utf-8")
    main = replace_once(
        main,
        "import './styles/13-lite.css'\n",
        "import './styles/13-lite.css'\nimport './styles/android.css'\n",
        "Android responsive stylesheet import",
    )
    main_path.write_text(main, encoding="utf-8")

    put(root / "src/styles/android.css", r'''/* Android-first layout. Desktop CSS remains untouched outside phone widths. */
.android-bottom-nav { display: none; }

@media (max-width: 760px) {
  html, body, #root, .window {
    width: 100%;
    height: 100%;
    min-height: 100%;
    overflow: hidden;
  }
  .window {
    height: 100dvh;
    min-height: 100dvh;
    max-height: 100dvh;
  }
  .titlebar { display: none !important; }

  #scr-app.app {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100dvh;
    min-width: 0;
    min-height: 0;
    max-height: 100dvh;
    padding: 0 !important;
    gap: 0 !important;
    overflow: hidden;
  }
  #scr-app.app > .sidebar { display: none !important; }
  #scr-app.app > .content {
    flex: 1 1 auto;
    width: 100%;
    min-width: 0;
    min-height: 0;
    height: 100%;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
    padding: 12px 10px calc(88px + env(safe-area-inset-bottom)) !important;
  }
  #scr-app:has(> .topbar.is-lobby) > .content {
    padding-top: calc(64px + env(safe-area-inset-top)) !important;
  }
  #scr-app .screen {
    width: 100%;
    max-width: none;
    min-width: 0;
    margin-inline: 0;
  }

  #scr-app > .topbar:not(.is-lobby) {
    position: sticky;
    top: 0;
    z-index: 60;
    flex: 0 0 auto;
    width: 100%;
    min-width: 0;
    min-height: 50px;
    height: auto;
    padding: 6px 10px;
    gap: 6px;
    box-sizing: border-box;
  }
  #scr-app > .topbar.is-lobby {
    position: absolute;
    top: calc(env(safe-area-inset-top) + 8px);
    right: 8px;
    left: auto;
    z-index: 70;
    width: auto;
    height: auto;
    padding: 0;
    background: transparent;
    box-shadow: none;
  }
  .topbar.is-lobby .lb-btns { gap: 5px; }
  .topbar.is-lobby .lb-btn {
    height: 42px;
    min-width: 42px;
    padding: 0 5px;
  }
  .topbar.is-lobby .lb-btn > svg { width: 20px; height: 20px; }
  .topbar.is-lobby .lb-heads .lb-head { width: 25px; height: 25px; }
  .topbar.is-lobby .lb-txt,
  .topbar.is-lobby .lb-acc-txt,
  .topbar.is-lobby .lb-btn.lb-fb { display: none !important; }
  .topbar.is-lobby .lb-btn.lb-acc {
    width: 42px;
    min-width: 42px;
    padding: 0;
    justify-content: center;
  }
  .topbar.is-lobby .lb-btn.lb-acc .ava { width: 34px; height: 34px; }
  .topbar.is-lobby .lb-vol .lb-quick-pop { right: 0; left: auto; }
  .topbar .btn, .topbar button { min-height: 40px; }

  .android-bottom-nav {
    position: fixed;
    z-index: 1500;
    left: 8px;
    right: 8px;
    bottom: 0;
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    align-items: stretch;
    gap: 3px;
    box-sizing: border-box;
    min-height: 66px;
    padding: 5px 5px calc(5px + env(safe-area-inset-bottom));
    background: rgba(15, 20, 17, .96);
    border: 1px solid rgba(130, 232, 164, .20);
    box-shadow: 0 -8px 28px rgba(0, 0, 0, .24);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border-radius: 14px 14px 0 0;
  }
  .android-bottom-nav__item {
    display: flex;
    min-width: 0;
    min-height: 50px;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 3px;
    padding: 4px 1px;
    color: #a7b3aa;
    background: transparent;
    border: 0;
    border-radius: 9px;
    font: 700 10px/1.15 var(--m-font, system-ui);
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }
  .android-bottom-nav__item svg { width: 21px; height: 21px; flex: none; }
  .android-bottom-nav__item span {
    display: block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .android-bottom-nav__item.is-active {
    color: #101a13;
    background: #8ce9a8;
  }
  .android-bottom-nav__item:active { transform: scale(.97); }

  /* First-run/login scene: card takes the width; desktop character art is hidden. */
  #scr-login.lg2 { min-height: 100dvh; }
  #scr-login.lg2 .lg2-wrap {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    align-items: center;
    justify-items: center;
    width: 100%;
    min-height: 100dvh;
    height: auto;
    box-sizing: border-box;
    padding: calc(22px + env(safe-area-inset-top)) 12px calc(22px + env(safe-area-inset-bottom));
  }
  #scr-login.lg2 .lg2-card {
    width: 100%;
    max-width: 460px;
    box-sizing: border-box;
    padding: 22px 18px 20px;
  }
  #scr-login.lg2 .lg2-card h1 { font-size: clamp(25px, 7vw, 32px); }
  #scr-login.lg2 .lg2-art { display: none !important; }
  #scr-login.lg2 .lg2-lang { top: 12px; right: 12px; }

  /* Phone-friendly dialogs and touch controls. */
  .modal {
    box-sizing: border-box;
    width: calc(100vw - 20px) !important;
    max-width: calc(100vw - 20px) !important;
    max-height: calc(100dvh - 24px - env(safe-area-inset-top) - env(safe-area-inset-bottom));
    overflow: auto;
    overscroll-behavior: contain;
  }
  button, .btn, [role="button"] { touch-action: manipulation; }
  input, textarea, select, [contenteditable="true"] { font-size: 16px !important; }
  :where(.screen, .modal, .content) { min-width: 0; }
  img, video, canvas { max-width: 100%; }

  /* Let cards and tables shrink instead of forcing a desktop-width canvas. */
  .screen :is(.grid, .cards, .card-grid, .skin-cards, .build-cards, .mod-cards) {
    min-width: 0;
    max-width: 100%;
  }
}

@media (max-width: 390px) {
  .android-bottom-nav { left: 4px; right: 4px; gap: 1px; }
  .android-bottom-nav__item { font-size: 9px; }
  .android-bottom-nav__item svg { width: 19px; height: 19px; }
  #scr-app.app > .content { padding-left: 8px !important; padding-right: 8px !important; }
}

@media (max-width: 760px) and (max-height: 520px) {
  .android-bottom-nav { min-height: 48px; }
  .android-bottom-nav__item { min-height: 38px; }
  .android-bottom-nav__item span { display: none; }
  #scr-app.app > .content { padding-bottom: calc(58px + env(safe-area-inset-bottom)) !important; }
}

@media (prefers-reduced-motion: reduce) {
  .android-bottom-nav__item { transition: none !important; }
}
''')

    print("Applied TatarHost Android brand, mobile bottom navigation, safe-area layout and custom deep links.")
    print("Millida account sign-in stays disabled on Android until the service owner authorizes this fork.")
    print("Minecraft Java/JNI and Android Storage Access Framework still require separate implementation.")

if __name__ == "__main__":
    main()
