"""World Cup 2026 — Flask backend for the single-page app.

Run with:  python app.py   →  http://localhost:5000

Reuses the existing prediction engine (app/predictor.py,
app/bracket_logic.py) and result store (results.json).  User predictions
for the competition page live in predictions.json.  No database.
"""

import hashlib
import json
import os
from datetime import date

from flask import Flask, jsonify, request, send_file

from app import data_store
from app.bracket_logic import full_group_rows, resolve_bracket
from app.flags import flag
from app.predictor import GROUPS, TEAMS, Predictor
from data.form import INJURIES, PRE_FORM

ROOT = os.path.dirname(os.path.abspath(__file__))
PREDICTIONS_PATH = os.path.join(ROOT, "predictions.json")

app = Flask(__name__)

EXACT_POINTS = 5      # competition scoring
OUTCOME_POINTS = 2

STAGE_TR = {"Group": "Grup Aşaması", "Round of 32": "Son 32",
            "Round of 16": "Son 16", "Quarter-finals": "Çeyrek Final",
            "Semi-finals": "Yarı Final", "Third place": "Üçüncülük",
            "Final": "Final"}


# ---------------------------------------------------------------------------
# state (memoised on the contents of results.json)
# ---------------------------------------------------------------------------
_cache = {"key": None}


def state():
    schedule = data_store.load_schedule()
    results = data_store.load_results()
    key = hashlib.md5(json.dumps(results["results"],
                                 sort_keys=True).encode()).hexdigest()
    if _cache["key"] != key:
        predictor = Predictor(schedule, results)
        _cache.update(
            key=key, schedule=schedule, results=results, predictor=predictor,
            projections={g: predictor.simulate_group(g, n=1200)
                         for g in GROUPS})
        _cache["bracket"] = resolve_bracket(schedule, results["results"],
                                            predictor,
                                            _cache["projections"])
    return _cache


def team_payload(name):
    meta = TEAMS[name]
    return {"name": name, "code": meta.code, "flag": flag(name),
            "rank": meta.fifa_rank, "group": meta.group}


def prediction_payload(predictor, t1, t2, knockout, match_date=None):
    p = predictor.predict(t1, t2, knockout=knockout, match_date=match_date)
    out = {"p1": round(p["p1"], 4), "px": round(p["px"], 4),
           "p2": round(p["p2"], 4), "score": list(p["score"]),
           "xg1": round(p["xg1"], 2), "xg2": round(p["xg2"], 2),
           "confidence": round(p["confidence"], 1), "factors": p["factors"]}
    if knockout:
        out["adv1"] = round(p["adv1"], 4)
        out["adv2"] = round(p["adv2"], 4)
    return out


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return send_file(os.path.join(ROOT, "index.html"))


# ---------------------------------------------------------------------------
# GET /api/matches/today
# ---------------------------------------------------------------------------
@app.get("/api/matches/today")
def api_today():
    s = state()
    schedule, results = s["schedule"], s["results"]["results"]
    dates = sorted({e["date"] for e in schedule})
    today = date.today().isoformat()
    picked = request.args.get("date")
    if not picked:
        picked = today if today in dates else \
            min((d for d in dates if d >= today), default=dates[-1])
    slots_by_num = {item["entry"]["num"]: item for item in s["bracket"]}

    matches = []
    for e in schedule:
        if e["date"] != picked:
            continue
        res = results.get(e["id"])
        t1, t2 = e["team1"], e["team2"]
        if res and res.get("teams"):
            t1, t2 = res["teams"]
        confirmed = t1 in TEAMS and t2 in TEAMS
        hint1, hint2 = t1, t2
        if not confirmed and e["num"] in slots_by_num:
            item = slots_by_num[e["num"]]
            s1, s2 = item["slot1"], item["slot2"]
            if s1.confirmed and s2.confirmed:
                t1, t2, confirmed = s1.team, s2.team, True
            else:
                hint1, hint2 = s1.label, s2.label
        m = {"id": e["id"], "time": e["time"], "venue": e["venue"],
             "stage": STAGE_TR[e["stage"]],
             "group": e["group"], "confirmed": confirmed}
        if confirmed:
            m["team1"] = team_payload(t1)
            m["team2"] = team_payload(t2)
            m["prediction"] = prediction_payload(
                s["predictor"], t1, t2, e["stage"] != "Group", e["date"])
            if res:
                m["result"] = {"s1": res["s1"], "s2": res["s2"],
                               "pens": res.get("pens")}
                actual = ("1" if res["s1"] > res["s2"] else
                          "2" if res["s1"] < res["s2"] else "x")
                pr = m["prediction"]
                predicted = ("1" if pr["p1"] >= max(pr["px"], pr["p2"]) else
                             "2" if pr["p2"] >= max(pr["p1"], pr["px"]) else "x")
                m["model_correct"] = actual == predicted
        else:
            m["hint1"], m["hint2"] = hint1, hint2
        matches.append(m)

    kickoff = date(2026, 6, 11)
    d = date.fromisoformat(picked)
    day_no = (d - kickoff).days + 1
    return jsonify({"date": picked, "dates": dates,
                    "day_label": (f"TURNUVA {day_no}. GÜN" if day_no >= 1
                                  else f"AÇILIŞA {1 - day_no} GÜN"),
                    "matches": matches})


# ---------------------------------------------------------------------------
# GET /api/groups
# ---------------------------------------------------------------------------
@app.get("/api/groups")
def api_groups():
    s = state()
    out = []
    for letter in sorted(GROUPS):
        rows, played, remaining = full_group_rows(
            letter, s["schedule"], s["results"]["results"])
        pos_probs, order, stats = s["projections"][letter]
        out.append({
            "letter": letter,
            "rows": [{**{k: r[k] for k in
                         ("P", "W", "D", "L", "GF", "GA", "GD", "Pts")},
                      **team_payload(r["team"]),
                      "top2_prob": round(pos_probs[r["team"]][0]
                                         + pos_probs[r["team"]][1], 3)}
                     for r in rows],
            "remaining": [{"date": e["date"],
                           "team1": team_payload(e["team1"]),
                           "team2": team_payload(e["team2"])}
                          for e in remaining],
            "projection": [{"team": team_payload(t),
                            "xpts": round(stats[t][0], 1),
                            "prob": round(pos_probs[t][i], 3)}
                           for i, t in enumerate(order)],
        })
    return jsonify(out)


# ---------------------------------------------------------------------------
# GET /api/bracket
# ---------------------------------------------------------------------------
def slot_payload(slot):
    out = {"confirmed": slot.confirmed, "label": slot.label}
    if slot.team:
        out.update(team_payload(slot.team))
        if not slot.confirmed and slot.prob is not None:
            out["prob"] = round(slot.prob, 3)
    return out


@app.get("/api/bracket")
def api_bracket():
    s = state()
    stages = {}
    champion = None
    for item in s["bracket"]:
        e, res = item["entry"], item["result"]
        m = {"num": e["num"], "date": e["date"], "venue": e["venue"],
             "slot1": slot_payload(item["slot1"]),
             "slot2": slot_payload(item["slot2"])}
        if res:
            m["result"] = {"s1": res["s1"], "s2": res["s2"],
                           "pens": res.get("pens")}
            names = res.get("teams") or [item["slot1"].team,
                                         item["slot2"].team]
            if names[0] and names[1]:
                if res["s1"] != res["s2"]:
                    w = names[0] if res["s1"] > res["s2"] else names[1]
                elif res.get("pens"):
                    w = names[0] if res["pens"][0] > res["pens"][1] else names[1]
                else:
                    w = None
                m["winner"] = w
                if e["stage"] == "Final" and w:
                    champion = team_payload(w)
        stages.setdefault(e["stage"], []).append(m)
    return jsonify({"stages": [{"name": st, "name_tr": STAGE_TR[st],
                                "matches": stages.get(st, [])}
                               for st in ("Round of 32", "Round of 16",
                                          "Quarter-finals", "Semi-finals",
                                          "Third place", "Final")],
                    "champion": champion})


# ---------------------------------------------------------------------------
# teams + on-demand predictor
# ---------------------------------------------------------------------------
@app.get("/api/teams")
def api_teams():
    return jsonify([{**team_payload(n),
                     "form": PRE_FORM.get(n, {}).get("last5"),
                     "form_note": PRE_FORM.get(n, {}).get("note"),
                     "injuries": [{"player": p, "status": st}
                                  for p, st in INJURIES.get(n, [])]}
                    for n in sorted(TEAMS)])


@app.get("/api/predict")
def api_predict():
    t1, t2 = request.args.get("t1"), request.args.get("t2")
    knockout = request.args.get("knockout") == "1"
    if t1 not in TEAMS or t2 not in TEAMS or t1 == t2:
        return jsonify({"error": "iki farklı takım seçin"}), 400
    s = state()
    return jsonify({"team1": team_payload(t1), "team2": team_payload(t2),
                    "prediction": prediction_payload(
                        s["predictor"], t1, t2, knockout,
                        date.today().isoformat())})


# ---------------------------------------------------------------------------
# prediction competition
# ---------------------------------------------------------------------------
def load_predictions():
    if os.path.exists(PREDICTIONS_PATH):
        with open(PREDICTIONS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {"players": {}}


def save_predictions(store):
    with open(PREDICTIONS_PATH, "w", encoding="utf-8") as fh:
        json.dump(store, fh, ensure_ascii=False, indent=1)


@app.get("/api/predictions")
def api_predictions():
    s = state()
    results = s["results"]["results"]
    store = load_predictions()
    schedule_by_id = {e["id"]: e for e in s["schedule"]}

    board = []
    for player, picks in store["players"].items():
        pts = exact = outcome = 0
        for mid, (ps1, ps2) in picks.items():
            res = results.get(mid)
            if not res:
                continue
            if ps1 == res["s1"] and ps2 == res["s2"]:
                pts += EXACT_POINTS
                exact += 1
            elif ((ps1 > ps2) == (res["s1"] > res["s2"])
                  and (ps1 == ps2) == (res["s1"] == res["s2"])):
                pts += OUTCOME_POINTS
                outcome += 1
        board.append({"name": player, "points": pts, "exact": exact,
                      "outcome": outcome, "picks": len(picks)})
    board.sort(key=lambda r: (-r["points"], -r["exact"], r["name"]))

    open_matches = []
    for e in s["schedule"]:
        if e["stage"] == "Group" and e["id"] not in results:
            open_matches.append({
                "id": e["id"], "date": e["date"],
                "label": f"{flag(e['team1'])} {e['team1']} – "
                         f"{e['team2']} {flag(e['team2'])}"})
        if len(open_matches) >= 18:
            break
    return jsonify({"leaderboard": board, "open_matches": open_matches,
                    "scoring": {"exact": EXACT_POINTS,
                                "outcome": OUTCOME_POINTS}})


@app.post("/api/predictions")
def api_predictions_post():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("player") or "").strip()[:24]
    mid = data.get("match_id")
    try:
        s1, s2 = int(data.get("s1")), int(data.get("s2"))
    except (TypeError, ValueError):
        return jsonify({"error": "geçersiz skor"}), 400
    s = state()
    if not name:
        return jsonify({"error": "isim gerekli"}), 400
    if mid not in {e["id"] for e in s["schedule"]}:
        return jsonify({"error": "maç bulunamadı"}), 404
    if mid in s["results"]["results"]:
        return jsonify({"error": "bu maç oynandı — tahmin kapalı"}), 409
    if not (0 <= s1 <= 15 and 0 <= s2 <= 15):
        return jsonify({"error": "skor 0-15 arası olmalı"}), 400
    store = load_predictions()
    store["players"].setdefault(name, {})[mid] = [s1, s2]
    save_predictions(store)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# real results in / live feed refresh
# ---------------------------------------------------------------------------
@app.post("/api/results")
def api_results_post():
    data = request.get_json(force=True, silent=True) or {}
    mid = data.get("match_id")
    try:
        s1, s2 = int(data.get("s1")), int(data.get("s2"))
    except (TypeError, ValueError):
        return jsonify({"error": "geçersiz skor"}), 400
    s = state()
    entry = next((e for e in s["schedule"] if e["id"] == mid), None)
    if entry is None:
        return jsonify({"error": "maç bulunamadı"}), 404
    pens, teams = None, None
    if entry["stage"] != "Group":
        item = next(i for i in s["bracket"] if i["entry"]["id"] == mid)
        if not (item["slot1"].confirmed and item["slot2"].confirmed):
            return jsonify({"error": "eşleşme henüz belli değil"}), 409
        teams = [item["slot1"].team, item["slot2"].team]
        if s1 == s2:
            p = data.get("pens") or []
            if len(p) != 2 or p[0] == p[1]:
                return jsonify({"error": "penaltı sonucu gerekli"}), 400
            pens = [int(p[0]), int(p[1])]
    data_store.save_result(mid, s1, s2, pens, teams)
    _cache["key"] = None
    return jsonify({"ok": True})


@app.post("/api/refresh")
def api_refresh():
    count, err = data_store.refresh_from_feed()
    if err:
        return jsonify({"error": err}), 502
    _cache["key"] = None
    return jsonify({"ok": True, "results": count})


# ---------------------------------------------------------------------------
# GET /api/analysis — model accuracy so far
# ---------------------------------------------------------------------------
@app.get("/api/analysis")
def api_analysis():
    s = state()
    predictor, results = s["predictor"], s["results"]["results"]
    history, by_stage = [], {}
    for e in s["schedule"]:
        res = results.get(e["id"])
        if not res:
            continue
        t1, t2 = e["team1"], e["team2"]
        if res.get("teams"):
            t1, t2 = res["teams"]
        if t1 not in TEAMS or t2 not in TEAMS:
            continue
        p = predictor.predict(t1, t2, knockout=e["stage"] != "Group",
                              match_date=e["date"])
        actual = ("1" if res["s1"] > res["s2"] else
                  "2" if res["s1"] < res["s2"] else "x")
        predicted = ("1" if p["p1"] >= max(p["px"], p["p2"]) else
                     "2" if p["p2"] >= max(p["p1"], p["px"]) else "x")
        ok = actual == predicted
        exact = [res["s1"], res["s2"]] == list(p["score"])
        stage = STAGE_TR[e["stage"]]
        agg = by_stage.setdefault(stage, {"stage": stage, "total": 0,
                                          "correct": 0})
        agg["total"] += 1
        agg["correct"] += ok
        history.append({"date": e["date"], "stage": stage,
                        "team1": team_payload(t1), "team2": team_payload(t2),
                        "predicted": list(p["score"]),
                        "actual": [res["s1"], res["s2"]],
                        "pens": res.get("pens"),
                        "correct": ok, "exact": exact,
                        "confidence": round(p["confidence"], 0)})
    total = len(history)
    correct = sum(h["correct"] for h in history)
    exact_n = sum(h["exact"] for h in history)
    return jsonify({"total": total, "correct": correct, "exact": exact_n,
                    "accuracy": round(100 * correct / total, 1) if total else None,
                    "by_stage": list(by_stage.values()),
                    "history": history[::-1]})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
