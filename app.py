import logging, requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, jsonify, render_template
from collections import OrderedDict

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)s: %(message)s")

app = Flask(__name__)

from datetime import timezone

startup_time = datetime.now(timezone.utc).isoformat()

@app.route("/version")
def version():
    return {"startup": startup_time}

@app.after_request
def add_header(resp):
    if resp.cache_control.max_age is not None:        # only static routes
        resp.cache_control.max_age = 0
        resp.cache_control.no_store = True
        resp.headers['Pragma'] = 'no-cache'
        resp.expires = -1
    return resp

# ─────────────────────────── helper util
def team_logo(team_json):
    if team_json["team"].get("logo"):
        return team_json["team"]["logo"]
    logos = team_json["team"].get("logos") or []
    return logos[0]["href"] if logos else ""

# ─────────────────────────── MLB parser
def parse_mlb(raw_json) -> list[dict]:
    out = []
    today = datetime.now(ZoneInfo("America/New_York")).date()
    for ev in raw_json.get("events", []):
        comp = ev["competitions"][0]
        status = comp["status"]["type"]
        state = status["state"]
        if state == "pre":
            ongoing = False
        else:
            ongoing = state != "post"

        teams = comp["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")

        away_pts = int(away.get("score", 0))
        home_pts = int(home.get("score", 0))

        out.append({
            "league":    "MLB",
            "away":      away["team"]["shortDisplayName"],
            "away_logo": team_logo(away),
            "home":      home["team"]["shortDisplayName"],
            "home_logo": team_logo(home),
            "score":     f"{away.get('score','-')} : {home.get('score','-')}",
            "status":    status["shortDetail"],
            "winner":    "away" if state=="post" and away_pts>home_pts
                        else "home" if state=="post" and home_pts>away_pts
                        else None,
            "ongoing":   ongoing
        })
    return out

# ─────────────────────────── ATP Men's Singles parser
def parse_atp(raw_json) -> list[dict]:
    out = []
    today = datetime.now(ZoneInfo("America/New_York")).date()
    for ev in raw_json.get("events", []):
        for grp in ev.get("groupings", []):
            if grp.get("grouping", {}).get("slug") != "mens-singles":
                continue
            for comp in grp.get("competitions", []):
                local = datetime.fromisoformat(
                    comp["date"].replace("Z","+00:00")
                ).astimezone(ZoneInfo("America/New_York"))
                if local.date() != today:
                    continue

                a, h = comp["competitors"]
                # build “6-4 7-5”
                sets=[]
                for i in range(len(a.get("linescores",[]))):
                    s1 = str(int(float(a["linescores"][i]["value"])))
                    s2 = str(int(float(h["linescores"][i]["value"])))
                    sets.append(f"{s1}-{s2}")
                score = " ".join(sets) if sets else "-"

                status = comp["status"]["type"]
                out.append({
                    "league":    "ATP Men's Singles",
                    "away":      a["athlete"]["shortName"],
                    "away_logo": a["athlete"].get("flag",{}).get("href",""),
                    "home":      h["athlete"]["shortName"],
                    "home_logo": h["athlete"].get("flag",{}).get("href",""),
                    "score":     score,
                    "status":    status["shortDetail"],
                    "winner":    "away" if a.get("winner") else "home" if h.get("winner") else None,
                    "ongoing":   status["state"] not in ("pre","post")
                })
    return out


def parse_wta(raw_json) -> list[dict]:
    out = []
    today = datetime.now(ZoneInfo("America/New_York")).date()
    for ev in raw_json.get("events", []):
        for grp in ev.get("groupings", []):
            if grp.get("grouping", {}).get("slug") != "womens-singles":
                continue
            for comp in grp.get("competitions", []):
                local = datetime.fromisoformat(
                    comp["date"].replace("Z","+00:00")
                ).astimezone(ZoneInfo("America/New_York"))
                if local.date() != today:
                    continue

                a, h = comp["competitors"]
                # build “6-4 7-5”
                sets=[]
                for i in range(len(a.get("linescores",[]))):
                    s1 = str(int(float(a["linescores"][i]["value"])))
                    s2 = str(int(float(h["linescores"][i]["value"])))
                    sets.append(f"{s1}-{s2}")
                score = " ".join(sets) if sets else "-"

                status = comp["status"]["type"]
                out.append({
                    "league":    "WTA Women's Singles",
                    "away":      a["athlete"]["shortName"],
                    "away_logo": a["athlete"].get("flag",{}).get("href",""),
                    "home":      h["athlete"]["shortName"],
                    "home_logo": h["athlete"].get("flag",{}).get("href",""),
                    "score":     score,
                    "status":    status["shortDetail"],
                    "winner":    "away" if a.get("winner") else "home" if h.get("winner") else None,
                    "ongoing":   status["state"] not in ("pre","post")
                })
    return out



# ─────────────────────────── NFL parser
def parse_nfl(raw_json) -> list[dict]:
    """
    ESPN NFL scoreboard canonical event list **for today's date in ET**.
    - If run between 00:00-03:59 ET it will also keep unfinished games that
    started yesterday (so the late MNF game stays visible after midnight).
    """
    tz_et = ZoneInfo("America/New_York")
    now_et = datetime.now(tz_et)
    today = now_et.date()
    yday = today - timedelta(days=1)
    keep_yday = now_et.hour < 4

    out = []
    for ev in raw_json.get("events", []):
        comp = ev["competitions"][0]

        # local start date
        local_start = datetime.fromisoformat(
            comp["date"].replace("Z", "+00:00")
        ).astimezone(tz_et).date()

        if local_start not in (today, yday):
            continue
        if local_start == yday and not keep_yday:
            continue

        status = comp["status"]["type"]
        state = status["state"] # pre | in | post

        teams = comp["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")

        away_pts = int(away.get("score", 0))
        home_pts = int(home.get("score", 0))

        out.append({
            "league":    "NFL",
            "away":      away["team"]["shortDisplayName"],
            "away_logo": away["team"]["logo"],
            "home":      home["team"]["shortDisplayName"],
            "home_logo": home["team"]["logo"],
            "score":     f"{away.get('score','-')} : {home.get('score','-')}",
            "status":    status["shortDetail"],   # e.g. "Final", "Q3 12:34"
            "winner":    "away" if state=="post" and away_pts>home_pts
                        else "home" if state=="post" and home_pts>away_pts
                        else None,
            "ongoing":   state not in ("pre", "post")
        })
    return out


def parse_nba(raw_json) -> list[dict]:
    """
    ESPN NBA scoreboard canonical event list.
    Only games that start today in ET are returned.
    If run between 00:00-03:59 ET, unfinished games that started
    yesterday are also kept so late West-coast games remain visible.
    """
    tz_et = ZoneInfo("America/New_York")
    now_et = datetime.now(tz_et)
    today = now_et.date()
    yday = today - timedelta(days=1)
    keep_yday = now_et.hour < 4  # same grace window as MLB

    out = []
    for ev in raw_json.get("events", []):
        comp = ev["competitions"][0]

        # convert start time to ET date
        local_date = datetime.fromisoformat(
            comp["date"].replace("Z", "+00:00")
        ).astimezone(tz_et).date()

        if local_date not in (today, yday):
            continue
        if local_date == yday and not keep_yday:
            continue

        status = comp["status"]["type"]
        state = status["state"] # pre | in | post

        teams = comp["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")

        away_pts = int(away.get("score", 0))
        home_pts = int(home.get("score", 0))

        out.append({
            "league":    "NBA",
            "away":      away["team"]["shortDisplayName"],
            "away_logo": away["team"]["logo"],
            "home":      home["team"]["shortDisplayName"],
            "home_logo": home["team"]["logo"],
            "score":     f"{away.get('score','-')} : {home.get('score','-')}",
            "status":    status["shortDetail"], # "Final", "3rd Q 04:21", etc.
            "winner":    "away" if state=="post" and away_pts>home_pts
                        else "home" if state=="post" and home_pts>away_pts
                        else None,
            "ongoing":   state not in ("pre", "post")
        })
    return out


def parse_ncaaf(raw_json) -> list[dict]:
    """
    ESPN College-Football scoreboard → canonical event list.
    Shows games that *start today* in U.S. Eastern Time
    (+ unfinished late games from last night if before 4 AM ET).
    """
    tz_et = ZoneInfo("America/New_York")
    now_et = datetime.now(tz_et)
    today = now_et.date()
    yday = today - timedelta(days=1)
    keep_yday = now_et.hour < 4  # same grace window

    out = []
    for ev in raw_json.get("events", []):
        comp = ev["competitions"][0]

        # local start date in ET
        local_date = datetime.fromisoformat(
            comp["date"].replace("Z", "+00:00")
        ).astimezone(tz_et).date()

        if local_date not in (today, yday):
            continue
        if local_date == yday and not keep_yday:
            continue

        status = comp["status"]["type"]
        state = status["state"] # pre | in | post

        teams = comp["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")

        away_pts = int(away.get("score", 0))
        home_pts = int(home.get("score", 0))

        out.append({
            "league":    "NCAA Football",
            "away":      away["team"]["shortDisplayName"],
            "away_logo": away["team"]["logo"],
            "home":      home["team"]["shortDisplayName"],
            "home_logo": home["team"]["logo"],
            "score":     f"{away.get('score','-')} : {home.get('score','-')}",
            "status":    status["shortDetail"],   # "Final", "3rd 08:15", etc.
            "winner":    "away" if state=="post" and away_pts>home_pts
                        else "home" if state=="post" and home_pts>away_pts
                        else None,
            "ongoing":   state not in ("pre", "post")
        })
    return out


def parse_ncaamb(raw_json) -> list[dict]:
    """
    ESPN men's-college-basketball scoreboard → canonical event list.
    Shows games that start **today (ET)**, plus unfinished games that
    began yesterday if it's before 4 AM ET.
    """
    tz_et = ZoneInfo("America/New_York")
    now_et = datetime.now(tz_et)
    today = now_et.date()
    yday = today - timedelta(days=1)
    keep_yday = now_et.hour < 4

    out = []
    for ev in raw_json.get("events", []):
        comp = ev["competitions"][0]

        # local start date
        local = datetime.fromisoformat(
            comp["date"].replace("Z", "+00:00")
        ).astimezone(tz_et).date()

        if local not in (today, yday):
            continue
        if local == yday and not keep_yday:
            continue

        status = comp["status"]["type"]
        state = status["state"] # pre | in | post

        teams = comp["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")

        away_pts = int(away.get("score", 0))
        home_pts = int(home.get("score", 0))

        out.append({
            "league":    "NCAA Basketball",
            "away":      away["team"]["shortDisplayName"],
            "away_logo": away["team"]["logo"],
            "home":      home["team"]["shortDisplayName"],
            "home_logo": home["team"]["logo"],
            "score":     f"{away.get('score','-')} : {home.get('score','-')}",
            "status":    status["shortDetail"],      # "Final", "2nd 05:12", …
            "winner":    "away" if state=="post" and away_pts>home_pts
                        else "home" if state=="post" and home_pts>away_pts
                        else None,
            "ongoing":   state not in ("pre", "post"),
        })
    return out


def parse_nhl(raw_json) -> list[dict]:
    """
    ESPN NHL scoreboard → canonical event list.
    Keeps games that start today in ET.
    If run between 00:00-03:59 ET keeps last-night games still in progress.
    """
    tz_et = ZoneInfo("America/New_York")
    now_et = datetime.now(tz_et)
    today = now_et.date()
    yday = today - timedelta(days=1)
    keep_yday = now_et.hour < 4

    out = []
    for ev in raw_json.get("events", []):
        comp = ev["competitions"][0]

        # convert start time to ET date
        local_date = datetime.fromisoformat(
            comp["date"].replace("Z", "+00:00")
        ).astimezone(tz_et).date()

        if local_date not in (today, yday):
            continue
        if local_date == yday and not keep_yday:
            continue

        status = comp["status"]["type"]
        state = status["state"] # pre | in | post

        teams = comp["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")

        away_pts = int(away.get("score", 0))
        home_pts = int(home.get("score", 0))

        out.append({
            "league":    "NHL",
            "away":      away["team"]["shortDisplayName"],
            "away_logo": away["team"]["logo"],
            "home":      home["team"]["shortDisplayName"],
            "home_logo": home["team"]["logo"],
            "score":     f"{away.get('score','-')} : {home.get('score','-')}",
            "status":    status["shortDetail"],     # e.g. "Final", "3rd 12:34"
            "winner":    "away" if state=="post" and away_pts>home_pts
                        else "home" if state=="post" and home_pts>away_pts
                        else None,
            "ongoing":   state not in ("pre", "post"),
        })
    return out


def parse_f1(raw_json) -> list[dict]:
    """
    ESPN F1 scoreboard → canonical list, one entry per session.

    • Pre-session (“pre”): show the entry list ordered by car number
    • Live / Post (“in” | “post”): show the classified result ordered by position
    • Only sessions that start **today** in US Eastern are emitted.
    """
    tz_et  = ZoneInfo("America/New_York")
    today  = datetime.now(tz_et).date()
    out    = []

    for ev in raw_json.get("events", []):
        for comp in ev.get("competitions", []):           # ← iterate every session
            # local start-date filter
            local_date = datetime.fromisoformat(
                comp["date"].replace("Z", "+00:00")
            ).astimezone(tz_et).date()
            if local_date != today:
                continue

            status = comp["status"]["type"]
            state  = status["state"]      # pre | in | post

            racers = comp.get("competitors", [])
            if len(racers) < 2:
                continue

            # sort: grid by carNumber before session, else by position
            if state == "pre":
                racers.sort(key=lambda r: int(r.get("carNumber", 99)))
            else:
                racers.sort(key=lambda r: int(r.get("position", 99)))

            def row(r):
                return {
                    "pos":  int(r.get("order", r.get("carNumber", 0))),
                    "name": r["athlete"]["shortName"],
                    "flag": r["athlete"].get("flag", {}).get("href", "")
                }

            field_list = [row(r) for r in racers]

            n1 = comp["type"].get("abbreviation", ev["shortName"])  # e.g. "FP1", "Qual
            n2 = ev['shortName']

            out.append({
                "league":  "Formula 1",
                "session": f'{n1} - {n2}',  # FP1 / Qual / Race
                "field":   field_list,
                "status":  status["shortDetail"],   # "FP1 Final", "Race – Lap 18/52", …
                "ongoing": state not in ("pre", "post"),
                "winner":  None,  # styling flag unused
            })

    return out


# ─────────────────────────── registry
LEAGUES = OrderedDict([
    ("NFL", {
        "url":    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
        "parser": parse_nfl,
    }),
    ("NCAA Football", {
        "url":    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
        "parser": parse_ncaaf,
    }),
    ("NBA", {
        "url":    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
        "parser": parse_nba,
    }),
    ("NCAA Basketball", {
        "url":    "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
        "parser": parse_ncaamb,
    }),
    ("MLB", {
        "url":    "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
        "parser": parse_mlb,
    }),
    ("ATP Men's Singles", {
        "url":    "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
        "parser": parse_atp,
    }),
    ("WTA Women's Singles", {
        "url":    "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard",
        "parser": parse_wta,
    }),
    ("NHL", {
        "url":    "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
        "parser": parse_nhl,
    }),
    ("Formula 1", {
        "url":    "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard",
        "parser": parse_f1,
    }),
])

# ─────────────────────────── fetch wrapper
def fetch_league(name: str):
    cfg   = LEAGUES[name]
    try:
        raw = requests.get(cfg["url"], timeout=10).json()
        return cfg["parser"](raw), None
    except Exception as e:
        logging.error("%s fetch error: %s", name, e)
        return [], f"⚠ {name} fetch failed"

# ─────────────────────────── Flask routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    all_events = []
    alert_msg  = None

    for name, info in LEAGUES.items():
        try:
            raw = requests.get(info["url"], timeout=10).json()
            events = info["parser"](raw)
            for ev in events:
                ev["sport"] = name  # inject display name
            all_events.extend(events)
        except Exception as e:
            logging.warning(f"{name} fetch failed: {e}")
            if not alert_msg:
                alert_msg = f"{name} fetch failed"

    return jsonify(events=all_events, alert=alert_msg)

if __name__ == "__main__":
    app.run(debug=True, port=5050)
