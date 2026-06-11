"""⚽ FIFA World Cup 2026 — live match-by-match predictor.

Run with:  streamlit run main.py
"""

import json
from datetime import date

import pandas as pd
import streamlit as st

from app import data_store
from app.bracket_logic import (full_group_rows, group_complete, rank_thirds,
                               resolve_bracket)
from app.predictor import GROUPS, TEAMS, Predictor
from data.form import INJURIES, PRE_FORM

st.set_page_config(page_title="World Cup 2026 Predictor", page_icon="⚽",
                   layout="wide", initial_sidebar_state="expanded")

FLAGS = {
    "Mexico": "🇲🇽", "South Africa": "🇿🇦", "Korea Republic": "🇰🇷",
    "Czechia": "🇨🇿", "Canada": "🇨🇦", "Switzerland": "🇨🇭", "Qatar": "🇶🇦",
    "Bosnia and Herzegovina": "🇧🇦", "Brazil": "🇧🇷", "Morocco": "🇲🇦",
    "Haiti": "🇭🇹", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "United States": "🇺🇸",
    "Paraguay": "🇵🇾", "Australia": "🇦🇺", "Türkiye": "🇹🇷", "Germany": "🇩🇪",
    "Curaçao": "🇨🇼", "Côte d'Ivoire": "🇨🇮", "Ecuador": "🇪🇨",
    "Netherlands": "🇳🇱", "Japan": "🇯🇵", "Tunisia": "🇹🇳", "Sweden": "🇸🇪",
    "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Iran": "🇮🇷", "New Zealand": "🇳🇿",
    "Spain": "🇪🇸", "Cabo Verde": "🇨🇻", "Saudi Arabia": "🇸🇦",
    "Uruguay": "🇺🇾", "France": "🇫🇷", "Senegal": "🇸🇳", "Norway": "🇳🇴",
    "Iraq": "🇮🇶", "Argentina": "🇦🇷", "Algeria": "🇩🇿", "Austria": "🇦🇹",
    "Jordan": "🇯🇴", "Portugal": "🇵🇹", "Uzbekistan": "🇺🇿",
    "Colombia": "🇨🇴", "DR Congo": "🇨🇩", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Croatia": "🇭🇷", "Ghana": "🇬🇭", "Panama": "🇵🇦",
}


def flag(name):
    return FLAGS.get(name, "⚽")


st.markdown("""
<style>
/* ⚽ Athletic campaign theme — off-white field, navy ink, electric red */
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap');

:root {
  --wc-bg: #F5F5F0; --wc-navy: #0A1628; --wc-red: #E8001D;
  --wc-gold: #FFB800; --wc-green: #00A651;
  --wc-display: 'Bebas Neue', 'Arial Narrow', sans-serif;
  --wc-shadow: 8px 8px 0 rgba(10,22,40,.08);
}
html, body, [data-testid="stAppViewContainer"] {background: var(--wc-bg);}
body, p, span, div {font-family: 'DM Sans', 'Segoe UI', sans-serif;}
[data-testid="stHeader"] {background: rgba(0,0,0,0);}
[data-testid="stSidebar"] {background: #FFFFFF;
                           border-right: 3px solid var(--wc-navy);}
h1, h2, h3 {font-family: var(--wc-display) !important;
            font-weight: 400 !important; letter-spacing: 1.5px;
            color: var(--wc-navy) !important; text-transform: uppercase;}
[data-testid="stSidebar"] h1 {color: var(--wc-red) !important;}

/* hero banner */
.wc-hero {position: relative; background: var(--wc-navy); overflow: hidden;
          padding: 26px 30px 38px; margin-bottom: 22px;
          clip-path: polygon(0 0, 100% 0, 100% 86%, 0 100%);}
.wc-hero::before {content: ""; position: absolute; top: -50px; right: -70px;
                  width: 210px; height: 380px; background: var(--wc-red);
                  transform: rotate(18deg);}
.wc-hero::after {content: ""; position: absolute; top: -50px; right: 84px;
                 width: 34px; height: 380px; background: var(--wc-gold);
                 transform: rotate(18deg);}
.wc-title {position: relative; z-index: 2; font-family: var(--wc-display);
           font-size: clamp(34px, 6vw, 58px); line-height: .95;
           letter-spacing: 2px; color: #fff;}
.wc-title .ol {color: transparent; -webkit-text-stroke: 2px #fff;}
.wc-title .rd {color: var(--wc-red); -webkit-text-stroke: 0;}
.wc-sub {position: relative; z-index: 2; font-family: var(--wc-display);
         color: var(--wc-gold); font-size: 16px; letter-spacing: 2px;
         margin-top: 8px;}

/* match cards */
.match-card {background: #FFFFFF; border: 1px solid rgba(10,22,40,.12);
             border-top: 6px solid var(--wc-red); border-radius: 2px;
             padding: 16px 18px; margin-bottom: 14px;
             box-shadow: var(--wc-shadow);
             transition: transform .15s, box-shadow .15s;}
.match-card:hover {transform: translate(-2px,-2px);
                   box-shadow: 11px 11px 0 rgba(10,22,40,.12);}
.teams-line {display: flex; justify-content: space-between;
             align-items: center; gap: 8px; flex-wrap: wrap;
             font-family: var(--wc-display); font-size: 24px;
             letter-spacing: 1px; color: var(--wc-navy);}
.vs {color: var(--wc-red); font-family: var(--wc-display); font-size: 30px;
     transform: skew(-10deg); display: inline-block;
     text-shadow: 2px 2px 0 rgba(10,22,40,.12);}
.kickoff {color: var(--wc-red); font-size: 12.5px; font-weight: 700;
          margin-bottom: 8px; letter-spacing: 1.4px;
          text-transform: uppercase;}
.kick {color: #6E7681; font-size: 13px;}

.prob-bar {display: flex; height: 26px; border-radius: 0; overflow: hidden;
           font-size: 13px; font-weight: 700; margin: 8px 0;
           border: 1.5px solid rgba(10,22,40,.2);}
.prob-bar div {display:flex; align-items:center; justify-content:center;
               white-space:nowrap; overflow:hidden;}

/* buttons: red slab, hard navy shadow, sharp corners */
.stButton > button {background: var(--wc-red) !important;
                    color: #fff !important;
                    font-family: var(--wc-display) !important;
                    font-size: 18px !important; letter-spacing: 2px;
                    border: none !important; border-radius: 0 !important;
                    box-shadow: 4px 4px 0 var(--wc-navy);
                    transition: transform .12s, box-shadow .12s;}
.stButton > button:hover {transform: translate(-2px,-2px);
                          box-shadow: 6px 6px 0 var(--wc-navy);
                          background: #C40019 !important;}
.stButton > button:active {transform: translate(2px,2px);
                           box-shadow: 1px 1px 0 var(--wc-navy);}

[data-testid="stMetric"] {background: #FFFFFF; border-radius: 2px;
                          border: 2px solid var(--wc-navy);
                          padding: 10px 14px; box-shadow: var(--wc-shadow);
                          transition: transform .15s;}
[data-testid="stMetric"]:hover {transform: translate(-2px,-2px);}
[data-testid="stMetricValue"] {color: var(--wc-red);
                               font-family: var(--wc-display);}

/* group cards with watermark letter */
.group-card {position: relative; overflow: hidden; background: #FFFFFF;
             border: 1px solid rgba(10,22,40,.12); border-radius: 2px;
             border-top: 6px solid var(--wc-navy);
             padding: 14px 16px; margin-bottom: 10px;
             box-shadow: var(--wc-shadow);}
.group-card::before {content: attr(data-letter); position: absolute;
                     right: -8px; top: -36px;
                     font-family: var(--wc-display); font-size: 150px;
                     color: rgba(10,22,40,.05); pointer-events: none;}
.group-name {font-family: var(--wc-display); font-size: 26px;
             color: var(--wc-navy); margin-bottom: 8px;
             letter-spacing: 2px;}
.wc-table {width: 100%; border-collapse: collapse; font-size: 14px;
           color: var(--wc-navy); position: relative;}
.wc-table th {background: var(--wc-navy); color: #fff;
              font-family: var(--wc-display); font-weight: 400;
              letter-spacing: 1.4px; padding: 5px 9px; text-align: left;}
.wc-table td {padding: 6px 9px; font-weight: 500;
              border-bottom: 1px solid rgba(10,22,40,.08);}
.wc-table tr.adv  {background: #E7F6EE; border-left: 5px solid var(--wc-green);}
.wc-table tr.wild {background: #FFF6E0; border-left: 5px solid var(--wc-gold);}
.wc-table tr.out  {background: #FBEAEA; border-left: 5px solid var(--wc-red);
                   opacity: .75;}

/* bracket slots */
.bracket-slot {border-radius: 0; padding: 4px 9px; margin: 3px 0;
               font-size: 13px; background: #FFFFFF;}
.confirmed {border-left: 4px solid var(--wc-navy); color: var(--wc-navy);
            font-weight: 700; border-top: 1px solid rgba(10,22,40,.12);
            border-bottom: 1px solid rgba(10,22,40,.12);
            border-right: 1px solid rgba(10,22,40,.12);}
.projected {border-left: 4px solid #B9BDC4; color: #8A8F98;
            font-style: italic; background: #EFEEE8;}
.played {border-left: 4px solid var(--wc-gold); background: #FFF6E0;
         color: var(--wc-navy); font-weight: 700;
         font-family: var(--wc-display); letter-spacing: 1px;}

/* tabs: athletic underline */
.stTabs [data-baseweb="tab"] {font-family: var(--wc-display);
                              font-size: 17px; letter-spacing: 1.4px;
                              color: var(--wc-navy);}
.stTabs [aria-selected="true"] {color: var(--wc-red) !important;}

.wc-footer {text-align: center; color: var(--wc-navy); font-weight: 700;
            font-family: var(--wc-display); letter-spacing: 2px;
            font-size: 16px; margin-top: 40px; padding: 16px 0 4px 0;
            border-top: 4px solid var(--wc-navy);}
.wc-footer em {color: var(--wc-red); font-style: normal;}

@media (max-width: 640px) {
  .wc-title {font-size: 32px;}
  .teams-line {font-size: 19px;}
  .vs {font-size: 22px;}
  .group-name {font-size: 21px;}
}
</style>
""", unsafe_allow_html=True)


KICKOFF_DAY = date(2026, 6, 11)
FINAL_DAY = date(2026, 7, 19)


def festival_header():
    today = date.today()
    if today < KICKOFF_DAY:
        n = (KICKOFF_DAY - today).days
        sub = f"KICK-OFF IN {n} DAY{'S' if n != 1 else ''}"
    elif today <= FINAL_DAY:
        sub = f"TOURNAMENT DAY {(today - KICKOFF_DAY).days + 1} OF 39"
    else:
        sub = "TOURNAMENT COMPLETE"
    st.markdown(
        f'<div class="wc-hero">'
        f'<div class="wc-title"><span class="ol">FIFA WORLD CUP</span> '
        f'20<span class="rd">26</span></div>'
        f'<div class="wc-sub">{sub} · {today:%d %B %Y} · '
        f'USA 🇺🇸 MEXICO 🇲🇽 CANADA 🇨🇦 · 48 TEAMS · ONE TROPHY</div>'
        f'</div>',
        unsafe_allow_html=True)


def festival_footer():
    st.markdown('<div class="wc-footer">EVERY MATCH A <em>BATTLE</em>. '
                'EVERY PREDICTION A <em>STATEMENT</em>. — powered by ⚽ data '
                '&amp; 🤖 AI predictions</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# data loading (cached on the contents of results.json)
# ---------------------------------------------------------------------------
def get_state():
    schedule = data_store.load_schedule()
    results = data_store.load_results()
    predictor = Predictor(schedule, results)
    key = json.dumps(results.get("results", {}), sort_keys=True)
    projections = _projections(key)
    return schedule, results, predictor, projections


@st.cache_data(show_spinner="Simulating group outcomes…")
def _projections(results_key):
    schedule = data_store.load_schedule()
    results = data_store.load_results()
    pred = Predictor(schedule, results)
    return {g: pred.simulate_group(g, n=1500) for g in GROUPS}


def prob_bar(p1, px, p2, name1, name2):
    # brand colours: navy for team 1, warm grey for the draw, red for team 2
    return f"""
<div class="prob-bar">
  <div style="width:{p1 * 100:.1f}%;background:#0A1628;color:#fff;">{name1} {p1 * 100:.0f}%</div>
  <div style="width:{px * 100:.1f}%;background:#C9C4B8;color:#0A1628;">draw {px * 100:.0f}%</div>
  <div style="width:{p2 * 100:.1f}%;background:#E8001D;color:#fff;">{name2} {p2 * 100:.0f}%</div>
</div>"""


def show_prediction(pred, knockout=False):
    t1, t2 = pred["team1"], pred["team2"]
    st.markdown(prob_bar(pred["p1"], pred["px"], pred["p2"],
                         f"{flag(t1)} {TEAMS[t1].code}",
                         f"{TEAMS[t2].code} {flag(t2)}"),
                unsafe_allow_html=True)
    cols = st.columns(3)
    cols[0].metric("Predicted score", f"{pred['score'][0]} - {pred['score'][1]}")
    cols[1].metric("Expected goals", f"{pred['xg1']:.2f} : {pred['xg2']:.2f}")
    cols[2].metric("Confidence", f"{pred['confidence']:.0f}%")
    if knockout and "adv1" in pred:
        st.caption(f"Advance probability (incl. extra time & penalties): "
                   f"{t1} **{pred['adv1'] * 100:.0f}%** · "
                   f"{t2} **{pred['adv2'] * 100:.0f}%**")
    with st.expander("🔑 Key factors"):
        for f in pred["factors"]:
            st.markdown(f"- {f}")


# ---------------------------------------------------------------------------
# PAGE 1 — Today's matches
# ---------------------------------------------------------------------------
def page_today(schedule, results, predictor):
    st.header("📅 TODAY'S MATCHES 🔥")
    dates = sorted({e["date"] for e in schedule})
    today = date.today().isoformat()
    default = today if today in dates else min((d for d in dates if d >= today),
                                               default=dates[-1])
    picked = st.date_input("Match day", value=date.fromisoformat(default),
                           min_value=date.fromisoformat(dates[0]),
                           max_value=date.fromisoformat(dates[-1])).isoformat()
    todays = [e for e in schedule if e["date"] == picked]
    if not todays:
        st.info("No matches scheduled on this day — pick another date. "
                "The group stage runs 11–27 June, knockouts 28 June – 19 July.")
        return
    correct_now = []
    for e in todays:
        res = results["results"].get(e["id"])
        t1, t2 = e["team1"], e["team2"]
        if res and res.get("teams"):
            t1, t2 = res["teams"]
        known = t1 in TEAMS and t2 in TEAMS
        left = f"{flag(t1)} {t1}" if known else t1
        right = f"{t2} {flag(t2)}" if known else t2
        stage = e["group"] and f"Group {e['group']}" or e["stage"]
        with st.container():
            st.markdown(f"""<div class="match-card">
<div class="kickoff">⏰ KICK-OFF {e['time']} · 🏟️ {e['venue']} · 🎯 {stage}</div>
<div class="teams-line"><span>{left}</span><span class="vs">VS</span><span>{right}</span></div>
</div>""", unsafe_allow_html=True)
            if not known:
                st.caption("Teams not decided yet — check the bracket page.")
                continue
            pred = predictor.predict(t1, t2, knockout=e["stage"] != "Group",
                                     match_date=e["date"])
            if res:
                score = f"{res['s1']}-{res['s2']}"
                if res.get("pens"):
                    score += f" ({res['pens'][0]}-{res['pens'][1]} pens)"
                actual = ("1" if res["s1"] > res["s2"]
                          else "2" if res["s1"] < res["s2"] else "x")
                predicted = ("1" if pred["p1"] == max(pred["p1"], pred["px"], pred["p2"])
                             else "2" if pred["p2"] == max(pred["p1"], pred["px"], pred["p2"])
                             else "x")
                if actual == predicted:
                    hit = "✅ outcome predicted correctly 🎯"
                    correct_now.append(e["id"])
                else:
                    hit = "❌ model got the outcome wrong"
                st.success(f"**FT: {t1} {score} {t2}**  ·  model predicted "
                           f"{pred['score'][0]}-{pred['score'][1]}  ·  {hit}")
            show_prediction(pred, knockout=e["stage"] != "Group")
            st.divider()

    celebrated = st.session_state.setdefault("celebrated", set())
    fresh = [mid for mid in correct_now if mid not in celebrated]
    if fresh:
        celebrated.update(fresh)
        st.balloons()
        st.toast("🎉 The model called it! Correct prediction! ⚽🏆")


# ---------------------------------------------------------------------------
# PAGE 2 — Match predictor
# ---------------------------------------------------------------------------
def page_predictor(schedule, results, predictor, projections):
    st.header("🔮 MATCH PREDICTOR 🎯")
    names = sorted(TEAMS)
    c1, c2, c3 = st.columns([4, 4, 2])
    t1 = c1.selectbox("Team 1", names, index=names.index("Argentina"))
    t2 = c2.selectbox("Team 2", names, index=names.index("Spain"))
    knockout = c3.toggle("Knockout rules", value=False)
    if t1 == t2:
        st.warning("Pick two different teams.")
        return
    pred = predictor.predict(t1, t2, knockout=knockout,
                             match_date=date.today().isoformat())
    show_prediction(pred, knockout=knockout)

    st.subheader("Head-to-head & form")
    meetings = predictor.tournament_meetings(t1, t2)
    if meetings:
        for e, res, a, b in meetings:
            sc = f"{res['s1']}-{res['s2']}"
            if res.get("pens"):
                sc += f" ({res['pens'][0]}-{res['pens'][1]} p)"
            st.markdown(f"- {e['round']}: **{a} {sc} {b}**")
    else:
        st.caption("These sides have not met in this tournament yet "
                    "(historical head-to-head is not part of the live dataset).")
    for name in (t1, t2):
        pf = PRE_FORM.get(name)
        mom = predictor.momentum(name)
        bits = [f"momentum {mom:+.0f}"]
        if pf:
            bits.insert(0, f"warm-up form **{pf['last5']}** — {pf['note']}")
        st.markdown(f"**{flag(name)} {name}** · " + " · ".join(bits))
        for player, status in INJURIES.get(name, []):
            st.markdown(f"  - 🚑 {player} — {status}")

    st.subheader("🏅 Who wins the group?")
    letter = st.selectbox("Group", sorted(GROUPS),
                          format_func=lambda g: f"Group {g}")
    pos_probs, order, _ = projections[letter]
    df = pd.DataFrame([{"Team": f"{flag(t)} {t}",
                        "Win group": f"{pos_probs[t][0] * 100:.0f}%",
                        "Top 2": f"{(pos_probs[t][0] + pos_probs[t][1]) * 100:.0f}%",
                        "3rd": f"{pos_probs[t][2] * 100:.0f}%"}
                       for t in order])
    st.dataframe(df, hide_index=True, width="stretch")


# ---------------------------------------------------------------------------
# PAGE 3 — Group stage
# ---------------------------------------------------------------------------
def group_table_html(letter, rows):
    cls_for_pos = {1: "adv", 2: "adv", 3: "wild", 4: "out"}
    body = ""
    for pos, r in enumerate(rows, 1):
        body += (f'<tr class="{cls_for_pos[pos]}"><td>{pos}</td>'
                 f'<td>{flag(r["team"])} {r["team"]}</td>'
                 f'<td>{r["P"]}</td><td>{r["W"]}</td><td>{r["D"]}</td>'
                 f'<td>{r["L"]}</td><td>{r["GF"]}</td><td>{r["GA"]}</td>'
                 f'<td>{r["GD"]:+d}</td><td><b>{r["Pts"]}</b></td></tr>')
    return (f'<div class="group-card" data-letter="{letter}">'
            f'<div class="group-name">GROUP {letter} ⚽</div>'
            f'<table class="wc-table"><tr><th>#</th><th>Team</th><th>P</th>'
            f'<th>W</th><th>D</th><th>L</th><th>GF</th><th>GA</th>'
            f'<th>GD</th><th>Pts</th></tr>{body}</table>'
            f'<div class="kick">🟢 top 2 advance · 🟡 3rd may advance as '
            f'best-third wild card · 🔴 eliminated</div></div>')


def page_groups(schedule, results, predictor, projections):
    st.header("📊 GROUP STAGE — LIVE STANDINGS 🌍")
    done = sum(1 for e in schedule if e["stage"] == "Group"
               and e["id"] in results["results"])
    st.caption(f"{done}/72 group matches played · standings update "
               "automatically as results arrive")
    tabs = st.tabs([f"Group {g}" for g in sorted(GROUPS)])
    for tab, letter in zip(tabs, sorted(GROUPS)):
        with tab:
            rows, played, remaining = full_group_rows(letter, schedule,
                                                      results["results"])
            st.markdown(group_table_html(letter, rows),
                        unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Remaining fixtures**")
                if not remaining:
                    st.caption("Group complete ✅")
                for e in remaining:
                    st.markdown(f"- {e['date']} · {flag(e['team1'])} "
                                f"{e['team1']} vs {e['team2']} "
                                f"{flag(e['team2'])} · {e['venue']}")
            with c2:
                st.markdown("**Projected final standings**")
                pos_probs, order, stats = projections[letter]
                for pos, t in enumerate(order, 1):
                    mark = "▲" if pos <= 2 else ("•" if pos == 3 else " ")
                    p = pos_probs[t][pos - 1] * 100
                    st.markdown(f"{mark} {pos}. {flag(t)} {t} "
                                f"— {stats[t][0]:.1f} xPts ({p:.0f}%)")


# ---------------------------------------------------------------------------
# PAGE 4 — Bracket
# ---------------------------------------------------------------------------
def slot_html(slot, result_cls=""):
    cls = "confirmed" if slot.confirmed else "projected"
    if result_cls:
        cls = result_cls
    label = slot.label
    if slot.team:
        label = f"{flag(slot.team)} {slot.team}"
        if not slot.confirmed and slot.prob is not None:
            label += f" ({slot.prob * 100:.0f}%)"
    return f'<div class="bracket-slot {cls}">{label}</div>'


def page_bracket(schedule, results, predictor, projections):
    st.header("🏆 TOURNAMENT BRACKET — ROAD TO THE FINAL 🔥")
    st.caption("navy = confirmed by real results · grey/italic = model "
               "projection (with probability of filling that slot) · gold = "
               "score of a played match. Projections are never chained more "
               "than one round ahead — no champion prediction here, that's "
               "football's job. 🔥")
    entries = resolve_bracket(schedule, results["results"], predictor,
                              projections)
    by_stage = {}
    for item in entries:
        by_stage.setdefault(item["entry"]["stage"], []).append(item)

    stages = ["Round of 32", "Round of 16", "Quarter-finals",
              "Semi-finals", "Final"]
    cols = st.columns([3, 3, 3, 3, 3])
    for col, stage in zip(cols, stages):
        with col:
            st.markdown(f"**{stage}**")
            items = by_stage.get(stage, [])
            if stage == "Final":
                items = items + by_stage.get("Third place", [])
            for item in items:
                e, res = item["entry"], item["result"]
                html = f'<span class="kick">M{e["num"]} · {e["date"]}</span>'
                if e["stage"] == "Third place":
                    html = f'<span class="kick">🥉 {html}</span>'
                s1h = slot_html(item["slot1"])
                s2h = slot_html(item["slot2"])
                if res:
                    score = f"{res['s1']}-{res['s2']}"
                    if res.get("pens"):
                        score += f" p{res['pens'][0]}-{res['pens'][1]}"
                    html += f'<div class="bracket-slot played">FT {score}</div>'
                st.markdown(f'<div class="match-card" style="padding:8px 10px">'
                            f'{html}{s1h}{s2h}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# PAGE 5 — Form tracker
# ---------------------------------------------------------------------------
def page_form(schedule, results, predictor):
    st.header("📈 FORM TRACKER ⚡")
    timeline = predictor.momentum_timeline()
    rows = []
    for name, meta in TEAMS.items():
        pf = PRE_FORM.get(name, {})
        rows.append({
            "Team": f"{flag(name)} {name}", "Group": meta.group,
            "FIFA rank": meta.fifa_rank,
            "Warm-up form": pf.get("last5", "—"),
            "Momentum": round(predictor.momentum(name), 1),
            "Injuries": len(INJURIES.get(name, [])),
            "Effective rating": round(predictor.rating(name), 1),
        })
    df = pd.DataFrame(rows).sort_values("Effective rating", ascending=False)
    st.dataframe(df, hide_index=True, width="stretch", height=420)

    st.subheader("Team detail")
    name = st.selectbox("Team", sorted(TEAMS))
    meta = TEAMS[name]
    pf = PRE_FORM.get(name)
    st.markdown(f"### {flag(name)} {name} — FIFA #{meta.fifa_rank} "
                f"({meta.fifa_points:.0f} pts, {meta.confederation})")
    if pf:
        st.markdown(f"**Pre-tournament form:** `{pf['last5']}` — {pf['note']} "
                    f"(rating {pf['adj']:+d})")
    else:
        st.caption("No reliable pre-tournament form reporting found — "
                   "starts neutral.")
    for player, status in INJURIES.get(name, []):
        st.markdown(f"- 🚑 **{player}** — {status}")
    events = timeline.get(name, [])
    if events:
        chart = pd.DataFrame(
            {"momentum": [0.0] + [e[3] for e in events]},
            index=["start"] + [f"{e[0]}" for e in events])
        st.line_chart(chart)
        for d, label, delta, cum in events:
            st.markdown(f"- {d} · {label} → momentum {delta:+.1f} (now {cum:+.1f})")
    else:
        st.caption("No tournament matches played yet — momentum builds once "
                   "real results come in.")


# ---------------------------------------------------------------------------
# sidebar: navigation + data management
# ---------------------------------------------------------------------------
def sidebar_data_tools(schedule, results, predictor, projections):
    st.sidebar.divider()
    st.sidebar.subheader("📡 Live data")
    n_results = len(results["results"])
    st.sidebar.caption(f"{n_results} results stored · last feed refresh: "
                       f"{results.get('last_refresh') or 'never'}")
    if st.sidebar.button("🔄 Fetch latest real results", width="stretch"):
        count, err = data_store.refresh_from_feed()
        if err:
            st.sidebar.error(err + " — you can still enter results manually.")
        else:
            st.sidebar.success(f"Feed OK — {count} results in store.")
            st.cache_data.clear()
            st.rerun()

    with st.sidebar.expander("✍️ Enter a result manually"):
        options = []
        for e in schedule:                      # group fixtures: names known
            if e["stage"] == "Group" and e["id"] not in results["results"] \
                    and e["team1"] in TEAMS and e["team2"] in TEAMS:
                options.append((e, e["team1"], e["team2"]))
        # knockout fixtures become enterable once real results decide both slots
        for item in resolve_bracket(schedule, results["results"], predictor,
                                    projections):
            s1, s2 = item["slot1"], item["slot2"]
            if (item["result"] is None and s1.confirmed and s2.confirmed):
                options.append((item["entry"], s1.team, s2.team))
        if not options:
            st.caption("No decidable fixtures awaiting a result.")
        else:
            labels = [f"{e['date']} · {t1} v {t2} ({e['group'] and 'Grp ' + e['group'] or e['stage']})"
                      for e, t1, t2 in options]
            idx = st.selectbox("Match", range(len(options)),
                               format_func=lambda i: labels[i])
            e, t1, t2 = options[idx]
            c1, c2 = st.columns(2)
            s1 = c1.number_input(TEAMS[t1].code, 0, 15, 0, key="ms1")
            s2 = c2.number_input(TEAMS[t2].code, 0, 15, 0, key="ms2")
            pens = None
            if e["stage"] != "Group" and s1 == s2:
                st.caption("Knockout draw — penalty shootout result:")
                p1 = c1.number_input(f"{TEAMS[t1].code} pens", 0, 30, 5, key="mp1")
                p2 = c2.number_input(f"{TEAMS[t2].code} pens", 0, 30, 4, key="mp2")
                pens = (p1, p2)
            if st.button("💾 Save result", width="stretch"):
                if pens and pens[0] == pens[1]:
                    st.error("Shootout can't end level.")
                else:
                    teams = [t1, t2] if e["stage"] != "Group" else None
                    data_store.save_result(e["id"], s1, s2, pens, teams)
                    st.cache_data.clear()
                    st.rerun()

    with st.sidebar.expander("🗑️ Remove a stored result"):
        ids = sorted(results["results"])
        if ids:
            rid = st.selectbox("Result", ids)
            if st.button("Delete", width="stretch"):
                data_store.delete_result(rid)
                st.cache_data.clear()
                st.rerun()
        else:
            st.caption("Nothing stored yet.")


def main():
    if "welcomed" not in st.session_state:
        st.session_state.welcomed = True
        st.toast("⚽ Welcome to the World Cup 2026 Festival! 🌍🔥",
                 icon="🏆")

    st.sidebar.title("⚽ WORLD CUP 2026 🏆")
    st.sidebar.caption("Match-by-match predictor · 🇺🇸 USA · 🇲🇽 Mexico · "
                       "🇨🇦 Canada")
    page = st.sidebar.radio("Pages", [
        "📅 Today's Matches", "🔮 Match Predictor", "📊 Group Stage",
        "🏆 Bracket", "📈 Form Tracker"], label_visibility="collapsed")

    schedule, results, predictor, projections = get_state()
    festival_header()
    sidebar_data_tools(schedule, results, predictor, projections)

    if page.startswith("📅"):
        page_today(schedule, results, predictor)
    elif page.startswith("🔮"):
        page_predictor(schedule, results, predictor, projections)
    elif page.startswith("📊"):
        page_groups(schedule, results, predictor, projections)
    elif page.startswith("🏆"):
        page_bracket(schedule, results, predictor, projections)
    else:
        page_form(schedule, results, predictor)

    festival_footer()
    st.sidebar.divider()
    st.sidebar.caption(
        "Data: FIFA ranking (June 2026) · openfootball/worldcup.json "
        "(public domain, no API key) · researched warm-up form & injury news. "
        "Predictions are probabilistic — enjoy responsibly 🍿")


main()
