"""API contract test for the Flask backend — run: python test_api.py"""
import importlib.util

# app.py shares its name with the app/ package, so load it by path
spec = importlib.util.spec_from_file_location("flask_backend", "app.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

c = backend.app.test_client()

r = c.get("/")
assert r.status_code == 200 and b"WC26" in r.data
print("GET / serves index.html OK")

r = c.get("/api/matches/today")
d = r.get_json()
assert r.status_code == 200 and d["matches"], d
assert all(m["confirmed"] for m in d["matches"]), "opening day teams known"
m0 = d["matches"][0]
assert {"p1", "px", "p2", "score", "confidence"} <= set(m0["prediction"])
print("GET /api/matches/today OK:", d["date"], d["day_label"],
      len(d["matches"]), "matches")

r = c.get("/api/matches/today?date=2026-06-28")
d = r.get_json()
assert d["matches"] and not d["matches"][0]["confirmed"]
assert d["matches"][0]["hint1"]
print("knockout day pre-tournament shows hints OK")

r = c.get("/api/groups")
gs = r.get_json()
assert len(gs) == 12 and all(len(g["rows"]) == 4 for g in gs)
print("GET /api/groups OK")

r = c.get("/api/bracket")
b = r.get_json()
assert len(b["stages"]) == 6
r32 = b["stages"][0]["matches"]
assert len(r32) == 16 and b["champion"] is None
print("GET /api/bracket OK (16 R32 matches, no champion yet)")

r = c.get("/api/teams")
assert len(r.get_json()) == 48
print("GET /api/teams OK")

r = c.get("/api/predict?t1=T%C3%BCrkiye&t2=Brazil&knockout=1")
p = r.get_json()
assert abs(p["prediction"]["p1"] + p["prediction"]["px"]
           + p["prediction"]["p2"] - 1) < 1e-3
assert "adv1" in p["prediction"]
print("GET /api/predict OK:", p["prediction"]["p1"], "/",
      p["prediction"]["px"], "/", p["prediction"]["p2"])

r = c.get("/api/predict?t1=Brazil&t2=Brazil")
assert r.status_code == 400
print("predict validation OK")

# competition flow
r = c.post("/api/predictions", json={"player": "TestUser",
                                     "match_id": "G|Mexico|South Africa",
                                     "s1": 2, "s2": 1})
assert r.status_code == 200, r.get_json()
r = c.get("/api/predictions")
d = r.get_json()
assert any(row["name"] == "TestUser" for row in d["leaderboard"])
assert d["open_matches"]
print("POST+GET /api/predictions OK")

# result entry + scoring + analysis
r = c.post("/api/results", json={"match_id": "G|Mexico|South Africa",
                                 "s1": 2, "s2": 1})
assert r.status_code == 200, r.get_json()
d = c.get("/api/predictions").get_json()
row = next(x for x in d["leaderboard"] if x["name"] == "TestUser")
assert row["points"] == 5 and row["exact"] == 1, row
print("scoring OK: exact score earned 5 points")

r = c.post("/api/predictions", json={"player": "X",
                                     "match_id": "G|Mexico|South Africa",
                                     "s1": 1, "s2": 0})
assert r.status_code == 409
print("predictions locked after result OK")

a = c.get("/api/analysis").get_json()
assert a["total"] == 1 and a["history"][0]["actual"] == [2, 1]
print("GET /api/analysis OK: accuracy", a["accuracy"], "%")

today = c.get("/api/matches/today?date=2026-06-11").get_json()
mex = next(m for m in today["matches"] if m["team1"]["name"] == "Mexico")
assert mex["result"] == {"s1": 2, "s2": 1, "pens": None}
assert "model_correct" in mex
print("result visible on today endpoint OK (model_correct:",
      mex["model_correct"], ")")

# cleanup test artefacts
from app import data_store
import os
data_store.delete_result("G|Mexico|South Africa")
os.remove("predictions.json")
print("ALL API TESTS PASSED")
