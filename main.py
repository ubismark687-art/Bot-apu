import requests
from datetime import datetime, timedelta

# =========================
# CONFIGURACIÓN
# =========================
API_KEY = "9aBfJNwvm0r63S4o"
TELEGRAM_TOKEN = "8780741189:AAGexBjBecMxA0Avscr0nrA8YeY2XB9J1Ss"
CHAT_ID = "7438828345"

HEADERS = {"x-rapidapi-key": API_KEY}
API_HOST = "live-score-api.p.rapidapi.com"

MAX_PARTIDOS = 10  # máximo a enviar

# =========================
# FUNCIONES PRINCIPALES
# =========================

def obtener_fixtures(fecha):
    url = f"https://{API_HOST}/fixtures.json"
    params = {"date": fecha}
    try:
        res = requests.get(url, headers=HEADERS, params=params)
        data = res.json()
        return data.get("matches", [])
    except Exception as e:
        print("Error al obtener fixtures:", e)
        return []

def obtener_resultados_equipo(team_id):
    url = f"https://{API_HOST}/history.json"
    params = {"team_id": team_id}
    try:
        res = requests.get(url, headers=HEADERS, params=params)
        return res.json().get("results", [])
    except:
        return []

def calcular_probabilidades(partido):
    home = partido["home"]["name"]
    away = partido["away"]["name"]
    home_id = partido["home"]["id"]
    away_id = partido["away"]["id"]

    hist_home = obtener_resultados_equipo(home_id)[:5]
    hist_away = obtener_resultados_equipo(away_id)[:5]

    goles_home = sum(m["home_goals"] for m in hist_home) / 5 if hist_home else 1
    goles_away = sum(m["away_goals"] for m in hist_away) / 5 if hist_away else 1

    both_home = sum(1 for m in hist_home if m["home_goals"] > 0 and m["away_goals"] > 0) / 5 if hist_home else 0
    both_away = sum(1 for m in hist_away if m["home_goals"] > 0 and m["away_goals"] > 0) / 5 if hist_away else 0

    prob_ambos = ((both_home + both_away) / 2) * 100
    avg_goles_total = (goles_home + goles_away) / 2
    prob_over25 = min(avg_goles_total / 3 * 100, 100)
    score_total = (prob_ambos * 0.5) + (prob_over25 * 0.5)

    return round(prob_ambos, 1), round(prob_over25,1), round(score_total,1)

def generar_resumen(partidos):
    resumen = "📊 *Ranking Ambos Marcan + Over 2.5* 📊\n\n"
    for i, p in enumerate(partidos,1):
        resumen += (f"{i}. {p['liga']}\n"
                    f"{p['local']} vs {p['visitante']} - {p['hora']}\n"
                    f"Prob AM: {p['prob_ambos']}% | Prob Over 2.5: {p['prob_over']}% | Score: {p['score']}\n---\n")
    return resumen

def enviar_telegram(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": texto, "parse_mode":"Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Error enviando Telegram:", e)

# =========================
# PROCESO PRINCIPAL
# =========================

def main():
    fechas = [datetime.now().strftime("%Y-%m-%d"),
              (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")]

    todos = []

    for f in fechas:
        fixtures = obtener_fixtures(f)
        for partido in fixtures:
            try:
                liga = partido["league"]["name"]
                local = partido["home"]["name"]
                visitante = partido["away"]["name"]
                hora = partido["fixture_date"].split("T")[1][:5]

                prob_ambos, prob_over, score_total = calcular_probabilidades(partido)

                todos.append({
                    "liga": liga,
                    "local": local,
                    "visitante": visitante,
                    "hora": hora,
                    "prob_ambos": prob_ambos,
                    "prob_over": prob_over,
                    "score": score_total
                })
            except:
                continue

    if not todos:
        enviar_telegram("No se encontraron partidos jugables.")
        return

    todos_sorted = sorted(todos, key=lambda x: x["score"], reverse=True)[:MAX_PARTIDOS]

    resumen = generar_resumen(todos_sorted)
    enviar_telegram(resumen)
    print(f"Se enviaron {len(todos_sorted)} partidos a Telegram.")

if __name__ == "__main__":
    main()
