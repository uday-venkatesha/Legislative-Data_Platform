import pandas as pd
from sqlalchemy import text

import json
from datetime import datetime
from standardize.normalizers import norm_state

RAW_UPSERT = ("INSERT INTO raw_bills (source, source_bill_id, state_code, payload, fetched_at) "
              "VALUES (:source, :source_bill_id, :state_code, :payload, :fetched_at) AS new "
              "ON DUPLICATE KEY UPDATE payload=new.payload, fetched_at=new.fetched_at, state_code=new.state_code;")

def land_raw(raw_bills, source, engine, state_code=None):
    now = datetime.utcnow(); recs = []
    for b in raw_bills:
        if source == "legiscan":
            code, sbid = state_code, str(b["bill_id"])
        else:  # openstates
            code, _ = norm_state((b.get("jurisdiction") or {}).get("name"))
            sbid = b["id"]
        recs.append(dict(source=source, source_bill_id=sbid, state_code=code,
                         payload=json.dumps(b), fetched_at=now))
    if recs:
        with engine.begin() as c: c.execute(text(RAW_UPSERT), recs)
    return len(recs)


COLS = ["bill_id","state","session","identifier","title","classification","subjects",
        "primary_sponsor","primary_sponsor_party","furthest_stage",
        "lifecycle_state","first_action_date","latest_action_date","latest_action_desc",
        "openstates_url","source_name","ingested_at","updated_at_source","bill_uid","state_code","chamber","source_bill_id"]

# Row-alias form (MySQL 8.0.19+). VALUES() in ON DUPLICATE KEY is deprecated, so we use `new`.
_UPDATE = ", ".join(f"{c}=new.{c}" for c in COLS if c != "bill_id")
UPSERT = (
    f"INSERT INTO bills ({', '.join(COLS)}) "
    f"VALUES ({', '.join(':'+c for c in COLS)}) AS new "
    f"ON DUPLICATE KEY UPDATE {_UPDATE};"
)

def upsert_bills(df, engine):
    # NaT/NaN -> None so MySQL stores proper NULLs
    records = df.astype(object).where(pd.notnull(df), None).to_dict("records")
    if not records:
        return 0
    with engine.begin() as conn:
        conn.execute(text(UPSERT), records)   # executemany
    return len(records)