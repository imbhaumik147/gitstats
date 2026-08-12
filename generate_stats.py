import os
import requests

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

# 2. Get your repositories
repos_response = requests.get(f"https://api.github.com/users/{username}/repos?per_page=100", headers=headers)
if repos_response.status_code != 200:
    print(f"Error fetching repos: {repos_response.text}")
    exit(1)

repos = repos_response.json()
repo_count = len(repos)
total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
total_forks = sum(repo.get("forks_count", 0) for repo in repos)

# 3. Calculate languages
languages = {}
for repo in repos:
    # Get languages for each repository
    repo_name = repo.get("name")
    lang_resp = requests.get(f"https://api.github.com/repos/{username}/{repo_name}/languages", headers=headers)
    if lang_resp.status_code == 200:
        repo_langs = lang_resp.json()
        for lang, bytes_count in repo_langs.items():
            languages[lang] = languages.get(lang, 0) + bytes_count

# Calculate language percentages
total_bytes = sum(languages.values())
language_percentages = {lang: (count / total_bytes * 100) for lang, count in languages.items()}
# Sort languages by percentage descending
top_languages = sorted(language_percentages.items(), key=lambda x: x[1], reverse=True)[:5]

print("Top Languages:")
for lang, pct in top_languages:
    print(f"{lang}: {pct:.1f}%")

# 4. Generate SVG
# For the SVG, we can create a simple visually appealing card
# You can customize this layout further!
svg = f"""<svg width="600" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect width="600" height="300" rx="12" fill="#0d1117"/>
    <text x="30" y="45" fill="white" font-size="24" font-family="Arial">GitHub Statistics - {username}</text>
    
    <text x="30" y="90" fill="white" font-size="18" font-family="Arial">Repositories: {repo_count}</text>
    <text x="30" y="125" fill="white" font-size="18" font-family="Arial">Stars: {total_stars}</text>
    <text x="30" y="160" fill="white" font-size="18" font-family="Arial">Forks: {total_forks}</text>
    
    <text x="300" y="90" fill="white" font-size="18" font-family="Arial">Top Languages:</text>
"""

y_pos = 125
for lang, pct in top_languages:
    svg += f'    <text x="300" y="{y_pos}" fill="white" font-size="16" font-family="Arial">{lang}: {pct:.1f}%</text>\n'
    y_pos += 30

svg += "</svg>"

with open("stats.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Generated stats.svg successfully!")

# 5. Generate Languages SVG
lang_svg = f"""<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect width="400" height="300" rx="12" fill="#0d1117"/>
    <text x="30" y="45" fill="white" font-size="22" font-family="Arial, sans-serif" font-weight="bold">Most Used Languages</text>
"""

y_pos = 90
for lang, pct in top_languages:
    # We can use simple bar widths
    bar_width = int(pct * 2.5) # Scale to fit 250px max width
    
    # Language name and percentage
    lang_svg += f'    <text x="30" y="{y_pos}" fill="#c9d1d9" font-size="14" font-family="Arial, sans-serif">{lang}</text>\n'
    lang_svg += f'    <text x="330" y="{y_pos}" fill="#8b949e" font-size="14" font-family="Arial, sans-serif" text-anchor="end">{pct:.1f}%</text>\n'
    
    # Progress bar background
    lang_svg += f'    <rect x="30" y="{y_pos + 8}" width="300" height="8" rx="4" fill="#21262d"/>\n'
    # Progress bar fill (using a default color, ideally you'd map languages to colors)
    lang_svg += f'    <rect x="30" y="{y_pos + 8}" width="{bar_width}" height="8" rx="4" fill="#58a6ff"/>\n'
    
    y_pos += 45

lang_svg += "</svg>"

with open("languages.svg", "w", encoding="utf-8") as f:
    f.write(lang_svg)

print("Generated languages.svg successfully!")
