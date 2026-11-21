"""Coleta notícias de GTA 6 nas fontes, filtra pelo tema e remove o que já foi postado."""
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "seen.json"
VEICULOS_CONFIAVEIS = ["rockstar", "take-two", "ign", "gamespot", "eurogamer", "pc gamer", "polygon", "kotaku",
                       "the verge", "gamesradar", "bbc", "cnn", "reuters", "bloomberg", "associated press",
                       "g1", "globo", "uol", "folha", "estadão", "estadao", "tecmundo", "the enemy",
                       "voxel", "ign brasil", "techtudo", "variety", "forbes"]
UA = {"User-Agent": "Mozilla/5.0 (BrasileiroEmVice bot; +https://instagram.com/brasileiroemvice)"}


def load_cfg():
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


def _seen() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def mark_seen(keys: list[str]):
    s = _seen()
    now = int(time.time())
    for k in keys:
        s[k] = now
    # guarda só os últimos 30 dias
    s = {k: v for k, v in s.items() if now - v < 30 * 86400}
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1))


def key_for(title: str) -> str:
    norm = re.sub(r"[^a-z0-9 ]", "", title.lower())
    norm = " ".join(sorted(set(norm.split())))[:200]
    return hashlib.sha1(norm.encode()).hexdigest()[:16]


def _og_image(url: str) -> str | None:
    try:
        r = requests.get(url, headers=UA, timeout=10)
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', r.text)
        return m.group(1) if m else None
    except Exception:
        return None


def collect() -> list[dict]:
    cfg = load_cfg()
    kws = [k.lower() for k in cfg["palavras_chave"]]
    blocked = [b.lower() for b in cfg["seguranca"]["palavras_bloqueadas"]]
    max_age = cfg["seguranca"]["idade_maxima_horas"] * 3600
    seen = _seen()
    items = []
    for src in cfg["fontes"]:
        try:
            raw = requests.get(src["url"], headers=UA, timeout=15).content
            feed = feedparser.parse(raw)
        except Exception as e:
            print(f"[fonte falhou] {src['nome']}: {e}")
            continue
        for e in feed.entries[:40]:
            title = e.get("title", "").strip()
            summary = re.sub("<[^>]+>", " ", e.get("summary", ""))[:600]
            text = f"{title} {summary}".lower()
            if not any(k in text for k in kws):
                continue
            if any(b in text for b in blocked):
                continue
            ts = e.get("published_parsed") or e.get("updated_parsed")
            if ts and time.time() - time.mktime(ts) > max_age:
                continue
            outlet = (e.get("source") or {}).get("title", "") if hasattr(e, "get") else ""
            trusted = src["confiavel"] or any(v in outlet.lower() for v in VEICULOS_CONFIAVEIS)
            items.append({
                "key": key_for(title),
                "title": title,
                "summary": summary.strip(),
                "link": e.get("link"),
                "source": outlet or src["nome"],
                "trusted": trusted,
                "published": datetime.fromtimestamp(time.mktime(ts), timezone.utc).isoformat() if ts else None,
            })
    fresh = [i for i in items if i["key"] not in seen]
    print(f"{len(items)} itens do tema, {len(fresh)} novos")
    return fresh


def og_image(url: str) -> str | None:
    """Foto da matéria. Ignora links do Google Notícias e logos (viram fundo feio na arte)."""
    if not url or "news.google." in url:
        return None
    img = _og_image(url)
    if img and not any(b in img.lower() for b in ("google", "logo", "favicon", "placeholder", "default")):
        return img
    return None
