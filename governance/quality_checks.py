from sqlalchemy import text

CHECKS = {
  "null_bill_uid":       "SELECT COUNT(*) FROM bills WHERE bill_uid IS NULL",
  "null_status":         "SELECT COUNT(*) FROM bills WHERE furthest_stage IS NULL "
                         "OR lifecycle_state IS NULL",
  "duplicate_source_id": "SELECT COUNT(*) FROM (SELECT source_name, source_bill_id "
                         "FROM bills GROUP BY source_name, source_bill_id "
                         "HAVING COUNT(*)>1) t",
  "bad_date_order":      "SELECT COUNT(*) FROM bills WHERE first_action_date IS NOT NULL "
                         "AND latest_action_date IS NOT NULL "
                         "AND latest_action_date < first_action_date",
  "unknown_state_code":  "SELECT COUNT(*) FROM bills WHERE state_code IS NULL",
}

# Rate checks — informational, not pass/fail (this is where the active-bias lives)
RATES = {
  "legiscan_active_rate":
     "SELECT ROUND(100*AVG(lifecycle_state='active'),1) "
     "FROM bills WHERE source_name='legiscan'",
  "missing_sponsor_rate":
     "SELECT ROUND(100*AVG(primary_sponsor IS NULL),1) FROM bills",
}

def run_checks(engine):
    print("=== integrity checks (expect 0) ===")
    failed = 0
    with engine.connect() as c:
        for name, sql in CHECKS.items():
            n = c.execute(text(sql)).scalar()
            flag = "OK" if n == 0 else "FAIL"
            if n: failed += 1
            print(f"  [{flag}] {name:22s} {n}")
        print("=== rate signals (informational) ===")
        for name, sql in RATES.items():
            print(f"  {name:22s} {c.execute(text(sql)).scalar()}%")
    return failed