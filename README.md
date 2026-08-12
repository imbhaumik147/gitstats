# GitStats 📊

This repository automatically generates beautiful, dynamically updated GitHub Statistics and Top Languages SVG cards for your GitHub Profile README. It runs entirely on GitHub Actions, so no external hosting or third-party tracking is required!

## ✨ Features
* **GitHub Stats Card** (`stats.svg`): Displays your total repositories, stars earned, commits from the last 30 days, and total pull requests.
* **Top Languages Card** (`languages.svg`): Calculates your top 5 most-used programming languages across all your repositories.
* **Private Repository Support**: Perfectly calculates stats and languages from your private repositories (if permissions are granted).

## 🚀 How to Use (Setup Guide)

If you have forked or cloned this repository, follow these steps to get your stats updating automatically:

### 1. Create a GitHub Personal Access Token (PAT)
To allow the script to fetch your statistics, you need to provide a Personal Access Token.
1. Go to your [GitHub Developer Settings](https://github.com/settings/tokens).
2. Click **Generate new token (classic)**.
3. Give it a note (e.g., "GitStats") and set an expiration date (or No Expiration).
4. **Important**: Check the box next to **`repo`** to allow it to read your private repositories and commits.
5. Click **Generate token** at the bottom and copy the token.

### 2. Add the Token to Repository Secrets
1. Go to the **Settings** tab of this repository.
2. On the left sidebar, click **Secrets and variables** > **Actions**.
3. Click **New repository secret**.
4. Name the secret exactly **`GH_TOKEN`**.
5. Paste your copied token into the Secret field and click **Add secret**.

### 3. Run the Workflow
1. Go to the **Actions** tab of this repository.
2. Click on **Generate GitHub Stats** on the left.
3. Click the **Run workflow** button on the right.
4. Once it finishes, your `stats.svg` and `languages.svg` files will be updated! (It will also automatically run every hour).

### 4. Display on your Profile
To show these cards on your main GitHub profile (`username/username`), add this snippet to your `README.md`:

```html
<p align="center">
  <img src="https://raw.githubusercontent.com/YOUR_USERNAME/gitstats/main/stats.svg?v=1" height="200" alt="GitHub Stats" />
  <img src="https://raw.githubusercontent.com/YOUR_USERNAME/gitstats/main/languages.svg?v=1" height="200" alt="Top Languages" />
</p>
```
*(Remember to replace `YOUR_USERNAME` with your actual GitHub username!)*
