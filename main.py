import requests
import time
from datetime import datetime

# =========================
# CONFIGURACIÓN
# =========================
API_KEY = "9aBfJNwvm0r63S4o"              
TELEGRAM_TOKEN = "8780741189:AAGexBjBecMxA0Avscr0nrA8YeY2XB9J1Ss"
CHAT_ID = "7438828345"

HEADERS = {"x-rapidapi-key": API_KEY}

# Ajustes de apuestas
UMBRAL_PROBABILIDAD = 55  # % mínimo para considerar partido
MAX_PARTIDOS = 3  # Solo enviar los 3 mejores

# =========================
# FUNCIONES
# =========================
def obtener_partidos():
    fecha = datetime.now().strftime("%Y-%m-%d")
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    params = {"date": fecha}
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        data = response.json()
        return data.get("response", [])
    except Exception as e:
        print("Error obteniendo partidos:", e)
        return []

def filtrar_y_rankear(partidos):
    recomendados = []
    for p in partidos:
        try:
            local = p['teams']['home']['name']
            visitante = p['teams']['away']['name']
            liga = p['league']['name']
            fecha_partido = p['fixture']['date']
            hora = fecha_partido.split("T")[1][:5]

            ambos_prob = 50  # Default si no hay datos
            odds = p.get('odds', [])

            if odds:
                for o in odds:
                    if o['bookmaker']['name'].lower() == 'bet365':
                        for bet in o['bets']:
                            if bet['name'].lower() in ['both teams to score', 'ambos marcan']:
                                ambos_prob = max([float(option['value']) for option in bet['values']])

            if float(ambos_prob) >= UMBRAL_PROBABILIDAD:
                recomendados.append({
                    "liga": liga,
                    "local": local,
                    "visitante": visitante,
                    "hora": hora,
                    "prob": ambos_prob
                })
        except:
            continue

    # Ordenar de mayor a menor probabilidad
    recomendados = sorted(recomendados, key=lambda x: x['prob'], reverse=True)
    return recomendados[:MAX_PARTIDOS]

def enviar_telegram(mensajes):
    if not mensajes:
        enviar_telegram_individual("No hay partidos con alta probabilidad de ambos marcan hoy.")
        return

    resumen = "📊 *Top partidos recomendados para apostar Ambos Marcan* 📊\n\n"
    for i, p in enumerate(mensajes, 1):
        resumen += (f"{i}. {p['liga']}\n"
                    f"{p['local']} vs {p['visitante']}\n"
                    f"Hora: {p['hora']}\n"
                    f"Probabilidad Ambos Marcan: {p['prob']}%\n---\n")

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

def analizar_y_enviar():
    print("Obteniendo partidos...")
    partidos = obtener_partidos()
    if not partidos:
        enviar_telegram_individual("No se encontraron partidos hoy.")
        return

    recomendados = filtrar_y_rankear(partidos)
    if not recomendados:
        enviar_telegram_individual("No hay partidos con alta probabilidad de ambos marcan hoy.")
        return

    enviar_telegram(recomendados)
    print(f"Resumen enviado con {len(recomendados)} partidos.")

# =========================
# LOOP INFINITO
# =========================
while True:
    analizar_y_enviar()
    print("Esperando 1 hora para la siguiente revisión...\n")
    time.sleep(3600)
