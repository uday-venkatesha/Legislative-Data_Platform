import pandas as pd

STAGE_ORDER = {"introduced": 0, "in_committee": 1, "passed_chamber": 2, "enacted": 3}

# Terminal-death language seen in real action descriptions across states.
DEAD_MARKERS = ("died", "vetoed", "failed", "postponed indefinitely",
                "withdrawn", "stricken", "tabled", "indefinitely postponed")
ENACTED_MARKERS = ("signed", "chapter", "effective", "became law",
                   "enacted", "delivered to secretary of state")

def _furthest_stage(actions):
    """High-water mark from the action classification history."""
    stage = "introduced"
    for a in actions or []:
        classes = set(a.get("classification") or [])
        if classes & {"became-law", "executive-signature"}:
            return "enacted"                      # can't go higher
        if "passage" in classes:
            stage = "passed_chamber"
        elif classes & {"referral-committee", "committee-passage",
                        "committee-passage-favorable"} and STAGE_ORDER[stage] < 1:
            stage = "in_committee"
    return stage

def _lifecycle_state(furthest, latest_desc):
    """Alive/dead/enacted from the LATEST action's language.
    Order matters: check enacted first, then death, then default active."""
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
        rows.append({
            "bill_id": b["id"],
            "state": (b.get("jurisdiction") or {}).get("name"),
            "session": b.get("session"),
            "identifier": b.get("identifier"),
            "title": (b.get("title") or "").strip(),
            "classification": (b.get("classification") or [None])[0],
            "subjects": "|".join(b.get("subject") or []) or None,
            "primary_sponsor": sponsor,
            "primary_sponsor_party": party,
            "furthest_stage": _furthest_stage(b.get("actions")),
            "lifecycle_state": _lifecycle_state(b.get("actions"), b.get("latest_action_description")),
            "first_action_date": b.get("first_action_date"),
            "latest_action_date": b.get("latest_action_date"),
            "latest_action_desc": b.get("latest_action_description"),
            "openstates_url": b.get("openstates_url"),
            "source_name": source,
            "ingested_at": now,
            "updated_at_source": b.get("updated_at"),
        })
    df = pd.DataFrame(rows)
    # Bad/empty dates become NaT rather than crashing — that's a quality signal we count in Phase 3.
    for col in ["first_action_date", "latest_action_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    df["updated_at_source"] = pd.to_datetime(df["updated_at_source"], errors="coerce")
    return df.drop_duplicates(subset="bill_id", keep="last")  # dedup within the batch