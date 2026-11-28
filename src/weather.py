"""Previsão do dia em Cascavel (Open-Meteo, grátis e sem chave) para o story das 7h."""
from datetime import datetime, timedelta, timezone

import requests

from news import load_cfg

WMO = {0: "céu limpo", 1: "quase sem nuvens", 2: "parcialmente nublado", 3: "nublado", 45: "neblina", 48: "neblina",
       51: "garoa fraca", 53: "garoa", 55: "garoa forte", 61: "chuva fraca", 63: "chuva", 65: "chuva forte",
       71: "neve fraca", 80: "pancadas de chuva", 81: "pancadas de chuva", 82: "temporal", 95: "trovoadas",
       96: "trovoadas com granizo", 99: "trovoadas com granizo"}
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def today() -> dict:
    c = load_cfg()["clima"]
    r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=20, params={
        "latitude": c["lat"], "longitude": c["lon"], "timezone": "America/Sao_Paulo", "forecast_days": 1,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,weather_code"})
    r.raise_for_status()
    d = r.json()["daily"]
    mx, mn = round(d["temperature_2m_max"][0]), round(d["temperature_2m_min"][0])
    chuva, vento = int(d["precipitation_probability_max"][0] or 0), round(d["wind_speed_10m_max"][0])
    desc = WMO.get(int(d["weather_code"][0]), "tempo firme")
    if chuva >= 60:
        dica = "Dia de guarda-chuva na bolsa. Avenida alagada não perdoa 🌧"
    elif mn <= 10:
        dica = "Madrugada gelada: casaco, meia grossa e chimarrão 🧉"
    elif vento >= 30:
        dica = "O famoso vento de Cascavel tá com tudo hoje. Segura o boné 💨"
    elif mx >= 31:
        dica = "Calorão! Água na garrafinha e fim de tarde no Lago 💧"
    else:
        dica = "Tempo bom pra rolê. Bora aproveitar o dia 😎"
    now = datetime.now(timezone(timedelta(hours=-3)))
    return {"max": mx, "min": mn, "chuva": chuva, "vento": vento, "descricao": desc, "dica": dica,
            "dia": f"{DIAS[now.weekday()]}, {now.day} de {MESES[now.month - 1]}"}
