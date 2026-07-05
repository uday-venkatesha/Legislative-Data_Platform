# Data Dictionary — Legislative & Public Sector Data Platform

## Overview
Canonical, deduplicated view of US legislative bills reconciled from multiple
public sources. One row per bill per session in `bills_canonical`, keyed by `bill_uid`.

## Sources & lineage
| Source | Role | Grain | Carries |
|---|---|---|---|
| OpenStates v3 | Deep | ~100 bills/state sample | sponsors, action history, subjects |
| LegiScan | Broad | Full session master list | status enum, last action, no sponsors |

Raw payloads land in `raw_bills` (source, source_bill_id, JSON, fetched_at) before
normalization — enabling replay without re-hitting rate-limited APIs.

## Canonical fields (`bills_canonical`)
| Field | Type | Description | Lineage / rule |
|---|---|---|---|
| bill_uid | string | Cross-source key: `STATE:YEAR:IDENT` | Derived; session collapsed to start year so sources align |
| state_code | char(2) | USPS state code | Normalized from "Kansas"/"KS" |
| identifier | string | Bill number, e.g. "HB 2427" | Normalized: prefix + int, spaces fixed |
| chamber | string | House / Senate | Derived from identifier prefix |
| furthest_stage | enum | introduced < in_committee < passed_chamber < enacted | Reconciled: MAX stage across sources |
| lifecycle_state | enum | active / dead / enacted | Reconciled: precedence enacted > dead > active |
| primary_sponsor | string | Primary sponsor name | OpenStates only |
| first_action_date | date | First action | OpenStates only |
| latest_action_date | date | Most recent action | MAX across sources |
| sources | string | Contributing sources | Provenance for audit |
| ... | | *(fill remaining columns)* | |

## Naming conventions
- snake_case for all columns; `*_date` = DATE, `*_at` = DATETIME.
- `state_code` (2-letter) is canonical; `state` (full name) is display-only.

## Known limitations (READ THIS)
1. **Active-state over-count (~76%).** LegiScan-only bills stuck at status 1 after
   session end read as `active` (no terminal action observed). Bills also covered by
   OpenStates are corrected to `dead`. Fix path: `getBill` enrichment or age-based
   inference. *Monitored via `legiscan_active_rate`.*
2. **Sponsor sparsity (~97%).** LegiScan masterlist carries no sponsor; only the
   OpenStates subset has sponsors. *Monitored via `missing_sponsor_rate`.*
3. **Coverage asymmetry.** OpenStates is a capped sample per state; LegiScan is the
   full session. Volume comparisons across sources are not apples-to-apples.

## Quality checks
Integrity (must be 0): null_bill_uid, null_status, duplicate_source_id,
bad_date_order, unknown_state_code. Rate signals (monitored, not pass/fail):
legiscan_active_rate, missing_sponsor_rate. Run via `governance/run_quality.py`.