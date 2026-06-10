"""Live group standings and knockout-bracket resolution.

Bracket tokens come straight from the official schedule feed:
  '1A'/'2B'  group winner / runner-up
  '3A/B/C/D/F'  best third-placed team drawn from the listed groups
  'W73'/'L101'  winner / loser of a numbered match

A slot is CONFIRMED when real results fully decide it, otherwise it is
PROJECTED from the prediction model (and rendered greyed-out in the UI).
Projections are never chained more than one round beyond real results,
so the app never names a predicted champion.
"""

from app.predictor import GROUPS, TEAMS


# ---------------------------------------------------------------------------
# group standings from real results
# ---------------------------------------------------------------------------
def group_results_table(letter, schedule, results):
    """Returns ({team: [pts, gd, gf]}, list of played match entries)."""
    stats = {t: [0, 0, 0] for t in GROUPS[letter]}
    played = []
    for e in schedule:
        if e["stage"] != "Group" or e["group"] != letter:
            continue
        res = results.get(e["id"])
        if res is None:
            continue
        s1, s2 = res["s1"], res["s2"]
        for team, gf, ga in ((e["team1"], s1, s2), (e["team2"], s2, s1)):
            stats[team][0] += 3 if gf > ga else (1 if gf == ga else 0)
            stats[team][1] += gf - ga
            stats[team][2] += gf
        played.append((e, res))
    return stats, played


def full_group_rows(letter, schedule, results):
    """Standings rows with full W/D/L detail, FIFA tiebreakers applied."""
    rows = {t: {"team": t, "P": 0, "W": 0, "D": 0, "L": 0,
                "GF": 0, "GA": 0} for t in GROUPS[letter]}
    played = []
    for e in schedule:
        if e["stage"] != "Group" or e["group"] != letter:
            continue
        res = results.get(e["id"])
        if res is None:
            continue
        played.append((e, res))
        s1, s2 = res["s1"], res["s2"]
        for team, gf, ga in ((e["team1"], s1, s2), (e["team2"], s2, s1)):
            r = rows[team]
            r["P"] += 1
            r["GF"] += gf
            r["GA"] += ga
            r["W"] += gf > ga
            r["D"] += gf == ga
            r["L"] += gf < ga
    for r in rows.values():
        r["GD"] = r["GF"] - r["GA"]
        r["Pts"] = 3 * r["W"] + r["D"]
    ordered = _fifa_sort(list(rows.values()), played)
    remaining = [e for e in schedule
                 if e["stage"] == "Group" and e["group"] == letter
                 and e["id"] not in results]
    return ordered, played, remaining


def _fifa_sort(rows, played):
    rows.sort(key=lambda r: (r["Pts"], r["GD"], r["GF"], r["team"]),
              reverse=True)
    # head-to-head among teams level on Pts/GD/GF
    out, i = [], 0
    while i < len(rows):
        j = i + 1
        key = (rows[i]["Pts"], rows[i]["GD"], rows[i]["GF"])
        while j < len(rows) and (rows[j]["Pts"], rows[j]["GD"],
                                 rows[j]["GF"]) == key:
            j += 1
        block = rows[i:j]
        if len(block) > 1:
            names = {r["team"] for r in block}
            h2h = {n: [0, 0, 0] for n in names}
            for e, res in played:
                if e["team1"] in names and e["team2"] in names:
                    s1, s2 = res["s1"], res["s2"]
                    for team, gf, ga in ((e["team1"], s1, s2),
                                         (e["team2"], s2, s1)):
                        h2h[team][0] += 3 if gf > ga else (1 if gf == ga else 0)
                        h2h[team][1] += gf - ga
                        h2h[team][2] += gf
            block.sort(key=lambda r: tuple(h2h[r["team"]]), reverse=True)
        out.extend(block)
        i = j
    return out


def group_complete(letter, schedule, results):
    return all(e["id"] in results for e in schedule
               if e["stage"] == "Group" and e["group"] == letter)


# ---------------------------------------------------------------------------
# third-place qualification
# ---------------------------------------------------------------------------
def rank_thirds(third_rows):
    """third_rows: {group_letter: standings row}. Best first."""
    return sorted(third_rows.items(),
                  key=lambda kv: (kv[1]["Pts"], kv[1]["GD"], kv[1]["GF"],
                                  kv[0]),
                  reverse=True)


def assign_third_slots(qualified_groups, slot_tokens):
    """qualified_groups: set of 8 group letters; slot_tokens: {num: 'ABCDF'}.
    Backtracking → {num: group letter}."""
    slots = sorted(slot_tokens,
                   key=lambda s: sum(g in qualified_groups
                                     for g in slot_tokens[s]))
    assignment = {}

    def solve(idx, used):
        if idx == len(slots):
            return True
        slot = slots[idx]
        for g in slot_tokens[slot]:
            if g in qualified_groups and g not in used:
                assignment[slot] = g
                if solve(idx + 1, used | {g}):
                    return True
                del assignment[slot]
        return False

    solve(0, frozenset())
    return assignment


# ---------------------------------------------------------------------------
# bracket resolution
# ---------------------------------------------------------------------------
class Slot:
    def __init__(self, team=None, confirmed=False, prob=None, hint=""):
        self.team = team
        self.confirmed = confirmed
        self.prob = prob          # probability the projected team fills the slot
        self.hint = hint          # shown when team is unknown

    @property
    def label(self):
        return self.team or self.hint or "TBD"


def resolve_bracket(schedule, results, predictor, group_projections):
    """Returns ordered knockout entries with resolved Slot objects.

    group_projections: {letter: (pos_probs, projected_order, projected_stats)}
    """
    knockout = [e for e in schedule if e["stage"] != "Group"]
    knockout.sort(key=lambda e: e["num"])
    by_num = {e["num"]: e for e in knockout}

    all_complete = all(group_complete(g, schedule, results) for g in GROUPS)

    # ---- third-place slots --------------------------------------------
    slot_tokens = {}
    for e in knockout:
        for token in (e["team1"], e["team2"]):
            if token.startswith("3") and "/" in token:
                slot_tokens[e["num"]] = token[1:].replace("/", "")
    third_rows = {}
    for g in GROUPS:
        if all_complete:
            rows, _, _ = full_group_rows(g, schedule, results)
            third_rows[g] = rows[2]
        else:
            _, order, stats = group_projections[g]
            t = order[2]
            third_rows[g] = {"team": t, "Pts": stats[t][0],
                             "GD": stats[t][1], "GF": stats[t][2]}
    ranked = rank_thirds(third_rows)
    qualified = {g for g, _ in ranked[:8]}
    third_assignment = assign_third_slots(qualified, slot_tokens)

    resolved = {}

    def resolve_token(token, num):
        # winner / loser of an earlier match
        if token[0] in "WL" and token[1:].isdigit():
            ref = int(token[1:])
            res = results.get(f"K{ref}")
            if res is not None:
                ref_slots = resolved.get(ref)
                t1 = res.get("teams", [None, None])
                names = (t1 if t1 and t1[0] else
                         [ref_slots[0].team, ref_slots[1].team]
                         if ref_slots else [None, None])
                if names[0] and names[1]:
                    winner = _winner(names, res)
                    pick = winner if token[0] == "W" else \
                        (names[1] if winner == names[0] else names[0])
                    return Slot(pick, confirmed=True)
            # project one round ahead only: both feeder slots confirmed
            ref_slots = resolved.get(ref)
            if (token[0] == "W" and ref_slots
                    and ref_slots[0].confirmed and ref_slots[1].confirmed):
                p = predictor.predict(ref_slots[0].team, ref_slots[1].team,
                                      knockout=True,
                                      match_date=by_num[ref]["date"])
                fav = ref_slots[0].team if p["adv1"] >= p["adv2"] \
                    else ref_slots[1].team
                return Slot(fav, confirmed=False,
                            prob=max(p["adv1"], p["adv2"]),
                            hint=f"Winner M{ref}")
            return Slot(hint=f"{'Winner' if token[0] == 'W' else 'Loser'} M{ref}")

        # third-place slot
        if token.startswith("3"):
            g = third_assignment.get(num)
            if g is None:
                return Slot(hint=f"3rd of {token[1:]}")
            row = third_rows[g]
            if all_complete:
                return Slot(row["team"], confirmed=True)
            probs = group_projections[g][0][row["team"]]
            return Slot(row["team"], confirmed=False, prob=probs[2],
                        hint=f"3rd of {token[1:]}")

        # group winner / runner-up
        pos, letter = int(token[0]) - 1, token[1]
        if group_complete(letter, schedule, results):
            rows, _, _ = full_group_rows(letter, schedule, results)
            return Slot(rows[pos]["team"], confirmed=True)
        pos_probs, order, _ = group_projections[letter]
        team = order[pos]
        return Slot(team, confirmed=False, prob=pos_probs[team][pos],
                    hint=token)

    entries = []
    for e in knockout:
        s1 = resolve_token(e["team1"], e["num"])
        s2 = resolve_token(e["team2"], e["num"])
        resolved[e["num"]] = (s1, s2)
        entries.append({"entry": e, "slot1": s1, "slot2": s2,
                        "result": results.get(f"K{e['num']}")})
    return entries


def _winner(names, res):
    if res["s1"] != res["s2"]:
        return names[0] if res["s1"] > res["s2"] else names[1]
    if res.get("pens"):
        return names[0] if res["pens"][0] > res["pens"][1] else names[1]
    return None
