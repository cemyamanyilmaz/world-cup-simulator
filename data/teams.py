"""
FIFA World Cup 2026 — real qualified teams, final-draw groups and ratings.

Sources (researched 10 June 2026):
  * Groups / final draw: FIFA.com Final Draw results & Wikipedia "2026 FIFA
    World Cup draw" (draw held 5 Dec 2025, playoff slots filled March 2026).
  * Ratings: FIFA/Coca-Cola Men's World Ranking points as of 10 June 2026
    (football-ranking.com live mirror of the official ranking; last official
    release 1 Apr 2026 — top three Argentina/Spain/France are within ~6 pts
    of each other, sources differ on the exact order at the very top).

Each entry: (name, code, confederation, group, fifa_rank, fifa_points, is_host)
"""

TEAMS_DATA = [
    # ---- Group A -------------------------------------------------------
    ("Mexico",                 "MEX", "CONCACAF", "A", 14, 1687.48, True),
    ("South Africa",           "RSA", "CAF",      "A", 60, 1429.00, False),
    ("Korea Republic",         "KOR", "AFC",      "A", 25, 1591.63, False),
    ("Czechia",                "CZE", "UEFA",     "A", 39, 1505.74, False),
    # ---- Group B -------------------------------------------------------
    ("Canada",                 "CAN", "CONCACAF", "B", 30, 1559.48, True),
    ("Switzerland",            "SUI", "UEFA",     "B", 19, 1650.07, False),
    ("Qatar",                  "QAT", "AFC",      "B", 55, 1454.00, False),
    ("Bosnia and Herzegovina", "BIH", "UEFA",     "B", 65, 1385.00, False),
    # ---- Group C -------------------------------------------------------
    ("Brazil",                 "BRA", "CONMEBOL", "C",  6, 1765.86, False),
    ("Morocco",                "MAR", "CAF",      "C",  7, 1755.44, False),
    ("Haiti",                  "HAI", "CONCACAF", "C", 83, 1291.00, False),
    ("Scotland",               "SCO", "UEFA",     "C", 42, 1503.34, False),
    # ---- Group D -------------------------------------------------------
    ("United States",          "USA", "CONCACAF", "D", 17, 1671.24, True),
    ("Paraguay",               "PAR", "CONMEBOL", "D", 40, 1505.35, False),
    ("Australia",              "AUS", "AFC",      "D", 27, 1579.34, False),
    ("Türkiye",                "TUR", "UEFA",     "D", 22, 1605.73, False),
    # ---- Group E -------------------------------------------------------
    ("Germany",                "GER", "UEFA",     "E", 10, 1735.77, False),
    ("Curaçao",                "CUW", "CONCACAF", "E", 82, 1294.00, False),
    ("Côte d'Ivoire",          "CIV", "CAF",      "E", 33, 1540.87, False),
    ("Ecuador",                "ECU", "CONMEBOL", "E", 23, 1598.51, False),
    # ---- Group F -------------------------------------------------------
    ("Netherlands",            "NED", "UEFA",     "F",  8, 1753.57, False),
    ("Japan",                  "JPN", "AFC",      "F", 18, 1661.58, False),
    ("Tunisia",                "TUN", "CAF",      "F", 44, 1483.00, False),
    ("Sweden",                 "SWE", "UEFA",     "F", 38, 1509.79, False),
    # ---- Group G -------------------------------------------------------
    ("Belgium",                "BEL", "UEFA",     "G",  9, 1742.23, False),
    ("Egypt",                  "EGY", "CAF",      "G", 29, 1562.37, False),
    ("Iran",                   "IRN", "AFC",      "G", 21, 1619.58, False),
    ("New Zealand",            "NZL", "OFC",      "G", 85, 1281.00, False),
    # ---- Group H -------------------------------------------------------
    ("Spain",                  "ESP", "UEFA",     "H",  2, 1873.87, False),
    ("Cabo Verde",             "CPV", "CAF",      "H", 69, 1366.00, False),
    ("Saudi Arabia",           "KSA", "AFC",      "H", 61, 1421.00, False),
    ("Uruguay",                "URU", "CONMEBOL", "H", 16, 1673.07, False),
    # ---- Group I -------------------------------------------------------
    ("France",                 "FRA", "UEFA",     "I",  3, 1870.69, False),
    ("Senegal",                "SEN", "CAF",      "I", 15, 1685.24, False),
    ("Norway",                 "NOR", "UEFA",     "I", 31, 1557.44, False),
    ("Iraq",                   "IRQ", "AFC",      "I", 57, 1447.00, False),
    # ---- Group J -------------------------------------------------------
    ("Argentina",              "ARG", "CONMEBOL", "J",  1, 1876.11, False),
    ("Algeria",                "ALG", "CAF",      "J", 28, 1571.04, False),
    ("Austria",                "AUT", "UEFA",     "J", 24, 1597.41, False),
    ("Jordan",                 "JOR", "AFC",      "J", 63, 1391.00, False),
    # ---- Group K -------------------------------------------------------
    ("Portugal",               "POR", "UEFA",     "K",  5, 1766.17, False),
    ("Uzbekistan",             "UZB", "AFC",      "K", 50, 1465.00, False),
    ("Colombia",               "COL", "CONMEBOL", "K", 13, 1698.35, False),
    ("DR Congo",               "COD", "CAF",      "K", 46, 1478.00, False),
    # ---- Group L -------------------------------------------------------
    ("England",                "ENG", "UEFA",     "L",  4, 1827.05, False),
    ("Croatia",                "CRO", "UEFA",     "L", 11, 1714.87, False),
    ("Ghana",                  "GHA", "CAF",      "L", 74, 1346.00, False),
    ("Panama",                 "PAN", "CONCACAF", "L", 34, 1539.15, False),
]

GROUP_LETTERS = "ABCDEFGHIJKL"
