"""Unit check for the live-badge logic — run: python test_live.py"""
import importlib.util
from datetime import datetime, timedelta, timezone

spec = importlib.util.spec_from_file_location("wcmain", "main.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)          # bare mode: streamlit calls are no-ops

now = datetime.now(timezone.utc)

# kicked off 30 minutes ago, no result stored -> LIVE
ko = now - timedelta(minutes=30)
entry = {"id": "G|X|Y", "date": ko.strftime("%Y-%m-%d"),
         "time": ko.strftime("%H:%M") + " UTC+0"}
assert m.is_live(entry, {}) is True, "in-window match should be live"

# same match but a final score is stored -> not live
assert m.is_live(entry, {"G|X|Y": {"s1": 1, "s2": 0}}) is False

# kicked off 4 hours ago -> window passed
ko_old = now - timedelta(hours=4)
entry_old = {"id": "G|A|B", "date": ko_old.strftime("%Y-%m-%d"),
             "time": ko_old.strftime("%H:%M") + " UTC+0"}
assert m.is_live(entry_old, {}) is False

# kickoff parsing with venue offsets (Mexico City opener: 13:00 UTC-6)
ko_mex = m.kickoff_utc({"date": "2026-06-11", "time": "13:00 UTC-6"})
assert ko_mex == datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc), ko_mex

# no time string -> never live, never crashes
assert m.is_live({"id": "x", "date": "2026-06-11", "time": ""}, {}) is False

print("LIVE-BADGE LOGIC OK: in-window=live, scored=final, "
      "expired=off, UTC-6 parsing correct")
