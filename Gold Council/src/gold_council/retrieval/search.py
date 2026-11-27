"""BM25 search over FTS5 with simple synonym expansion. Returns citations, never summaries."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

SYNONYMS = {
    "fvg": ["fair value gap", "imbalance"],
    "ob": ["order block"],
    "bos": ["break of structure"],
    "choch": ["change of character"],
    "cisd": ["change in state of delivery"],
    "vwap": ["volume weighted average price"],
    "orb": ["opening range breakout"],
    "pbo": ["probability of backtest overfitting"],
    "dsr": ["deflated sharpe ratio"],
}


@dataclass
class Hit:
    chunk_id: str
    source_id: str
    title: str
    page_start: int
    page_end: int
    score: float
    snippet: str


def _fts_query(q: str) -> str:
    terms = re.findall(r"[\w']+", q.lower())
    groups = []
    for t in terms:
        alts = [f'"{t}"'] + [f'"{s}"' for s in SYNONYMS.get(t, [])]
        groups.append("(" + " OR ".join(alts) + ")" if len(alts) > 1 else alts[0])
    return " OR ".join(groups)


def search(con: sqlite3.Connection, query: str, limit: int = 5, source_id: str | None = None) -> list[Hit]:
    limit = max(1, min(int(limit), 50))
    fq = _fts_query(query)
    if not fq:
        return []
    sql = ("SELECT f.chunk_id, f.source_id, s.title, c.page_start, c.page_end, bm25(chunks_fts) AS score, "
           "snippet(chunks_fts, 0, '[', ']', ' … ', 24) FROM chunks_fts f "
           "JOIN chunks c ON c.chunk_id=f.chunk_id JOIN sources s ON s.source_id=f.source_id "
           "WHERE chunks_fts MATCH ?")
    args: list = [fq]
    if source_id:
        sql += " AND f.source_id=?"
        args.append(source_id)
    sql += " ORDER BY score LIMIT ?"
    args.append(limit)
    return [Hit(*r) for r in con.execute(sql, args).fetchall()]
