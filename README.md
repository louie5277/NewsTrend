🗞️ NewsTrend — Keyword Co-Trends & Broad Topic Miner

Find what’s trending inside a topic in minutes.
NewsTrend pulls headlines from NewsAPI + SerpApi (Google News), normalizes timestamps to UTC, applies recency-weighted scoring, and outputs clean CSV and Markdown briefs. A simple Tkinter app is included for non-technical users.

✨ Features

✅ Two modes:
• Keyword (default) → co-trending phrases around a seed query using TF-IDF (1–3 grams) + time decay
• Broad → overall topics via RAKE keyphrase extraction + time decay

✅ Multi-source fetch: NewsAPI + SerpApi, de-duped by URL

✅ Freshness aware: exponential decay with configurable half-life

✅ Clean exports: CSV (topics/cotopics) + Markdown (report/coreport)

✅ Desktop app: Tkinter GUI with double-click to open articles

✅ Config via .env: language, lookback days, result caps, etc.

🔗 Live Demo

No hosted demo — run locally or package as a Windows .exe (guide below).

🧰 Tech Stack
Area	Choices
Core	Python 3.10–3.12, requests, python-dotenv, tenacity
NLP	scikit-learn (TF-IDF), rake-nltk, nltk, numpy, pandas
Date	dateparser, python-dateutil
APIs	NewsAPI, SerpApi (Google News)
App	Tkinter GUI (program.py)
💡 Example Queries

“Alabama shooting”

“iPhone 16”

“US elections”

“OpenAI”

“Hurricane Florida”

Keyword mode automatically removes generic seed terms (e.g., alabama, shooting, police) so you see contextual phrases (e.g., Montgomery mass shooting, 12 injured, bond).

🚀 Quick Start
# 1) Create env
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt
# or:
# pip install requests python-dotenv tenacity pandas scikit-learn numpy scipy nltk rake-nltk python-dateutil dateparser tqdm


Create a .env in the project root:

# API keys
NEWSAPI_KEY=your_newsapi_key
SERPAPI_API_KEY=your_serpapi_key

# Defaults
LANG=en
DAYS=7
TOP_K=15
HALF_LIFE_H=36

# Source knobs
NEWSAPI_MAX_RESULTS=100          # free tier cap
NEWSAPI_SEARCH_IN=title,description
SERPAPI_NUM=100
SERPAPI_PAGES=2
SERPAPI_PHRASE=0                 # set 1 to quote the query (exact phrase)
REQUEST_TIMEOUT=20

🧪 Run (CLI)

Keyword (co-trends) — default

python main.py --queries "Alabama shooting, iPhone 16"


Broad topics

python main.py --mode broad --queries "technology, sports"


What you’ll get (in output/):

Keyword mode → cotopics_<slug>.csv and coreport_<slug>.md

Broad mode → topics_<slug>.csv and report_<slug>.md

🖥️ GUI App (Tkinter)
python program.py


Enter Query, adjust Days / Top-K / Half-life, click Run

Top table: topics · Bottom table: articles (double-click to open)

Save Markdown / Save CSV directly from the UI

⚙️ How It Works

Pipeline

Fetch from NewsAPI + SerpApi, de-dupe by URL, require parseable published_at (coerced to UTC), sort newest→oldest.

Apply recency decay:
weight = 0.5 ** (hours_since_pub / HALF_LIFE_H)

Keyword mode:

Build docs: title + ". " + summary

TF-IDF (1–3 grams, English stopwords, min_df=2)

Score = wᵀ · X (recency-weighted term sum)

Remove seed/generic tokens → rank by normalized score (0–10)

Broad mode:

RAKE per article → aggregate decayed scores per phrase → rank

🧩 Outputs

CSV (topic, score, count) — easy to sort / chart
Markdown — newsroom-friendly brief + linked recent articles (UTC timestamps)

🧯 Troubleshooting

No results / “no signal”

Ensure .env is loaded (print(os.getenv("NEWSAPI_KEY")) in a REPL).

NewsAPI free plan returns up to 100 items → tune NEWSAPI_MAX_RESULTS, page sizes.

SerpApi dates can be messy; we normalize most formats + relative strings.
If you see drops, try SERPAPI_PHRASE=1 (exact phrase) or reduce SERPAPI_PAGES.

NLTK errors (punkt / punkt_tab)

python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"

📦 Build a Windows EXE (optional)
pip install pyinstaller
pyinstaller --name NewsTrendGUI --onefile --noconsole --collect-data dateparser program.py


Put a .env next to the exe.

If NLTK data is needed at runtime, add:

--add-data "C:\Users\<you>\AppData\Roaming\nltk_data;nltk_data"

📁 Project Layout
NewsTrend/
 ├─ main.py                # CLI
 ├─ program.py             # Tkinter GUI
 ├─ news_sources.py        # NewsAPI + SerpApi clients, date parsing
 ├─ keyword_trending.py    # co-trend analysis (TF-IDF + decay)
 ├─ topic_miner.py         # broad topic miner (RAKE + decay)
 ├─ analysis.py            # CSV/Markdown writers
 └─ output/                # generated reports

✅ License & Use

Prototype for internal newsroom analytics.
Respect rate limits and terms of service for all APIs. Use scores directionally.