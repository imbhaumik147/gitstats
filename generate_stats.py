import os
import requests
import datetime

TOKEN = os.environ.get("GH_TOKEN")
if not TOKEN:
    print("Error: GH_TOKEN environment variable not set.")
    exit(1)

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

# 1. User details
response = requests.get("https://api.github.com/user", headers=headers)
if response.status_code != 200:
    print(f"Error fetching user: {response.text}")
    exit(1)
user = response.json()
username = user.get("login")
name = user.get("name") or username

# 2. Get repositories
repos_response = requests.get("https://api.github.com/user/repos?per_page=100&type=all", headers=headers)
repos = repos_response.json() if repos_response.status_code == 200 else []

repo_count = len(repos)
total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)

# 3. Last 30 Days Commits
thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
recent_commits_resp = requests.get(f"https://api.github.com/search/commits?q=author:{username}+committer-date:>{thirty_days_ago}", headers=headers)
recent_commits = recent_commits_resp.json().get('total_count', 0) if recent_commits_resp.status_code == 200 else 0

# 4. Languages
languages = {}
for repo in repos:
    languages_url = repo.get("languages_url")
    if languages_url:
        lang_resp = requests.get(languages_url, headers=headers)
        if lang_resp.status_code == 200:
            for lang, bytes_count in lang_resp.json().items():
                languages[lang] = languages.get(lang, 0) + bytes_count

total_bytes = sum(languages.values())
language_percentages = {lang: (count / total_bytes * 100) for lang, count in languages.items()} if total_bytes > 0 else {}
top_languages = sorted(language_percentages.items(), key=lambda x: x[1], reverse=True)[:4]

# 5. Generate Professional stats.svg
date_str = datetime.datetime.now().strftime("%d %b %Y")
svg = f"""<svg width="600" height="420" xmlns="http://www.w3.org/2000/svg">
    <style>
        .header {{ font: bold 22px 'Segoe UI', Arial, sans-serif; fill: #58a6ff; }}
        .name {{ font: bold 18px 'Segoe UI', Arial, sans-serif; fill: #c9d1d9; }}
        .box {{ fill: #161b22; stroke: #30363d; stroke-width: 1; rx: 6; }}
        .box-num {{ font: bold 24px 'Segoe UI', Arial, sans-serif; fill: #ffffff; }}
        .box-text {{ font: 12px 'Segoe UI', Arial, sans-serif; fill: #8b949e; font-weight: bold; }}
        .title {{ font: bold 16px 'Segoe UI', Arial, sans-serif; fill: #c9d1d9; }}
        .lang-text {{ font: 14px 'Segoe UI', Arial, sans-serif; fill: #c9d1d9; }}
        .lang-pct {{ font: 14px 'Segoe UI', Arial, sans-serif; fill: #8b949e; text-anchor: end; }}
        .footer {{ font: 12px 'Segoe UI', Arial, sans-serif; fill: #8b949e; }}
    </style>
    <rect width="600" height="420" rx="12" fill="#0d1117" stroke="#30363d" stroke-width="1"/>
    
    <text x="40" y="50" class="header">⚡ GITHUB STATISTICS</text>
    <text x="40" y="80" class="name">{name}</text>
    
    <!-- Boxes -->
    <rect x="40" y="110" width="160" height="80" class="box" />
    <text x="120" y="150" class="box-num" text-anchor="middle">{repo_count}</text>
    <text x="120" y="175" class="box-text" text-anchor="middle">REPOS</text>
    
    <rect x="220" y="110" width="160" height="80" class="box" />
    <text x="300" y="150" class="box-num" text-anchor="middle">{total_stars}</text>
    <text x="300" y="175" class="box-text" text-anchor="middle">STARS</text>
    
    <rect x="400" y="110" width="160" height="80" class="box" />
    <text x="480" y="150" class="box-num" text-anchor="middle">{recent_commits}</text>
    <text x="480" y="175" class="box-text" text-anchor="middle">COMMITS (30D)</text>
    
    <!-- Languages -->
    <text x="40" y="240" class="title">TOP LANGUAGES</text>
"""

y_pos = 270
colors = ["#f1e05a", "#4F5D95", "#00B4AB", "#e34c26", "#58a6ff"]
for i, (lang, pct) in enumerate(top_languages):
    bar_width = int(pct * 3) # max 300px
    color = colors[i % len(colors)]
    svg += f'    <text x="40" y="{y_pos}" class="lang-text">{lang}</text>\n'
    svg += f'    <rect x="170" y="{y_pos - 10}" width="300" height="10" rx="5" fill="#21262d"/>\n'
    svg += f'    <rect x="170" y="{y_pos - 10}" width="{bar_width}" height="10" rx="5" fill="{color}"/>\n'
    svg += f'    <text x="540" y="{y_pos}" class="lang-pct">{pct:.1f}%</text>\n'
    y_pos += 30

svg += f"""
    <text x="40" y="{y_pos + 10}" class="footer">Updated: {date_str}</text>
</svg>"""

with open("stats.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print("Generated stats.svg successfully!")


# 6. Fetch Commit Graph Data (All Branches) via Search API
import datetime

# Generate last 30 days list
today = datetime.datetime.now()
last_30_days_dates = [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
commits_per_day = {d: 0 for d in last_30_days_dates}

page = 1
while True:
    search_url = f"https://api.github.com/search/commits?q=author:{username}+committer-date:>{thirty_days_ago}&per_page=100&page={page}"
    search_resp = requests.get(search_url, headers=headers)
    if search_resp.status_code == 200:
        data = search_resp.json()
        items = data.get('items', [])
        if not items:
            break
        for item in items:
            commit_date_time = item.get('commit', {}).get('committer', {}).get('date', '')
            if commit_date_time:
                date_part = commit_date_time.split('T')[0]
                try:
                    time_part = commit_date_time.split('T')[1].replace('Z', '')
                    time_part = time_part.split('+')[0].split('-')[0].split('.')[0]
                    dt_str = f"{date_part}T{time_part}+0000"
                    dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")
                except Exception:
                    dt = None
                
                if dt:
                    # Convert to local time
                    local_dt = dt.astimezone()
                    date_str = local_dt.strftime("%Y-%m-%d")
                    
                    if date_str in commits_per_day:
                        commits_per_day[date_str] += 1

        
        if len(items) < 100 or page >= 10: # limit to 10 pages to avoid rate limits
            break
        page += 1
    else:
        print(f"Search API Error: {search_resp.text}")
        break

# Create last_30_days list with structure similar to old data
last_30_days = [{'date': d, 'contributionCount': commits_per_day[d]} for d in last_30_days_dates]

# Graph dimensions and margins
W, H = 800, 300
M_LEFT, M_RIGHT, M_TOP, M_BOTTOM = 70, 30, 60, 50
GW = W - M_LEFT - M_RIGHT
GH = H - M_TOP - M_BOTTOM

# Calculate max Y value, rounded up to nearest 5
max_count = max([day['contributionCount'] for day in last_30_days] + [1])
y_max = max(5, ((max_count + 4) // 5) * 5)

graph_svg = f"""<svg width="100%" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
    <style>
        .bg {{ fill: #0d1117; }}
        .title {{ font: bold 20px 'Segoe UI', Arial, sans-serif; fill: #38bdf8; }}
        .axis-label {{ font: bold 12px 'Segoe UI', Arial, sans-serif; fill: #38bdf8; }}
        .tick-label {{ font: 12px 'Segoe UI', Arial, sans-serif; fill: #c9d1d9; }}
        .grid {{ stroke: #30363d; stroke-width: 1; stroke-dasharray: 4 4; }}
        .line {{ fill: none; stroke: #38bdf8; stroke-width: 4; stroke-linejoin: round; }}
        .dot {{ fill: #ffffff; stroke: #38bdf8; stroke-width: 2; }}
    </style>
    <rect width="{W}" height="{H}" rx="12" class="bg" stroke="#30363d" stroke-width="1"/>
    <text x="{W//2}" y="40" class="title" text-anchor="middle">{name}'s Commit Graph (All Branches)</text>
    
    <!-- Axis Titles -->
    <text x="25" y="{M_TOP + GH//2}" class="axis-label" text-anchor="middle" transform="rotate(-90 25,{M_TOP + GH//2})">Commits</text>
    <text x="{M_LEFT + GW//2}" y="{H - 15}" class="axis-label" text-anchor="middle">Days</text>
"""

# Draw horizontal grid lines and Y-axis labels
step = max(1, y_max // 5)
if step > 2 and step % 5 != 0: step = ((step + 4) // 5) * 5

y_ticks = list(range(0, y_max + 1, step))
if y_max not in y_ticks: y_ticks.append(y_max)

for val in y_ticks:
    y = M_TOP + GH - (val / y_max) * GH
    graph_svg += f'    <line x1="{M_LEFT}" y1="{y}" x2="{M_LEFT + GW}" y2="{y}" class="grid"/>\\n'
    graph_svg += f'    <text x="{M_LEFT - 15}" y="{y + 4}" class="tick-label" text-anchor="end">{val}</text>\\n'
    
# Vertical grid lines, X-axis labels, and points
points = []
for i, day in enumerate(last_30_days):
    x = M_LEFT + (i / 29) * GW
    count = day['contributionCount']
    y = M_TOP + GH - (count / y_max) * GH
    points.append(f"{x},{y}")
    
    # X-axis tick
    day_num = int(day['date'][-2:])
    graph_svg += f'    <line x1="{x}" y1="{M_TOP}" x2="{x}" y2="{M_TOP + GH}" class="grid"/>\\n'
    graph_svg += f'    <text x="{x}" y="{M_TOP + GH + 20}" class="tick-label" text-anchor="middle">{day_num}</text>\\n'
    
path_d = "M " + " L ".join(points)
graph_svg += f'    <path d="{path_d}" class="line" />\\n'

# Draw interactive dots
for p, day in zip(points, last_30_days):
    px, py = p.split(',')
    count = day['contributionCount']
    graph_svg += f'    <g><title>{count} commits on {day["date"]}</title>\\n'
    graph_svg += f'        <circle cx="{px}" cy="{py}" r="4" class="dot"/>\\n'
    graph_svg += f'    </g>\\n'
    
graph_svg += "</svg>"

with open("graph.svg", "w", encoding="utf-8") as f:
    f.write(graph_svg)
print("Generated graph.svg successfully!")
