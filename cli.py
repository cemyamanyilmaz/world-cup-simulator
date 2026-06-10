"""FIFA World Cup 2026 — full tournament simulation.

Usage:  python main.py [random_seed]
"""

import random
import sys

from data.teams import TEAMS_DATA
from simulator.team import Team
from simulator.tournament import (Tournament, R32_PAIRINGS, FEED_MAP,
                                  ROUNDS)

LINE = "═" * 78
THIN = "─" * 78
LABEL_W = 13


# ----------------------------------------------------------------------
# presentation helpers
# ----------------------------------------------------------------------
def banner():
    print(LINE)
    print("║{:^76}║".format("FIFA WORLD CUP 2026"))
    print("║{:^76}║".format("United States · Mexico · Canada"))
    print("║{:^76}║".format("48 teams · 12 groups · 104 matches"))
    print(LINE)


def print_group(group, table):
    inner = 76

    def row(content):
        print(f"│{content:<{inner}}│")

    print(f"\n┌─ GROUP {group.letter} " + "─" * (inner - 10) + "┐")
    for m in group.matches:
        score = f"{m.home_goals}-{m.away_goals}"
        row(f"  {m.home.name:>28}  {score:^5}  {m.away.name:<28}")
    print("├" + "─" * inner + "┤")
    row(f" {'#':<3}{'Team':<28}{'P':>3}{'W':>3}{'D':>3}{'L':>3}"
        f"{'GF':>4}{'GA':>4}{'GD':>4}{'Pts':>5}")
    for pos, t in enumerate(table, 1):
        marker = "▲" if pos <= 2 else ("•" if pos == 3 else " ")
        row(f"{marker}{pos:<3}{t.name:<28}{t.played:>3}{t.won:>3}"
            f"{t.drawn:>3}{t.lost:>3}{t.goals_for:>4}{t.goals_against:>4}"
            f"{t.goal_difference:>4}{t.points:>5}")
    print("└" + "─" * inner + "┘")


def print_thirds(tournament):
    print(f"\n{LINE}")
    print("{:^78}".format("RANKING OF THIRD-PLACED TEAMS  (best 8 advance)"))
    print(THIN)
    print(f"  {'#':<3}{'Grp':<5}{'Team':<28}{'Pts':>4}{'GD':>5}{'GF':>4}"
          f"   {'Status'}")
    for pos, t in enumerate(tournament.third_ranking, 1):
        status = "ADVANCES ▲" if pos <= 8 else "eliminated"
        print(f"  {pos:<3}{t.group:<5}{t.name:<28}{t.points:>4}"
              f"{t.goal_difference:>5}{t.goals_for:>4}   {status}")


def print_knockout_rounds(tournament):
    for round_name, numbers in ROUNDS:
        print(f"\n{LINE}")
        print("{:^78}".format(round_name.upper()))
        print(THIN)
        for no in numbers:
            m = tournament.matches[no]
            print(f"  M{no:<4} {m.home.name:>24}  {m.score_string():^16}  "
                  f"{m.away.name:<24}")


# ----------------------------------------------------------------------
# bracket rendering
# ----------------------------------------------------------------------
def _match_label(match):
    s = f"{match.winner.code} {match.home_goals}-{match.away_goals}"
    if match.penalties:
        s += "p"
    return s


def _build_tree(tournament, match_no):
    match = tournament.matches[match_no]
    node = {"label": _match_label(match)}
    if match_no in FEED_MAP:
        a, b = FEED_MAP[match_no]
        node["children"] = [_build_tree(tournament, a),
                            _build_tree(tournament, b)]
    else:   # round-of-32 match: leaves are the entrants
        node["children"] = [{"label": match.home.code},
                            {"label": match.away.code}]
    return node


def _render_node(node):
    """Returns (lines, spine_row) for a bracket sub-tree."""
    label = node["label"].ljust(LABEL_W)
    children = node.get("children")
    if not children:
        return [label], 0

    top_lines, top_spine = _render_node(children[0])
    bot_lines, bot_spine = _render_node(children[1])
    width = max(len(line) for line in top_lines + bot_lines)
    top_lines = [line.ljust(width) for line in top_lines]
    bot_lines = [line.ljust(width) for line in bot_lines]

    lines = top_lines + [" " * width] + bot_lines
    spine_top = top_spine
    spine_bot = len(top_lines) + 1 + bot_spine
    mid = (spine_top + spine_bot) // 2

    out = []
    pad = " " * (LABEL_W + 4)
    for i, line in enumerate(lines):
        if i == spine_top or i == spine_bot:
            trimmed = line.rstrip()
            dashes = "─" * (width - len(trimmed))
            corner = "┐" if i == spine_top else "┘"
            out.append(trimmed + dashes + "─" + corner + " " * (LABEL_W + 2))
        elif i == mid:
            out.append(line + " ├─ " + label)
        elif spine_top < i < spine_bot:
            out.append(line + " │" + " " * (LABEL_W + 2))
        else:
            out.append(line + pad)
    return out, mid


def print_bracket(tournament):
    print(f"\n{LINE}")
    print("{:^78}".format("KNOCKOUT BRACKET"))
    print(THIN)
    tree = _build_tree(tournament, 104)
    lines, spine = _render_node(tree)
    lines[spine] = (lines[spine].rstrip()
                    + f" ══▶ 🏆 {tournament.champion.name.upper()}")
    for line in lines:
        print(" " + line.rstrip())


def champion_banner(tournament):
    champ = tournament.champion
    final = tournament.matches[104]
    print(f"\n\n{'★' * 78}")
    print("{:^78}".format(""))
    print("{:^78}".format("🏆  CHAMPIONS OF THE WORLD  🏆"))
    print("{:^78}".format(""))
    print("{:^78}".format(champ.name.upper()))
    print("{:^78}".format(""))
    print("{:^78}".format(f"{final.home.name} {final.score_string()} "
                          f"{final.away.name}"))
    print("{:^78}".format("MetLife Stadium, New York/New Jersey · 19 July 2026"))
    print("{:^78}".format(""))
    print("{:^78}".format(f"Runners-up: {tournament.runner_up.name}    "
                          f"Third place: {tournament.third_place.name}"))
    print("{:^78}".format(""))
    print("★" * 78)


# ----------------------------------------------------------------------
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else random.randrange(10 ** 6)
    rng = random.Random(seed)
    print(f"(simulation seed: {seed} — rerun with `python main.py {seed}` "
          f"to reproduce)\n")

    teams = [Team(*row) for row in TEAMS_DATA]
    tournament = Tournament(teams, rng)
    tournament.run()

    banner()
    print("\n{:^78}".format("G R O U P   S T A G E"))
    for letter, group in tournament.groups.items():
        print_group(group, tournament.group_tables[letter])

    print_thirds(tournament)
    print_knockout_rounds(tournament)
    print_bracket(tournament)
    champion_banner(tournament)


if __name__ == "__main__":
    main()
