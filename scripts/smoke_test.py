import os, requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# 1. DB reachable?
engine = create_engine(os.environ["DB_URL"])
with engine.connect() as c:
    print("MySQL OK:", c.execute(text("SELECT VERSION()")).scalar())

# 2. OpenStates key valid?
r = requests.get(
    "https://v3.openstates.org/jurisdictions",
    headers={"X-API-KEY": os.environ["OPENSTATES_API_KEY"]},
    params={"classification": "state", "per_page": 3},
    timeout=30,
)
r.raise_for_status()
print("OpenStates OK:", [j["name"] for j in r.json()["results"]])