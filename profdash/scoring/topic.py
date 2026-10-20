"""Find professors who publish on a topic, via DBLP title search.

    prof topic "named data networking" --query "information-centric" --name ndn

DBLP's publication search matches title words. Every hit's author list is
matched against your professors by exact DBLP name (CSRankings names *are*
DBLP names, including disambiguators like "0001"). Matches are stored in
the professor_topics table, so the dashboard can filter by topic, and a
CSV report also lists frequent authors who are *not* in your database
(students, industry, or faculty CSRankings doesn't track).
"""
from __future__ import annotations

import csv
import datetime as dt
import re
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import httpx

from .digest import MIRRORS, SKIP_TYPES, USER_AGENT

PAGE = 1000          # DBLP's maximum page size
MAX_RESULTS = 10000  # DBLP stops paging around here


def _get_json(client: httpx.Client, path: str, *, log=print) -> dict | None:
    for attempt in range(6):
        host = MIRRORS[attempt % len(MIRRORS)]
        try:
            r = client.get(host + path, headers={"User-Agent": USER_AGENT},
                           timeout=60, follow_redirects=True)
            if r.status_code == 200:
                return r.json()
            log(f"  {host}: HTTP {r.status_code}, retrying ...")
        except (httpx.HTTPError, ValueError) as e:
            log(f"  {host}: {type(e).__name__}, retrying ...")
        time.sleep(2 + 3 * attempt)
    return None


def _as_list(x) -> list:
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def search(query: str, *, since: int | None = None, client: httpx.Client,
           log=print) -> list[dict]:
    """All DBLP hits for a title query: [{title, venue, year, authors[]}]."""
    out: list[dict] = []
    offset, total = 0, None
    while offset < MAX_RESULTS:
        data = _get_json(client, f"/search/publ/api?q={quote(query)}"
                                 f"&format=json&h={PAGE}&f={offset}", log=log)
        if data is None:
            raise RuntimeError("DBLP did not answer (network/proxy?). Try again later.")
        hits = data.get("result", {}).get("hits", {})
        total = int(hits.get("@total", 0)) if total is None else total
        page = _as_list(hits.get("hit"))
        for h in page:
            info = h.get("info", {})
            if info.get("type") in SKIP_TYPES:
                continue
            try:
                year = int(info.get("year", 0))
            except ValueError:
                year = 0
            if since and year < since:
                continue
            authors = [a.get("text", "") if isinstance(a, dict) else str(a)
                       for a in _as_list(info.get("authors", {}).get("author"))]
            out.append({"title": (info.get("title") or "").rstrip("."),
                        "venue": info.get("venue") or "", "year": year,
                        "authors": [a for a in authors if a]})
        offset += PAGE
        log(f"  '{query}': {min(offset, total)}/{total} hits scanned")
        if not page or offset >= total:
            break
        time.sleep(1.0)
    if total and total > MAX_RESULTS:
        log(f"  note: DBLP returns at most {MAX_RESULTS} of {total} hits for "
            f"'{query}'; narrow the query or use --since")
    return out


def run(db_path: Path, queries: list[str], *, name: str, since: int | None = None,
        min_papers: int = 1, csv_path: Path | None = None,
        exclude_countries: list[str] | None = None, log=print) -> dict:
    from ..schema import create_all

    papers: dict[str, dict] = {}       # dedupe by title+year across queries
    with httpx.Client() as client:
        for q in queries:
            for p in search(q, since=since, client=client, log=log):
                papers.setdefault(f"{p['title'].lower()}|{p['year']}", p)

    by_author: dict[str, list[dict]] = defaultdict(list)
    for p in papers.values():
        for a in p["authors"]:
            by_author[a].append(p)

    conn = sqlite3.connect(str(db_path), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        create_all(conn)
        profs: dict[str, sqlite3.Row] = {}
        for r in conn.execute("SELECT id, professor, university, location_country, "
                              "homepage, area FROM professors"):
            profs.setdefault(r["professor"], r)
        excluded = {c.lower() for c in (exclude_countries or [])}

        rows = []
        for author, plist in by_author.items():
            if len(plist) < min_papers:
                continue
            prof = profs.get(author)
            if prof and (prof["location_country"] or "").lower() in excluded:
                continue
            plist = sorted(plist, key=lambda p: -p["year"])
            rows.append({
                "author": author, "papers": len(plist),
                "last_year": plist[0]["year"],
                "in_db": bool(prof),
                "professor_id": prof["id"] if prof else "",
                "university": prof["university"] if prof else "",
                "country": prof["location_country"] if prof else "",
                "homepage": prof["homepage"] if prof else "",
                "area": prof["area"] if prof else "",
                "titles": " | ".join(f"{p['year']} {p['title']}" for p in plist[:3]),
            })
        rows.sort(key=lambda r: (-r["in_db"], -r["papers"], -r["last_year"]))

        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        conn.execute("DELETE FROM professor_topics WHERE topic = ?", (name,))
        conn.executemany(
            """INSERT INTO professor_topics (professor_id, topic, papers, last_year,
                   sample_titles, updated_at) VALUES (?,?,?,?,?,?)""",
            [(r["professor_id"], name, r["papers"], r["last_year"], r["titles"], now)
             for r in rows if r["in_db"]])
        conn.commit()
    finally:
        conn.close()

    if csv_path:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["author"])
            w.writeheader()
            w.writerows(rows)
    return {"papers": len(papers), "authors": len(by_author),
            "matched": sum(r["in_db"] for r in rows), "rows": rows}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "topic"
