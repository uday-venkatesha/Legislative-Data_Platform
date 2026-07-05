import pandas as pd
from standardize.normalizers import (norm_state, norm_party, norm_identifier,
                                      norm_chamber, make_uid)

STAGE_ORDER = {"introduced": 0, "in_committee": 1, "passed_chamber": 2, "enacted": 3}
DEAD_MARKERS = ("died", "vetoed", "failed", "postponed indefinitely",
                "withdrawn", "stricken", "tabled", "indefinitely postponed")
ENACTED_MARKERS = ("signed", "chapter", "effective", "became law",
                   "enacted", "delivered to secretary of state")

def _furthest_stage(actions):
    stage = "introduced"
    for a in actions or []:
        classes = set(a.get("classification") or [])
        if classes & {"became-law", "executive-signature"}:
            return "enacted"
        if "passage" in classes:
            stage = "passed_chamber"
        elif classes & {"referral-committee", "committee-passage",
                        "committee-passage-favorable"} and STAGE_ORDER[stage] < 1:
            stage = "in_committee"
    return stage

def _lifecycle_state(furthest, latest_desc):
    desc = (latest_desc or "").lower()
    if furthest == "enacted" or any(m in desc for m in ENACTED_MARKERS):
        return "enacted"
    if any(m in desc for m in DEAD_MARKERS):
        return "dead"
    return "active"

def _primary_sponsor(sponsorships):
    for s in sponsorships or []:
        if s.get("primary"):
            return s.get("name"), (s.get("person") or {}).get("party")
    return None, None

def transform_bills(raw_bills, source="openstates"):
    now = pd.Timestamp.utcnow().to_pydatetime()
    rows = []
    for b in raw_bills:
        sponsor, party = _primary_sponsor(b.get("sponsorships"))
        code, name = norm_state((b.get("jurisdiction") or {}).get("name"))
        ident = norm_identifier(b.get("identifier"))
        session = b.get("session")
        furthest = _furthest_stage(b.get("actions"))          # compute ONCE
        rows.append({
            "bill_id": b["id"],
            "bill_uid": make_uid(code, session, ident),
            "state": name,
            "state_code": code,
            "chamber": norm_chamber(identifier=ident),
            "session": session,
            "identifier": ident,
            "title": (b.get("title") or "").strip(),
            "classification": (b.get("classification") or [None])[0],
            "subjects": "|".join(b.get("subject") or []) or None,
            "primary_sponsor": sponsor,
            "primary_sponsor_party": norm_party(party),
            "furthest_stage": furthest,
            "lifecycle_state": _lifecycle_state(furthest, b.get("latest_action_description")),
            "first_action_date": b.get("first_action_date"),
            "latest_action_date": b.get("latest_action_date"),
            "latest_action_desc": b.get("latest_action_description"),
            "openstates_url": b.get("openstates_url"),
            "source_name": source,
            "source_bill_id": b["id"],
            "ingested_at": now,
            "updated_at_source": b.get("updated_at"),
        })
    df = pd.DataFrame(rows)
    for col in ["first_action_date", "latest_action_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    df["updated_at_source"] = pd.to_datetime(df["updated_at_source"], errors="coerce")
    return df.drop_duplicates(subset="bill_id", keep="last")