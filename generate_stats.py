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
    svg += f'    <text x="490" y="{y_pos}" class="lang-pct">{pct:.1f}%</text>\n'
    svg += f'    <rect x="170" y="{y_pos - 10}" width="300" height="10" rx="5" fill="#21262d"/>\n'
    svg += f'    <rect x="170" y="{y_pos - 10}" width="{bar_width}" height="10" rx="5" fill="{color}"/>\n'
    y_pos += 30

svg += f"""
    <text x="40" y="{y_pos + 10}" class="footer">Updated: {date_str}</text>
</svg>"""

with open("stats.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print("Generated stats.svg successfully!")


# 6. Fetch Contribution Graph Data via GraphQL
graphql_query = """
query($userName:String!) {
  user(login: $userName){
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            contributionCount
            date
            color
          }
        }
      }
    }
  }
}
"""
graph_resp = requests.post(
    'https://api.github.com/graphql', 
    json={'query': graphql_query, 'variables': {'userName': username}}, 
    headers=headers
)

if graph_resp.status_code == 200:
    data = graph_resp.json()
    if 'errors' in data or 'data' not in data:
        print(f"GraphQL Error: {data}")
        # Create a fallback graph.svg with the error
        with open("graph.svg", "w", encoding="utf-8") as f:
            f.write('<svg width="400" height="150" xmlns="http://www.w3.org/2000/svg"><text x="20" y="50" fill="red">GraphQL Error. Check Action logs.</text></svg>')
    else:
        weeks = data['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
        # Get last 5 weeks to cover ~30 days
        recent_weeks = weeks[-5:]
        
        # Flatten all days
        all_days = []
        for w in recent_weeks:
            all_days.extend(w['contributionDays'])
            
        last_30_days = all_days[-30:]
        
        # Generate graph.svg
        graph_svg = f"""<svg width="400" height="150" xmlns="http://www.w3.org/2000/svg">
            <style>
                .title {{ font: bold 16px 'Segoe UI', Arial, sans-serif; fill: #c9d1d9; }}
                .date {{ font: 10px 'Segoe UI', Arial, sans-serif; fill: #8b949e; }}
                .line {{ fill: none; stroke: #39d353; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }}
                .area {{ fill: #39d353; opacity: 0.15; }}
            </style>
            <rect width="400" height="150" rx="12" fill="#0d1117" stroke="#30363d" stroke-width="1"/>
            <text x="20" y="30" class="title">Commit Activity (Last 30 Days)</text>
        """
        
        points = []
        x_pos = 20
        # Determine max commits to scale the graph heights properly
        max_count = max([day['contributionCount'] for day in last_30_days] + [1])
        
        for i, day in enumerate(last_30_days):
            count = day['contributionCount']
            # Scale height proportionally, max 70px
            h = (count / max_count) * 70
            y = 110 - h
            points.append(f"{x_pos},{y}")
            
            # Print dates on X axis roughly every 7 days
            if i == 0 or i == len(last_30_days) - 1 or i % 7 == 0:
                # MM-DD format
                date_short = day['date'][5:] 
                # Adjust text anchor for first/last elements so they don't overflow
                anchor = "start" if i == 0 else "end" if i == len(last_30_days)-1 else "middle"
                graph_svg += f'    <text x="{x_pos}" y="135" class="date" text-anchor="{anchor}">{date_short}</text>\n'
                
            x_pos += 12
            
        path_d = "M " + " L ".join(points)
        area_d = f"M {points[0].split(',')[0]},110 L " + " L ".join(points) + f" L {points[-1].split(',')[0]},110 Z"
        
        graph_svg += f'    <path d="{area_d}" class="area" />\n'
        graph_svg += f'    <path d="{path_d}" class="line" />\n'
        
        # Add interactive points for hover tooltips
        for p, day in zip(points, last_30_days):
            px, py = p.split(',')
            count = day['contributionCount']
            graph_svg += f'    <g><title>{count} commits on {day["date"]}</title>\n'
            graph_svg += f'        <circle cx="{px}" cy="{py}" r="3" fill="#0d1117" stroke="#39d353" stroke-width="1.5"/>\n'
            graph_svg += f'    </g>\n'
            
        graph_svg += "</svg>"
        
        with open("graph.svg", "w", encoding="utf-8") as f:
            f.write(graph_svg)
        print("Generated graph.svg successfully!")
else:
    print(f"GraphQL Error: {graph_resp.text}")
    with open("graph.svg", "w", encoding="utf-8") as f:
        f.write('<svg width="400" height="150" xmlns="http://www.w3.org/2000/svg"><text x="20" y="50" fill="red">API Error. Check Action logs.</text></svg>')
