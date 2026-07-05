import os, time, requests
from dotenv import load_dotenv
from requests.exceptions import Timeout, ConnectionError as ReqConnError

load_dotenv()
BASE = "https://api.legiscan.com/"
KEY = os.environ["LEGISCAN_API_KEY"]

def _call(op, timeout=45, retries=4, **params):
    """One LegiScan operation, with the same network resilience as OpenStates."""
    params.update(key=KEY, op=op)
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(BASE, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            if data.get("status") != "OK":
                raise RuntimeError(f"LegiScan {op}: {data.get('alert') or 'non-OK status'}")
            return data
        except (Timeout, ReqConnError) as e:
            last = e; wait = 5 * (attempt + 1)
            print(f"  network error ({type(e).__name__}), retry in {wait}s"); time.sleep(wait)
    raise RuntimeError(f"LegiScan {op} failed after {retries} tries") from last

def fetch_masterlist(state):
    """Returns (session_meta, [bill dicts]) for a state's current session.
    The masterlist mixes a 'session' entry with numbered bill entries."""
    ml = _call("getMasterList", state=state).get("masterlist", {})
    session = ml.get("session", {})
    bills = [v for v in ml.values() if isinstance(v, dict) and "bill_id" in v]
    return session, bills