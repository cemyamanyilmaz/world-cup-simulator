# ⚽ World Cup 2026 — Live Match-by-Match Predictor

An interactive Streamlit web app for the 2026 FIFA World Cup (USA · Mexico ·
Canada, 11 June – 19 July 2026). It does **not** simulate the whole
tournament up front — it predicts match by match, and every real result you
feed it updates team momentum and reshapes all future predictions.

## Quick start

```bash
pip install -r requirements.txt
streamlit run main.py
```

The app opens at http://localhost:8501 and works fully offline out of the
box (the official schedule is bundled). Press **🔄 Fetch latest real
results** in the sidebar whenever you're online to pull real scores.

## Pages

| Page | What it does |
|------|--------------|
| 📅 **Today's Matches** | Fixtures for any day with win/draw/loss percentages, predicted score, key factors — and actual-vs-predicted once a result is in |
| 🔮 **Match Predictor** | Pick any two teams: probabilities, expected score, in-tournament head-to-head, form, injuries — plus "who wins Group X?" tables |
| 📊 **Group Stage** | Live standings for all 12 groups (FIFA tiebreakers), remaining fixtures, Monte-Carlo projected final tables |
| 🏆 **Bracket** | Round of 32 → Final. Green = confirmed by real results, grey/italic = projection with its probability. Never predicts the champion |
| 📈 **Form Tracker** | Effective rating table, warm-up form, injury list, and a momentum chart that grows match by match |

## Data system

- **Schedule & live results** — [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json):
  public-domain, no API key, all 104 matches with dates/kick-off times/venues.
  A snapshot is bundled at `data/schedule.json`; the sidebar refresh button
  re-downloads it and merges any real scores into `results.json`.
  (Commercial alternatives researched: football-data.org free tier has
  delayed scores; API-Football free tier is capped at 100 req/day — the
  openfootball feed beat both for this use case.)
- **Manual entry** — if you're offline or the feed lags, enter any score by
  hand in the sidebar (knockout fixtures unlock once real results decide the
  participants). Manual entries always win over feed data.
- **Cache** — everything lives in two local JSON files; group projections
  are memoised per results-state, so the app stays snappy.

## Prediction model

- Base = official **FIFA ranking points** (10 June 2026) per team
- **+45** host bonus (USA/Mexico/Canada play at home)
- **Pre-tournament form** adjustments researched from the June 2026 warm-ups
  (e.g. Argentina's six straight wins, France's shock loss to Côte d'Ivoire)
- **Injuries/absences** researched from squad news (Rodrygo, Timber,
  Baumgartner, Fermín López, Cole Palmer, …) — see `data/form.py`
- **Momentum** earned from real results: beating expectation raises a team's
  rating for future matches, capped at ±45 points
- **Rest days** differential between the two sides at kick-off
- Win/draw/loss probabilities are computed analytically from two Poisson
  goal processes calibrated to the real World Cup scoring average; knockout
  predictions include extra-time/shootout advancement probability
- The bracket never chains projections more than one round past real
  results — the app deliberately **never names a predicted champion**

## Project layout

```
world-cup-simulator/
├── main.py              ← Streamlit app (streamlit run main.py)
├── cli.py               ← original terminal simulator (python cli.py)
├── requirements.txt
├── results.json         ← local result store (created/updated at runtime)
├── data/
│   ├── teams.py         ← 48 real teams, groups, FIFA points (June 2026)
│   ├── form.py          ← researched warm-up form + injury news
│   └── schedule.json    ← bundled openfootball schedule snapshot
├── app/
│   ├── data_store.py    ← schedule/results storage + live feed refresh
│   ├── predictor.py     ← rating, momentum, Poisson model, group Monte Carlo
│   └── bracket_logic.py ← standings, tiebreakers, bracket resolution
└── simulator/           ← original CLI simulation engine (still works)
```

## Tests

```bash
python test_logic.py   # schedule integrity, predictions, full-tournament walkthrough
python test_ui.py      # renders all five pages headlessly via streamlit AppTest
```

## Data sources (researched 10 June 2026)

- Schedule/feed: [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json)
- FIFA ranking points: [FIFA World Ranking](https://inside.fifa.com/fifa-world-ranking/men) via [football-ranking.com](https://football-ranking.com/fifa-world-rankings)
- Format & bracket: [FIFA.com](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/groups-how-teams-qualify-tie-breakers), [Wikipedia](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup)
- Warm-up form: [FIFA warm-up round-up](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/pre-tournament-warm-up-results-fixtures-scorers), [football365](https://www.football365.com/news/world-cup-2026-warm-up-friendly-fixtures-results-kick-off-times-what-tv-channel)
- Injuries: [ESPN injuries tracker](https://www.espn.com/soccer/story/_/id/48572979/2026-fifa-world-cup-injuries-tracker-which-stars-miss-latest-info), [Goal.com](https://www.goal.com/en-us/lists/biggest-stars-miss-2026-world-cup-injury-suspension-selection/bltd6ff2d56ebf99a62)

Predictions are probabilistic entertainment, not betting advice. 🍿
