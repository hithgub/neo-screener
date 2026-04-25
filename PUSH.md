# Push to GitHub (One-Time Setup)

## Step 1: Create the repo on GitHub
1. Go to https://github.com/hithgub
2. Click **New Repository**
3. Name: `neo-screener`
4. Set to **Public**
5. Click **Create repository**

## Step 2: Push the code

On Windows, open **PowerShell** or **Git Bash** and run:

```bash
cd C:\Claude\Hermes\neo-screener

git init
git add .
git commit -m "Initial commit — daily short screener"
git branch -M main
git remote add origin https://github.com/hithgub/neo-screener.git
git push -u origin main
```

Enter your GitHub username + password (or use a **Personal Access Token** if you have 2FA).

## Step 3: Enable GitHub Pages
1. On your repo page, go to **Settings → Pages** (left sidebar)
2. Under **Source**, select **Deploy from a branch**
3. Under **Branch**, select `gh-pages` → `/` (root)
4. Click **Save**
5. Wait 2-3 minutes for the first deployment
6. Your live URL: `https://hithgub.github.io/neo-screener/`

## Step 4: Verify the workflow works
1. Go to **Actions** tab in your repo
2. You should see the "Daily Screener" workflow
3. Click it → **Run workflow** (manual trigger) → **Run workflow**
4. Wait 5-10 minutes for it to complete
5. Check back at `https://hithgub.github.io/neo-screener/` — it should show the report

## Step 5: Build your Android APK
1. Open Android Studio
2. File → Open → `C:\Claude\Hermes\daily-short-screener-android`
3. Build → Build Bundle(s) / APK(s) → Build APK(s)
4. APK location: `C:\Claude\Hermes\daily-short-screener-android\app\build\outputs\apk\debug\app-debug.apk`
5. Install on your Samsung via USB or ADB
