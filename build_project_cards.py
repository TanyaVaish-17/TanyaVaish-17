#!/usr/bin/env python3
"""
Builds the animated project cards from the screenshots in ./screenshots

Put this file in the ROOT of your profile repo (next to README.md), then run:

    pip install pillow          # one time (shrinks the images so the cards stay light)
    python build_project_cards.py

It reads screenshots named  booth1, booth2 ... / kisansathi1 ... / lawsetu1 ... / marvo1 ...
(.png .jpg .jpeg .webp, any capitalisation) and writes these files into ./assets:

    project-photobooth.svg   project-kisansathi.svg   project-lawsetu.svg   project-marvo.svg

Each card flashes that project's screenshots one by one (crossfade + progress bar).
Images are embedded inside the SVG because GitHub blocks external files inside SVGs.
Re-run it whenever you add or change screenshots.
"""
import base64, io, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(ROOT, "screenshots")
ASSETS = os.path.join(ROOT, "assets")

SANS = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
SECONDS_PER_SLIDE = 3.4
FADE = 0.7

PROJECTS = [
    dict(prefix="kisansathi", out="project-kisansathi.svg", title="KisanSathi", tag="FULL-STACK  ·  REAL-TIME",
         url="kisan-sathi-bay.vercel.app", a="#34d399", b="#22d3ee",
         pitch=["Virtual queue tokens for farmers at mandis &", "procurement centres, tracked live."],
         stack=["React", "Vite", "Tailwind", "Node.js", "Express", "MongoDB", "Socket.IO"]),
    dict(prefix="marvo", out="project-marvo.svg", title="MARVO", tag="TEAM  ·  SMART INDIA HACKATHON 2026",
         url="orca-teal-nine.vercel.app", a="#22d3ee", b="#a78bfa",
         pitch=["Turn marine data into decisions: 10 cooperating", "agents deliver safe, explainable guidance for fishers."],
         stack=["Python", "FastAPI", "React", "TypeScript", "Leaflet", "Tailwind"]),
    dict(prefix="lawsetu", out="project-lawsetu.svg", title="LawSetu", tag="TEAM  ·  AI  ·  FULL-STACK",
         url="law-setu.vercel.app", a="#8b5cf6", b="#f472b6",
         pitch=["AI legal assistant: draft, upload & export", "contracts from NDA to lease agreements."],
         stack=["React", "Vite", "Node.js", "Express", "MongoDB", "OpenAI API"]),
    dict(prefix="booth", out="project-photobooth.svg", title="K-Click Booth", tag="FRONTEND  ·  CREATIVE",
         url="k-click-booth.vercel.app", a="#f472b6", b="#fbbf24",
         pitch=["An aesthetic photo-strip booth in the browser:", "capture, customise and keep your memories."],
         stack=["React", "Vite", "Tailwind", "React Router", "Vercel"]),
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def find_images(prefix):
    if not os.path.isdir(SHOTS):
        return []
    found = []
    pat = re.compile(rf"^{re.escape(prefix)}[-_ ]?(\d+)\.(png|jpe?g|webp)$", re.I)
    for name in os.listdir(SHOTS):
        m = pat.match(name)
        if m:
            found.append((int(m.group(1)), os.path.join(SHOTS, name)))
    return [p for _, p in sorted(found)]


def encode(path):
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        if im.width > 1040:
            im = im.resize((1040, round(im.height * 1040 / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80, optimize=True)
        return "image/jpeg", base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        raw = open(path, "rb").read()
        if len(raw) > 400_000:
            print(f"   ! {os.path.basename(path)} is {len(raw)//1000} KB. Run 'pip install pillow' to shrink it.")
        ext = path.rsplit(".", 1)[1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}[ext]
        return mime, base64.b64encode(raw).decode()


def vis_points(i, n, f):
    s, e = i / n, (i + 1) / n
    if n == 1:
        return [(0, 1), (1, 1)]
    if i == 0:
        return [(0, 1), (e - f, 1), (e, 0), (1 - f, 0), (1, 1)]
    if i == n - 1:
        return [(0, 0), (s, 0), (s + f, 1), (1 - f, 1), (1, 0)]
    return [(0, 0), (s, 0), (s + f, 1), (e - f, 1), (e, 0), (1, 0)]


def kv(points, scale=1.0, base=0.0):
    return (";".join(f"{t:.4f}" for t, _ in points),
            ";".join(f"{base + v * scale:.3f}" for _, v in points))


def chips(items, x0, y0, maxw, color, h=26, gap=7):
    out, x, y = "", x0, y0
    for i, it in enumerate(items):
        wd = len(it) * 7.2 + 26
        if x + wd > x0 + maxw:
            x, y = x0, y + h + gap
        out += (f'<g transform="translate({x:.0f} {y})"><g>'
                f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -2;0 0" dur="{3 + (i % 4) * 0.4:.1f}s" begin="{(i * 0.23) % 3:.2f}s" repeatCount="indefinite"/>'
                f'<rect width="{wd:.0f}" height="{h}" rx="{h / 2}" fill="{color}" fill-opacity=".12" stroke="{color}" stroke-opacity=".55"/>'
                f'<text x="{wd / 2:.0f}" y="{h / 2 + 4.5}" text-anchor="middle" font-family="{SANS}" font-size="12" fill="#e6edf3">{esc(it)}</text></g></g>')
        x += wd + gap
    return out


def card(p, images):
    W, H = 560, 540
    a, b = p["a"], p["b"]
    n = max(len(images), 1)
    cycle = n * SECONDS_PER_SLIDE
    f = min(FADE / cycle, 0.4 / n)

    if images:
        slides = ""
        for i, path in enumerate(images):
            mime, b64 = encode(path)
            kt, vv = kv(vis_points(i, n, f))
            anim = "" if n == 1 else f'<animate attributeName="opacity" values="{vv}" keyTimes="{kt}" dur="{cycle:.1f}s" repeatCount="indefinite"/>'
            slides += (f'<image x="20" y="42" width="520" height="278" preserveAspectRatio="xMidYMin slice" '
                       f'href="data:{mime};base64,{b64}" opacity="{1 if (i == 0 or n == 1) else 0}">{anim}</image>')
    else:
        slides = (f'<rect x="20" y="42" width="520" height="278" fill="#131722"/>'
                  f'<text x="280" y="186" text-anchor="middle" font-family="{SANS}" font-size="13" letter-spacing="3" fill="#8b949e">NO SCREENSHOTS FOUND</text>'
                  f'<text x="280" y="210" text-anchor="middle" font-family="{SANS}" font-size="12" fill="#6b7280">screenshots/{p["prefix"]}1.png</text>')

    dots = progress = ""
    if images and n > 1:
        x0 = 280 - (n - 1) * 14 / 2
        for i in range(n):
            kt, vv = kv(vis_points(i, n, f), scale=0.75, base=0.25)
            dots += (f'<circle cx="{x0 + i * 14:.0f}" cy="306" r="3" fill="#fff" fill-opacity="0.25">'
                     f'<animate attributeName="fill-opacity" values="{vv}" keyTimes="{kt}" dur="{cycle:.1f}s" repeatCount="indefinite"/></circle>')
        progress = (f'<rect x="20" y="318" height="2" width="0" fill="{b}">'
                    f'<animate attributeName="width" values="0;520" dur="{SECONDS_PER_SLIDE:.1f}s" repeatCount="indefinite"/></rect>')

    tw = len(p["tag"]) * 7.2 + 28
    pitch = "".join(f'<text x="24" y="{428 + i * 21}" font-family="{SANS}" font-size="14" fill="#9fb0c8">{esc(t)}</text>' for i, t in enumerate(p["pitch"]))
    ch = chips(p["stack"], 24, 478, 512, a)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(p["title"])} screenshots">
<defs>
<linearGradient id="bd" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0" spreadMethod="reflect"><stop offset="0" stop-color="{a}"/><stop offset=".5" stop-color="{b}"/><stop offset="1" stop-color="{a}"/><animateTransform attributeName="gradientTransform" type="translate" values="0 0;{W} 0" dur="6s" repeatCount="indefinite"/></linearGradient>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#101827"/></linearGradient>
<radialGradient id="gl" cx="0.85" cy="0.05" r="0.8"><stop offset="0" stop-color="{a}" stop-opacity=".25"/><stop offset="1" stop-color="{a}" stop-opacity="0"/></radialGradient>
<linearGradient id="ti" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="320" y2="0" spreadMethod="reflect"><stop offset="0" stop-color="#fff"/><stop offset=".5" stop-color="{b}"/><stop offset="1" stop-color="#fff"/><animateTransform attributeName="gradientTransform" type="translate" values="0 0;320 0" dur="5s" repeatCount="indefinite"/></linearGradient>
<linearGradient id="vg" x1="0" y1="0" x2="0" y2="1"><stop offset=".75" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".4"/></linearGradient>
<clipPath id="fr"><rect x="20" y="20" width="520" height="300" rx="12"/></clipPath>
</defs>
<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="20" fill="url(#bg)"/>
<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="20" fill="url(#gl)"/>
<g clip-path="url(#fr)">
<rect x="20" y="20" width="520" height="300" fill="#10131a"/>
{slides}
<rect x="20" y="42" width="520" height="278" fill="url(#vg)"/>
{dots}{progress}
<rect x="20" y="20" width="520" height="22" fill="#161b22"/>
<circle cx="36" cy="31" r="3.5" fill="#ff5f56"/><circle cx="48" cy="31" r="3.5" fill="#ffbd2e"/><circle cx="60" cy="31" r="3.5" fill="#27c93f"/>
<rect x="170" y="24" width="220" height="14" rx="7" fill="#0d1117"/>
<text x="280" y="34.5" text-anchor="middle" font-family="{SANS}" font-size="9.5" fill="#8b949e">{esc(p["url"])}</text>
</g>
<rect x="20" y="20" width="520" height="300" rx="12" fill="none" stroke="#ffffff" stroke-opacity=".14"/>
<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="20" fill="none" stroke="url(#bd)" stroke-width="2"/>
<g transform="translate(24 336)"><rect width="{tw:.0f}" height="22" rx="11" fill="{a}" fill-opacity=".15" stroke="{a}" stroke-opacity=".5"/><circle cx="12" cy="11" r="3.5" fill="{b}"><animate attributeName="opacity" values="1;.3;1" dur="1.8s" repeatCount="indefinite"/></circle><text x="22" y="15.5" font-family="{SANS}" font-size="11" letter-spacing="1" fill="#e6edf3">{esc(p["tag"])}</text></g>
<text x="24" y="394" font-family="{SANS}" font-size="34" font-weight="800" fill="url(#ti)">{esc(p["title"])}</text>
{pitch}
{ch}
</svg>'''


def main():
    os.makedirs(ASSETS, exist_ok=True)
    if not os.path.isdir(SHOTS):
        print("! 'screenshots' folder not found next to this script:", SHOTS)
    for p in PROJECTS:
        imgs = find_images(p["prefix"])
        out = os.path.join(ASSETS, p["out"])
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(card(p, imgs))
        print(f"{p['title']:<14} {len(imgs)} screenshot(s) -> assets/{p['out']} ({os.path.getsize(out) // 1000} KB)")
        if not imgs:
            print(f"   (no files like screenshots/{p['prefix']}1.png found)")


if __name__ == "__main__":
    main()
