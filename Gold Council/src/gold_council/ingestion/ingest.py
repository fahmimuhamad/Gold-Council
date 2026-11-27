"""Knowledge ingestion into SQLite FTS5 (Step 6). Document text is untrusted data."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SUPPORTED = {".pdf", ".txt", ".md"}
TARGET_WORDS = 450       # ~600 tokens
OVERLAP_WORDS = 60       # ~80 tokens
SCANNED_MIN_CHARS = 40

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY, title TEXT, author TEXT, edition TEXT, rights TEXT,
  path TEXT, sha256 TEXT UNIQUE, ingested_at TEXT, pages INTEGER, flagged_pages TEXT);
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY, source_id TEXT REFERENCES sources(source_id),
  page_start INTEGER, page_end INTEGER, heading TEXT, text TEXT, quality TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  text, heading, chunk_id UNINDEXED, source_id UNINDEXED, tokenize='porter unicode61');
"""


@dataclass
class IngestResult:
    path: str
    status: str        # INGESTED | DUPLICATE | UNSUPPORTED | EMPTY
    source_id: str | None = None
    chunks: int = 0
    flagged_pages: list[int] | None = None


def connect(db_path: str | Path) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    return con


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def extract_pages(p: Path) -> list[str]:
    if p.suffix.lower() == ".pdf":
        import pymupdf
        with pymupdf.open(p) as doc:
            return [page.get_text("text") for page in doc]
    text = p.read_text(encoding="utf-8", errors="replace")
    return [text]  # whole text file = "page" 1


def _heading(text: str) -> str:
    for line in text.splitlines():
        s = line.strip().lstrip("#").strip()
        if 3 <= len(s) <= 120:
            return s
    return ""


def chunk_pages(pages: list[str]) -> list[tuple[int, int, str]]:
    """Paragraph-preserving chunks with word overlap. Returns (page_start, page_end, text)."""
    paras: list[tuple[int, str]] = []
    for pno, text in enumerate(pages, start=1):
        for para in re.split(r"\n\s*\n", text):
            para = " ".join(para.split())
            if para:
                paras.append((pno, para))
    chunks, cur, cur_pages, words = [], [], [], 0
    for pno, para in paras:
        n = len(para.split())
        if words and words + n > TARGET_WORDS:
            chunks.append((cur_pages[0], cur_pages[-1], "\n\n".join(cur)))
            tail = " ".join(" ".join(cur).split()[-OVERLAP_WORDS:])
            cur, cur_pages, words = [tail], [cur_pages[-1]], len(tail.split())
        cur.append(para)
        cur_pages.append(pno)
        words += n
    if cur:
        chunks.append((cur_pages[0], cur_pages[-1], "\n\n".join(cur)))
    return chunks


def ingest_file(con: sqlite3.Connection, p: Path, meta: dict | None = None) -> IngestResult:
    meta = meta or {}
    if p.suffix.lower() not in SUPPORTED:
        return IngestResult(str(p), "UNSUPPORTED")
    digest = sha256_file(p)
    row = con.execute("SELECT source_id FROM sources WHERE sha256=?", (digest,)).fetchone()
    if row:
        return IngestResult(str(p), "DUPLICATE", row[0])
    pages = extract_pages(p)
    flagged = [i for i, t in enumerate(pages, 1) if len(t.strip()) < SCANNED_MIN_CHARS]
    chunks = chunk_pages(pages)
    if not chunks:
        return IngestResult(str(p), "EMPTY", flagged_pages=flagged)
    source_id = meta.get("source_id") or "src_" + digest[:12]
    con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?)",
                (source_id, meta.get("title", p.stem), meta.get("author", ""), meta.get("edition", ""),
                 meta.get("rights", "unrecorded"), str(p), digest,
                 datetime.now(timezone.utc).isoformat(), len(pages), ",".join(map(str, flagged))))
    for k, (ps, pe, text) in enumerate(chunks):
        cid = f"{source_id}_c{k:05d}"
        quality = "flagged_scan" if any(ps <= f <= pe for f in flagged) else "text"
        h = _heading(text)
        con.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?)", (cid, source_id, ps, pe, h, text, quality))
        con.execute("INSERT INTO chunks_fts (text, heading, chunk_id, source_id) VALUES (?,?,?,?)",
                    (text, h, cid, source_id))
    con.commit()
    return IngestResult(str(p), "INGESTED", source_id, len(chunks), flagged)


def ingest_path(con: sqlite3.Connection, root: Path, catalog: dict[str, dict] | None = None) -> list[IngestResult]:
    catalog = catalog or {}
    files = [root] if root.is_file() else sorted(x for x in root.rglob("*") if x.is_file() and x.name != ".gitkeep")
    return [ingest_file(con, f, catalog.get(f.name)) for f in files]


def stats(con: sqlite3.Connection) -> dict:
    s = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    c = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    f = con.execute("SELECT COUNT(*) FROM chunks WHERE quality!='text'").fetchone()[0]
    return {"sources": s, "chunks": c, "flagged_chunks": f}
