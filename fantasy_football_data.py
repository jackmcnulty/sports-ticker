import os
from dotenv import load_dotenv
from espn_api.football import League

load_dotenv()

def _player_list(players):
    return [{
        "name": p.name,
        "pos": p.position,
        "lineup_slot": p.lineupSlot,
        "score": p.points,
        "pro_team": p.proTeam,
        "stats": p.stats
    } for p in players]


def get_league():
    league = League(
        league_id=482514371,
        year=2024,
        espn_s2=os.getenv("ESPN_S2"),
        swid=os.getenv("SWID"),
        debug=False
    )
    return league


def get_matchup_data(league):
    matchups = league.box_scores(week=1)
    events = []
    for match in matchups:
        # Home and Away names and scores
        home_team = match.home_team
        away_team = match.away_team
        home_score = match.home_score
        away_score = match.away_score
        events.append({
            "home": home_team.team_name,
            "away": away_team.team_name,
            "home_score": home_score,
            "away_score": away_score,
            "home_players": _player_list(match.home_lineup),
            "away_players": _player_list(match.away_lineup)
        })
    return events

def get_current_week_matchups():
    league = get_league()
    events = get_matchup_data(league)
    return events