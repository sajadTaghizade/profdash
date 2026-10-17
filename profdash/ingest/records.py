"""Import university programs, deadlines and positions from CSV / JSON.

These pages have no public dataset to pull from, so the data comes from
you or your AI agent: research the programs, write a CSV (or JSON) file,
and import it. `prof template <kind>` prints a ready-to-fill example.

Usage:
    prof import programs  programs.csv  [--dry-run] [--db PATH]
    prof import deadlines deadlines.csv [--dry-run] [--db PATH]
    prof import positions positions.json [--dry-run] [--db PATH]

Files: .csv (header row), .json (a list of objects, or {"items": [...]}),
or .jsonl (one object per line). Unknown columns are ignored; empty cells
mean "not provided". Re-importing the same file is safe: rows are matched
by a stable id and updated in place.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
import sqlite3
from pathlib import Path

KINDS = ("programs", "deadlines", "positions")

PROGRAM_FIELDS = [
    "university", "program_name", "track", "location_country", "department_url",
    "admission_requirements", "english_requirements", "tuition_info",
    "funding_info", "funding_confidence", "application_components",
    "visa_notes", "notable_faculty", "source_urls", "research_date", "notes",
]
DEADLINE_FIELDS = [
    "university", "program_name", "track", "deadline_type", "deadline_date",
    "deadline_date_confidence", "cycle_label", "description", "source_url",
]
POSITION_FIELDS = [
    "title", "institution", "location_country", "professor_name", "track",
    "deadline", "funding_stated", "source_type", "source_url", "mailing_list",
    "fit_tier", "recommendation", "score", "why", "status",
    "application_status", "application_notes",
]
REQUIRED = {
    "programs": ("university",),
    "deadlines": ("university", "deadline_type", "deadline_date"),
    "positions": ("title", "institution"),
}
# Columns that track *your* progress: set on first import, never overwritten
# by a re-import (change them in the dashboard instead).
POSITION_USER_FIELDS = ("status", "application_status", "application_notes")

TEMPLATES = {
    "programs": [
        {"university": "ETH Zurich", "program_name": "Direct Doctorate in Computer Science",
         "track": "phd", "location_country": "Switzerland",
         "department_url": "https://inf.ethz.ch/doctorate.html",
         "admission_requirements": "MSc or excellent BSc; research statement",
         "english_requirements": "TOEFL iBT 100 or IELTS 7",
         "tuition_info": "CHF 730 / semester",
         "funding_info": "Funded by the supervisor's grant (PhD positions are employment)",
         "funding_confidence": "likely",
         "application_components": "CV; transcripts; 2-3 references; statement of purpose",
         "visa_notes": "Residence permit via employer contract",
         "notable_faculty": "", "source_urls": "https://inf.ethz.ch/doctorate.html",
         "research_date": "2026-10-01", "notes": ""},
    ],
    "deadlines": [
        {"university": "ETH Zurich", "program_name": "Direct Doctorate in Computer Science",
         "track": "phd", "deadline_type": "application", "deadline_date": "2026-12-15",
         "deadline_date_confidence": "firm", "cycle_label": "Fall 2027",
         "description": "Main application deadline",
         "source_url": "https://inf.ethz.ch/doctorate.html"},
        {"university": "ETH Zurich", "program_name": "Direct Doctorate in Computer Science",
         "track": "phd", "deadline_type": "application_open", "deadline_date": "2026-11-01",
         "deadline_date_confidence": "estimated", "cycle_label": "Fall 2027",
         "description": "Portal opens", "source_url": ""},
    ],
    "positions": [
        {"title": "PhD position in Systems Security", "institution": "CISPA",
         "location_country": "Germany", "professor_name": "Jane Doe", "track": "phd",
         "deadline": "2026-12-31", "funding_stated": "Fully funded (TV-L E13)",
         "source_type": "web", "source_url": "https://example.org/job/123",
         "mailing_list": "", "fit_tier": "", "recommendation": "", "score": "",
         "why": "", "status": "new", "application_status": "not_applied",
         "application_notes": ""},
    ],
}

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FIELDS = {"programs": PROGRAM_FIELDS, "deadlines": DEADLINE_FIELDS,
           "positions": POSITION_FIELDS}


def _slug(*parts: str | None) -> str:
    raw = "-".join(p for p in parts if p).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug[:120] or hashlib.sha1(raw.encode()).hexdigest()[:12]


def _clean(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = "; ".join(str(v) for v in value if v not in (None, ""))
    s = str(value).strip()
    return s or None


def read_rows(path: Path) -> list[dict]:
    """Rows from a .csv / .json / .jsonl file, as dicts of raw values."""
    text = path.read_text(encoding="utf-8-sig")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return list(csv.DictReader(io.StringIO(text)))
    if suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if suffix == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("items", [data])
        if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
            raise ValueError("JSON must be a list of objects (or {\"items\": [...]})")
        return data
    raise ValueError(f"unsupported file type {suffix!r}: use .csv, .json or .jsonl")


def normalize(kind: str, raw: dict) -> tuple[dict, list[str]]:
    """Keep known fields, clean values, validate. Returns (row, errors)."""
    lowered = {str(k).strip().lower(): v for k, v in raw.items() if k is not None}
    row = {f: _clean(lowered.get(f)) for f in _FIELDS[kind]}
    errors = [f"missing {f}" for f in REQUIRED[kind] if not row.get(f)]
    for f in ("deadline_date", "deadline", "research_date"):
        if row.get(f) and not _DATE.match(row[f]):
            errors.append(f"{f} must be YYYY-MM-DD (got {row[f]!r})")
    if row.get("track"):
        row["track"] = row["track"].lower()
    if kind == "positions" and row.get("score"):
        try:
            row["score"] = int(float(row["score"]))
            if not 0 <= row["score"] <= 10:
                errors.append("score must be 0-10")
        except ValueError:
            errors.append(f"score must be a number (got {row['score']!r})")
    if kind == "deadlines" and row.get("deadline_type"):
        row["deadline_type"] = re.sub(r"[\s-]+", "_", row["deadline_type"].lower())
    if kind == "programs":
        nested = lowered.get("deadlines")
        if isinstance(nested, list):
            row["_deadlines"] = nested
    return row, errors


def program_id(university: str, track: str | None, program_name: str | None) -> str:
    return "prog-" + _slug(university, track, program_name)


def _country_for(conn: sqlite3.Connection, university: str) -> str | None:
    r = conn.execute(
        """SELECT location_country FROM professors
           WHERE university = ? AND location_country IS NOT NULL
                 AND location_country != '' LIMIT 1""", (university,)).fetchone()
    return r[0] if r else None


def _upsert(conn: sqlite3.Connection, table: str, rid: str, row: dict,
            now: str, *, keep: tuple[str, ...] = ()) -> str:
    """Insert, or update the provided (non-empty) fields. -> 'inserted'|'updated'."""
    fields = {k: v for k, v in row.items() if not k.startswith("_")}
    exists = conn.execute(f"SELECT 1 FROM {table} WHERE id = ?", (rid,)).fetchone()
    if exists is None:
        cols = ["id", "created_at", "updated_at"] + [k for k, v in fields.items()
                                                     if v is not None]
        vals = [rid, now, now] + [v for v in fields.values() if v is not None]
        conn.execute(f"INSERT INTO {table} ({', '.join(cols)}) "
                     f"VALUES ({', '.join('?' * len(cols))})", vals)
        return "inserted"
    sets = {k: v for k, v in fields.items() if v is not None and k not in keep}
    if sets:
        conn.execute(
            f"UPDATE {table} SET updated_at = ?, "
            + ", ".join(f"{k} = ?" for k in sets) + " WHERE id = ?",
            [now, *sets.values(), rid])
    return "updated"


def _ensure_program(conn, university, track, program_name, now) -> str:
    pid = program_id(university, track, program_name)
    if not conn.execute("SELECT 1 FROM university_programs WHERE id = ?",
                        (pid,)).fetchone():
        _upsert(conn, "university_programs", pid,
                {"university": university, "track": track,
                 "program_name": program_name,
                 "location_country": _country_for(conn, university)}, now)
    return pid


def _store_deadline(conn, row: dict, now: str) -> str:
    pid = _ensure_program(conn, row["university"], row.get("track"),
                          row.get("program_name"), now)
    existing = conn.execute(
        """SELECT id FROM program_deadlines
           WHERE university_program_id = ? AND deadline_type = ?
                 AND COALESCE(cycle_label, '') = COALESCE(?, '')""",
        (pid, row["deadline_type"], row.get("cycle_label"))).fetchone()
    vals = {k: row.get(k) for k in ("deadline_type", "deadline_date",
                                    "deadline_date_confidence", "cycle_label",
                                    "description", "source_url")}
    if existing:
        sets = {k: v for k, v in vals.items() if v is not None}
        conn.execute("UPDATE program_deadlines SET "
                     + ", ".join(f"{k} = ?" for k in sets) + " WHERE id = ?",
                     [*sets.values(), existing[0]])
        return "updated"
    conn.execute(
        """INSERT INTO program_deadlines (university_program_id, deadline_type,
               deadline_date, deadline_date_confidence, cycle_label, description,
               source_url) VALUES (?,?,?,?,?,?,?)""",
        (pid, *vals.values()))
    return "inserted"


def _match_professor(conn, name: str | None, institution: str) -> str | None:
    """Link a position to a known professor (DBLP numbers like ' 0001' ignored)."""
    if not name:
        return None
    rows = conn.execute(
        "SELECT id, professor, university FROM professors WHERE professor LIKE ?",
        (f"{name}%",)).fetchall()
    rows = [r for r in rows
            if re.sub(r"\s+\d{4}$", "", r[1]).lower() == name.lower()]
    same_uni = [r for r in rows if (r[2] or "").lower() == institution.lower()]
    if len(same_uni) == 1:
        return same_uni[0][0]
    return rows[0][0] if len(rows) == 1 else None


def run_import(db_path: Path, kind: str, file_path: Path, *,
               dry_run: bool = False, log=print) -> dict:
    """Validate + import one file. Returns counts."""
    from ..schema import create_all

    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    raw_rows = read_rows(file_path)
    stats = {"rows": len(raw_rows), "inserted": 0, "updated": 0, "invalid": 0,
             "deadlines_inserted": 0, "deadlines_updated": 0}
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    conn = sqlite3.connect(str(db_path), timeout=15)
    try:
        create_all(conn)
        for i, raw in enumerate(raw_rows, start=2 if file_path.suffix == ".csv" else 1):
            row, errors = normalize(kind, raw)
            nested_errors = []
            nested = []
            for d in row.pop("_deadlines", []) if kind == "programs" else []:
                d = {"university": row["university"], "track": row.get("track"),
                     "program_name": row.get("program_name"), **d}
                drow, derr = normalize("deadlines", d)
                nested_errors += [f"deadline: {e}" for e in derr]
                nested.append(drow)
            if errors or nested_errors:
                stats["invalid"] += 1
                log(f"  row {i}: skipped — {'; '.join(errors + nested_errors)}")
                continue

            if kind == "programs":
                if not row.get("location_country"):
                    row["location_country"] = _country_for(conn, row["university"])
                pid = program_id(row["university"], row.get("track"),
                                 row.get("program_name"))
                stats[_upsert(conn, "university_programs", pid, row, now)] += 1
                for drow in nested:
                    stats["deadlines_" + _store_deadline(conn, drow, now)] += 1
            elif kind == "deadlines":
                stats[_store_deadline(conn, row, now)] += 1
            else:
                if not row.get("location_country"):
                    row["location_country"] = _country_for(conn, row["institution"])
                row["source_type"] = row.get("source_type") or "manual"
                row["professor_id"] = _match_professor(
                    conn, row.get("professor_name"), row["institution"])
                rid = "pos-" + _slug(row["institution"], row["title"])
                stats[_upsert(conn, "positions", rid, row, now,
                              keep=POSITION_USER_FIELDS)] += 1
        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    finally:
        conn.close()
    return stats


def template(kind: str, fmt: str = "csv") -> str:
    rows = TEMPLATES[kind]
    if fmt == "json":
        return json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=_FIELDS[kind], extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()
