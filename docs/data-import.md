# Importing programs, deadlines and positions

The **Universities**, **Deadlines** and **Positions** pages have no public
dataset behind them, so their data comes from you (or your AI agent):
research, write a CSV or JSON file, import it.

```bash
prof template programs  > programs.csv     # example file to fill in
prof template deadlines > deadlines.csv
prof template positions > positions.csv     # --format json for JSON

prof import programs  programs.csv --dry-run   # validate only
prof import programs  programs.csv
prof import deadlines deadlines.csv
prof import positions positions.csv
```

Accepted files: `.csv` (header row), `.json` (a list of objects, or
`{"items": [...]}`), `.jsonl`. Unknown columns are ignored, empty cells mean
"not provided", invalid rows are skipped with a message naming the row.
Re-importing is safe: rows are matched by a stable id and updated in place.

## programs → Universities page

Required: `university`. Optional: `program_name`, `track` (`phd` / `masters`),
`location_country`, `department_url`, `admission_requirements`,
`english_requirements`, `tuition_info`, `funding_info`, `funding_confidence`,
`application_components`, `visa_notes`, `notable_faculty`, `source_urls`,
`research_date` (YYYY-MM-DD), `notes`.

* A program is identified by `university` + `track` + `program_name`.
* Use the **same university name as CSRankings** (e.g. "ETH Zurich",
  "Technical University of Munich") so the program page lists that
  university's professors. Country is filled from your professors if empty.
* In JSON, a program may carry its deadlines inline:
  `{"university": "...", "track": "phd", "deadlines": [{"deadline_type": "application", "deadline_date": "2027-01-15"}]}`

## deadlines → Deadlines page

Required: `university`, `deadline_type`, `deadline_date` (YYYY-MM-DD).
Optional: `program_name`, `track`, `deadline_date_confidence`
(`firm` / `estimated`), `cycle_label` (e.g. "Fall 2027"), `description`,
`source_url`.

* `university` + `track` + `program_name` pick the program; it is created
  if it doesn't exist yet.
* A deadline is identified by program + `deadline_type` + `cycle_label`, so
  importing a corrected date updates it instead of duplicating it.
* `deadline_type` examples: `application`, `scholarship`, `application_open`
  (shown as "opens" on the dashboard), `interview`.

## positions → Positions page

Required: `title`, `institution`. Optional: `location_country`,
`professor_name`, `track`, `deadline` (YYYY-MM-DD), `funding_stated`,
`source_type`, `source_url`, `mailing_list`, `fit_tier`, `recommendation`,
`score` (0–10), `why`, `status`, `application_status`, `application_notes`.

* A position is identified by `institution` + `title`.
* `professor_name` is linked to a professor in your database when the name
  matches (DBLP numbers like "0001" are ignored).
* `status`, `application_status` and `application_notes` are set on first
  import only; afterwards you change them in the dashboard and re-imports
  leave them alone.

## Let an AI agent fill them

Ask your agent (Claude Code, Codex, ...) something like:

> For each university in my shortlist (`/shortlist`), find the CS PhD
> program page and write `programs.json` in the format of
> `prof template programs --format json`, with deadlines inline. Use only
> facts from the official program pages, put every URL you used in
> `source_urls`, mark guessed dates `"deadline_date_confidence": "estimated"`.
> Then run `prof import programs programs.json --dry-run` and fix any
> skipped rows.

Always spot-check dates against the official page before relying on them.
