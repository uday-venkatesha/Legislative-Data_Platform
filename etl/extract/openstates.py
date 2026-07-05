import os, time, requests
from dotenv import load_dotenv
from requests.exceptions import Timeout, ConnectionError as ReqConnError
load_dotenv()
BASE = "https://v3.openstates.org"
HEADERS = {"X-API-KEY": os.environ["OPENSTATES_API_KEY"]}

def _get_with_retry(url, params, retries=4, timeout=45):
    """Retry on rate-limits AND transient network failures with backoff."""
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 15))
                print(f"  rate limited, sleeping {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except (Timeout, ReqConnError) as e:
            last_err = e
            wait = 5 * (attempt + 1)
            print(f"  network error ({type(e).__name__}), retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Failed after {retries} attempts: {url}") from last_err

def fetch_bills(state, max_pages=5, per_page=20, sleep=1.0):
    """Yield raw bill dicts for one jurisdiction, freshest activity first.
    per_page maxes at 20 on v3. max_pages caps the first run so it's quick."""
    page = 1
    while page <= max_pages:
        params = {
            "jurisdiction": state,
            "sort": "latest_action_desc",
            "per_page": per_page,
            "page": page,
            "include": ["sponsorships", "actions"],  # gives us sponsor + real status
        }
        data = _get_with_retry(f"{BASE}/bills", params).json()
        results = data.get("results", [])
        if not results:
            break
        yield from results
        if page >= data.get("pagination", {}).get("max_page", page):
            break
        page += 1
        time.sleep(sleep)   # be polite; raise this if you see 429s