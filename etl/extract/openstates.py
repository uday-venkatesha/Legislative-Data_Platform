import os, time, requests
from dotenv import load_dotenv

load_dotenv()
BASE = "https://v3.openstates.org"
HEADERS = {"X-API-KEY": os.environ["OPENSTATES_API_KEY"]}

def _get_with_retry(url, params, retries=4):
    """OpenStates free tier is rate-limited; respect 429 + Retry-After."""
    for _ in range(retries):
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 15))
            print(f"  rate limited, sleeping {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()

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