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

# Collect user emails for commit matching
user_emails = set()
if user.get("email"):
    user_emails.add(user["email"].lower())
user_emails.add(f"{username}@users.noreply.github.com".lower())
if user.get("id"):
    user_emails.add(f"{user['id']}+{username}@users.noreply.github.com".lower())

try:
    emails_resp = requests.get("https://api.github.com/user/emails", headers=headers)
    if emails_resp.status_code == 200:
        for e in emails_resp.json():
            if isinstance(e, dict) and e.get("email"):
                user_emails.add(e["email"].lower())
except Exception as e:
    print(f"Note: Could not fetch user/emails ({e})")

# 2. Get all repositories (paginated)
repos = []
page = 1
while True:
    repos_response = requests.get(
        f"https://api.github.com/user/repos?per_page=100&page={page}&affiliation=owner,collaborator,organization_member&sort=pushed&direction=desc",
        headers=headers
    )
    if repos_response.status_code != 200:
        break
    data = repos_response.json()
    if not isinstance(data, list) or not data:
        break
    repos.extend(data)
    if len(data) < 100:
        break
    page += 1

repo_count = len(repos)
total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)

# 3. Languages
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

# 4. Fetch Commits Across ALL Branches for the Last 30 Days
now_utc = datetime.datetime.now(datetime.timezone.utc)
thirty_days_ago_dt = now_utc - datetime.timedelta(days=30)
since_iso = thirty_days_ago_dt.strftime("%Y-%m-%dT00:00:00Z")

print("Fetching commits for the last 30 days across all branches...")

seen_shas = set()
daily_counts = {}

def process_commit(sha, commit_date_str, author_login, author_email, author_name, repo_owner):
    if not sha or sha in seen_shas:
        return
    
    author_login_l = (author_login or "").lower()
    author_email_l = (author_email or "").lower()
    author_name_l = (author_name or "").lower()
    
    is_user = False
    if author_login_l and author_login_l == username.lower():
        is_user = True
    elif author_email_l and author_email_l in user_emails:
        is_user = True
    elif author_name_l and name and author_name_l == name.lower():
        is_user = True
    elif repo_owner.lower() == username.lower():
        if author_email_l in user_emails or (name and author_name_l == name.lower()) or (not author_login_l and not author_email_l):
            is_user = True
            
    if is_user:
        seen_shas.add(sha)
        if commit_date_str:
            date_key = commit_date_str[:10]
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

gql_query = """
query($owner: String!, $name: String!, $since: GitTimestamp!) {
  repository(owner: $owner, name: $name) {
    refs(refPrefix: "refs/heads/", first: 100) {
      nodes {
        name
        target {
          ... on Commit {
            history(since: $since, first: 100) {
              nodes {
                oid
                committedDate
                authoredDate
                author {
                  name
                  email
                  user {
                    login
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

for repo in repos:
    pushed_at_str = repo.get("pushed_at")
    if not pushed_at_str:
        continue
    try:
        pushed_at_dt = datetime.datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
        if pushed_at_dt < thirty_days_ago_dt:
            continue
    except Exception:
        pass
    
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    if not owner or not repo_name:
        continue

    # Try GraphQL first for efficient multi-branch commit retrieval
    gql_success = False
    try:
        variables = {"owner": owner, "name": repo_name, "since": since_iso}
        gql_resp = requests.post(
            "https://api.github.com/graphql",
            json={"query": gql_query, "variables": variables},
            headers=headers
        )
        if gql_resp.status_code == 200:
            data = gql_resp.json().get("data", {})
            repo_data = data.get("repository") if data else None
            if repo_data and "refs" in repo_data and repo_data["refs"]:
                gql_success = True
                for ref_node in repo_data["refs"].get("nodes", []):
                    target = ref_node.get("target")
                    if not target or "history" not in target:
                        continue
                    for commit_node in target["history"].get("nodes", []):
                        oid = commit_node.get("oid")
                        commit_date = commit_node.get("authoredDate") or commit_node.get("committedDate")
                        author_info = commit_node.get("author") or {}
                        author_user = author_info.get("user") or {}
                        author_login = author_user.get("login") or ""
                        author_email = author_info.get("email") or ""
                        author_name = author_info.get("name") or ""
                        
                        process_commit(oid, commit_date, author_login, author_email, author_name, owner)
    except Exception as e:
        print(f"GraphQL note for {owner}/{repo_name}: {e}")

    # Fallback to REST API if GraphQL was unsuccessful
    if not gql_success:
        try:
            branches_resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/branches?per_page=100",
                headers=headers
            )
            if branches_resp.status_code == 200:
                branches = branches_resp.json()
                if isinstance(branches, list):
                    for branch in branches:
                        bname = branch.get("name")
                        if not bname:
                            continue
                        commits_resp = requests.get(
                            f"https://api.github.com/repos/{owner}/{repo_name}/commits?sha={bname}&since={since_iso}&per_page=100",
                            headers=headers
                        )
                        if commits_resp.status_code == 200:
                            branch_commits = commits_resp.json()
                            if isinstance(branch_commits, list):
                                for item in branch_commits:
                                    sha = item.get("sha")
                                    commit_obj = item.get("commit", {})
                                    commit_author = commit_obj.get("author", {})
                                    commit_date = commit_author.get("date") or commit_obj.get("committer", {}).get("date")
                                    author_obj = item.get("author") or {}
                                    author_login = author_obj.get("login") or ""
                                    author_email = commit_author.get("email") or ""
                                    author_name = commit_author.get("name") or ""
                                    
                                    process_commit(sha, commit_date, author_login, author_email, author_name, owner)
        except Exception as e:
            print(f"REST note for {owner}/{repo_name}: {e}")

recent_commits = len(seen_shas)
print(f"Total commits found across all branches (last 30 days): {recent_commits}")

# 5. Generate Professional stats.svg
date_str = now_utc.strftime("%d %b %Y")
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


# 6. Generate Contribution Activity Graph (graph.svg)
last_30_days = []
for i in range(29, -1, -1):
    d = (now_utc - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
    last_30_days.append({
        "date": d,
        "contributionCount": daily_counts.get(d, 0)
    })

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
    <text x="{W//2}" y="40" class="title" text-anchor="middle">{name}'s Last 30 Days Commits</text>
    
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
    graph_svg += f'    <line x1="{M_LEFT}" y1="{y}" x2="{M_LEFT + GW}" y2="{y}" class="grid"/>\n'
    graph_svg += f'    <text x="{M_LEFT - 15}" y="{y + 4}" class="tick-label" text-anchor="end">{val}</text>\n'
    
# Vertical grid lines, X-axis labels, and points
points = []
for i, day in enumerate(last_30_days):
    x = M_LEFT + (i / 29) * GW
    count = day['contributionCount']
    y = M_TOP + GH - (count / y_max) * GH
    points.append(f"{x},{y}")
    
    # X-axis tick
    day_num = int(day['date'][-2:])
    graph_svg += f'    <line x1="{x}" y1="{M_TOP}" x2="{x}" y2="{M_TOP + GH}" class="grid"/>\n'
    graph_svg += f'    <text x="{x}" y="{M_TOP + GH + 20}" class="tick-label" text-anchor="middle">{day_num}</text>\n'
    
path_d = "M " + " L ".join(points)
graph_svg += f'    <path d="{path_d}" class="line" />\n'

# Draw interactive dots
for p, day in zip(points, last_30_days):
    px, py = p.split(',')
    count = day['contributionCount']
    graph_svg += f'    <g><title>{count} commits on {day["date"]}</title>\n'
    graph_svg += f'        <circle cx="{px}" cy="{py}" r="4" class="dot"/>\n'
    graph_svg += f'    </g>\n'
    
graph_svg += "</svg>"

with open("graph.svg", "w", encoding="utf-8") as f:
    f.write(graph_svg)
print("Generated graph.svg successfully!")
