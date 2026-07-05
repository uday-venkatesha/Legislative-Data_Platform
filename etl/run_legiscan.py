import os, re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from etl.extract.legiscan import fetch_masterlist
from etl.transform.legiscan_bills import transform_masterlist
from etl.load.mysql_loader import upsert_bills, land_raw
from standardize.normalizers import session_year

load_dotenv()
STATES = ["KS", "MO", "CO"]   # 2-letter for LegiScan

def main():
    engine = create_engine(os.environ["DB_URL"])
    total = 0
    for st in STATES:
        session, bills = fetch_masterlist(st)
        yr = session_year(session.get("year_start"))
        if not yr and bills:                      # fallback: year is the tail of the url
            m = re.search(r"/(\d{4})$", bills[0].get("url", ""))
            yr = int(m.group(1)) if m else None
        land_raw(bills, "legiscan", engine, state_code=st)
        n = upsert_bills(transform_masterlist(bills, st, yr), engine)
        total += n
        print(f"{st}  year={yr}  fetched={len(bills):5d}  upserted={n:5d}")
    with engine.connect() as c:
        rows = c.execute(text("SELECT COUNT(*) FROM bills")).scalar()
    print(f"\nUpserted this run: {total} | Rows in bills: {rows}")

if __name__ == "__main__":
    main()