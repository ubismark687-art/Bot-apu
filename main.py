import requests
import math
from datetime import datetime, timedelta
import pytz
import time
import json
import os

# =========================
# CONFIGURACIÓN
# =========================
API_KEY = "TU_API_KEY"  # Tu API Key de RapidAPI
HEADERS = {"x-rapidapi-key": API_KEY}

TELEGRAM_TOKEN = "TU_TOKEN"  # Token de tu bot Telegram
CHAT_ID = "TU_CHAT_ID"       # Chat ID para enviar picks
TIMEZONE = "America/Managua"

HISTORICO_FILE = "historico_picks.json"

# =========================
# UTILIDADES MATEMÁTICAS
# =========================
def poisson_prob(lmbda, k):
    return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

def prob_over_15(lmbda_total):
    p0 = poisson_prob(lmbda_total, 0)
    p1 = poisson_prob(lmbda_total, 1)
    return 1 - (p0 + p1)

def prob_btts(lmbda_home, lmbda_away):
    p_home0 = poisson_prob(lmbda_home, 0)
    p_away0 = poisson_prob(lmbda_away, 0)
    p_00 = p_home0 * p_away0
    return 1 - p_home0 - p_away0 + p_00

# =========================
# HISTÓRICO Y ESTADÍSTICAS
# =========================
def cargar_historico():
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r") as f:
            return json.load(f)
    return {"picks": {}, "estadisticas": {}}

def guardar_historico(data):
    with open(HISTORICO_FILE, "w") as f:
        json.dump(data, f, indent=2)

def actualizar_estadisticas(historico, pick_info):
    tipo = pick_info["pick"]
    liga = pick_info.get("league", "General")
    if liga not in historico["estadisticas"]:
        historico["estadisticas"][liga] = {"ganados":0, "perdidos":0, "total":0}
    stats = historico["estadisticas"][liga]
    stats["total"] += 1
    if pick_info["status"] == "ganado":
        stats["ganados"] += 1
    else:
        stats["perdidos"] += 1

# =========================
# TELEGRAM
# =========================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Error enviando Telegram:", e)

# =========================
# FUNCIONES DE API
# =========================
def get_matches(days=2):
    matches = []
    tz = pytz.timezone(TIMEZONE)
    for d in range(days):
        date = (datetime.now(tz) + timedelta(days=d)).strftime("%Y-%m-%d")
        url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?date={date}"
        try:
            resp = requests.get(url, headers=HEADERS)
            data = resp.json()
            matches.extend(data.get("response", []))
        except Exception as e:
            print(f"Error obteniendo partidos para {date}: {e}")
    return matches

def get_team_stats(team_id):
    try:
        url = f"https://api-football-v1.p.rapidapi.com/v3/teams/statistics?team={team_id}"
        resp = requests.get(url, headers=HEADERS).json()
        stats = resp.get("response", {})
        avg_scored = stats.get("goals", {}).get("for", {}).get("total", {}).get("average", 1.5)
        avg_conceded = stats.get("goals", {}).get("against", {}).get("total", {}).get("average", 1.2)
        btts_last5 = stats.get("lineups", {}).get("matches", 4)
        return {"avg_scored": avg_scored, "avg_conceded": avg_conceded, "btts_last5": btts_last5}
    except:
        return {"avg_scored": 1.5, "avg_conceded": 1.2, "btts_last5": 4}

# =========================
# ANÁLISIS DE PICKS
# =========================
def analizar(match):
    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]

    h = get_team_stats(home_id)
    a = get_team_stats(away_id)

    lambda_home = (h["avg_scored"] + a["avg_conceded"]) / 2
    lambda_away = (a["avg_scored"] + h["avg_conceded"]) / 2
    lambda_total = lambda_home + lambda_away

    p_over15 = prob_over_15(lambda_total)
    p_btts = prob_btts(lambda_home, lambda_away)

    score = 0
    if p_over15 > 0.75: score += 3
    if p_btts > 0.65: score += 3
    if h["btts_last5"] >= 4: score += 2
    if a["btts_last5"] >= 4: score += 2

    pick = None
    prob = 0
    if score >= 8: pick, prob = "🔥 BTTS", p_btts
    elif score >= 6: pick, prob = "✅ Over 1.5", p_over15

    return {
        "match": f"{home} vs {away}",
        "pick": pick,
        "score": score,
        "prob": round(prob*100,1),
        "fixture_id": match["fixture"]["id"],
        "league": match["league"]["name"] if "league" in match else "General"
    }

# =========================
# ACTUALIZACIÓN DE RESULTADOS
# =========================
def actualizar_resultados(historico):
    for fixture_id, info in historico["picks"].items():
        if info["status"] == "pendiente":
            try:
                url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?id={fixture_id}"
                resp = requests.get(url, headers=HEADERS).json()
                fixture = resp["response"][0]["fixture"]
                status = fixture["status"]["short"]
                goals = resp["response"][0]["goals"]
                if status in ["FT","AET"]:
                    home_goals = goals["home"]
                    away_goals = goals["away"]
                    acierto = False
                    if info["pick"]=="🔥 BTTS": acierto = home_goals>0 and away_goals>0
                    elif info["pick"]=="✅ Over 1.5": acierto = (home_goals+away_goals)>1
                    info["status"] = "ganado" if acierto else "perdido"
                    actualizar_estadisticas(historico, info)
                    send_telegram(f"✅ Resultado pick: {info['match']}\nPick: {info['pick']}\nResultado: {'GANADO' if acierto else 'PERDIDO'}")
            except Exception as e:
                print(f"Error actualizando fixture {fixture_id}: {e}")
    guardar_historico(historico)

# =========================
# MAIN
# =========================
def main():
    historico = cargar_historico()
    matches = get_matches(days=2)
    picks_nuevos = []

    for m in matches:
        r = analizar(m)
        if r["pick"] and r["fixture_id"] not in historico["picks"]:
            r["status"] = "pendiente"
            historico["picks"][r["fixture_id"]] = r
            picks_nuevos.append(r)

    if picks_nuevos:
        msg = "🔥 NUEVOS PICKS PRO+ 🔥\n\n"
        for p in picks_nuevos:
            msg += f"{p['match']}\n{p['pick']} | Prob: {p['prob']}% | Score: {p['score']} | Liga: {p['league']}\n\n"
        send_telegram(msg)
        guardar_historico(historico)

    actualizar_resultados(historico)

    # Resumen diario
    msg_resumen = "📊 RESUMEN DIARIO DE PICKS 📊\n\n"
    for liga, stats in historico["estadisticas"].items():
        msg_resumen += f"{liga}: {stats['ganados']}/{stats['total']} ganados\n"
    send_telegram(msg_resumen)

# =========================
# EJECUCIÓN 24/7
# =========================
if __name__=="__main__":
    while True:
        try:
            main()
            time.sleep(60*60)  # revisar cada hora
        except Exception as e:
            print("Error principal del bot:", e)
            time.sleep(60)
