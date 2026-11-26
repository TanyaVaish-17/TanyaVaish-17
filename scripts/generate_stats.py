#!/usr/bin/env python3
"""
Generates assets/github-stats.svg and assets/github-heatmap.svg straight from the
GitHub GraphQL API, using the workflow's built-in GITHUB_TOKEN. No third-party
stats service, so nothing to rate-limit.

  GH_TOKEN=... GH_USER=TanyaVaish-17 python scripts/generate_stats.py
  python scripts/generate_stats.py --demo      # placeholder output, no network
"""
import datetime as dt, json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "TanyaVaish-17"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

INK, PAPER, MUTED, LINE, ACCENT = "#0e0f11", "#efebe4", "#8c8880", "#2a2c30", "#d6a572"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
LANG_TONES = ["#d6a572", "#b98a5a", "#9a7048", "#7d7468", "#625f5a", "#4b4a47", "#37363a"]

QUERY = """
query($login:String!){
  user(login:$login){
    followers{totalCount}
    repositories(ownerAffiliations:OWNER, privacy:PUBLIC, first:100){
      totalCount
      nodes{ stargazerCount languages(first:8, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } }
    }
    contributionsCollection{
      contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount date } } }
    }
  }
}"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload or not payload.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {payload.get('errors')}")
    u = payload["data"]["user"]
    langs = {}
    stars = 0
    for repo in u["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    return dict(repos=u["repositories"]["totalCount"], stars=stars, followers=u["followers"]["totalCount"],
                total=cal["totalContributions"], weeks=[[d for d in w["contributionDays"]] for w in cal["weeks"]],
                langs=langs)


def demo():
    today = dt.date.today()
    start = today - dt.timedelta(days=today.weekday() + 1 + 52 * 7)
    weeks = []
    for w in range(53):
        weeks.append([dict(date=(start + dt.timedelta(days=w * 7 + d)).isoformat(), contributionCount=0) for d in range(7)])
    return dict(repos=None, stars=None, followers=None, total=None, weeks=weeks, langs={})


def streaks(weeks):
    days = [d for w in weeks for d in w]
    days.sort(key=lambda d: d["date"])
    today = dt.date.today().isoformat()
    days = [d for d in days if d["date"] <= today]
    longest = cur = 0
    for d in days:
        cur = cur + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, cur)
    cur = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            cur += 1
        elif d["date"] == today:
            continue  # today may not have contributions yet
        else:
            break
    return cur, longest


def fmt(v):
    return "—" if v is None else f"{v:,}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fade(delay):
    total = delay + 0.8
    return f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{delay / total:.4f};1" dur="{total:.2f}s" fill="freeze"/>'


def stats_svg(d):
    cur, longest = streaks(d["weeks"])
    if d["total"] is None:
        cur = longest = None
    cols = [("Public repositories", d["repos"]), ("Stars earned", d["stars"]),
            ("Contributions · last year", d["total"]), ("Current streak (days)", cur), ("Longest streak (days)", longest)]
    W, H = 1200, 270
    cw = (W - 80) / len(cols)
    body = ""
    for i, (label, val) in enumerate(cols):
        x = 40 + i * cw
        if i:
            body += f'<rect x="{x:.0f}" y="40" width="1" height="64" fill="{LINE}"/>'
        body += (f'<g opacity="0">{fade(0.1 + i * 0.12)}<text x="{x + cw / 2:.0f}" y="82" text-anchor="middle" font-family="{SERIF}" font-size="40" fill="{PAPER}">{fmt(val)}</text>'
                 f'<text x="{x + cw / 2:.0f}" y="106" text-anchor="middle" font-family="{SANS}" font-size="10.5" letter-spacing="1.8" fill="{MUTED}">{esc(label.upper())}</text></g>')
    # languages
    langs = sorted(d["langs"].items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in langs) or 1
    top = langs[:6]
    other = sum(v for _, v in langs[6:])
    if other:
        top.append(("Other", other))
    body += f'<text x="40" y="162" font-family="{SANS}" font-size="10.5" letter-spacing="2" fill="{ACCENT}">LANGUAGES</text>'
    bx, bw = 40, 1120
    if not top:
        body += f'<rect x="{bx}" y="176" width="{bw}" height="8" rx="4" fill="#1a1b1e"/><text x="40" y="214" font-family="{SANS}" font-size="12" fill="{MUTED}">Fills in after the first workflow run.</text>'
    else:
        body += '<clipPath id="lb"><rect x="40" y="176" width="1120" height="8" rx="4"/></clipPath><g clip-path="url(#lb)">'
        x = bx
        for i, (name, v) in enumerate(top):
            wd = bw * v / total
            body += (f'<rect x="{x:.1f}" y="176" width="{wd:.1f}" height="8" fill="{LANG_TONES[i % len(LANG_TONES)]}">'
                     f'<animate attributeName="width" values="0;{wd:.1f}" dur="1.1s" begin="{0.2 + i * 0.1:.1f}s" fill="freeze"/></rect>')
            x += wd
        body += "</g>"
        lx = 40
        for i, (name, v) in enumerate(top):
            label = f"{name}  {100 * v / total:.0f}%"
            body += (f'<circle cx="{lx + 4}" cy="212" r="4" fill="{LANG_TONES[i % len(LANG_TONES)]}"/>'
                     f'<text x="{lx + 16}" y="216" font-family="{SANS}" font-size="12.5" fill="#c9c5bd">{esc(label)}</text>')
            lx += 16 + len(label) * 7.2 + 26
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="{INK}" stroke="{LINE}"/>{body}</svg>')


def heatmap_svg(d):
    weeks = d["weeks"]
    n = len(weeks)
    pitch, cell = 18, 14
    W = 1200
    x0 = (W - n * pitch) / 2
    y0 = 78
    H = 232
    mx = max([day["contributionCount"] for w in weeks for day in w] + [1])
    def shade(c):
        if c <= 0:
            return "#1a1b1e", 1
        lvl = min(4, 1 + int(3 * (c - 1) / max(mx - 1, 1) + 0.0001))
        return ACCENT, (0.28, 0.5, 0.75, 1.0)[lvl - 1]
    body, last_month = "", None
    for ci, w in enumerate(weeks):
        dly = ci * 0.02
        total = dly + 0.6
        g = f'<g opacity="0"><animate attributeName="opacity" values="0;0;1" keyTimes="0;{dly / total:.4f};1" dur="{total:.2f}s" fill="freeze"/>'
        for ri, day in enumerate(w):
            col, op = shade(day["contributionCount"])
            g += f'<rect x="{x0 + ci * pitch:.0f}" y="{y0 + ri * pitch}" width="{cell}" height="{cell}" rx="3" fill="{col}" fill-opacity="{op}"><title>{day["date"]}: {day["contributionCount"]}</title></rect>'
        body += g + "</g>"
        m = dt.date.fromisoformat(w[0]["date"]).strftime("%b")
        if m != last_month and ci < n - 2:
            body += f'<text x="{x0 + ci * pitch:.0f}" y="{y0 - 12}" font-family="{SANS}" font-size="10.5" fill="{MUTED}">{m}</text>'
            last_month = m
    total_txt = "—" if d["total"] is None else f"{d['total']:,}"
    head = (f'<text x="{x0:.0f}" y="40" font-family="{SANS}" font-size="10.5" letter-spacing="2" fill="{ACCENT}">CONTRIBUTIONS</text>'
            f'<text x="{x0 + n * pitch - 4:.0f}" y="40" text-anchor="end" font-family="{SERIF}" font-size="15" fill="{PAPER}">{total_txt} <tspan font-family="{SANS}" font-size="11" fill="{MUTED}">in the last year</tspan></text>')
    ly = y0 + 7 * pitch + 14
    legend = f'<text x="{x0 + n * pitch - 4 - 5 * 18 - 36:.0f}" y="{ly + 10}" text-anchor="end" font-family="{SANS}" font-size="10.5" fill="{MUTED}">Less</text>'
    for i, (c, o) in enumerate([("#1a1b1e", 1), (ACCENT, .28), (ACCENT, .5), (ACCENT, .75), (ACCENT, 1)]):
        legend += f'<rect x="{x0 + n * pitch - 4 - (5 - i) * 18 - 14:.0f}" y="{ly}" width="{cell - 2}" height="{cell - 2}" rx="3" fill="{c}" fill-opacity="{o}"/>'
    legend += f'<text x="{x0 + n * pitch - 4 - 10:.0f}" y="{ly + 10}" font-family="{SANS}" font-size="10.5" fill="{MUTED}">More</text>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="{INK}" stroke="{LINE}"/>{head}{body}{legend}</svg>')


def main():
    if "--demo" in sys.argv or not TOKEN:
        if "--demo" not in sys.argv:
            print("No GH_TOKEN found - writing placeholder cards")
        d = demo()
    else:
        d = fetch()
    open(os.path.join(ASSETS, "github-stats.svg"), "w", encoding="utf-8").write(stats_svg(d))
    open(os.path.join(ASSETS, "github-heatmap.svg"), "w", encoding="utf-8").write(heatmap_svg(d))
    print("wrote assets/github-stats.svg and assets/github-heatmap.svg")


if __name__ == "__main__":
    main()
