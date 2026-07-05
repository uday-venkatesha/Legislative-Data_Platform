from datetime import date
from standardize.normalizers import (norm_state, norm_party, norm_date,
                                     norm_identifier, norm_chamber, make_uid)
def ck(a, b, m): assert a == b, f"FAIL {m}: {a!r} != {b!r}"

ck(norm_state("Kansas"), ("KS","Kansas"), "state name")
ck(norm_state("KS"), ("KS","Kansas"), "state code")
ck(norm_state("United States"), ("US","United States"), "federal")
ck(norm_party("R"), "Republican", "party R"); ck(norm_party("Democratic"), "Democrat", "party dem")
ck(norm_date("2026-05-11T22:38:34"), date(2026,5,11), "iso datetime")
ck(norm_date("0000-00-00"), None, "junk date")
ck(norm_identifier("hb 02427"), "HB 2427", "identifier")
ck(norm_chamber(identifier="SB 124"), "Senate", "chamber id")
ck(norm_chamber(body="H"), "House", "chamber body")
ck(make_uid("KS","2025-2026","HB 2427"), "KS:2025-2026:HB2427", "uid")
print("all normalizer tests passed")