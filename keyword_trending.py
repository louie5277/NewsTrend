# keyword_trending.py
from __future__ import annotations
import re
from typing import List, Tuple
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from news_sources import fetch_both  # NewsAPI + SerpApi combo

def _to_aware_utc(dt) -> datetime:
    if isinstance(dt, np.datetime64):
        return pd.Timestamp(dt, tz="UTC").to_pydatetime()
    if isinstance(dt, pd.Timestamp):
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = dt.tz_localize("UTC")
        else:
            dt = dt.tz_convert("UTC")
        return dt.to_pydatetime()
    if isinstance(dt, datetime):
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return datetime.now(timezone.utc)

def _hours_ago(dt) -> float:
    now = datetime.now(timezone.utc)
    dt_utc = _to_aware_utc(dt)
    return max(0.0, (now - dt_utc).total_seconds() / 3600.0)

def _decay_weight(hours: float, half_life_h: float) -> float:
    return 0.5 ** (hours / max(half_life_h, 1e-6))

def _normalize_text(s: str) -> str:
    return (s or "").replace("\n", " ").strip()

def _build_docs(rows: List[dict]) -> Tuple[List[str], List[datetime]]:
    texts, times = [], []
    for r in rows:
        title = _normalize_text(r.get("title", ""))
        summary = _normalize_text(r.get("summary", ""))
        txt = (title + ". " + summary).strip()
        if not txt:
            continue
        texts.append(txt)
        times.append(r["published_at"])
    return texts, times

def _default_stop_terms(query: str) -> set:
    tokens = re.findall(r"[A-Za-z]+", (query or "").lower())
    generic = {
        "alabama", "shooting", "shootings", "shot", "shots", "gun", "guns", "suspect",
        "police", "breaking", "update", "live", "mass", "killed", "injured"
    }
    return set(tokens) | generic

def co_trending_topics(
    query: str,
    lang: str = "en",
    days: int = 7,
    half_life_h: float = 36.0,
    top_k: int = 15,
    ngram_range: tuple = (1, 3),
    min_df: int = 2,
    max_features: int = 6000,
):
    """
    Pull news for `query`, then rank co-occurring n-grams with recency-weighted TF-IDF.
    Returns: (topics_df, rows) with topics_df columns ['topic','score','count'].
    """
    rows = fetch_both(
        query=query,
        lang=lang,
        days=days,
        nc_page_size=100,
        nc_pages=2,
        serp_pages=2,
    )
    if not rows:
        return pd.DataFrame(columns=["topic", "score", "count"]), []

    docs, ts = _build_docs(rows)
    if not docs:
        return pd.DataFrame(columns=["topic", "score", "count"]), rows

    # Recency weights per doc
    hrs = np.array([_hours_ago(t) for t in ts], dtype=float)
    w = np.array([_decay_weight(h, half_life_h) for h in hrs], dtype=np.float64)

    # Be gentle if doc count is small
    n_docs = len(docs)
    adaptive_min_df = 1 if n_docs < 25 else min_df
    adaptive_ngram = (1, 2) if n_docs < 25 else ngram_range

    vec = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=adaptive_ngram,
        min_df=adaptive_min_df,
        max_features=max_features,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b",
    )
    X = vec.fit_transform(docs)

    term_scores = np.asarray(X.T.dot(w)).ravel()           # recency-weighted
    doc_freq = np.asarray((X > 0).sum(axis=0)).ravel()     # in how many docs term appears
    vocab = np.array(vec.get_feature_names_out())

    # Filter out seed terms to surface *co* topics
    stop_terms = _default_stop_terms(query)
    mask = np.array([not any(tok in stop_terms for tok in term.split()) for term in vocab], dtype=bool)

    vocab = vocab[mask]
    term_scores = term_scores[mask]
    doc_freq = doc_freq[mask]

    if vocab.size == 0:
        return pd.DataFrame(columns=["topic", "score", "count"]), rows

    # Normalize scores to 0..10 for readability
    m = term_scores.max()
    if m > 0:
        term_scores = term_scores / m * 10.0

    order = np.argsort(-term_scores)
    top_idx = order[:top_k]
    out = pd.DataFrame({
        "topic": vocab[top_idx],
        "score": term_scores[top_idx],
        "count": doc_freq[top_idx].astype(int),
    })
    return out, rows
