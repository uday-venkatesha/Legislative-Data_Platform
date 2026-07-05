import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from etl.extract.openstates import fetch_bills
from etl.transform.bills import transform_bills
from etl.load.mysql_loader import upsert_bills

load_dotenv()
STATES = ["Kansas", "Missouri", "Colorado"]   # a few to start; edit freely
MAX_PAGES = 5

def main():
    engine = create_engine(os.environ["DB_URL"])
    total = 0
    for state in STATES:
        raw = list(fetch_bills(state, max_pages=MAX_PAGES))
        n = upsert_bills(transform_bills(raw), engine)
        total += n
        print(f"{state:10s} fetched={len(raw):4d}  upserted={n:4d}")
    with engine.connect() as c:
        rows = c.execute(text("SELECT COUNT(*) FROM bills")).scalar()
    print(f"\nUpserted this run: {total} | Rows in bills: {rows}")

if __name__ == "__main__":
    main()