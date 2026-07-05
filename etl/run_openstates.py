import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from etl.extract.openstates import fetch_bills
from etl.transform.bills import transform_bills
from etl.load.mysql_loader import upsert_bills, land_raw
from governance.audit import start_run, finish_run


load_dotenv()
STATES = ["Kansas", "Missouri", "Colorado"]   # a few to start; edit freely
MAX_PAGES = 5

def main():
    engine = create_engine(os.environ["DB_URL"])
    run_id = start_run(engine, "openstates")
    fetched = upserted = 0
    try:
        for state in STATES:
            raw = list(fetch_bills(state, max_pages=MAX_PAGES))
            land_raw(raw, "openstates", engine)
            n = upsert_bills(transform_bills(raw), engine)
            fetched += len(raw); upserted += n
            print(f"{state:10s} fetched={len(raw):4d}  upserted={n:4d}")
        finish_run(engine, run_id, fetched, upserted, "success")
    except Exception as e:
        finish_run(engine, run_id, fetched, upserted, "failed", str(e)[:2000])
        raise
    print(f"\nUpserted this run: {upserted} | run_id: {run_id}")

if __name__ == "__main__":
    main()