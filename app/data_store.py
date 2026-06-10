"""Schedule + results storage.

Schedule comes from the openfootball/worldcup.json public-domain feed
(bundled snapshot in data/schedule.json, refreshable in-app — no API key).
Real results are merged from the feed and/or entered manually, and cached
in results.json next to the project so the app stays fast and works
offline.
"""

import json
import os
from datetime import date

import requests

FEED_URL = ("https://raw.githubusercontent.com/openfootball/worldcup.json/"
            "master/2026/worldcup.json")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEDULE_PATH = os.path.join(ROOT, "data", "schedule.json")
RESULTS_PATH = os.path.join(ROOT, "results.json")

# openfootball feed names -> official FIFA names used in data/teams.py
FEED_NAME_MAP = {
    "South Korea": "Korea Republic",
    "Czech Republic": "Czechia",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Ivory Coast": "Côte d'Ivoire",
    "Turkey": "Türkiye",
    "USA": "United States",
    "Cape Verde": "Cabo Verde",
}

STAGE_OF_ROUND = {
    "Round of 32": "Round of 32",
    "Round of 16": "Round of 16",
    "Quarter-final": "Quarter-finals",
    "Semi-final": "Semi-finals",
    "Match for third place": "Third place",
    "Final": "Final",
}
KNOCKOUT_ORDER = ["Round of 32", "Round of 16", "Quarter-finals",
                  "Semi-finals", "Third place", "Final"]


def canonical(name):
    return FEED_NAME_MAP.get(name, name)


def is_placeholder(name):
    """True for bracket tokens like '1A', '2B', '3A/B/C/D/F', 'W73', 'L101'."""
    return (len(name) <= 4 and name[0] in "123WL" and name[1:].isdigit()) \
        or name.startswith("3") and "/" in name \
        or (len(name) == 2 and name[0] in "12" and name[1].isalpha())


# ---------------------------------------------------------------------------
# schedule
# ---------------------------------------------------------------------------
def _match_id(entry):
    if entry["stage"] == "Group":
        return f"G|{entry['team1']}|{entry['team2']}"
    return f"K{entry['num']}"


def _normalise(raw):
    matches = []
    for m in raw["matches"]:
        rnd = m["round"]
        if rnd.startswith("Matchday"):
            stage, group = "Group", m["group"][-1]
            num = None
        else:
            stage, group = STAGE_OF_ROUND[rnd], None
            num = m.get("num") or (103 if "third" in rnd.lower() else 104)
        entry = {
            "stage": stage,
            "round": rnd,
            "group": group,
            "num": num,
            "date": m["date"],
            "time": m.get("time", ""),
            "venue": m.get("ground", ""),
            "team1": canonical(m["team1"]),
            "team2": canonical(m["team2"]),
        }
        entry["id"] = _match_id(entry)
        matches.append(entry)
    matches.sort(key=lambda e: (e["date"], e["time"]))
    return matches


def load_schedule():
    with open(SCHEDULE_PATH, encoding="utf-8") as fh:
        return _normalise(json.load(fh))


# ---------------------------------------------------------------------------
# results store
# ---------------------------------------------------------------------------
def load_results():
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {"results": {}, "last_refresh": None}


def _write(store):
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(store, fh, ensure_ascii=False, indent=1)


def save_result(match_id, s1, s2, pens=None, teams=None, source="manual"):
    store = load_results()
    store["results"][match_id] = {
        "s1": int(s1), "s2": int(s2),
        "pens": list(pens) if pens else None,
        "teams": list(teams) if teams else None,
        "source": source,
    }
    _write(store)
    return store


def delete_result(match_id):
    store = load_results()
    store["results"].pop(match_id, None)
    _write(store)
    return store


# ---------------------------------------------------------------------------
# live feed refresh
# ---------------------------------------------------------------------------
def _extract_score(m):
    """Handle both openfootball score styles; returns (s1, s2, pens) or None."""
    sc = m.get("score")
    if isinstance(sc, dict):
        ft = sc.get("et") or sc.get("ft")     # after extra time if it went there
        if ft is None:
            return None
        pens = sc.get("p")
        return int(ft[0]), int(ft[1]), (list(map(int, pens)) if pens else None)
    if m.get("score1") is not None and m.get("score2") is not None:
        return int(m["score1"]), int(m["score2"]), None
    return None


def refresh_from_feed(timeout=20):
    """Fetch the live feed; update bundled schedule + merge real scores.

    Returns (number of results now stored from the feed, error message or None).
    """
    try:
        resp = requests.get(FEED_URL, timeout=timeout)
        resp.raise_for_status()
        raw = resp.json()
    except Exception as exc:                      # offline-friendly
        return None, f"Could not reach the live feed: {exc}"

    with open(SCHEDULE_PATH, "w", encoding="utf-8") as fh:
        json.dump(raw, fh, ensure_ascii=False, indent=1)

    store = load_results()
    count = 0
    for m in raw["matches"]:
        score = _extract_score(m)
        if score is None:
            continue
        rnd = m["round"]
        if rnd.startswith("Matchday"):
            mid = f"G|{canonical(m['team1'])}|{canonical(m['team2'])}"
        else:
            num = m.get("num") or (103 if "third" in rnd.lower() else 104)
            mid = f"K{num}"
        existing = store["results"].get(mid)
        if existing and existing.get("source") == "manual":
            continue                              # manual entries win
        t1, t2 = canonical(m["team1"]), canonical(m["team2"])
        teams = None if is_placeholder(t1) else [t1, t2]
        store["results"][mid] = {
            "s1": score[0], "s2": score[1], "pens": score[2],
            "teams": teams, "source": "feed",
        }
        count += 1
    store["last_refresh"] = date.today().isoformat()
    _write(store)
    return count, None
