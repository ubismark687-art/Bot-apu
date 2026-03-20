import requests
import math

# =========================
# CONFIG
# =========================
API_KEY = "TU_API_KEY"
HEADERS = {"x-rapidapi-key": API_KEY}

TELEGRAM_TOKEN = "TU_TOKEN"
CHAT_ID = "TU_CHAT_ID"

SEASON = 2026
HOME_ADVANTAGE = 1.2  # +20% goles para local
MIN_PROB = 0.75       # picks solo si >75% probabilidad

# =========================
# POISSON
# =========================
def poisson_prob(lmbda, k):
    return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

def prob_over_n(lmbda_total, n):
    prob = sum(poisson_prob(lmbda_total, k) for k in range(n))
    return 1 - prob

def prob_btts(lambda_home, lambda_away):
    p_home_goals = 1 - poisson_prob(lambda_home, 0)
    p_away_goals = 1 - poisson_prob(lambda_away, 0)
    return p_home_goals * p_away_goals

# =========================
# API
# =========================
def get_matches():
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures?next=20"
    matches = requests.get(url, headers=HEADERS).json()["response"]
    return sorted(matches, key=lambda x: x["fixture"]["timestamp"])

def get_team_stats(team_id):
    url = f"https://api-football-v1.p.rapidapi.com/v3/teams/statistics?team={team_id}&season={SEASON}"
    res = requests.get(url, headers=HEADERS).json()["response"]
    stats = res["team"]["statistics"]["all"]["goals"]
    matches_played = stats["matches"]["played"]["total"] or 1
    avg_scored = stats["for"]["total"]["total"] / matches_played
    avg_conceded = stats["against"]["total"]["total"] / matches_played
    last5_btts = stats.get("btts", {}).get("last5", 3)
    return {"avg_scored": avg_scored, "avg_conceded": avg_conceded, "btts_last5": last5_btts}

def get_injuries(match):
    home_inj = sum(1 for p in match["teams"]["home"].get("players", []) if p.get("injured"))
    away_inj = sum(1 for p in match["teams"]["away"].get("players", []) if p.get("injured"))
    return home_inj, away_inj

# =========================
# ANALISIS ULTRA PRO
# =========================
def analizar(match):
    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]
    home_name = match["teams"]["home"]["name"]
    away_name = match["teams"]["away"]["name"]

    h = get_team_stats(home_id)
    a = get_team_stats(away_id)

    lambda_home = ((h["avg_scored"] * HOME_ADVANTAGE) + a["avg_conceded"]) / 2
    lambda_away = (a["avg_scored"] + h["avg_conceded"]) / 2
    lambda_total = lambda_home + lambda_away

    home_inj, away_inj = get_injuries(match)
    lambda_home *= 0.9 ** home_inj
    lambda_away *= 0.9 ** away_inj
    lambda_total = lambda_home + lambda_away

    # Probabilidades
    p_btts = prob_btts(lambda_home, lambda_away)
    p_over15 = prob_over_n(lambda_total, 2)
    p_over25 = prob_over_n(lambda_total, 3)
    p_under25 = 1 - p_over25

    picks = []
    # BTTS
    if p_btts >= MIN_PROB:
        picks.append(("🔥 BTTS", round(p_btts*100,1)))
    # Over 1.5
    if p_over15 >= MIN_PROB:
        picks.append(("✅ Over 1.5", round(p_over15*100,1)))
    # Over 2.5
    if p_over25 >= MIN_PROB:
        picks.append(("⚡ Over 2.5", round(p_over25*100,1)))
    # Under 2.5
    if p_under25 >= MIN_PROB:
        picks.append(("💧 Under 2.5", round(p_under25*100,1)))

    return {"match": f"{home_name} vs {away_name}", "picks": picks}

# =========================
# TELEGRAM
# =========================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# =========================
# MAIN
# =========================
def main():
    matches = get_matches()
    all_picks = []

    for m in matches:
        r = analizar(m)
        if r["picks"]:
            all_picks.append(r)

    # Ordenar top picks por la probabilidad más alta
    all_picks = sorted(all_picks, key=lambda x: max([p[1] for p in x["picks"]]), reverse=True)[:5]

    msg = "🔥 *PICKS ULTRA PRO DEL DÍA* 🔥\n\n"
    for p in all_picks:
        msg += f"🏟 {p['match']}\n"
        for pick, prob in p["picks"]:
            msg += f"{pick} | Probabilidad: {prob}%\n"
        msg += "\n"

    send_telegram(msg)

if __name__ == "__main__":
    main()
