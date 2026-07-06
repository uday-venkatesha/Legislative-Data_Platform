import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.environ["DB_URL"])

# 2023 populations — extend if you add states later
STATE_POP = {"KS": 2_940_000, "MO": 6_200_000, "CO": 5_900_000}

df = pd.read_sql("SELECT * FROM bills_canonical", engine)

# derived columns the dashboard uses (mirror the synthetic set)
df["state_population"] = df["state_code"].map(STATE_POP)
df["is_enacted"] = (df["lifecycle_state"] == "enacted").astype(int)
df["reached_passed_chamber"] = df["furthest_stage"].isin(["passed_chamber", "enacted"]).astype(int)

df["first_action_date"] = pd.to_datetime(df["first_action_date"], errors="coerce")
df["latest_action_date"] = pd.to_datetime(df["latest_action_date"], errors="coerce")
today = pd.Timestamp.utcnow().tz_localize(None).normalize()
df["days_active"] = (df["latest_action_date"] - df["first_action_date"]).dt.days
df["days_since_last_action"] = (today - df["latest_action_date"]).dt.days

# primary_topic = first subject (OpenStates-only; null for LegiScan-only rows)
df["primary_topic"] = df["subjects"].str.split("|").str[0]

# tidy dates back to plain YYYY-MM-DD for Sheets/Looker
for c in ["first_action_date", "latest_action_date"]:
    df[c] = df[c].dt.strftime("%Y-%m-%d")

out = "bills_canonical_export.csv"
df.to_csv(out, index=False)
print(f"exported {len(df)} rows -> {out}")
print("by source coverage:", df["sources"].value_counts().to_dict())
print("enriched (both sources):", int((df["source_count"] > 1).sum()))