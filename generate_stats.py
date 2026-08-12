import os
import requests
import datetime

# The token is read from the environment variable GH_TOKEN
TOKEN = os.environ.get("GH_TOKEN")
if not TOKEN:
    print("Error: GH_TOKEN environment variable not set.")
    exit(1)

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

# 1. Get your profile details
response = requests.get("https://api.github.com/user", headers=headers)
if response.status_code != 200:
    print(f"Error fetching user: {response.text}")
    exit(1)

user = response.json()
username = user.get("login")
print(f"Generating stats for {username}...")

# 2. Get your repositories (including private if token allows)
repos_response = requests.get("https://api.github.com/user/repos?per_page=100&type=all", headers=headers)
if repos_response.status_code != 200:
    print(f"Error fetching repos: {repos_response.text}")
    exit(1)

repos = repos_response.json()
repo_count = len(repos)
total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
total_forks = sum(repo.get("forks_count", 0) for repo in repos)

# 3. Get Advanced Stats (Commits, PRs)
# Total PRs
pr_resp = requests.get(f"https://api.github.com/search/issues?q=author:{username}+type:pr", headers=headers)
total_prs = pr_resp.json().get('total_count', 0) if pr_resp.status_code == 200 else 0

# Total Commits
commits_resp = requests.get(f"https://api.github.com/search/commits?q=author:{username}", headers=headers)
total_commits = commits_resp.json().get('total_count', 0) if commits_resp.status_code == 200 else 0

# Last 30 Days Commits
thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
recent_commits_resp = requests.get(f"https://api.github.com/search/commits?q=author:{username}+committer-date:>{thirty_days_ago}", headers=headers)
recent_commits = recent_commits_resp.json().get('total_count', 0) if recent_commits_resp.status_code == 200 else 0

# 4. Calculate languages
languages = {}
for repo in repos:
    # Get languages for each repository
    languages_url = repo.get("languages_url")
    if languages_url:
        lang_resp = requests.get(languages_url, headers=headers)
        if lang_resp.status_code == 200:
        repo_langs = lang_resp.json()
        for lang, bytes_count in repo_langs.items():
            languages[lang] = languages.get(lang, 0) + bytes_count

# Calculate language percentages
total_bytes = sum(languages.values())
if total_bytes > 0:
    language_percentages = {lang: (count / total_bytes * 100) for lang, count in languages.items()}
else:
    language_percentages = {}
# Sort languages by percentage descending
top_languages = sorted(language_percentages.items(), key=lambda x: x[1], reverse=True)[:5]

print("Top Languages:")
for lang, pct in top_languages:
    print(f"{lang}: {pct:.1f}%")

# 5. Generate Stats SVG (Without Languages, With Commits & PRs)
svg = f"""<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect width="400" height="300" rx="12" fill="#0d1117"/>
    <text x="30" y="45" fill="white" font-size="22" font-family="Arial, sans-serif" font-weight="bold">GitHub Statistics</text>
    
    <text x="30" y="90" fill="#c9d1d9" font-size="16" font-family="Arial, sans-serif">Repositories:</text>
    <text x="370" y="90" fill="white" font-size="16" font-family="Arial, sans-serif" font-weight="bold" text-anchor="end">{repo_count}</text>

    <text x="30" y="125" fill="#c9d1d9" font-size="16" font-family="Arial, sans-serif">Stars Earned:</text>
    <text x="370" y="125" fill="white" font-size="16" font-family="Arial, sans-serif" font-weight="bold" text-anchor="end">{total_stars}</text>

    <text x="30" y="160" fill="#c9d1d9" font-size="16" font-family="Arial, sans-serif">Total Commits:</text>
    <text x="370" y="160" fill="white" font-size="16" font-family="Arial, sans-serif" font-weight="bold" text-anchor="end">{total_commits}</text>

    <text x="30" y="195" fill="#c9d1d9" font-size="16" font-family="Arial, sans-serif">Commits (Last 30 Days):</text>
    <text x="370" y="195" fill="#58a6ff" font-size="16" font-family="Arial, sans-serif" font-weight="bold" text-anchor="end">{recent_commits}</text>

    <text x="30" y="230" fill="#c9d1d9" font-size="16" font-family="Arial, sans-serif">Pull Requests:</text>
    <text x="370" y="230" fill="white" font-size="16" font-family="Arial, sans-serif" font-weight="bold" text-anchor="end">{total_prs}</text>
</svg>"""

with open("stats.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Generated stats.svg successfully!")

# 6. Generate Languages SVG
lang_svg = f"""<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect width="400" height="300" rx="12" fill="#0d1117"/>
    <text x="30" y="45" fill="white" font-size="22" font-family="Arial, sans-serif" font-weight="bold">Most Used Languages</text>
"""

y_pos = 90
for lang, pct in top_languages:
    bar_width = int(pct * 2.5) # Scale to fit 250px max width
    lang_svg += f'    <text x="30" y="{y_pos}" fill="#c9d1d9" font-size="14" font-family="Arial, sans-serif">{lang}</text>\n'
    lang_svg += f'    <text x="330" y="{y_pos}" fill="#8b949e" font-size="14" font-family="Arial, sans-serif" text-anchor="end">{pct:.1f}%</text>\n'
    lang_svg += f'    <rect x="30" y="{y_pos + 8}" width="300" height="8" rx="4" fill="#21262d"/>\n'
    lang_svg += f'    <rect x="30" y="{y_pos + 8}" width="{bar_width}" height="8" rx="4" fill="#58a6ff"/>\n'
    y_pos += 45

lang_svg += "</svg>"

with open("languages.svg", "w", encoding="utf-8") as f:
    f.write(lang_svg)

print("Generated languages.svg successfully!")
