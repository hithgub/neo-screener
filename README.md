# Neo Screener

Daily short squeeze + overextended stock screener. Runs automatically every morning via GitHub Actions and publishes to a live webpage.

**Live report:** `https://hithgub.github.io/neo-screener/index.html`

## How it works

1. GitHub Actions runs `daily_screener.py` on a free Ubuntu VM every day at 8 AM PST (and hourly during market hours)
2. The script downloads 285 tickers, computes RSI / Wavetrend / Bollinger Bands / squeeze signals
3. Results are published to GitHub Pages (free hosting)
4. The Android app loads that page with offline caching

## Running locally

```bash
python daily_screener.py
```

## Files

| File | Purpose |
|------|---------|
| `daily_screener.py` | Core screener engine |
| `template.html` | HTML template for reports |
| `assets/` | Icons + universe cache |
| `.github/workflows/screener.yml` | Auto-run schedule |

## How to push to your own repo

See `PUSH.md` for exact commands.
