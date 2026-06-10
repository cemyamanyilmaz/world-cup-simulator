"""Pre-tournament form and player availability — researched 10 June 2026.

Sources:
  * FIFA.com "Every nation's pre-FIFA World Cup 2026 warm-up matches"
  * football365.com warm-up friendly results round-up
  * ESPN "2026 World Cup injuries tracker", Goal.com missing-stars list

`adj` is a rating adjustment in FIFA-ranking-point units applied on top of
the team's official June 2026 ranking points.  Teams not listed had no
reliable recent-form reporting found and start neutral (0).
"""

# ---------------------------------------------------------------------------
# Recent form (final warm-up window before the tournament)
# ---------------------------------------------------------------------------
PRE_FORM = {
    "Argentina": {
        "last5": "WWWWW", "adj": +28,
        "note": "Won all six friendlies since qualifying, conceding once",
    },
    "Spain": {
        "last5": "WWWWD", "adj": +12,
        "note": "Unbeaten in nine, but held by Iraq in their last friendly",
    },
    "France": {
        "last5": "WWWWL", "adj": -14,
        "note": "Shock warm-up defeat to Côte d'Ivoire (had beaten Brazil "
                "and Colombia earlier in 2026)",
    },
    "Côte d'Ivoire": {
        "last5": "WWDWW", "adj": +18,
        "note": "Beat France in their final June warm-up",
    },
    "Belgium": {
        "last5": "WWWWW", "adj": +14,
        "note": "Crushed Tunisia 5-0 in final warm-up",
    },
    "Tunisia": {
        "last5": "WDWLL", "adj": -12,
        "note": "0-5 warm-up loss to Belgium",
    },
    "Germany": {
        "last5": "WWWDW", "adj": +12,
        "note": "Beat the USA 2-1 at Soldier Field",
    },
    "United States": {
        "last5": "WWDWL", "adj": -6,
        "note": "1-2 home warm-up loss to Germany",
    },
    "England": {
        "last5": "WWWDW", "adj": +8,
        "note": "Beat New Zealand 1-0 (Kane) in final warm-up",
    },
    "New Zealand": {
        "last5": "WDWDL", "adj": -4,
        "note": "Narrow 0-1 warm-up loss to England",
    },
    "Scotland": {
        "last5": "WWDWW", "adj": +12,
        "note": "4-0 statement win over Bolivia in New Jersey",
    },
    "Brazil": {
        "last5": "WLWDW", "adj": +4,
        "note": "Beat Egypt 2-1 in final warm-up; lost to France in April",
    },
    "Egypt": {
        "last5": "WWDWL", "adj": -5,
        "note": "2-1 warm-up loss to Brazil",
    },
    "Colombia": {
        "last5": "WWWLD", "adj": -4,
        "note": "Beaten by France in a 2026 friendly",
    },
}

# ---------------------------------------------------------------------------
# Injuries / suspensions / notable absences (squads of 10 June 2026)
# ---------------------------------------------------------------------------
INJURIES = {
    "Brazil": [
        ("Rodrygo", "torn ACL and meniscus — out for 2026"),
        ("Estêvão", "hamstring — left off preliminary squad"),
    ],
    "Spain": [
        ("Fermín López", "fractured metatarsal — ruled out"),
    ],
    "Germany": [
        ("Lennart Karl", "thigh injury — replaced by Assan Ouédraogo"),
    ],
    "Netherlands": [
        ("Jurriën Timber", "groin — withdrew from squad"),
    ],
    "Austria": [
        ("Christoph Baumgartner", "torn thigh muscle — out"),
    ],
    "England": [
        ("Cole Palmer", "missing from squad (injury)"),
    ],
}

# rating penalty for the squad weakening caused by the absences above
INJURY_ADJ = {
    "Brazil": -12,
    "Spain": -5,
    "Germany": -4,
    "Netherlands": -8,
    "Austria": -10,
    "England": -4,
}
