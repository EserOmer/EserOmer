"""GitHub profil istatistik kartlarını (SVG) üretir.

GITHUB_TOKEN ile GraphQL API'den herkese açık verileri çeker ve
assets/ altına açık ve koyu tema için iki kart yazar:
  stats-dark.svg, stats-light.svg, langs-dark.svg, langs-light.svg
"""
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "EserOmer")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

THEMES = {
    "dark": {"bg": "#0E1116", "border": "#30363D", "text": "#E6EAF0",
             "muted": "#9AA4B2", "accent": "#3DD6B5", "track": "#1F2630"},
    "light": {"bg": "#FFFFFF", "border": "#D0D7DE", "text": "#1F2328",
              "muted": "#59636E", "accent": "#0F8A72", "track": "#EAEEF2"},
}
FONT = "'Segoe UI', Helvetica, Arial, sans-serif"


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-stats"})
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL hatası: {data['errors']}")
    return data["data"]["user"]


def fmt(n):
    return f"{n/1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def stats_svg(u, t):
    repos = u["repositories"]
    cc = u["contributionsCollection"]
    rows = [
        ("Son 1 yılın katkıları", cc["contributionCalendar"]["totalContributions"]),
        ("Commit (son 1 yıl)", cc["totalCommitContributions"]),
        ("Pull request", u["pullRequests"]["totalCount"]),
        ("Herkese açık repo", repos["totalCount"]),
        ("Toplam yıldız", sum(n["stargazerCount"] for n in repos["nodes"])),
        ("Takipçi", u["followers"]["totalCount"]),
    ]
    lines = []
    for i, (label, val) in enumerate(rows):
        y = 74 + i * 24
        lines.append(
            f'<circle cx="32" cy="{y - 5}" r="4" fill="{t["accent"]}"/>'
            f'<text x="46" y="{y}" fill="{t["muted"]}" font-size="14">{escape(label)}</text>'
            f'<text x="463" y="{y}" fill="{t["text"]}" font-size="14" font-weight="700" text-anchor="end">{fmt(val)}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="230" viewBox="0 0 495 230" '
            f'role="img" aria-label="{USER} GitHub istatistikleri">'
            f'<rect x="0.5" y="0.5" width="494" height="229" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'<g font-family="{FONT}">'
            f'<text x="24" y="38" fill="{t["accent"]}" font-size="17" font-weight="700">GitHub istatistikleri</text>'
            + "".join(lines) + '</g></svg>')


def langs_svg(u, t, top=6):
    totals = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            prev = totals.get(name, (0, e["node"]["color"]))
            totals[name] = (prev[0] + e["size"], e["node"]["color"] or "#8B949E")
    items = sorted(totals.items(), key=lambda kv: kv[1][0], reverse=True)[:top]
    total = sum(v[0] for _, v in items) or 1
    bar, x = [], 24.0
    for name, (size, color) in items:
        w = 447 * size / total
        bar.append(f'<rect x="{x:.2f}" y="56" width="{w:.2f}" height="10" fill="{color}"/>')
        x += w
    legend = []
    for i, (name, (size, color)) in enumerate(items):
        col, row = i % 2, i // 2
        lx, ly = 24 + col * 230, 100 + row * 28
        legend.append(
            f'<circle cx="{lx + 5}" cy="{ly - 5}" r="5" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{ly}" fill="{t["text"]}" font-size="14">{escape(name)}'
            f'<tspan fill="{t["muted"]}"> {100 * size / total:.1f}%</tspan></text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="230" viewBox="0 0 495 230" '
            f'role="img" aria-label="En çok kullanılan diller">'
            f'<rect x="0.5" y="0.5" width="494" height="229" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'<clipPath id="r"><rect x="24" y="56" width="447" height="10" rx="5"/></clipPath>'
            f'<rect x="24" y="56" width="447" height="10" rx="5" fill="{t["track"]}"/>'
            f'<g clip-path="url(#r)">' + "".join(bar) + '</g>'
            f'<g font-family="{FONT}">'
            f'<text x="24" y="38" fill="{t["accent"]}" font-size="17" font-weight="700">En çok kullanılan diller</text>'
            + "".join(legend) + '</g></svg>')


def main():
    if not TOKEN:
        sys.exit("GITHUB_TOKEN tanımlı değil")
    u = fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, t in THEMES.items():
        with open(os.path.join(OUT, f"stats-{name}.svg"), "w", encoding="utf-8") as f:
            f.write(stats_svg(u, t))
        with open(os.path.join(OUT, f"langs-{name}.svg"), "w", encoding="utf-8") as f:
            f.write(langs_svg(u, t))
    print("Kartlar güncellendi.")


if __name__ == "__main__":
    main()
