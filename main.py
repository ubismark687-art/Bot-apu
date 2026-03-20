import requests
import math
import os
from datetime import datetime

API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
}

# =========================
# FUNCIONES MATEMÁTICAS
# =========================
def poisson(l, k):
    return (math.exp(-l) * (l ** k)) / math.factorial(k)

def prob_over15(l):
    return 1 - (poisson(l, 0) + poisson(l, 1))

def prob_btts(lh, la):
    p0h = poisson(lh, 0)
    p0a = poisson(la, 0)
    return 1 - p0h - p0a + (p0h * p0a)

# =========================
# PARTIDOS DEL DÍA
# =========================
def get_matches():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?date={today}"
    res = requests.get(url, headers=HEADERS).json()
    return res.get("response", [])

# =========================
# STATS DE EQUIPOS
# =========================
def get_team_stats(team_id, league_id):
    url = f"https://api-football-v1.p.rapidapi.com/v3/teams/statistics?team={team_id}&league={league_id}&season=2023"
    res = requests.get(url, headers=HEADERS).json()

    if "response" not in res:
        return None

    data = res["response"]

    goals_for = data["goals"]["for"]["average"]["total"]
    goals_against = data["goals"]["against"]["average"]["total"]

    return {
        "scored": float(goals_for) if goals_for else 1.2,
        "conceded": float(goals_against) if goals_against else 1.2
    }

# =========================
# ANÁLISIS REAL
# =========================
def analizar(match):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]
    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]
    league_id = match["league"]["id"]
    league = match["league"]["name"]

    h_stats = get_team_stats(home_id, league_id)
    a_stats = get_team_stats(away_id, league_id)

    if not h_stats or not a_stats:
        return None

    # Goles esperados
    lh = (h_stats["scored"] + a_stats["conceded"]) / 2
    la = (a_stats["scored"] + h_stats["conceded"]) / 2

    p_over = prob_over15(lh + la)
    p_btts = prob_btts(lh, la)

    score = 0

    if p_over > 0.75:
        score += 3
    if p_btts > 0.65:
        score += 3
    if lh > 1.3:
        score += 2
    if la > 1.2:
        score += 2

    if score < 5:
        return None

    if p_btts > p_over:
        pick = "🔥 Ambos anotan"
        prob = p_btts
    else:
        pick = "✅ Más de 1.5 goles"
        prob = p_over

    return {
        "league": league,
        "match": f"{home} vs {away}",
        "pick": pick,
        "prob": round(prob * 100, 1),
        "score": score
    }

# =========================
# TELEGRAM
# =========================
def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =========================
# MAIN
# =========================
def main():
    matches = get_matches()

    today_str = datetime.now().strftime("%d-%m-%Y")

    if not matches:
        send("⚠️ No hay partidos hoy")
        return

    results = []

    for m in matches:
        r = analizar(m)
        if r:
            results.append(r)

    # Ordenar por mejor score
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    msg = f"🔥 PICKS PRO REALES ({today_str}) 🔥\n\n"

    if not results:
        msg += "No hay picks claros hoy ⚠️"
    else:
        for r in results[:5]:
            msg += f"{r['league']}\n{r['match']}\n{r['pick']} ({r['prob']}%) | Score: {r['score']}\n\n"

    send(msg)

main()
