import requests
import math
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

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
# PARTIDOS (SIMULADOS PERO VARIADOS)
# =========================
def get_matches():
    return [
        {"teams": {"home": {"name": "Barcelona"}, "away": {"name": "Valencia"}}, "strength": 1.5},
        {"teams": {"home": {"name": "Real Madrid"}, "away": {"name": "Sevilla"}}, "strength": 1.6},
        {"teams": {"home": {"name": "Bayern"}, "away": {"name": "Dortmund"}}, "strength": 1.8},
        {"teams": {"home": {"name": "Liverpool"}, "away": {"name": "Chelsea"}}, "strength": 1.7},
        {"teams": {"home": {"name": "Inter"}, "away": {"name": "Atalanta"}}, "strength": 1.6},
        {"teams": {"home": {"name": "PSG"}, "away": {"name": "Lyon"}}, "strength": 1.7},
        {"teams": {"home": {"name": "Ajax"}, "away": {"name": "PSV"}}, "strength": 1.9}
    ]

# =========================
# ANÁLISIS
# =========================
def analizar(m):
    home = m["teams"]["home"]["name"]
    away = m["teams"]["away"]["name"]
    strength = m["strength"]

    # Ajuste dinámico
    lh = strength
    la = strength - 0.2

    p_over = prob_over15(lh + la)
    p_btts = prob_btts(lh, la)

    # SCORE INTELIGENTE
    score = 0

    if p_over > 0.75:
        score += 3
    if p_btts > 0.65:
        score += 3
    if lh > 1.5:
        score += 2
    if la > 1.2:
        score += 2

    # DECISIÓN
    if p_btts > p_over:
        pick = "🔥 Ambos anotan"
        prob = p_btts
    else:
        pick = "✅ Más de 1.5 goles"
        prob = p_over

    return {
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
    results = []

    for m in matches:
        results.append(analizar(m))

    # Ordenar por mejores picks
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    msg = "🔥 PICKS PRO DEL DÍA 🔥\n\n"

    for r in results:
        msg += f"{r['match']}\n{r['pick']} | Prob: {r['prob']}% | Score: {r['score']}\n\n"

    send(msg)

main()
