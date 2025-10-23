<p align="center">
  <img src="https://img.shields.io/badge/NewsTrend-Keyword%20Co--Trends%20%26%20Topic%20Radar-111111?style=for-the-badge&labelColor=111111&color=0ea5e9" alt="NewsTrend banner">
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-3776ab?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Platforms" src="https://img.shields.io/badge/Platforms-Windows%20%7C%20macOS%20%7C%20Linux-4b5563?style=for-the-badge">
  <img alt="Interface" src="https://img.shields.io/badge/Interface-CLI%20%26%20Tkinter%20GUI-8b5cf6?style=for-the-badge">
  <img alt="SerpApi" src="https://img.shields.io/badge/API-SerpApi-22c55e?style=for-the-badge">
  <img alt="NewsAPI" src="https://img.shields.io/badge/API-NewsAPI-f59e0b?style=for-the-badge">
</p>

---

# 🗞️ NewsTrend — Keyword Co-Trends & Topic Radar

Find what’s *actually* trending around a keyword across the news cycle.  
Pulls from **SerpApi (Google News)** + **NewsAPI**, de-dupes, time-decays, ranks co-occurring phrases, and saves **CSV + Markdown**. Comes with a simple **Tkinter GUI** and a CLI.

---

## ✨ Features

- ✅ **Two sources**: SerpApi (Google News) + NewsAPI (optional)
- ✅ **Co-trend mining** (TF-IDF(Term frequency) + recency decay) for a given keyword
- ✅ **Broad mode** (RAKE keyphrases) to surface general topics
- ✅ **Clean outputs**: `*.csv` (topic, score, count) + `*.md` report with linked recent articles (UTC timestamps)
- ✅ **Tkinter desktop app** for non-technical users
- ✅ **Robust date parsing** with fallbacks & de-dupe by URL
- ✅ **Free-tier friendly** knobs & backoffs

---

## ▶️ How to Use: Desktop App (Tkinter)
### Ensure you have .env and python installed!!

`python program.py`

•Type a Query, adjust Days / Top-K / Half-life, then Run

•Top table: ranked topics │ Bottom table: recent articles

•Double-click an article to open the link

•Save Markdown / Save CSV directly from the UI

# Minimal Config via .env
| Key                             | What it does                            |
| ------------------------------- | --------------------------------------- |
| `SERPAPI_API_KEY`               | Required. Google News via SerpApi       |
| `NEWSAPI_KEY`                   | Optional. NewsAPI “everything” endpoint |
| `LANG`                          | Search language (e.g. `en`)             |
| `DAYS`                          | Lookback for NewsAPI                    |
| `TOP_K`                         | Number of topics to show                |
| `HALF_LIFE_H`                   | Recency half-life (hours)               |
| `NEWSAPI_MAX_RESULTS`           | Cap for free tier (default 100)         |
| `SERPAPI_NUM` / `SERPAPI_PAGES` | Page size/pages for Google News         |
| `SERPAPI_PHRASE`                | `1` = search exact phrase `"query"`     |

---

# 🧭 Newsroom Value (at a glance)
💡 Faster signal — Immediately see what’s rising with your term (e.g., “Alabama shooting”) without sifting feeds.

🧱 Actionable — Ranked co-topics + freshest links → plug into alerts, pitches, and briefs.

🧑‍💻 Human-in-loop — CSV + MD keep editors in control; tweak knobs for recall vs. precision.

🔌 Scalable — Add schedules, Slack/Teams routing, and thresholds for on-duty desks.
