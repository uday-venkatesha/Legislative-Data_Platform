import os, re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from etl.extract.legiscan import fetch_masterlist
from etl.transform.legiscan_bills import transform_masterlist
from etl.load.mysql_loader import upsert_bills, land_raw
from standardize.normalizers import session_year
from governance.audit import start_run, finish_run

load_dotenv()
STATES = ["KS", "MO", "CO"]

def main():
    engine = create_engine(os.environ["DB_URL"])
    run_id = start_run(engine, "legiscan")
    fetched = upserted = 0
    try:
        for st in STATES:
            session, bills = fetch_masterlist(st)
            yr = session_year(session.get("year_start"))
            if not yr and bills:
                m = re.search(r"/(\d{4})$", bills[0].get("url", ""))
                yr = int(m.group(1)) if m else None
            land_raw(bills, "legiscan", engine, state_code=st)
            n = upsert_bills(transform_masterlist(bills, st, yr), engine)
            fetched += len(bills); upserted += n
            print(f"{st}  year={yr}  fetched={len(bills):5d}  upserted={n:5d}")
        finish_run(engine, run_id, fetched, upserted, "success")
    except Exception as e:
        finish_run(engine, run_id, fetched, upserted, "failed", str(e)[:2000])
        raise
    print(f"\nUpserted this run: {upserted} | run_id: {run_id}")

if __name__ == "__main__":
    main()