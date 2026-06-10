import json
import random

from app import data_store
from app.predictor import Predictor, GROUPS, TEAMS
from app.bracket_logic import full_group_rows, resolve_bracket, group_complete

schedule = data_store.load_schedule()
assert len(schedule) == 104, len(schedule)
group_ms = [e for e in schedule if e["stage"] == "Group"]
assert len(group_ms) == 72
names = {e["team1"] for e in group_ms} | {e["team2"] for e in group_ms}
unknown = names - set(TEAMS)
assert not unknown, unknown
print("schedule OK: 104 matches, all 48 group-stage names map to FIFA names")

# --- pre-tournament: no results -------------------------------------------
results = {"results": {}}
pred = Predictor(schedule, results)
p = pred.predict("Argentina", "Spain", knockout=True, match_date="2026-07-01")
assert abs(p["p1"] + p["px"] + p["p2"] - 1) < 1e-6
print("ARG v ESP:", round(p["p1"], 3), round(p["px"], 3), round(p["p2"], 3),
      "score", p["score"], "adv", round(p["adv1"], 3))
p2 = pred.predict("France", "Haiti", match_date="2026-06-12")
print("FRA v HAI:", round(p2["p1"], 3), round(p2["px"], 3), round(p2["p2"], 3),
      "xg", round(p2["xg1"], 2), round(p2["xg2"], 2))
assert p2["p1"] > 0.7

proj = {g: pred.simulate_group(g) for g in GROUPS}
entries = resolve_bracket(schedule, results["results"], pred, proj)
assert len(entries) == 32
r32 = [x for x in entries if x["entry"]["stage"] == "Round of 32"]
projected = [x for x in r32 if x["slot1"].team and not x["slot1"].confirmed]
print("pre-tournament bracket: R32 projected slot1s:", len(projected),
      "sample:", r32[1]["slot1"].label, "vs", r32[1]["slot2"].label,
      "p=", r32[1]["slot2"].prob)
r16 = [x for x in entries if x["entry"]["stage"] == "Round of 16"]
assert all(x["slot1"].team is None for x in r16), \
    "R16 must not be projected pre-tournament"
print("no champion chaining: R16+ slots are TBD pre-tournament OK")

# --- fill the whole group stage with fake results --------------------------
rng = random.Random(1)
for e in group_ms:
    results["results"][e["id"]] = {"s1": rng.randint(0, 4),
                                   "s2": rng.randint(0, 3),
                                   "pens": None, "teams": None,
                                   "source": "manual"}
pred = Predictor(schedule, results)
assert all(group_complete(g, schedule, results["results"]) for g in GROUPS)
rows, played, remaining = full_group_rows("A", schedule, results["results"])
assert not remaining and len(played) == 6
proj = {g: pred.simulate_group(g) for g in GROUPS}
entries = resolve_bracket(schedule, results["results"], pred, proj)
r32 = [x for x in entries if x["entry"]["stage"] == "Round of 32"]
assert all(x["slot1"].confirmed and x["slot2"].confirmed for x in r32)
teams_in_r32 = [x["slot1"].team for x in r32] + [x["slot2"].team for x in r32]
assert len(set(teams_in_r32)) == 32, len(set(teams_in_r32))
print("group stage complete -> all 32 R32 slots confirmed, all distinct")

mom = pred.momentum("Argentina")
print("Argentina momentum after fake groups:", round(mom, 1))
assert len(pred.momentum_timeline()["Brazil"]) == 3

# --- play knockouts round by round -----------------------------------------
for _ in range(6):
    entries = resolve_bracket(schedule, results["results"], pred, proj)
    for item in entries:
        s1, s2 = item["slot1"], item["slot2"]
        if item["result"] is None and s1.confirmed and s2.confirmed:
            a, b = rng.randint(0, 3), rng.randint(0, 3)
            pens = None
            if a == b:
                pens = [5, 4] if rng.random() < .5 else [3, 5]
            results["results"]["K%d" % item["entry"]["num"]] = {
                "s1": a, "s2": b, "pens": pens,
                "teams": [s1.team, s2.team], "source": "manual"}
    pred = Predictor(schedule, results)
entries = resolve_bracket(schedule, results["results"], pred, proj)
final = [x for x in entries if x["entry"]["stage"] == "Final"][0]
assert final["result"] is not None, "final should be played"
assert len(results["results"]) == 104
print("full knockout playable round by round; final:",
      final["slot1"].team, final["result"]["s1"], "-",
      final["result"]["s2"], final["slot2"].team)

# --- results store round-trip ----------------------------------------------
store = data_store.save_result("G|Mexico|South Africa", 2, 1)
assert store["results"]["G|Mexico|South Africa"]["s1"] == 2
store = data_store.delete_result("G|Mexico|South Africa")
assert "G|Mexico|South Africa" not in store["results"]
print("results.json save/delete round-trip OK")
print("ALL LOGIC TESTS PASSED")
