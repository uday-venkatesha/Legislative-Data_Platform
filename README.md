# Legislative Data Platform

A multi-source ETL pipeline that pulls US state legislative data from public APIs, reconciles it into a single canonical model, and serves it to a Looker Studio dashboard built for government-affairs teams tracking bills across states.

It looks like a civic project, but the point of it is data engineering: two sources that disagree, a reconciliation layer that resolves the conflicts by rule, and a governance layer that makes every run auditable. Everything is nonpartisan by design — the platform reports counts, rates, and status, never "good" or "bad" bills.

**Live dashboard:** https://datastudio.google.com/reporting/c60e0d63-58fc-40bf-9b30-a7cfb747389d

Currently covering Kansas, Missouri, and Colorado (2025–26 sessions), ~5,500 source rows reconciled into 5,343 distinct bills.

## Why it exists

The intended user is a policy or government-affairs director at an advocacy nonprofit or trade association — someone tracking thousands of bills across many states with a small team, whose real problem is deciding where to spend limited attention. Every metric on the dashboard is built to answer a version of "where do I point staff this week," not to editorialize.

Under the hood, the interesting problem is that no single free source is both broad and deep. So I use two and merge them:

- **OpenStates v3** is *deep* — full action histories, sponsors, subjects — but the free tier is slow and rate-limited, so I pull a capped sample per state.
- **LegiScan** is *broad* — the entire session master list in one call (Missouri alone is ~3,100 bills) — but its summaries carry no sponsor and encode status as a single integer.

The two sources describe the same bills differently, and reconciling them is most of the work.

## Architecture

```
OpenStates v3 ─┐
               ├─► raw_bills ──► normalize ──► bills ──► bills_canonical ──► Looker Studio
LegiScan ──────┘   (landing)   (standardize)  (per-src)    (reconciled)       (5 views)
```

- **raw_bills** — every source payload lands here as JSON before anything touches it. This means a logic change can be replayed from stored data without re-hitting a rate-limited API.
- **normalize** (`standardize/normalizers.py`) — pure, unit-tested functions that map each source's dialect onto one vocabulary: state names → USPS codes, `"HB2427"` → `"HB 2427"`, party strings → a fixed set, dates → real `DATE`s, and status → the two-dimension model below.
- **bills** — one row per source per bill (a "silver" layer). Loads are idempotent upserts, so re-running never duplicates.
- **bills_canonical** — a SQL view that merges the source rows into one canonical record per bill, keyed by `bill_uid`.

## The data model

Two decisions drive everything.

**Status is two dimensions, not one.** A single "status" field can't tell you that a bill passed a chamber and *then* died — it looks identical to a bill sitting alive in committee. So status is split:

- `furthest_stage` — the high-water mark: `introduced → in_committee → passed_chamber → enacted`
- `lifecycle_state` — whether it's still moving: `active`, `dead`, or `enacted`

A bill can be `passed_chamber` **and** `dead`, and the model says so.

**`bill_uid` is a cross-source key.** Built as `STATE:YEAR:IDENTIFIER` (e.g. `KS:2025:SB476`), using the session's *start year* rather than each source's own session label — otherwise OpenStates' `"2025-2026"` and LegiScan's `"2025"` would never line up. This is what lets the same bill from two sources collide and merge.

### Reconciliation rules

When both sources describe a bill, the canonical view resolves each field deliberately:

| Field | Rule | Why |
| --- | --- | --- |
| `furthest_stage` | max stage reached by either source | sources differ in granularity, not truth |
| `lifecycle_state` | precedence: `enacted` > `dead` > `active` | a terminal signal beats "never updated" |
| `primary_sponsor`, `subjects`, `first_action_date` | OpenStates only | LegiScan's master list doesn't carry them |
| `latest_action_date` | most recent of the two | freshest wins |

These rules aren't arbitrary — they came from actually looking at where the two sources disagreed (see below).

## What the reconciliation found

Of the 190 bills covered by both sources, the two independently-built parsers **agreed on 148** — including hard cases like a bill that advanced to `passed_chamber` and then died, which both derived correctly from completely different inputs (an action history vs. a status integer). The 42 disagreements were structured, not random:

- 39 were OpenStates=`dead` / LegiScan=`active` — LegiScan leaves stalled bills at "Introduced" after a session ends, where OpenStates records the death. Resolved to `dead`.
- A handful were OpenStates=`active` / LegiScan=`enacted` — OpenStates' capped sample missed a signing LegiScan caught. Resolved to `enacted`.

The pattern is precedence on the *status values themselves*, not "one source always wins" — which is more defensible than any source-priority scheme.

## Governance

The pipeline logs and checks itself so the answer to "how do you know this data is good?" isn't "trust me."

- **`audit_log`** — one row per source per run: rows fetched, rows upserted, duration, success/failure, and the error on failure. The fetched-vs-upserted gap is itself a signal (OpenStates fetches 300, dedups to 190).
- **Quality checks** (`governance/run_quality.py`) — five integrity checks that must be zero (null keys, null status, duplicate source IDs, reversed dates, unmapped states) plus two monitored *rate signals* that aren't failures, just tracked characteristics.
- **Data dictionary** (`governance/data_dictionary.md`) — every canonical field, its lineage, and its caveats.

## Known limitations

Being upfront about these, because they're real and understanding them is part of the work:

- **"Active" is over-counted (~76%).** Most bills are LegiScan-only, and LegiScan leaves a bill at "Introduced" after its session ends rather than marking it dead. So a large share of nominally-`active` bills are actually stalled. Bills also covered by OpenStates get corrected; the LegiScan-only majority don't. The dashboard handles this honestly with a staleness breakdown rather than trusting the raw `active` count. Proper fix: enrich via LegiScan's `getBill`, or infer death from "session ended + unchanged for N months."
- **Sponsors are sparse (~97% null).** Only the OpenStates-covered subset has sponsors, so any sponsor-level view is scoped to those bills by design, not accident.
- **Coverage is asymmetric.** OpenStates is a capped per-state sample; LegiScan is the full session. Cross-source volume comparisons aren't apples-to-apples.
- **Three states, current sessions only.** The pipeline is state-agnostic; the scope is a deliberate limit, not a ceiling.

## Repo layout

```
├── etl/
│   ├── extract/         openstates.py, legiscan.py      (source adapters)
│   ├── transform/       bills.py, legiscan_bills.py      (source → canonical rows)
│   ├── load/            mysql_loader.py                  (idempotent upserts, raw landing)
│   ├── run_openstates.py
│   └── run_legiscan.py
├── standardize/         normalizers.py                   (shared field normalizers)
├── governance/          audit.py, quality_checks.py, run_quality.py, data_dictionary.md
├── scripts/             smoke_test.py, test_normalizers.py, export_canonical.py
├── sql/                 schema.sql                       (tables + bills_canonical view)
├── requirements.txt
└── .env.example
```

## Running it

Requires Python 3.11+ and MySQL 8.

```bash
# 1. environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. database — create the schema (tables + canonical view)
mysql -u <user> -p <db> < sql/schema.sql

# 3. keys — copy .env.example to .env and fill in:
#    OPENSTATES_API_KEY, LEGISCAN_API_KEY, DB_URL

# 4. sanity check the DB + API key
python -m scripts.smoke_test

# 5. run the pipeline
python -m etl.run_openstates
python -m etl.run_legiscan

# 6. quality report
python -m governance.run_quality

# 7. export the canonical view for the dashboard
python -m scripts.export_canonical
```

Free API keys: [OpenStates](https://openstates.org/accounts/profile/) and [LegiScan](https://legiscan.com/legiscan).

## Dashboard

The Looker Studio report reads from `bills_canonical` (via the CSV export → Google Sheets) and is organized as one decision per page:

- **Landscape** — where is activity concentrated, by state and topic
- **Pipeline** — the funnel from introduced to enacted, and where bills die within it
- **Momentum** — what's actually moved recently vs. gone stale
- **Actors** — most active sponsors and their success rates (scoped to enriched bills)
- **Priority** — a ranked state × topic score, normalized per capita

## Stack

Python (pandas, requests, SQLAlchemy, PyMySQL) · MySQL 8 · Looker Studio · OpenStates v3 and LegiScan APIs.

## Roadmap

- LegiScan `getBill` enrichment to close the sponsor and active-state gaps
- A Flask submission portal with input validation and PII anonymization into a staging table
- Congress.gov as a third (federal) source
- Scheduled runs instead of manual invocation

## License

MIT. Legislative data belongs to its respective public sources; this project only transforms and presents it.