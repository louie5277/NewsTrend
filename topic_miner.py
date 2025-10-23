# topic_miner.py
from __future__ import annotations
import math, re
from datetime import datetime, timezone
from typing import Dict, List
import pandas as pd
from rake_nltk import Rake
import nltk

# Ensure NLTK resources (RAKE uses punkt; NLTK 3.9+ needs punkt_tab)
for pkg in ("stopwords", "punkt", "punkt_tab"):
    try:
        nltk.data.find(f"tokenizers/{pkg}" if "punkt" in pkg else f"corpora/{pkg}")
    except LookupError:
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass

def _as_text(v) -> str:
    if v is None: return ""
    if isinstance(v, float) and math.isnan(v): return ""
    return str(v)

def _hours_ago(dt: datetime) -> float:
    now = datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 3600.0)

def extract_keyphrases(text: str, top_n: int = 3) -> list[str]:
    text = _as_text(text).strip()
    if not text:
        return []
    rake = Rake()
    rake.extract_keywords_from_text(text)
    phrases = []
    seen = set()
    for score, phrase in rake.get_ranked_phrases_with_scores():
        if not isinstance(phrase, str):
            continue
        p = phrase.strip().lower()
        if not p or p in seen:
            continue
        wc = len(re.findall(r"\w+", p))
        if 1 <= wc <= 3 and len(p) <= 50:
            phrases.append(p); seen.add(p)
        if len(phrases) >= top_n:
            break
    return phrases

def build_topics_df(rows: List[Dict], half_life_h: float = 36.0, top_k: int = 15) -> pd.DataFrame:
    topic_rows = []
    for r in rows:
        title = _as_text(r.get("title"))
        summary = _as_text(r.get("summary"))
        phrases = extract_keyphrases(f"{title}. {summary}", top_n=3)
        if not phrases:
            continue
        hrs = _hours_ago(r["published_at"])
        decay = 0.5 ** (hrs / max(1e-6, half_life_h))
        for p in phrases:
            topic_rows.append({"topic": p, "decayed": decay, "source": r.get("source")})

    if not topic_rows:
        return pd.DataFrame(columns=["topic", "score", "count"])

    df = pd.DataFrame(topic_rows)
    agg = df.groupby("topic").agg(score=("decayed","sum"), count=("topic","size")).reset_index()
    agg = agg.sort_values("score", ascending=False).head(top_k)
    return agg
