"""Cross-source field normalizers. Pure, unit-testable functions that map each
source's dialect onto ONE canonical vocabulary. Reused by every source adapter."""
import re
from datetime import date, datetime

_STATE_TO_CODE = {"alabama":"AL","alaska":"AK","arizona":"AZ","arkansas":"AR",
 "california":"CA","colorado":"CO","connecticut":"CT","delaware":"DE","florida":"FL",
 "georgia":"GA","hawaii":"HI","idaho":"ID","illinois":"IL","indiana":"IN","iowa":"IA",
 "kansas":"KS","kentucky":"KY","louisiana":"LA","maine":"ME","maryland":"MD",
 "massachusetts":"MA","michigan":"MI","minnesota":"MN","mississippi":"MS","missouri":"MO",
 "montana":"MT","nebraska":"NE","nevada":"NV","new hampshire":"NH","new jersey":"NJ",
 "new mexico":"NM","new york":"NY","north carolina":"NC","north dakota":"ND","ohio":"OH",
 "oklahoma":"OK","oregon":"OR","pennsylvania":"PA","rhode island":"RI","south carolina":"SC",
 "south dakota":"SD","tennessee":"TN","texas":"TX","utah":"UT","vermont":"VT","virginia":"VA",
 "washington":"WA","west virginia":"WV","wisconsin":"WI","wyoming":"WY","district of columbia":"DC"}
_CODE_TO_STATE = {v: k.title() for k, v in _STATE_TO_CODE.items()}
_CODE_TO_STATE["US"] = "United States"
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def norm_state(value):
    """'Kansas' / 'KS' / 'United States' -> ('KS','Kansas'); federal -> ('US',...)."""
    if not value: return (None, None)
    v = str(value).strip(); low = v.lower()
    if low in ("us", "united states", "congress", "u.s.", "federal"): return ("US", "United States")
    if low in _STATE_TO_CODE: return (_STATE_TO_CODE[low], v.title())
    if v.upper() in _CODE_TO_STATE: return (v.upper(), _CODE_TO_STATE[v.upper()])
    return (None, v)                      # unknown -> null code flags it for a quality check

def norm_party(value):
    if not value: return None
    v = str(value).strip().lower()
    if v in ("r","rep","republican"): return "Republican"
    if v in ("d","dem","democrat","democratic"): return "Democrat"
    if v in ("i","ind","independent"): return "Independent"
    return "Other"

def norm_date(value):
    """ISO strings, datetimes, 'YYYY-MM-DD', junk -> date or None."""
    if value in (None, "", "0000-00-00"): return None
    if isinstance(value, datetime): return value.date()
    if isinstance(value, date): return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d","%Y-%m-%dT%H:%M:%S","%m/%d/%Y","%Y/%m/%d"):
        try: return datetime.strptime(s[:19], fmt).date()
        except ValueError: pass
    try: return datetime.fromisoformat(s.replace("Z","+00:00")).date()
    except ValueError: return None

_ID_RE = re.compile(r"^([A-Za-z]+)\s*0*(\d+)$")
def norm_identifier(value):
    """'HB2427' / 'hb 02427' -> 'HB 2427'."""
    if not value: return None
    s = str(value).strip(); m = _ID_RE.match(s)
    return f"{m.group(1).upper()} {int(m.group(2))}" if m else s.upper()

def norm_chamber(identifier=None, body=None):
    if body:
        b = str(body).strip().lower()
        if b in ("h","house","lower"): return "House"
        if b in ("s","senate","upper"): return "Senate"
    ident = norm_identifier(identifier) or ""
    p = ident.split(" ")[0]
    if p.startswith(("HB","HR","HCR","HJR","HJ","H","AB","A")): return "House"
    if p.startswith(("SB","SR","SCR","SJR","SJ","S")): return "Senate"
    return None

def session_year(value):
    """Collapse any source's session label to its START YEAR so keys align
    across sources: '2025-2026'->2025, '2026A'->2026, 2025 (int)->2025."""
    if value is None: return None
    if isinstance(value, int): return value
    m = _YEAR_RE.search(str(value))
    return int(m.group(0)) if m else None

def make_uid(state_code, session, identifier):
    """Cross-source dedup key on the session's START YEAR: KS:2025:HB2427.
    Accepts a raw session label OR a year; both collapse to the same key."""
    ident = (norm_identifier(identifier) or "").replace(" ", "")
    yr = session_year(session)
    return f"{state_code or 'NA'}:{yr or 'NA'}:{ident}"
