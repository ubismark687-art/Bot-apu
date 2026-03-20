import requests
import math
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def poisson(l, k):
    return (math.exp(-l) * l**k) / math.factorial(k)

def prob_over15(l):
    return 1 - (poisson(l,0) + poisson(l,1))

def prob_btts(lh, la):
    p0h = poisson(lh,0)
    p0a = poisson(la,0)
    return 1 - p0h - p0a + (p0h * p0a)

# 🔥 PARTIDOS DE PRUEBA (SIN API)
def get_matches():
    return [
        {"teams": {"home": {"name": "Barcelona"}, "away": {"name": "Valencia"}}},
        {"teams": {"home": {"name": "Real Madrid"}, "away": {"name": "Sevilla"}}},
        {"teams": {"home": {"name": "Bayern Munich"}, "away": {"name": "Dortmund"}}},
        {"teams": {"home": {"name": "Liverpool"}, "away": {"name": "Chelsea"}}},
        {"teams": {"home": {"name": "Inter Milan"}, "away": {"name": "Atalanta"}}}
    ]

def analizar(m):
    home = m["teams"]["home"]["name"]
    away = m["teams"]["away"]["name"]

    # Valores simulados (puedes ajustarlos)
    lh = 1.5
    la = 1.3

    p1 = prob_over15(lh + la)
    p2 = prob_btts(lh, la)

    score = 0
    if p1 > 0.75:
        score += 3
    if p2 > 0.65:
        score += 3

    pick = None
    prob = 0

    if score >= 6:
        if p2 > p1:
            pick = "🔥 Ambos anotan"
            prob = p2
        else:
            pick = "✅ Más de 1.5 goles"
            prob = p1

    return {
        "match": f"{home} vs {away}",
        "pick": pick,
        "prob": round(prob * 100, 1)
    }

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def main():
    matches = get_matches()
    msg = "🔥 PICKS DEL DÍA 🔥\n\n"

    for m in matches:
        r = analizar(m)
        if r["pick"]:
            msg += f"{r['match']}\n{r['pick']} ({r['prob']}%)\n\n"

    send(msg)

main()
    
