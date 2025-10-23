# analysis.py
from __future__ import annotations
from typing import List, Dict
from pathlib import Path
import pandas as pd

def write_csv_topics(df: pd.DataFrame | None, path: Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df if isinstance(df, pd.DataFrame) else pd.DataFrame(columns=["topic", "score", "count"])
    out.to_csv(path, index=False, encoding="utf-8")
    print(f"Saved: {path.name} ({len(out)} rows)")

def write_markdown(query: str, topics_df: pd.DataFrame | None, sample_rows: List[Dict], path: Path):
    lines = [f"# Trends for: **{query}**", ""]

    if topics_df is None or topics_df.empty:
        lines.append("_No signal found._")
    else:
        lines += ["## Top topics", ""]
        for _, row in topics_df.iterrows():
            lines.append(f"- **{row['topic']}** — score {row['score']:.3f} (docs: {int(row['count'])})")
        lines.append("")

    if sample_rows:
        lines += ["## Sample recent articles", ""]
        for r in sample_rows[:15]:
            # r['published_at'] is tz-aware UTC; render explicitly
            ts = r["published_at"].strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"- [{r['title']}]({r['url']}) — *{ts}*, source: {r['source']}")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Saved: {path.name}")
