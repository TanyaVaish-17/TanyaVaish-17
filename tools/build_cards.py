#!/usr/bin/env python3
"""
Builds the animated project cards (assets/project-*.svg) from YOUR screenshots.

Put 1-6 screenshots per project in assets/screens/ named:
    kisansathi-1.png  kisansathi-2.png ...
    orca-1.png        orca-2.png ...
    lawsetu-1.png     lawsetu-2.png ...
    photobooth-1.png  photobooth-2.png ...
(.png .jpg .jpeg .webp all work) then run, from the repo root:

    pip install pillow      # optional but recommended: shrinks images
    python tools/build_cards.py

Images are embedded inside each SVG (GitHub blocks external files inside SVGs),
so the cards stay self-contained. Re-run any time you change screenshots.
"""
import base64, io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
SCREENS = os.path.join(ASSETS, "screens")

INK, PAPER, MUTED, LINE, ACCENT = "#0e0f11", "#efebe4", "#8c8880", "#2a2c30", "#d6a572"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

SECONDS_PER_SLIDE = 3.6
FADE = 0.7  # seconds

PROJECTS = [
    dict(key="kisansathi", n="01", title="KisanSathi", tag="FULL STACK  ·  REAL-TIME",
         url="kisan-sathi-bay.vercel.app",
         pitch=["Virtual queue tokens for farmers at mandis", "and procurement centres, with live position", "tracking so nobody waits in line all day."],
         feats=["Live queue position via Socket.IO", "Farmer, operator and admin roles (JWT)", "Analytics dashboards with Recharts"],
         stack="REACT  ·  VITE  ·  TAILWIND  ·  NODE.JS  ·  EXPRESS  ·  MONGODB  ·  SOCKET.IO"),
    dict(key="orca", n="02", title="ORCA", tag="TEAM PROJECT  ·  SMART INDIA HACKATHON 2026",
         url="orca-teal-nine.vercel.app",
         pitch=["Ten cooperating agents turn India's marine", "data into one safe, explainable decision", "for fishers, in their own language."],
         feats=["English, Hindi and Marathi answers + voice", "Risk engine with deterministic safety floors", "Live nautical chart with wind and current flow"],
         stack="PYTHON  ·  FASTAPI  ·  REACT  ·  TYPESCRIPT  ·  LEAFLET  ·  TAILWIND"),
    dict(key="lawsetu", n="03", title="LawSetu", tag="TEAM PROJECT  ·  AI  ·  FULL STACK",
         url="law-setu.vercel.app",
         pitch=["AI-assisted legal drafting: generate, edit", "and export contracts such as NDAs,", "employment and lease agreements."],
         feats=["OpenAI drafting with live Markdown editor", "PDF / image upload with OCR parsing", "Google OAuth + JWT auth, dark mode"],
         stack="REACT  ·  VITE  ·  NODE.JS  ·  EXPRESS  ·  MONGODB  ·  OPENAI API"),
    dict(key="photobooth", n="04", title="K-Click Booth", tag="FRONTEND  ·  CREATIVE",
         url="k-click-booth.vercel.app",
         pitch=["A browser photo booth that turns snapshots", "into styled photo strips you can customise,", "download and revisit later."],
         feats=["Filters, frames and stickers in real time", "Quick templates, download and retake", "Memories page, fully responsive"],
         stack="REACT  ·  VITE  ·  TAILWIND  ·  REACT ROUTER  ·  VERCEL"),
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def find_images(key):
    out = []
    for n in range(1, 9):
        for ext in ("png", "jpg", "jpeg", "webp"):
            p = os.path.join(SCREENS, f"{key}-{n}.{ext}")
            if os.path.exists(p):
                out.append(p)
                break
    return out


def encode(path):
    """-> (mime, base64). Uses Pillow (if installed) to keep SVGs small."""
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        if im.width > 1100:
            im = im.resize((1100, round(im.height * 1100 / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82, optimize=True)
        return "image/jpeg", base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        raw = open(path, "rb").read()
        if len(raw) > 700_000:
            print(f"  ! {os.path.basename(path)} is {len(raw)//1000} KB - run 'pip install pillow' to shrink it")
        ext = path.rsplit(".", 1)[1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}[ext]
        return mime, base64.b64encode(raw).decode()


def vis_points(i, n, f):
    """Opacity keyframes (t, v) for slide i of n, crossfading cyclically."""
    s, e = i / n, (i + 1) / n
    if n == 1:
        return [(0, 1), (1, 1)]
    if i == 0:
        return [(0, 1), (e - f, 1), (e, 0), (1 - f, 0), (1, 1)]
    if i == n - 1:
        return [(0, 0), (s, 0), (s + f, 1), (1 - f, 1), (1, 0)]
    return [(0, 0), (s, 0), (s + f, 1), (e - f, 1), (e, 0), (1, 0)]


def kv(points, scale=1.0, base=0.0):
    kt = ";".join(f"{t:.4f}" for t, _ in points)
    vv = ";".join(f"{base + v * scale:.3f}" for _, v in points)
    return kt, vv


def fade_in(delay, dur=1.4):
    """values/keyTimes that hold 0 for `delay` seconds then fade to 1 (plays once)."""
    total = delay + 0.8
    kt = f"0;{delay / total:.4f};1"
    return f'<animate attributeName="opacity" values="0;0;1" keyTimes="{kt}" dur="{total:.2f}s" fill="freeze"/>'


def card(p, images):
    W, H = 1200, 440
    n = max(len(images), 1)
    cycle = n * SECONDS_PER_SLIDE
    f = min(FADE / cycle, 0.4 / n)

    slides = ""
    if images:
        for i, path in enumerate(images):
            mime, b64 = encode(path)
            kt, vv = kv(vis_points(i, n, f))
            anim = "" if n == 1 else f'<animate attributeName="opacity" values="{vv}" keyTimes="{kt}" dur="{cycle:.1f}s" repeatCount="indefinite"/>'
            slides += (f'<image x="30" y="58" width="700" height="352" preserveAspectRatio="xMidYMin slice" '
                       f'href="data:{mime};base64,{b64}" opacity="{1 if (i == 0 or n == 1) else 0}">{anim}</image>')
    else:
        slides = (f'<rect x="30" y="58" width="700" height="352" fill="url(#ph)"/>'
                  f'<text x="380" y="226" text-anchor="middle" font-family="{SANS}" font-size="13" letter-spacing="3" fill="{MUTED}">ADD SCREENSHOTS</text>'
                  f'<text x="380" y="250" text-anchor="middle" font-family="{SANS}" font-size="12" fill="#5d5a54">assets/screens/{p["key"]}-1.png  ...  then run tools/build_cards.py</text>')

    dots = progress = ""
    if images and n > 1:
        gap = 16
        x0 = 380 - (n - 1) * gap / 2
        for i in range(n):
            kt, vv = kv(vis_points(i, n, f), scale=0.75, base=0.25)
            dots += (f'<circle cx="{x0 + i * gap:.0f}" cy="394" r="3" fill="#fff" fill-opacity="0.25">'
                     f'<animate attributeName="fill-opacity" values="{vv}" keyTimes="{kt}" dur="{cycle:.1f}s" repeatCount="indefinite"/></circle>')
        progress = (f'<rect x="30" y="408" height="2" width="0" fill="{ACCENT}">'
                    f'<animate attributeName="width" values="0;700" dur="{SECONDS_PER_SLIDE:.1f}s" repeatCount="indefinite"/></rect>')

    feats = ""
    for i, t in enumerate(p["feats"]):
        y = 296 + i * 28
        feats += (f'<g opacity="0">{fade_in(0.9 + i * 0.15)}<rect x="780" y="{y - 4}" width="10" height="1.5" fill="{ACCENT}"/>'
                  f'<text x="802" y="{y}" font-family="{SANS}" font-size="13.5" fill="#cfcbc3">{esc(t)}</text></g>')
    pitch = "".join(f'<text x="780" y="{206 + i * 22}" font-family="{SANS}" font-size="14.5" fill="#a9a59d">{esc(t)}</text>' for i, t in enumerate(p["pitch"]))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(p["title"])} screenshots">
<defs>
<linearGradient id="ph" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#15161a"/><stop offset="1" stop-color="#1b1c21"/></linearGradient>
<clipPath id="fr"><rect x="30" y="30" width="700" height="380" rx="10"/></clipPath>
<linearGradient id="vg" x1="0" y1="0" x2="0" y2="1"><stop offset="0.7" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".45"/></linearGradient>
</defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="{INK}" stroke="{LINE}"/>
<g clip-path="url(#fr)">
<rect x="30" y="30" width="700" height="380" fill="#131417"/>
{slides}
<rect x="30" y="58" width="700" height="352" fill="url(#vg)"/>
{dots}{progress}
<rect x="30" y="30" width="700" height="28" fill="#17181b"/>
<circle cx="50" cy="44" r="4.5" fill="#3a3c41"/><circle cx="66" cy="44" r="4.5" fill="#3a3c41"/><circle cx="82" cy="44" r="4.5" fill="#3a3c41"/>
<rect x="250" y="35" width="260" height="18" rx="9" fill="#0e0f11"/>
<text x="380" y="48" text-anchor="middle" font-family="{SANS}" font-size="11" fill="{MUTED}">{esc(p["url"])}</text>
<rect x="30" y="58" width="700" height="1" fill="{LINE}"/>
</g>
<rect x="30" y="30" width="700" height="380" rx="10" fill="none" stroke="#33353a"/>
<g opacity="0">{fade_in(0.1)}<text x="780" y="72" font-family="{SERIF}" font-size="15" letter-spacing="4" fill="{ACCENT}">{p["n"]}</text></g>
<g opacity="0">{fade_in(0.25)}<text x="780" y="122" font-family="{SERIF}" font-size="42" fill="{PAPER}">{esc(p["title"])}</text></g>
<g opacity="0">{fade_in(0.4)}<text x="780" y="150" font-family="{SANS}" font-size="10.5" letter-spacing="2.2" fill="{MUTED}">{esc(p["tag"])}</text>
<rect x="780" y="168" width="390" height="1" fill="{LINE}"/></g>
<g opacity="0">{fade_in(0.6)}{pitch}</g>
{feats}
<g opacity="0">{fade_in(1.4)}<rect x="780" y="364" width="390" height="1" fill="{LINE}"/>
<text x="780" y="392" font-family="{SANS}" font-size="10.5" letter-spacing="1.6" fill="{MUTED}">{esc(p["stack"])}</text></g>
</svg>'''


def main():
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(SCREENS, exist_ok=True)
    for p in PROJECTS:
        imgs = find_images(p["key"])
        out = os.path.join(ASSETS, f"project-{p['key']}.svg")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(card(p, imgs))
        kb = os.path.getsize(out) // 1000
        print(f"{p['key']:<11} {len(imgs)} screenshot(s) -> assets/project-{p['key']}.svg ({kb} KB)")
        if not imgs:
            print(f"            (none found: add assets/screens/{p['key']}-1.png ...)")


if __name__ == "__main__":
    main()
