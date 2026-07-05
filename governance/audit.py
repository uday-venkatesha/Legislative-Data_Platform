from datetime import datetime
from sqlalchemy import text

def start_run(engine, source):
    """Open an audit record, return its run_id."""
    with engine.begin() as c:
        r = c.execute(text(
            "INSERT INTO audit_log (source, run_started_at, status) "
            "VALUES (:s, :t, 'running')"), {"s": source, "t": datetime.utcnow()})
        return r.lastrowid

def finish_run(engine, run_id, fetched, upserted, status="success", error=None):
    with engine.begin() as c:
        c.execute(text(
            "UPDATE audit_log SET run_ended_at=:t, rows_fetched=:f, "
            "rows_upserted=:u, status=:s, error_message=:e WHERE run_id=:id"),
            {"t": datetime.utcnow(), "f": fetched, "u": upserted,
             "s": status, "e": error, "id": run_id})