"""Full 2026 FIFA World Cup tournament — official 104-match structure.

Round of 32 pairings and the third-place slot constraints follow the
official FIFA match schedule (matches 73-88), as published on FIFA.com
and Wikipedia's "2026 FIFA World Cup knockout stage":

  M73 2A v 2B    M74 1E v 3rd   M75 1F v 2C    M76 1C v 2F
  M77 1I v 3rd   M78 2E v 2I    M79 1A v 3rd   M80 1L v 3rd
  M81 1D v 3rd   M82 1G v 3rd   M83 2K v 2L    M84 1H v 2J
  M85 1B v 3rd   M86 1J v 2H    M87 1K v 3rd   M88 2D v 2G

Eight best third-placed teams fill the 3rd slots subject to each slot's
allowed-group list; the assignment is solved by backtracking so every
qualified third always lands in a legal slot.
"""

from .group import Group
from .match import Match

# winner-of / runner-up-of pairings for the round of 32
R32_PAIRINGS = {
    73: ("2A", "2B"), 74: ("1E", "3?"), 75: ("1F", "2C"), 76: ("1C", "2F"),
    77: ("1I", "3?"), 78: ("2E", "2I"), 79: ("1A", "3?"), 80: ("1L", "3?"),
    81: ("1D", "3?"), 82: ("1G", "3?"), 83: ("2K", "2L"), 84: ("1H", "2J"),
    85: ("1B", "3?"), 86: ("1J", "2H"), 87: ("1K", "3?"), 88: ("2D", "2G"),
}

# allowed source groups for each third-place slot
THIRD_SLOTS = {
    74: "ABCDF", 77: "CDFGH", 79: "CEFHI", 80: "EHIJK",
    81: "BEFIJ", 82: "AEHIJ", 85: "EFGIJ", 87: "DEIJL",
}

R16_FEED = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
            93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87)}
QF_FEED = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
SF_FEED = {101: (97, 98), 102: (99, 100)}
FINAL_FEED = {104: (101, 102)}
FEED_MAP = {**R16_FEED, **QF_FEED, **SF_FEED, **FINAL_FEED}

ROUNDS = [
    ("Round of 32", list(range(73, 89))),
    ("Round of 16", list(range(89, 97))),
    ("Quarter-finals", list(range(97, 101))),
    ("Semi-finals", [101, 102]),
    ("Third-place play-off", [103]),
    ("Final", [104]),
]


class Tournament:
    def __init__(self, teams, rng):
        self.rng = rng
        self.teams = list(teams)
        for team in self.teams:                       # pre-tournament form
            team.form = max(-55.0, min(55.0, rng.gauss(0.0, 22.0)))

        self.groups = {}
        by_group = {}
        for team in self.teams:
            by_group.setdefault(team.group, []).append(team)
        for letter in sorted(by_group):
            self.groups[letter] = Group(letter, by_group[letter], rng)

        self.group_tables = {}        # letter -> ordered team list
        self.third_ranking = []       # all 12 thirds, best first
        self.third_slot_map = {}      # match no -> third-placed Team
        self.matches = {}             # match no -> Match
        self.champion = None
        self.runner_up = None
        self.third_place = None

    # ------------------------------------------------------------------
    def run(self):
        self._play_groups()
        self._rank_thirds()
        self._play_knockouts()
        return self.champion

    # ------------------------------------------------------------------
    def _play_groups(self):
        for letter, group in self.groups.items():
            table = group.play()
            self.group_tables[letter] = table
            for pos, team in enumerate(table):
                team.add_momentum((6, 3, -2, -6)[pos] if pos < 4 else 0)

    def _rank_thirds(self):
        thirds = [self.group_tables[g][2] for g in sorted(self.groups)]
        self.third_ranking = sorted(
            thirds,
            key=lambda t: (t.points, t.goal_difference, t.goals_for,
                           t.fair_play, self.rng.random()),
            reverse=True)
        qualified = self.third_ranking[:8]
        self.third_slot_map = self._assign_thirds(qualified)

    def _assign_thirds(self, qualified):
        """Backtracking assignment of the 8 best thirds to legal slots."""
        by_group = {t.group: t for t in qualified}
        slots = sorted(THIRD_SLOTS,
                       key=lambda s: sum(g in by_group for g in THIRD_SLOTS[s]))
        assignment = {}

        def solve(idx, used):
            if idx == len(slots):
                return True
            slot = slots[idx]
            for g in THIRD_SLOTS[slot]:
                if g in by_group and g not in used:
                    assignment[slot] = by_group[g]
                    if solve(idx + 1, used | {g}):
                        return True
                    del assignment[slot]
            return False

        if not solve(0, frozenset()):
            # cannot happen with FIFA's slot design, but never crash
            remaining = list(qualified)
            for slot in THIRD_SLOTS:
                assignment[slot] = remaining.pop(0)
        return assignment

    # ------------------------------------------------------------------
    def _resolve_entry(self, match_no, token):
        if token == "3?":
            return self.third_slot_map[match_no]
        pos, letter = int(token[0]) - 1, token[1]
        return self.group_tables[letter][pos]

    def _play_knockouts(self):
        for round_name, match_numbers in ROUNDS:
            for no in match_numbers:
                if no == 103:   # third-place play-off: semi-final losers
                    home = self.matches[101].loser
                    away = self.matches[102].loser
                elif no in FEED_MAP:
                    feed_a, feed_b = FEED_MAP[no]
                    home = self.matches[feed_a].winner
                    away = self.matches[feed_b].winner
                else:
                    a, b = R32_PAIRINGS[no]
                    home = self._resolve_entry(no, a)
                    away = self._resolve_entry(no, b)
                match = Match(home, away, self.rng, knockout=True,
                              label=f"{round_name} · Match {no}").play()
                match.winner.add_momentum(7)
                match.loser.add_momentum(-5)
                self.matches[no] = match

        final = self.matches[104]
        self.champion, self.runner_up = final.winner, final.loser
        self.third_place = self.matches[103].winner
