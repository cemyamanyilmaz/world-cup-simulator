"""Match-by-match prediction engine.

Rating = official FIFA points (June 2026)
       + host-nation bonus (+45 for USA/Mexico/Canada)
       + researched pre-tournament form adjustment
       + injury/absence penalty
       + in-tournament momentum earned from REAL results
       + rest-day differential at prediction time

Win/draw/loss probabilities are computed analytically from two Poisson
goal processes (no sampling noise in the headline numbers).  Group
projections use Monte Carlo over the remaining fixtures only.
"""

import math
import random
from datetime import date as date_cls

from data.teams import TEAMS_DATA
from data.form import PRE_FORM, INJURIES, INJURY_ADJ

BASE_GOALS = 2.55
MISMATCH_GOALS = 1.5
SHARE_TEMPER = 0.85
HOST_BONUS = 45.0
MAX_GOALS = 8


class TeamMeta:
    def __init__(self, row):
        (self.name, self.code, self.confederation, self.group,
         self.fifa_rank, self.fifa_points, self.is_host) = row


TEAMS = {row[0]: TeamMeta(row) for row in TEAMS_DATA}
GROUPS = {}
for _t in TEAMS.values():
    GROUPS.setdefault(_t.group, []).append(_t.name)


def _pmf_vector(lam):
    pmf = [math.exp(-lam)]
    for k in range(1, MAX_GOALS + 1):
        pmf.append(pmf[-1] * lam / k)
    pmf[-1] += max(0.0, 1.0 - sum(pmf))      # fold the tail into the last bin
    return pmf


def _parse_date(s):
    y, m, d = (int(x) for x in s.split("-"))
    return date_cls(y, m, d)


class Predictor:
    def __init__(self, schedule, results):
        self.schedule = schedule
        self.results = results.get("results", {})
        self._timeline = None

    # ------------------------------------------------------------------
    # ratings
    # ------------------------------------------------------------------
    def base_rating(self, name):
        meta = TEAMS[name]
        r = meta.fifa_points
        if meta.is_host:
            r += HOST_BONUS
        r += PRE_FORM.get(name, {}).get("adj", 0)
        r += INJURY_ADJ.get(name, 0)
        return r

    def momentum_timeline(self):
        """Per team: list of (date, label, delta, cumulative momentum)."""
        if self._timeline is not None:
            return self._timeline
        timeline = {name: [] for name in TEAMS}
        for entry in self.schedule:                      # already date-sorted
            res = self.results.get(entry["id"])
            if res is None:
                continue
            t1, t2 = self._real_teams(entry, res)
            if t1 not in TEAMS or t2 not in TEAMS:
                continue
            r1, r2 = self.base_rating(t1), self.base_rating(t2)
            we = 1.0 / (1.0 + 10 ** (-(r1 - r2) / 600.0))
            s1, s2 = res["s1"], res["s2"]
            if s1 > s2:
                ap1, ap2 = 3.0, 0.0
            elif s1 < s2:
                ap1, ap2 = 0.0, 3.0
            elif res.get("pens"):
                won1 = res["pens"][0] > res["pens"][1]
                ap1, ap2 = (2.0, 1.0) if won1 else (1.0, 2.0)
            else:
                ap1 = ap2 = 1.0
            ep1 = 3.0 * we * 0.8 + 0.2          # smooth expected points
            ep2 = 3.0 * (1 - we) * 0.8 + 0.2
            surprise = max(-4.0, min(4.0, (s1 - s2) - (we - 0.5) * 2.5))
            d1 = max(-15.0, min(15.0, 4.0 * (ap1 - ep1) + 1.2 * surprise))
            d2 = max(-15.0, min(15.0, 4.0 * (ap2 - ep2) - 1.2 * surprise))
            label = f"{t1} {s1}-{s2} {t2}"
            for team, delta in ((t1, d1), (t2, d2)):
                prev = timeline[team][-1][3] if timeline[team] else 0.0
                cum = max(-45.0, min(45.0, prev + delta))
                timeline[team].append((entry["date"], label, delta, cum))
        self._timeline = timeline
        return timeline

    def _real_teams(self, entry, res):
        if res.get("teams"):
            return res["teams"][0], res["teams"][1]
        return entry["team1"], entry["team2"]

    def momentum(self, name, as_of=None):
        events = self.momentum_timeline().get(name, [])
        if as_of:
            events = [e for e in events if e[0] < as_of]
        return events[-1][3] if events else 0.0

    def rating(self, name, as_of=None):
        return self.base_rating(name) + self.momentum(name, as_of)

    # ------------------------------------------------------------------
    # rest days
    # ------------------------------------------------------------------
    def last_played(self, name, before_date):
        last = None
        for entry in self.schedule:
            if entry["date"] >= before_date:
                break
            res = self.results.get(entry["id"])
            if res is None:
                continue
            t1, t2 = self._real_teams(entry, res)
            if name in (t1, t2):
                last = entry["date"]
        return last

    def rest_adjustment(self, t1, t2, match_date):
        if not match_date:
            return 0.0, None
        d1, d2 = self.last_played(t1, match_date), self.last_played(t2, match_date)
        if not d1 or not d2:
            return 0.0, None
        rest1 = (_parse_date(match_date) - _parse_date(d1)).days
        rest2 = (_parse_date(match_date) - _parse_date(d2)).days
        diff = rest1 - rest2
        if diff == 0:
            return 0.0, (rest1, rest2)
        return max(-12.0, min(12.0, 3.0 * diff)), (rest1, rest2)

    # ------------------------------------------------------------------
    # core prediction
    # ------------------------------------------------------------------
    def lambdas(self, r1, r2):
        we = 1.0 / (1.0 + 10 ** (-(r1 - r2) / 600.0))
        total = BASE_GOALS + MISMATCH_GOALS * abs(we - 0.5)
        share = 0.5 + (we - 0.5) * SHARE_TEMPER
        return max(total * share, 0.18), max(total * (1 - share), 0.18), we

    def predict(self, t1, t2, knockout=False, match_date=None):
        rest_adj, rest_days = self.rest_adjustment(t1, t2, match_date)
        r1 = self.rating(t1, match_date) + rest_adj
        r2 = self.rating(t2, match_date)
        lam1, lam2, we = self.lambdas(r1, r2)

        p1v, p2v = _pmf_vector(lam1), _pmf_vector(lam2)
        p_win = p_draw = p_loss = 0.0
        best, best_p = (0, 0), -1.0
        for i in range(MAX_GOALS + 1):
            for j in range(MAX_GOALS + 1):
                p = p1v[i] * p2v[j]
                if p > best_p:
                    best, best_p = (i, j), p
                if i > j:
                    p_win += p
                elif i == j:
                    p_draw += p
                else:
                    p_loss += p

        out = {
            "team1": t1, "team2": t2,
            "p1": p_win, "px": p_draw, "p2": p_loss,
            "xg1": lam1, "xg2": lam2,
            "score": best, "score_prob": best_p,
            "rating1": r1, "rating2": r2,
            "rest": rest_days,
            "confidence": 100.0 * max(p_win, p_draw, p_loss),
        }
        if knockout:
            edge = 0.5 + (we - 0.5) * 0.7        # ET + pens tilt to the stronger side
            out["adv1"] = p_win + p_draw * edge
            out["adv2"] = p_loss + p_draw * (1 - edge)
        out["factors"] = self._factors(t1, t2, rest_days, match_date)
        return out

    def _factors(self, t1, t2, rest_days, as_of):
        facts = []
        m1, m2 = TEAMS[t1], TEAMS[t2]
        facts.append(f"FIFA ranking: {t1} #{m1.fifa_rank} ({m1.fifa_points:.0f} pts) "
                     f"vs {t2} #{m2.fifa_rank} ({m2.fifa_points:.0f} pts)")
        for name in (t1, t2):
            pf = PRE_FORM.get(name)
            if pf:
                facts.append(f"Form — {name}: {pf['last5']} · {pf['note']}")
            mom = self.momentum(name, as_of)
            if abs(mom) >= 3:
                arrow = "📈" if mom > 0 else "📉"
                facts.append(f"{arrow} Tournament momentum — {name}: {mom:+.0f}")
            for player, status in INJURIES.get(name, []):
                facts.append(f"🚑 {name}: {player} — {status}")
            if TEAMS[name].is_host:
                facts.append(f"🏟️ {name} play on home soil (host nation)")
        if rest_days and rest_days[0] != rest_days[1]:
            facts.append(f"Rest: {t1} {rest_days[0]} days vs {t2} {rest_days[1]} days")
        return facts

    # ------------------------------------------------------------------
    # tournament meetings so far (head-to-head inside this World Cup)
    # ------------------------------------------------------------------
    def tournament_meetings(self, t1, t2):
        out = []
        for entry in self.schedule:
            res = self.results.get(entry["id"])
            if res is None:
                continue
            a, b = self._real_teams(entry, res)
            if {a, b} == {t1, t2}:
                out.append((entry, res, a, b))
        return out

    # ------------------------------------------------------------------
    # group Monte Carlo
    # ------------------------------------------------------------------
    def simulate_group(self, letter, n=1500, seed=0):
        """Returns (pos_probs, projected_order, projected_stats).

        pos_probs[team][k] = probability of finishing in position k (0-based);
        projected stats are mean Pts/GD/GF over the simulations.
        """
        from app.bracket_logic import group_results_table   # local import, no cycle

        teams = GROUPS[letter]
        rng = random.Random(seed)
        base, played = group_results_table(letter, self.schedule, self.results)
        remaining = [e for e in self.schedule
                     if e["stage"] == "Group" and e["group"] == letter
                     and e["id"] not in self.results]
        ratings = {t: self.rating(t) for t in teams}
        lams = {}
        for e in remaining:
            lam1, lam2, _ = self.lambdas(ratings[e["team1"]], ratings[e["team2"]])
            lams[e["id"]] = (lam1, lam2)

        pos_counts = {t: [0] * 4 for t in teams}
        sums = {t: [0.0, 0.0, 0.0] for t in teams}       # pts, gd, gf
        for _ in range(n):
            stats = {t: list(base[t]) for t in teams}    # [pts, gd, gf]
            for e in remaining:
                lam1, lam2 = lams[e["id"]]
                g1, g2 = _sample_poisson(lam1, rng), _sample_poisson(lam2, rng)
                _apply(stats[e["team1"]], g1, g2)
                _apply(stats[e["team2"]], g2, g1)
            order = sorted(teams, key=lambda t: (stats[t][0], stats[t][1],
                                                 stats[t][2], rng.random()),
                           reverse=True)
            for pos, t in enumerate(order):
                pos_counts[t][pos] += 1
            for t in teams:
                for k in range(3):
                    sums[t][k] += stats[t][k]

        pos_probs = {t: [c / n for c in pos_counts[t]] for t in teams}
        projected_stats = {t: [s / n for s in sums[t]] for t in teams}
        projected_order = _greedy_order(teams, pos_probs)
        return pos_probs, projected_order, projected_stats


def _apply(stats, gf, ga):
    stats[0] += 3 if gf > ga else (1 if gf == ga else 0)
    stats[1] += gf - ga
    stats[2] += gf


def _sample_poisson(lam, rng):
    threshold = math.exp(-lam)
    k, p = 0, 1.0
    while p > threshold:
        k += 1
        p *= rng.random()
    return min(k - 1, MAX_GOALS)


def _greedy_order(teams, pos_probs):
    """Most-likely finishing order: pick the most probable team per slot."""
    order, used = [], set()
    for pos in range(4):
        pick = max((t for t in teams if t not in used),
                   key=lambda t: pos_probs[t][pos])
        order.append(pick)
        used.add(pick)
    return order
