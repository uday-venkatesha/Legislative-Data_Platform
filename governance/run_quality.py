import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from governance.quality_checks import run_checks

load_dotenv()
engine = create_engine(os.environ["DB_URL"])
failed = run_checks(engine)
print(f"\n{failed} integrity check(s) failed" if failed else "\nAll integrity checks passed")