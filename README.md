NewsTrend — Keyword Co-Trends & Broad Topic Miner

NewsTrend helps a newsroom quickly surface what’s trending inside any topic. It pulls articles from NewsAPI and SerpApi (Google News), de-duplicates and time-orders them, and then:

Keyword mode: finds co-trending phrases around your seed query using recency-weighted TF-IDF (e.g., “Alabama shooting” → “Montgomery mass shooting”, “12 injured”, “bond”).

Broad mode: finds overall topics from all returned articles using RAKE keyphrase extraction + recency weighting.

Outputs are CSV (scores, counts) and Markdown (readable brief + recent links). A simple Tkinter GUI (program.py) gives a click-and-go desktop app.

Features

Pulls from NewsAPI + SerpApi (Google News) in one pass

Strict UTC timestamps and recency decay (half-life) to favor fresh stories

Two analyses:

Keyword (co-trends) — 1–3-gram TF-IDF with decay, stops generic terms and the seed tokens

Broad — RAKE keyphrases per article aggregated with decay

Exports:

cotopics_<slug>.csv / coreport_<slug>.md (keyword mode)

topics_<slug>.csv / report_<slug>.md (broad mode)

GUI app to run queries, browse topics and double-click articles

Quick start
1) Requirements

Python 3.10–3.12 (Windows/macOS/Linux)

API keys:

NewsAPI: https://newsapi.org/
 (free plan returns up to 100 results)

SerpApi: https://serpapi.com/
 (Google News engine)

2) Install
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt


If you don’t have requirements.txt, install:
pip install requests python-dotenv tenacity pandas scikit-learn numpy scipy nltk rake-nltk python-dateutil dateparser tqdm

3) Configure .env

Create a .env in the project root:

# API keys
NEWSAPI_KEY=your_newsapi_key_here
SERPAPI_API_KEY=your_serpapi_key_here

# Defaults
LANG=en
DAYS=7
TOP_K=15
HALF_LIFE_H=36

# Source knobs
NEWSAPI_MAX_RESULTS=100        # free dev cap
NEWSAPI_SEARCH_IN=title,description

SERPAPI_NUM=100                # per page
SERPAPI_PAGES=2                # total pages
SERPAPI_PHRASE=0               # 1 to quote the query
REQUEST_TIMEOUT=20

4) First run (CLI)
# Keyword mode (default)
python main.py --queries "Alabama shooting"

# Broad mode
python main.py --mode broad --queries "US politics"


Outputs land in output/.

CLI usage
# Keyword co-trends (default mode)
python main.py --mode keyword --queries "Alabama shooting, iPhone 16, OpenAI"

# Broad topic mining
python main.py --mode broad --queries "technology, sports"


Multiple queries: comma-separated, each is run independently.

Uses .env knobs for language, lookback days, top-K, half-life, etc.

File naming

Keyword mode → cotopics_<slug>.csv + coreport_<slug>.md

Broad mode → topics_<slug>.csv + report_<slug>.md

GUI app (Tkinter)
python program.py


Enter Query, adjust Days / Top K / Half-life (h), click Run

Top pane: co-trending topics (keyword mode logic)

Bottom pane: most recent articles (UTC time)

Double-click an article to open in browser

Save Markdown / Save CSV buttons export the current view

How it works (scoring)
Normalization

Fetch from NewsAPI and SerpApi, dedupe by URL, require a parseable published_at, and sort newest→oldest.

Timestamps are coerced to timezone-aware UTC.

Recency weight

For each article with age hours, weight =
0.5 ** (hours / HALF_LIFE_H)
(defaults to 36h half-life).

Keyword mode (co-trends)

Build documents: title + ". " + summary per article

TF-IDF over 1–3-grams, English stopwords, min_df=2

Term score = wᵀ·X (recency-weighted sum across docs)

Drop seed tokens and generic terms (e.g., “alabama”, “shooting”, “police”)

Output topic, normalized score (0–10), and count (doc frequency)

Broad mode

RAKE extracts candidate phrases per article

Sum recency weights per phrase across all docs, then rank

Folder layout
NewsTrend/
 ├─ main.py                # CLI
 ├─ program.py             # Tkinter GUI
 ├─ news_sources.py        # NewsAPI + SerpApi clients, date parsing
 ├─ keyword_trending.py    # co-trend analysis (TF-IDF + decay)
 ├─ topic_miner.py         # RAKE + decay (broad mode)
 ├─ analysis.py            # writers for CSV/Markdown
 ├─ output/                # generated reports
 └─ .env                   # your config (not checked in)

Troubleshooting
“No signal” / very few articles

Check API key env vars are loaded (print at start or python -c "import os;print(bool(os.getenv('NEWSAPI_KEY')))").

NewsAPI free plan returns up to 100 results; code caps pages with NEWSAPI_MAX_RESULTS.

SerpApi can return many results with relative/odd dates; we parse with dateparser then dateutil and regex fallbacks. If you see drops:

Try SERPAPI_PHRASE=1 to search the exact phrase.

Reduce SERPAPI_PAGES or SERPAPI_NUM to limit noisy pages.

Keep LANG=en (SerpApi returns English-ish dates by default).

“maximumResultsReached” / HTTP 426 from NewsAPI

This means you requested beyond the free cap. Lower NEWSAPI_MAX_RESULTS, NEWS_MAX_PAGES, or NEWS_PAGE_SIZE. The code already guards with NEWSAPI_MAX_RESULTS; tune it if you changed page sizes.

NLTK “punkt” / “punkt_tab” missing
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"

Date parsing quirks (SerpApi)

We normalize formats like 10/21/2025, 08:55 PM, +0000 UTC and relative strings like “3 hours ago”.

If drops persist, print examples (already logged) and adjust _parse_date normalization rules in news_sources.py.

Building a Windows EXE (optional)

Using PyInstaller:

pip install pyinstaller
# Collect dateparser’s data so its tz cache loads when frozen
pyinstaller --name NewsTrendGUI --onefile --noconsole --collect-data dateparser program.py


If you bundle NLTK data, add:

--add-data "C:\Users\<you>\AppData\Roaming\nltk_data;nltk_data"


Place a .env next to the exe, then double-click NewsTrendGUI.exe.

If you see a dateparser_tz_cache.pkl error, either use --collect-data dateparser
or rely on our code’s lazy import/fallbacks (already implemented).

Extending (ideas)

Teams routing: add a post-processing step that uses keyword rules or embeddings to send matching article links to Teams channels via Incoming Webhooks or Microsoft Graph.

Priority tuning: add source weights (e.g., higher weight for vetted outlets).

Regional filters: add domain whitelists/blacklists in .env.

Scheduled runs: wrap CLI with Task Scheduler / cron and drop reports to a shared drive.

Notes on responsible use

Respect rate limits and terms of service for both APIs.

Don’t store or redistribute full article content unless permitted.

Use scores comparatively; they’re signals, not ground truth.