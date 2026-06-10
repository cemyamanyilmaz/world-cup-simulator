"""Group stage logic — 2026 format: 12 groups of 4, single round-robin.

The top two of each group advance directly; third-placed teams enter a
12-team comparison from which the best eight also advance (handled by
the Tournament).  Ranking inside a group follows the official FIFA 2026
regulations, article 13:

  1. points  2. goal difference  3. goals scored
  4. head-to-head points among tied teams
  5. head-to-head goal difference  6. head-to-head goals scored
  7. fair-play points (yellow -1, red -4)
  8. drawing of lots
"""

from .match import Match


class Group:
    # real matchday pairings: 1v2 & 3v4, 1v3 & 4v2, 4v1 & 2v3
    FIXTURE_ORDER = [(0, 1), (2, 3), (0, 2), (3, 1), (3, 0), (1, 2)]

    def __init__(self, letter, teams, rng):
        self.letter = letter
        self.teams = list(teams)
        self.rng = rng
        self.matches = []

    # ------------------------------------------------------------------
    def play(self, on_result=None):
        for i, j in self.FIXTURE_ORDER:
            match = Match(self.teams[i], self.teams[j], self.rng,
                          knockout=False, label=f"Group {self.letter}").play()
            hy, hr = match.home_cards
            ay, ar = match.away_cards
            match.home.record_result(match.home_goals, match.away_goals, hy, hr)
            match.away.record_result(match.away_goals, match.home_goals, ay, ar)
            self.matches.append(match)
            if on_result:
                on_result(match)
        return self.standings()

    # ------------------------------------------------------------------
    def standings(self):
        ordered = sorted(self.teams,
                         key=lambda t: (t.points, t.goal_difference,
                                        t.goals_for),
                         reverse=True)
        return self._break_ties(ordered)

    def _break_ties(self, ordered):
        result = []
        i = 0
        while i < len(ordered):
            j = i + 1
            key = (ordered[i].points, ordered[i].goal_difference,
                   ordered[i].goals_for)
            while j < len(ordered) and (ordered[j].points,
                                        ordered[j].goal_difference,
                                        ordered[j].goals_for) == key:
                j += 1
            tied = ordered[i:j]
            if len(tied) > 1:
                tied = self._head_to_head_sort(tied)
            result.extend(tied)
            i = j
        return result

    def _head_to_head_sort(self, tied):
        names = {t.name for t in tied}
        h2h = {t.name: {"pts": 0, "gd": 0, "gf": 0} for t in tied}
        for m in self.matches:
            if m.home.name in names and m.away.name in names:
                for team, gf, ga in ((m.home, m.home_goals, m.away_goals),
                                     (m.away, m.away_goals, m.home_goals)):
                    rec = h2h[team.name]
                    rec["gd"] += gf - ga
                    rec["gf"] += gf
                    rec["pts"] += 3 if gf > ga else (1 if gf == ga else 0)
        return sorted(tied,
                      key=lambda t: (h2h[t.name]["pts"], h2h[t.name]["gd"],
                                     h2h[t.name]["gf"], t.fair_play,
                                     self.rng.random()),
                      reverse=True)

    def __str__(self):
        return f"Group {self.letter}: " + ", ".join(t.name for t in self.teams)
