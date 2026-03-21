import requests
from datetime import datetime, timedelta

# =========================
# CONFIGURACIÓN
# =========================
API_KEY = "9aBfJNwvm0r63S4o"              
TELEGRAM_TOKEN = "8780741189:AAGexBjBecMxA0Avscr0nrA8YeY2XB9J1Ss"
CHAT_ID = "7438828345"

HEADERS = {"x-rapidapi-key": API_KEY}

UMBRAL_PROB_AMBOS_MARCAN = 55
UMBRAL_PROB_OVER_15 = 55
MAX_PARTIDOS = 5  # Top partidos a enviar

# =========================
# FUNCIONES
# =========================
def obtener_partidos(fecha):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    params = {"date": fecha}
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        data = response.json()
        return data.get("response", [])
    except Exception as e:
        print("Error obteniendo partidos:", e)
        return []

def filtrar_partidos(partidos):
    recomendados = []
    for p in partidos:
        try:
            local = p['teams']['home']['name']
            visitante = p['teams']['away']['name']
            liga = p['league']['name']
            fecha_partido = p['fixture']['date']
            hora = fecha_partido.split("T")[1][:5]

            prob_ambos = 50
            prob_over = 50
            odds = p.get('odds', [])

            if odds:
                for o in odds:
                    if o['bookmaker']['name'].lower() == 'bet365':
                        for bet in o['bets']:
                            name_lower = bet['name'].lower()
                            if name_lower in ['both teams to score', 'ambos marcan']:
                                prob_ambos = max([float(opt['value']) for opt in bet['values']])
                            elif name_lower in ['over/under 1.5', 'over 1.5', 'más 1.5']:
                                prob_over = max([float(opt['value']) for opt in bet['values']])

            if prob_ambos >= UMBRAL_PROB_AMBOS_MARCAN and prob_over >= UMBRAL_PROB_OVER_15:
                recomendados.append({
                    "liga": liga,
                    "local": local,
                    "visitante": visitante,
                    "hora": hora,
                    "prob_ambos": prob_ambos,
                    "prob_over": prob_over
                })
        except:
            continue

    recomendados = sorted(recomendados, key=lambda x: x['prob_ambos'], reverse=True)
    return recomendados[:MAX_PARTIDOS]

def enviar_telegram(partidos):
    if not partidos:
        enviar_telegram_individual("No hay partidos que cumplan Ambos Marcan + Over 1.5 para hoy y mañana.")
        return

    resumen = "📊 *Partidos recomendados para apostar Ambos Marcan + Over 1.5* 📊\n\n"
    for i, p in enumerate(partidos, 1):
        resumen += (f"{i}. {p['liga']}\n"
                    f"{p['local']} vs {p['visitante']}\n"
                    f"Hora: {p['hora']}\n"
                    f"Probabilidad Ambos Marcan: {p['prob_ambos']}%\n"
                    f"Probabilidad Over 1.5: {p['prob_over']}%\n---\n")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": resumen, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Error enviando Telegram:", e)

def enviar_telegram_individual(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Error enviando Telegram:", e)

# =========================
# PROCESO PRINCIPAL
# =========================
def main():
    fechas = [datetime.now(), datetime.now() + timedelta(days=1)]
    todos_partidos = []

    for fecha in fechas:
        fecha_str = fecha.strftime("%Y-%m-%d")
        partidos = obtener_partidos(fecha_str)
        filtrados = filtrar_partidos(partidos)
        todos_partidos.extend(filtrados)

    enviar_telegram(todos_partidos)
    print(f"Se enviaron {len(todos_partidos)} partidos a Telegram.")

if __name__ == "__main__":
    main()
