"""Add real, public-profile activity counters to generated circuit SVGs."""
import os
import json
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

query = """query($login:String!){user(login:$login){contributionsCollection{
 contributionCalendar{totalContributions}
 totalCommitContributions totalPullRequestContributions
 totalIssueContributions totalPullRequestReviewContributions
}}}"""
request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": query, "variables": {"login": os.environ["PROFILE_USER"]}}).encode(),
    headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json", "User-Agent": "profile-circuit-telemetry"},
)
with urllib.request.urlopen(request, timeout=30) as response:
    result = json.load(response)
if result.get("errors"):
    raise RuntimeError("GitHub contribution query failed")
stats = result["data"]["user"]["contributionsCollection"]
metrics = [
    ("CONTRIBUTIONS", stats["contributionCalendar"]["totalContributions"]),
    ("COMMITS", stats["totalCommitContributions"]),
    ("PULL REQUESTS", stats["totalPullRequestContributions"]),
    ("ISSUES", stats["totalIssueContributions"]),
    ("REVIEWS", stats["totalPullRequestReviewContributions"]),
]
for path in Path("dist").glob("circuit-v1-*.svg"):
    source = path.read_text()
    root = ET.fromstring(source)
    width, height = map(float, root.attrib["viewBox"].split()[2:])
    dark = "-dark" in path.name
    bg, border, fg, muted, accent = (
        ("#090d14", "#33474f", "#edf7f1", "#a0b9bc", "#a5ffb8") if dark else
        ("#edf0e7", "#9baea5", "#172d2b", "#45625d", "#176b40")
    )
    pad = 12
    header = 88
    gap = 9
    cw = (width - 2*pad - 4*gap)/5
    pieces = [
        f'<rect x="1" y="1" width="{width-2}" height="{height+header-2}" rx="7" fill="{bg}" stroke="{border}"/>',
        f'<g font-family="monospace"><text x="12" y="20" font-size="12" fill="{accent}" letter-spacing="1.4">05 / ACTIVITY BUS</text>',
        f'<text x="{width-12}" y="20" text-anchor="end" font-size="10" fill="{muted}">GITHUB / LAST YEAR</text>',
        f'<path d="M12 76H{width-12}" stroke="{border}" fill="none"/>',
    ]
    for i, (label, value) in enumerate(metrics):
        x = pad+i*(cw+gap)
        center = x+cw/2
        pieces.append(f'<g><path d="M{center} 71V76" stroke="{accent}" fill="none"/><circle cx="{center}" cy="76" r="2" fill="{accent}"/>'
                      f'<rect x="{x}" y="29" width="{cw}" height="42" rx="3" fill="{bg}" stroke="{border}"/>'
                      f'<text x="{x+8}" y="42" font-size="9" fill="{muted}">{label}</text>'
                      f'<text x="{x+8}" y="61" font-size="17" font-weight="bold" fill="{fg}">{value:,}</text></g>')
    pieces.append('</g>')
    # Nest the original SVG intact, preserving its viewBox and CSS transforms.
    source = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height+header}" viewBox="0 0 {width} {height+header}" role="img" aria-label="GitHub contribution circuit and last-year activity metrics">' + "".join(pieces) + f'<g transform="translate(0 {header})">'+source+'</g></svg>'
    ET.fromstring(source)
    path.write_text(source)
