import pandas as pd
from standardize.normalizers import (norm_state, norm_identifier, norm_chamber,
                                     norm_date, make_uid)
from etl.transform.bills import DEAD_MARKERS, ENACTED_MARKERS   # reuse — one source of truth

LEGISCAN_STAGE = {1: "introduced", 2: "passed_chamber", 3: "passed_chamber",
                  4: "enacted", 5: "passed_chamber", 6: "introduced"}
LEGISCAN_DEAD, LEGISCAN_ENACTED = {5, 6}, {4}
_RES_PREFIXES = {"HR", "SR", "HCR", "SCR", "HJR", "SJR", "HJ", "SJ"}

def _map_status(status, last_action):
    """Numeric enum + last_action text -> canonical two-dimension status."""
    desc = (last_action or "").lower()
    stage = LEGISCAN_STAGE.get(status, "introduced")
    if stage == "introduced" and "committee" in desc:   # text upgrades granularity
        stage = "in_committee"
    if status in LEGISCAN_ENACTED or any(m in desc for m in ENACTED_MARKERS):
        return "enacted", "enacted"
    if status in LEGISCAN_DEAD or any(m in desc for m in DEAD_MARKERS):
        return stage, "dead"
    return stage, "active"

def _classify(ident):
    p = ident.split(" ")[0] if ident else ""
    return "resolution" if p in _RES_PREFIXES else "bill"

def transform_masterlist(bills, state_code, session_year_val, source="legiscan"):
    _, state_name = norm_state(state_code)
    now = pd.Timestamp.utcnow().to_pydatetime()
    rows = []
    for b in bills:
        ident = norm_identifier(b.get("number"))
        stage, life = _map_status(b.get("status"), b.get("last_action"))
        rows.append({
            "bill_id": str(b["bill_id"]),
            "bill_uid": make_uid(state_code, session_year_val, ident),
            "state": state_name, "state_code": state_code,
            "chamber": norm_chamber(identifier=ident),
            "session": str(session_year_val),
            "identifier": ident,
            "title": (b.get("title") or "").strip(),
            "classification": _classify(ident),
            "subjects": None,                    # not in masterlist
            "primary_sponsor": None,             # needs getBill (completeness gap)
            "primary_sponsor_party": None,
            "furthest_stage": stage,
            "lifecycle_state": life,
            "first_action_date": None,           # masterlist has no intro date
            "latest_action_date": norm_date(b.get("last_action_date")),
            "latest_action_desc": b.get("last_action"),
            "openstates_url": None,              # LegiScan url is preserved in raw_bills
            "source_name": source,
            "source_bill_id": str(b["bill_id"]),
            "ingested_at": now,
            "updated_at_source": None,
        })
    return pd.DataFrame(rows).drop_duplicates(subset="bill_id", keep="last")