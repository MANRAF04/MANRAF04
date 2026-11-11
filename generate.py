import json
import os
import sys
import urllib.request
from calendar import monthrange
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

LOGIN = "MANRAF04"
HERE = Path(__file__).parent
WIDTH = 50
FONT_SIZE = 14
LINE_HEIGHT = 18
CHAR_WIDTH = 8.4
PADDING = 24
INFO_X = 480
SVG_WIDTH = INFO_X + WIDTH * CHAR_WIDTH + PADDING

THEMES = {
    "dark_mode.svg": {"bg": "#0d1117", "text": "#c9d1d9", "key": "#ffa657", "value": "#a5d6ff", "dot": "#616e7f"},
    "light_mode.svg": {"bg": "#f6f8fa", "text": "#24292f", "key": "#953800", "value": "#0a3069", "dot": "#c2cfde"},
}

PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes { stargazerCount }
    }
  }
}
"""


def graphql(query, token, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if body.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {body['errors']}")
    return body["data"]


def total_contributions(token, since_year, now):
    def year_field(year):
        end = min(datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc), now)
        return (
            f'y{year}: contributionsCollection(from: "{year}-01-01T00:00:00Z", to: "{end.isoformat()}") '
            "{ contributionCalendar { totalContributions } }"
        )

    fields = " ".join(year_field(year) for year in range(since_year, now.year + 1))
    query = f'query($login: String!) {{ user(login: $login) {{ {fields} }} }}'
    years = graphql(query, token, {"login": LOGIN})["user"].values()
    return sum(year["contributionCalendar"]["totalContributions"] for year in years)


def plural(n, word):
    return f"{n} {word}{'s' if n != 1 else ''}"


def uptime(since, today):
    months = (today.year - since.year) * 12 + today.month - since.month - (today.day < since.day)
    anchor_year, anchor_month = divmod(since.month - 1 + months, 12)
    anchor_year += since.year
    anchor_month += 1
    anchor_day = min(since.day, monthrange(anchor_year, anchor_month)[1])
    days = (today - date(anchor_year, anchor_month, anchor_day)).days
    years, months = divmod(months, 12)
    return f"{plural(years, 'year')}, {plural(months, 'month')}, {plural(days, 'day')}"


def span(css_class, text):
    return f'<tspan class="{css_class}">{escape(text)}</tspan>'


def key_value(key, value):
    dots = "." * max(1, WIDTH - len(key) - len(value) - 3)
    return f'{span("key", key)}:{span("dot", f" {dots} ")}{span("value", value)}'


def header(title):
    return f'{span("key", title)} {"─" * (WIDTH - len(title) - 1)}'


def info_lines(stats):
    return [
        header("manraf@github"),
        key_value("OS", "EndeavourOS, Linux"),
        key_value("Uptime", stats["uptime"]),
        key_value("Role", "Software Engineer"),
        key_value("Location", "Volos, Greece"),
        key_value("Languages", "Python, Haskell, Dart, C, Rust"),
        key_value("Frameworks", "React, Flutter"),
        "",
        header("Contact"),
        key_value("Portfolio", "manraf04.github.io/portfolio"),
        key_value("GitHub", f"github.com/{LOGIN}"),
        "",
        header("GitHub Stats"),
        key_value("Repos", f"{stats['repos']:,}"),
        key_value("Stars", f"{stats['stars']:,}"),
        key_value("Followers", f"{stats['followers']:,}"),
        key_value("Contributions", f"{stats['contributions']:,}"),
    ]


def render(art, info, colors):
    height = PADDING * 2 + len(art) * LINE_HEIGHT
    first_line_y = PADDING + FONT_SIZE
    info_top = first_line_y + (len(art) - len(info)) // 2 * LINE_HEIGHT
    art_spans = "\n".join(
        f'<tspan x="{PADDING}" y="{first_line_y + i * LINE_HEIGHT}">{escape(line)}</tspan>' for i, line in enumerate(art)
    )
    info_spans = "\n".join(
        f'<tspan x="{INFO_X}" y="{info_top + i * LINE_HEIGHT}">{line}</tspan>' for i, line in enumerate(info)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH:.0f}" height="{height}" font-family="ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace" font-size="{FONT_SIZE}px">
<style>
.key {{ fill: {colors['key']}; }}
.value {{ fill: {colors['value']}; }}
.dot {{ fill: {colors['dot']}; }}
text {{ fill: {colors['text']}; white-space: pre; }}
</style>
<rect width="100%" height="100%" rx="15" fill="{colors['bg']}"/>
<text xml:space="preserve">
{art_spans}
</text>
<text xml:space="preserve">
{info_spans}
</text>
</svg>
"""


def collect_stats(token):
    user = graphql(PROFILE_QUERY, token, {"login": LOGIN})["user"]
    # shortcut: first 100 public repos only, paginate if that is ever exceeded
    repos = user["repositories"]["nodes"]
    created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return {
        "uptime": uptime(created.date(), now.date()),
        "repos": user["repositories"]["totalCount"],
        "stars": sum(repo["stargazerCount"] for repo in repos),
        "followers": user["followers"]["totalCount"],
        "contributions": total_contributions(token, created.year, now),
    }


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GH_TOKEN is not set")
    art = (HERE / "ascii.txt").read_text().rstrip("\n").split("\n")
    info = info_lines(collect_stats(token))
    for filename, colors in THEMES.items():
        (HERE / filename).write_text(render(art, info, colors))


if __name__ == "__main__":
    main()
