import requests
import math
import os
from datetime import datetime, timedelta

# =========================================
# CONFIGURACIÓN
# =========================================
API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
}

# =========================================
# FUNCIONES MATEMÁTICAS
# =========================================
def poisson(l, k):
    return (math.exp(-l) * (l ** k)) / math.factorial(k)

def prob_over15(l):
    return 1 - (poisson(l, 0) + poisson(l, 1))

def prob_btts(lh, la):
    p0h = poisson(lh, 0)
    p0a = poisson(la, 0)
    return 1 - p0h - p0a + (p0h * p0a)

# =========================================
# OBTENER PARTIDOS POR FECHA
# =========================================
def get_matches(date):
    url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?date={date}"
    res = requests.get(url, headers=HEADERS).json()
    return res.get("response", [])

# =========================================
# STATS CON FALLBACK AUTOMÁTICO
# =========================================
def get_team_stats(team_id, league_id):
    years = [datetime.now().year, datetime.now().year - 1]
    for y in years:
        url = f"https://api-football-v1.p.rapidapi.com/v3/teams/statistics?team={team_id}&league={league_id}&season={y}"
        res = requests.get(url, headers=HEADERS).json()
        if "response" in res:
            data = res["response"]
            goals_for = data["goals"]["for"]["average"]["total"]
            goals_against = data["goals"]["against"]["average"]["total"]
            return {
                "scored": float(goals_for) if goals_for else 1.2,
                "conceded": float(goals_against) if goals_against else 1.2
            }
    return None

# =========================================
# ANALISIS DE PARTIDO
# =========================================
def analizar(match):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]
    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]
    league_id = match["league"]["id"]
    league = match["league"]["name"]

    h = get_team_stats(home_id, league_id)
    a = get_team_stats(away_id, league_id)

    # fallback si stats no disponibles
    if not h or not a:
        lh = 1.4
        la = 1.2
    else:
        lh = (h["scored"] + a["conceded"]) / 2
        la = (a["scored"] + h["conceded"]) / 2

    p_over = prob_over15(lh + la)
    p_btts = prob_btts(lh, la)

    # Elegir pick más confiable
    if p_btts > p_over:
        pick = "🔥 Ambos anotan"
        prob = p_btts
    else:
        pick = "✅ Más de 1.5 goles"
        prob = p_over

    # Calcular score de confiabilidad 1-10
    score = round(prob * 10, 1)

    return {
        "league": league,
        "match": f"{home} vs {away}",
        "pick": pick,
        "prob": round(prob * 100, 1),
        "score": score
    }

# =========================================
# ENVÍO A TELEGRAM
# =========================================
def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =========================================
# MAIN: 7 DÍAS, 5 PARTIDOS POR DÍA
# =========================================
def main():
    today = datetime.now()
    msg = "🔥 PICKS TOP SEMANALES 🔥\n\n"
    total = 0

    for i in range(7):  # 7 días
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        display = (today + timedelta(days=i)).strftime("%d-%m-%Y")
        matches = get_matches(date)

        if matches:
            msg += f"📅 {display}\n"
            for m in matches[:5]:  # hasta 5 partidos por día
                r = analizar(m)
                msg += f"{r['league']}\n{r['match']}\n{r['pick']} ({r['prob']}%) | Score: {r['score']}/10\n\n"
                total += 1
            msg += "----------------------\n\n"

    if total == 0:
        msg = "⚠️ No hay partidos o problema con API"

    send(msg)

main()
