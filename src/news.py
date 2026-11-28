"""Coleta o que está acontecendo em Cascavel nas fontes, filtra o tema e tira o que já foi postado."""
import hashlib
import html as _h
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
ASSUNTOS = ROOT / "state" / "assuntos.json"  # quando cada manchete apareceu pela 1ª vez
LOCAIS = ["cgn", "catve", "o paraná", "oparana", "radar bo", "tarobá", "taroba", "band b", "bandab", "rpc", "g1",
          "prefeitura de cascavel", "cascavel.pr.gov", "câmara de cascavel", "aen", "agência estadual", "bem paraná",
          "tribuna", "gazeta do povo", "massa news", "ric", "cbn cascavel"]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
      "Accept-Language": "pt-BR,pt;q=0.9"}


def load_cfg():
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


def _seen() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def mark_seen(keys: list[str]):
    s = _seen()
    now = int(time.time())
    for k in keys:
        s[k] = now
    s = {k: v for k, v in s.items() if now - v < 30 * 86400}
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1))


def key_for(title: str) -> str:
    norm = re.sub(r"[^a-z0-9 ]", "", title.lower())
    norm = " ".join(sorted(set(norm.split())))[:200]
    return hashlib.sha1(norm.encode()).hexdigest()[:16]


def _fetch_feed(url: str):
    raw = requests.get(url, headers=UA, timeout=20).content
    return feedparser.parse(raw)


def collect(max_age_h: int | None = None) -> list[dict]:
    cfg = load_cfg()
    kws = [k.lower() for k in cfg["palavras_chave"]]
    blocked = [b.lower() for b in cfg.get("bloqueados", [])]
    max_age = (max_age_h or cfg["seguranca"]["idade_maxima_horas"]) * 3600
    seen = _seen()
    items, velhos = [], []
    for src in cfg["fontes"]:
        try:
            feed = _fetch_feed(src["url"])
        except Exception as e:
            print(f"[fonte falhou] {src['nome']}: {e}")
            continue
        n = 0
        for e in feed.entries[:50]:
            title = _h.unescape(e.get("title", "")).strip()
            summary = _h.unescape(re.sub("<[^>]+>", " ", e.get("summary", "")))[:700]
            text = f"{title} {summary}".lower()
            if not src.get("local") and not any(k in text for k in kws):
                continue
            if any(b in text for b in blocked):
                continue
            ts = e.get("published_parsed") or e.get("updated_parsed")
            if ts and time.time() - time.mktime(ts) > max_age:
                if time.time() - time.mktime(ts) < 48 * 3600:
                    velhos.append(title)  # já circulou: serve para reconhecer notícia requentada
                continue
            outlet = (e.get("source") or {}).get("title", "")
            trusted = src["confiavel"] or any(v in outlet.lower() for v in LOCAIS)
            items.append({"key": key_for(title), "title": title, "summary": re.sub(r"\s+", " ", summary).strip(),
                          "link": _unwrap(e.get("link")), "source": outlet or src["nome"], "trusted": trusted,
                          "published": datetime.fromtimestamp(time.mktime(ts), timezone.utc).isoformat() if ts else None})
            n += 1
        print(f"[fonte] {src['nome']}: {len(feed.entries)} itens, {n} de Cascavel")
    uniq = {}
    for i in items:
        uniq.setdefault(i["key"], i)
    fresh = [i for i in uniq.values() if i["key"] not in seen]
    _memoriza(list(uniq.values()), velhos)
    print(f"{len(uniq)} itens do tema, {len(fresh)} novos")
    return fresh


def _memoriza(items: list[dict], velhos: list[str]):
    mem = json.loads(ASSUNTOS.read_text()) if ASSUNTOS.exists() else {}
    now = int(time.time())
    for i in items:
        mem.setdefault(i["key"], {"t": i["title"], "em": now})
    for t in velhos:
        mem.setdefault(key_for(t), {"t": t, "em": now - 24 * 3600})
    mem = {k: v for k, v in mem.items() if now - v["em"] < 3 * 86400}
    ASSUNTOS.parent.mkdir(exist_ok=True)
    ASSUNTOS.write_text(json.dumps(mem, ensure_ascii=False))


def ja_circulou(horas: int = 6) -> list[str]:
    """Manchetes que já estavam rodando há mais de `horas` (nos sites ou nas páginas grandes da cidade)."""
    mem = json.loads(ASSUNTOS.read_text()) if ASSUNTOS.exists() else {}
    now = int(time.time())
    antigos = sorted((v for v in mem.values() if now - v["em"] > horas * 3600), key=lambda v: -v["em"])
    out = [f"(site, há {int((now - v['em']) / 3600)}h) {v['t']}" for v in antigos[:60]]
    try:
        from radar import concorrencia
        out += concorrencia()
    except Exception as e:
        print("[concorrência] não deu para ler:", str(e)[:120])
    return out


def _unwrap(url: str) -> str:
    """Links do Bing Notícias vêm com o endereço real no parâmetro url=."""
    if url and "bing.com" in url:
        from urllib.parse import parse_qs, urlparse
        q = parse_qs(urlparse(url).query)
        if q.get("url"):
            return q["url"][0]
    return url


def resolve(url: str) -> str:
    """Links do Google Notícias escondem o endereço real da matéria: decodifica para chegar no site."""
    url = _unwrap(url)
    if url and "news.google." in url:
        try:
            from googlenewsdecoder import gnewsdecoder
            r = gnewsdecoder(url, interval=1)
            if r.get("status") and r.get("decoded_url"):
                return r["decoded_url"]
        except Exception as e:
            print("[google news] não decodificou:", e)
    return url


def _og_image(url: str) -> str | None:
    try:
        r = requests.get(url, headers=UA, timeout=12)
        m = (re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', r.text)
             or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', r.text))
        return _h.unescape(m.group(1)) if m else None
    except Exception:
        return None


def og_image(url: str) -> str | None:
    """Foto da matéria. Ignora logos e imagens genéricas (viram fundo feio na arte)."""
    url = resolve(url)
    if not url or "news.google." in url:
        return None
    img = _og_image(url)
    if img and not any(b in img.lower() for b in ("google", "logo", "favicon", "placeholder", "default", "padrao", "avatar")):
        return img
    return None


def article_text(url: str) -> str:
    """Texto corrido da matéria (parágrafos e listas)."""
    try:
        url = resolve(url)
        r = requests.get(url, headers=UA, timeout=15)
        page = re.sub(r"(?is)<(script|style|nav|footer|header|aside|form)[^>]*>.*?</\1>", " ", r.text)
        parts = re.findall(r"(?is)<(?:p|li|h2|h3)[^>]*>(.*?)</(?:p|li|h2|h3)>", page)
        txt = [_h.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in parts]
        return "\n".join(t for t in txt if len(t) > 25)
    except Exception:
        return ""


def stock_photo(query: str) -> tuple[str | None, str]:
    """Foto genérica de licença aberta (Openverse, sem chave) quando a notícia não tem foto própria."""
    if not query:
        return None, ""
    try:
        r = requests.get("https://api.openverse.org/v1/images/", headers=UA, timeout=20,
                         params={"q": query, "license_type": "commercial", "page_size": 20, "mature": "false"})
        for it in r.json().get("results", []):
            if (it.get("width") or 0) >= 1000 and (it.get("height") or 0) >= 700 and it.get("url"):
                autor = (it.get("creator") or "").strip()[:40]
                return it["url"], f"Foto ilustrativa: {autor + ' / ' if autor else ''}{(it.get('license') or 'cc').upper()}"
    except Exception as e:
        print("Foto genérica falhou:", e)
    return None, ""


def event_photo(nome: str) -> tuple[str | None, str]:
    """Foto real do evento: procura uma notícia sobre ele (Bing Notícias) e usa a foto da matéria."""
    from urllib.parse import quote_plus
    try:
        feed = _fetch_feed(f"https://www.bing.com/news/search?q={quote_plus(nome + ' Cascavel')}&format=rss&setlang=pt-BR")
        for e in feed.entries[:5]:
            link = _unwrap(e.get("link", ""))
            img = og_image(link) if link else None
            if img:
                from urllib.parse import urlparse
                return img, f"Foto: divulgação/{urlparse(link).netloc.replace('www.', '')}"
    except Exception as ex:
        print("Foto do evento falhou:", nome, ex)
    return None, ""
