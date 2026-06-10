"""Match simulation engine.

Model
-----
* Win expectancy follows the formula FIFA's own ranking uses
  (Elo-style with a 600 divisor):  We = 1 / (1 + 10 ** (-dr / 600)).
* Goals are sampled from independent Poisson processes.  The combined
  expected-goals budget is anchored to the real World Cup average
  (2.69 goals/game at Qatar 2022) and split between the sides according
  to the win expectancy, so upsets fall out of the model naturally with
  realistic frequency rather than being bolted on.
* Mismatched games get a slightly bigger goal budget (lopsided group
  games historically produce more goals than tight knockout ties).
* Knockout games that finish level go to 30 minutes of extra time
  (one third of the regulation scoring rate) and then to a penalty
  shootout (~74% historical conversion rate, tiny edge to the stronger
  side, sudden death after five kicks each).
"""

import math


class Match:
    BASE_GOALS = 2.55          # expected total goals in an even game
    MISMATCH_GOALS = 1.5       # extra goal budget at maximum mismatch
    SHARE_TEMPER = 0.85        # how strongly We tilts the goal split
    PEN_BASE = 0.74            # historical WC shootout conversion rate

    def __init__(self, home, away, rng, knockout=False, label=""):
        self.home = home
        self.away = away
        self.rng = rng
        self.knockout = knockout
        self.label = label

        self.home_goals = 0
        self.away_goals = 0
        self.extra_time = False
        self.penalties = None      # (home_pens, away_pens) when used
        self.home_cards = (0, 0)   # (yellows, reds)
        self.away_cards = (0, 0)
        self.winner = None
        self.loser = None

    # ------------------------------------------------------------------
    @property
    def win_expectancy(self):
        dr = self.home.strength - self.away.strength
        return 1.0 / (1.0 + 10 ** (-dr / 600.0))

    def _poisson(self, lam):
        threshold = math.exp(-lam)
        k, p = 0, 1.0
        while p > threshold:
            k += 1
            p *= self.rng.random()
        return min(k - 1, 8)

    def _cards(self):
        yellows = min(self._poisson(1.7), 5)
        reds = 1 if self.rng.random() < 0.04 else 0
        return yellows, reds

    # ------------------------------------------------------------------
    def play(self):
        we = self.win_expectancy
        total = self.BASE_GOALS + self.MISMATCH_GOALS * abs(we - 0.5)
        share = 0.5 + (we - 0.5) * self.SHARE_TEMPER
        lam_home = max(total * share, 0.18)
        lam_away = max(total * (1.0 - share), 0.18)

        self.home_goals = self._poisson(lam_home)
        self.away_goals = self._poisson(lam_away)
        self.home_cards = self._cards()
        self.away_cards = self._cards()

        if self.knockout and self.home_goals == self.away_goals:
            self.extra_time = True
            self.home_goals += self._poisson(lam_home / 3.0)
            self.away_goals += self._poisson(lam_away / 3.0)
            if self.home_goals == self.away_goals:
                self._shootout(we)

        self._settle()
        return self

    # ------------------------------------------------------------------
    def _shootout(self, we):
        p_home = self.PEN_BASE + 0.05 * (we - 0.5)
        p_away = self.PEN_BASE - 0.05 * (we - 0.5)
        home_p = away_p = 0
        for kick in range(5):
            if self.rng.random() < p_home:
                home_p += 1
            remaining = 4 - kick
            if home_p > away_p + remaining + 1:   # away can't catch up
                break
            if self.rng.random() < p_away:
                away_p += 1
            if away_p > home_p + remaining or home_p > away_p + remaining:
                break
        while home_p == away_p:                   # sudden death
            home_p += 1 if self.rng.random() < p_home else 0
            away_p += 1 if self.rng.random() < p_away else 0
        self.penalties = (home_p, away_p)

    def _settle(self):
        if self.penalties:
            home_won = self.penalties[0] > self.penalties[1]
        elif self.home_goals != self.away_goals:
            home_won = self.home_goals > self.away_goals
        else:
            self.winner = self.loser = None       # group-stage draw
            return
        self.winner = self.home if home_won else self.away
        self.loser = self.away if home_won else self.home

    # ------------------------------------------------------------------
    def score_string(self):
        s = f"{self.home_goals}-{self.away_goals}"
        if self.penalties:
            s += f" ({self.penalties[0]}-{self.penalties[1]} pens)"
        elif self.extra_time:
            s += " (a.e.t.)"
        return s

    def __str__(self):
        return f"{self.home.name} {self.score_string()} {self.away.name}"
