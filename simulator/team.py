"""Team model for the 2026 World Cup simulator."""


class Team:
    """A national team, rated by its real FIFA ranking points.

    The effective ``strength`` used by the match model combines:
      * fifa_points  — official FIFA/Coca-Cola ranking points (June 2026)
      * form         — pre-tournament form noise, drawn once per simulation
      * momentum     — earned (or lost) match by match during the tournament
      * host bonus   — USA / Mexico / Canada play every game at home; the
                       World Football Elo home advantage is ~100 pts, FIFA's
                       own model uses none, so a conservative +45 is applied
    """

    HOST_BONUS = 45.0

    def __init__(self, name, code, confederation, group, fifa_rank,
                 fifa_points, is_host=False):
        self.name = name
        self.code = code
        self.confederation = confederation
        self.group = group
        self.fifa_rank = fifa_rank
        self.fifa_points = fifa_points
        self.is_host = is_host

        self.form = 0.0
        self.momentum = 0.0
        self.reset_stats()

    # ------------------------------------------------------------------
    # rating
    # ------------------------------------------------------------------
    @property
    def strength(self):
        bonus = self.HOST_BONUS if self.is_host else 0.0
        return self.fifa_points + self.form + self.momentum + bonus

    def add_momentum(self, delta):
        self.momentum = max(-25.0, min(40.0, self.momentum + delta))

    # ------------------------------------------------------------------
    # group-stage statistics
    # ------------------------------------------------------------------
    def reset_stats(self):
        self.played = 0
        self.won = 0
        self.drawn = 0
        self.lost = 0
        self.goals_for = 0
        self.goals_against = 0
        self.fair_play = 0          # negative deduction points (FIFA scale)

    @property
    def points(self):
        return 3 * self.won + self.drawn

    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against

    def record_result(self, scored, conceded, yellows=0, reds=0):
        self.played += 1
        self.goals_for += scored
        self.goals_against += conceded
        if scored > conceded:
            self.won += 1
        elif scored < conceded:
            self.lost += 1
        else:
            self.drawn += 1
        self.fair_play -= yellows + 4 * reds

    # ------------------------------------------------------------------
    def __str__(self):
        return f"{self.name} ({self.code}, FIFA #{self.fifa_rank})"

    def __repr__(self):
        return f"Team({self.code})"
