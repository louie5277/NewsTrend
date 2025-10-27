# main.py
import os, argparse
from pathlib import Path
import sys
from config_loader import load_env_near_exe

env_info = load_env_near_exe(require_local=True,  # require a sibling .env
                             verbose=("--debug-env" in sys.argv))


from news_sources import fetch_both
from topic_miner import build_topics_df
from keyword_trending import co_trending_topics
from analysis import write_csv_topics, write_markdown

LANG = os.getenv("LANG", "en")
DAYS = int(os.getenv("DAYS", "7"))
TOP_K = int(os.getenv("TOP_K", "15"))
HALF_LIFE_H = float(os.getenv("HALF_LIFE_H", "36"))
NEWS_MAX_PAGES = int(os.getenv("NEWS_MAX_PAGES", "2"))
NEWS_PAGE_SIZE = int(os.getenv("NEWS_PAGE_SIZE", "100"))
SERPAPI_PAGES = int(os.getenv("SERPAPI_PAGES", "2"))

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

def run_broad(query: str):
    print(f"\n=== [BROAD] Query: {query} | lang={LANG} | days={DAYS} ===")
    rows = fetch_both(query=query, lang=LANG, days=DAYS,
                      nc_page_size=NEWS_PAGE_SIZE, nc_pages=NEWS_MAX_PAGES,
                      serp_pages=SERPAPI_PAGES)
    print(f"Fetched {len(rows)} articles")
    topics_df = build_topics_df(rows, half_life_h=HALF_LIFE_H, top_k=TOP_K)
    write_csv_topics(topics_df, OUTPUT / f"topics_{query.replace(' ','_')}.csv")
    write_markdown(query, topics_df, rows, OUTPUT / f"report_{query.replace(' ','_')}.md")
    print("(no signal)" if topics_df.empty else f"\nTop topics:\n{topics_df.to_string(index=False)}")

def run_keyword(query: str):
    print(f"\n=== [KEYWORD] Query: {query} | lang={LANG} | days={DAYS} ===")
    topics_df, rows = co_trending_topics(query=query, lang=LANG, days=DAYS,
                                         half_life_h=HALF_LIFE_H, top_k=TOP_K)
    slug = query.replace(" ", "_")
    write_csv_topics(topics_df, OUTPUT / f"cotopics_{slug}.csv")
    write_markdown(query, topics_df, rows, OUTPUT / f"coreport_{slug}.md")
    print("(no signal)" if topics_df.empty else topics_df.to_string(index=False))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["broad", "keyword"], default="keyword")
    ap.add_argument("--queries", required=True)
    args = ap.parse_args()
    for q in [s.strip() for s in args.queries.split(",") if s.strip()]:
        (run_broad if args.mode == "broad" else run_keyword)(q)

if __name__ == "__main__":
    main()
