from dotenv import load_dotenv; load_dotenv(override=True)
from news_sources import fetch_serpapi_google_news
rows = fetch_serpapi_google_news("Alabama shooting", lang="en", pages=2)
print("SerpApi rows:", len(rows))
for r in rows[:5]:
    print(r["published_at"].isoformat(), "—", r["title"][:80])