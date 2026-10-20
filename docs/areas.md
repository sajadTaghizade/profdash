# Research areas

profdash tags each professor with a research area taken from [CSRankings](https://csrankings.org):
27 areas in 4 groups. Run `prof areas` to list them.

| Group | Areas (code) |
|---|---|
| **AI** | AI (`ai`), Vision (`vision`), ML (`mlmining`), NLP (`nlp`), Web+IR (`inforet`) |
| **Systems** | Architecture (`arch`), Networks (`comm`), Security (`sec`), Databases (`mod`), EDA (`da`), Embedded (`bed`), HPC (`hpc`), Mobile (`mobile`), Metrics (`metrics`), OS (`ops`), PL (`plan`), SE (`soft`) |
| **Theory** | Algorithms (`act`), Crypto (`crypt`), Logic (`log`) |
| **Interdisciplinary** | Comp. Bio (`bio`), Graphics (`graph`), CS Education (`csed`), Econ+Comp (`ecom`), HCI (`chi`), Robotics (`robotics`), Visualization (`visualization`) |

## How the area is chosen

`generated-author-info.csv` from CSRankings lists each author's papers per
conference. profdash maps every conference to its area and sums the
author-adjusted paper counts over the last 10 years (`--area-years N`, `0` = all
time). The area with the highest score is the professor's **primary area**
(`professors.area` / `professors.area_group`). The full breakdown is kept in the
`professor_areas` table and shown on the professor page.

Professors with no papers in any CSRankings conference have no area.

## Importing by area

```bash
prof import csrankings --area vision --area nlp          # codes or names
prof import csrankings --area "Comp. Bio"
prof import csrankings --area group:theory               # a whole group
prof import csrankings --country Germany --area security # combine with country filters
```

`--area` matches the **primary** area. Use `group:ai` (not `ai`) for the AI
group, because `ai` is also the code of the general-AI area.

Re-running the import refreshes areas on professors you already have.

## In the dashboard

* Professors table: **Area** column (sortable: group, then area), plus *All groups* / *All areas* filters.
* Stats bar: per-area counts; click one to filter.
* Professor page: area chips, strongest first.

## Venue presets per area

Each area also carries DBLP venue tiers (its CSRankings conferences as
*strong*, well-known second-tier venues and journals as *moderate*). Use them
for paper selection and scoring digests:

```toml
[venues]
preset = ["mlmining", "nlp"]     # or "group:ai", or mix with "theory"
strong = ["MyFavConf"]           # extra entries still work
```

`prof areas --venues` prints every area's tiers. Matching ignores case and
DBLP volume suffixes such as "ECCV (12)".

## Existing databases

`prof serve` and `prof migrate` add the new columns automatically. Run
`prof import csrankings` once to fill in areas for professors you already have.

## Narrower topics: `prof topic`

Areas are broad. For a specific topic, search DBLP paper titles:

```bash
prof topic "named data networking" --also "information-centric" --name ndn --since 2015
prof topic "federated learning" --min-papers 3 --exclude-country Iran
```

Every author is matched to your professors by exact DBLP name. You get a
ranked list in the terminal, a CSV (`topic-<name>.csv`) that also lists
frequent authors who are *not* in your database (students, industry,
faculty CSRankings doesn't track), and a **topic** filter on the
Professors page. Re-running a topic replaces its previous results.
