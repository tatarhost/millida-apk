#!/usr/bin/env python3
"""Apply the reproducible TatarHost identity overlay to Amethyst Android."""
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: prepare-upstream.py <Amethyst-Android checkout>")

root = Path(sys.argv[1]).resolve()
expected = "28d6e12d68121b7dd75f2e841058a6b7cdfe4a29"
actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
if actual != expected:
    raise SystemExit(f"Unexpected Amethyst source revision: {actual} (expected {expected})")

gradle = root / "app_pojavlauncher/build.gradle"
text = gradle.read_text(encoding="utf-8")
replacements = [
    ('applicationId "org.angelauramc.amethyst"', 'applicationId "net.tatarhost.launcher"'),
    ("applicationIdSuffix '.debug'", "applicationIdSuffix ''"),
    ('resValue "string", "app_name", "Amethyst (Debug)"', 'resValue "string", "app_name", "TatarHost Launcher (Test)"'),
    ('resValue "string", "app_short_name", "Amethyst (Debug)"', 'resValue "string", "app_short_name", "TatarHost"'),
    ("'org.angelauramc.amethyst.debug'", "'net.tatarhost.launcher'"),
    ("'org.angelauramc.amethyst.scoped.gamefolder.debug'", "'net.tatarhost.launcher.scoped.gamefolder'"),
    ("'org.angelauramc.amethyst.scoped.controlfolder.debug'", "'net.tatarhost.launcher.scoped.controlfolder'"),
    ("'org.angelauramc.amethyst'", "'net.tatarhost.launcher'"),
    ("'org.angelauramc.amethyst.scoped.gamefolder'", "'net.tatarhost.launcher.scoped.gamefolder'"),
]
for old, new in replacements:
    if old not in text:
        raise SystemExit(f"Expected Gradle setting not found: {old}")
    text = text.replace(old, new)
gradle.write_text(text, encoding="utf-8")

# New monochrome TatarHost mark; no Millida or Amethyst logo is used as the app icon.
svg_dir = root / "app_pojavlauncher/build/tatarhost-icons"
svg_dir.mkdir(parents=True, exist_ok=True)
foreground = """<svg xmlns="http://www.w3.org/2000/svg" width="432" height="432" viewBox="0 0 432 432">
<g fill="#ffffff">
<path d="M76 88h142v38h-52v218h-38V126H76z"/>
<path d="M249 88h38v106h91V88h38v256h-38V232h-91v112h-38z"/>
</g>
<rect x="352" y="360" width="44" height="16" rx="4" fill="#a8a8a8"/>
</svg>"""
background = """<svg xmlns="http://www.w3.org/2000/svg" width="432" height="432" viewBox="0 0 432 432">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#202020"/><stop offset="1" stop-color="#050505"/></linearGradient></defs>
<rect width="432" height="432" rx="96" fill="url(#g)"/>
<rect x="8" y="8" width="416" height="416" rx="90" fill="none" stroke="#ffffff" stroke-opacity=".12" stroke-width="4"/>
</svg>"""
full = """<svg xmlns="http://www.w3.org/2000/svg" width="432" height="432" viewBox="0 0 432 432">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#202020"/><stop offset="1" stop-color="#050505"/></linearGradient></defs>
<rect width="432" height="432" rx="96" fill="url(#g)"/>
<rect x="8" y="8" width="416" height="416" rx="90" fill="none" stroke="#ffffff" stroke-opacity=".12" stroke-width="4"/>
<g fill="#ffffff">
<path d="M76 88h142v38h-52v218h-38V126H76z"/>
<path d="M249 88h38v106h91V88h38v256h-38V232h-91v112h-38z"/>
</g>
<rect x="352" y="360" width="44" height="16" rx="4" fill="#a8a8a8"/>
</svg>"""
(svg_dir / "foreground.svg").write_text(foreground, encoding="utf-8")
(svg_dir / "background.svg").write_text(background, encoding="utf-8")
(svg_dir / "full.svg").write_text(full, encoding="utf-8")

sizes = {"mipmap-mdpi": 48, "mipmap-hdpi": 72, "mipmap-xhdpi": 96,
         "mipmap-xxhdpi": 144, "mipmap-xxxhdpi": 192}
res = root / "app_pojavlauncher/src/main/res"
for folder, size in sizes.items():
    dest = res / folder
    dest.mkdir(parents=True, exist_ok=True)
    for source, name in [("foreground", "ic_launcher_foreground.webp"),
                         ("background", "ic_launcher_background.webp"),
                         ("full", "ic_launcher.webp")]:
        png = svg_dir / f"{source}-{size}.png"
        subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size),
                        "-o", str(png), str(svg_dir / f"{source}.svg")], check=True)
        subprocess.run(["cwebp", "-quiet", "-q", "92", str(png), "-o", str(dest / name)], check=True)
    (dest / "ic_launcher_round.webp").write_bytes((dest / "ic_launcher.webp").read_bytes())

for icon in ["mipmap-anydpi-v26/ic_launcher.xml", "mipmap-anydpi-v26/ic_launcher_round.xml"]:
    if not (res / icon).exists():
        raise SystemExit(f"Expected adaptive launcher icon resource not found: {icon}")

print("Prepared TatarHost identity; Android package net.tatarhost.launcher")
