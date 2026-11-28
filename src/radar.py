"""Telegram do guizo: recebe as pautas que o dono manda e envia comentários prontos para posts em alta.

- Pautas: o Rafael compartilha um link, print ou texto com o @guizoo_bot. De hora em hora o robô lê,
  a IA decide se vale post e, se valer, entra na fila (config/pautas.yaml) do próximo post do feed.
- Radar: de hora em hora o robô olha os posts recentes (menos de 6 h) de perfis grandes de Cascavel,
  separa os que estão bombando e manda no Telegram o link + um comentário pronto para colar.
"""
import html
import json
import os
import re
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "telegram.json"
RADAR = ROOT / "state" / "radar.json"
PAUTAS = ROOT / "config" / "pautas.yaml"
BRT = timezone(timedelta(hours=-3))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"}


def _load(p, d):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return d


def _save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def ativo() -> bool:
    return bool(os.environ.get("TELEGRAM_TOKEN", "").strip())


def tg(method, **data):
    tok = os.environ["TELEGRAM_TOKEN"].strip()
    r = requests.post(f"https://api.telegram.org/bot{tok}/{method}", data=data, timeout=30)
    j = r.json()
    if not j.get("ok"):
        print("[telegram]", method, j)
    return j.get("result")


def send(text, preview=False):
    st = _load(STATE, {})
    if not st.get("chat_id"):
        print("[telegram] ainda sem chat: mande /start para o bot")
        return
    tg("sendMessage", chat_id=st["chat_id"], text=text[:4000], disable_web_page_preview="false" if preview else "true")


# ------------------------------------------------------------------ pautas
def _page_info(url: str) -> dict:
    """Título, descrição e texto de um link (matéria, post ou reel público)."""
    out = {"link": url, "titulo": "", "texto": ""}
    try:
        r = requests.get(url, headers=UA, timeout=20)
        page = r.text
        def meta(p):
            m = re.search(rf'<meta[^>]+(?:property|name)=["\']{p}["\'][^>]+content=["\']([^"\']+)', page, re.I) or \
                re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{p}["\']', page, re.I)
            return html.unescape(m.group(1)) if m else ""
        out["titulo"] = meta("og:title") or (re.search(r"<title>(.*?)</title>", page, re.S | re.I) or [None, ""])[1]
        desc = meta("og:description") or meta("description")
        from news import article_text
        corpo = article_text(url) if "instagram.com" not in url and "tiktok.com" not in url else ""
        out["texto"] = (desc + "\n" + corpo)[:3500]
        out["img"] = meta("og:image")
    except Exception as e:
        print("[pauta] não abriu", url, e)
    return out


def inbox():
    """Lê o que chegou no bot e transforma em pauta (ou descarta com o motivo)."""
    from writer import avaliar_pauta
    st = _load(STATE, {})
    ups = tg("getUpdates", offset=st.get("offset", 0), timeout=0) or []
    novas = 0
    for u in ups:
        st["offset"] = u["update_id"] + 1
        m = u.get("message") or u.get("channel_post")
        if not m:
            continue
        chat = m["chat"]["id"]
        if not st.get("chat_id"):
            st["chat_id"] = chat  # o primeiro a mandar /start vira o dono
            _save(STATE, st)
            send("Pronto! O guizo vai te mandar aqui os comentários prontos e você pode me mandar pautas (link, print ou texto).")
        if chat != st["chat_id"]:
            continue
        texto = (m.get("text") or m.get("caption") or "").strip()
        if texto.startswith("/start"):
            continue
        if _processa(texto, f"tg{u['update_id']}", "Telegram"):
            novas += 1
    _save(STATE, st)
    return novas


def _processa(texto: str, pid: str, canal: str) -> bool:
    """Lê o material (texto + links), a IA decide se vale e, se valer, põe na fila do próximo post."""
    from writer import avaliar_pauta
    links = re.findall(r"https?://\S+", texto)
    material = texto
    for l in links[:2]:
        info = _page_info(l)
        material += f"\n\n[link {l}]\n{info['titulo']}\n{info['texto']}"
    if not material.strip():
        send(f"Recebi pelo {canal}, mas não consegui ler nada. Manda o link ou um texto junto 🙏")
        return False
    r = avaliar_pauta(material)
    if not r.get("vale"):
        send(f"[{canal}] Essa eu deixei passar: {r.get('motivo', 'não rendeu post')}.")
        return False
    fila = (yaml.safe_load(PAUTAS.read_text(encoding="utf-8")) if PAUTAS.exists() else []) or []
    fila.append({"id": pid, "titulo": r["titulo"], "resumo": r["resumo"], "link": links[0] if links else "",
                 "fonte": r.get("fonte") or "leitor do guizo"})
    PAUTAS.write_text(yaml.safe_dump(fila[-30:], allow_unicode=True, sort_keys=False), encoding="utf-8")
    send(f"[{canal}] Boa! Entrou na fila: \"{r['titulo']}\". Sai no próximo post do feed (11h40 ou 17h20).")
    return True


def ig_inbox():
    """Lê o direct do guizo com o dono (perfil em `dono_instagram`): reels, posts e links que ele mandar viram pauta."""
    from instagram import IG
    cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    dono = (cfg.get("dono_instagram") or "").lower()
    if not dono:
        return 0
    ig = IG()
    st = _load(STATE, {})
    vistos = set(st.get("ig_vistos", []))
    try:
        conv = ig._get(f"{ig.user}/conversations", platform="instagram",
                       fields="participants,messages.limit(15){id,message,from,created_time,attachments,shares}")["data"]
    except Exception as e:
        print("[direct] sem acesso às mensagens:", str(e)[:200])
        return 0
    novas = 0
    for c in conv:
        nomes = [p.get("username", "").lower() for p in c.get("participants", {}).get("data", [])]
        if dono not in nomes:
            continue
        for m in reversed(c.get("messages", {}).get("data", [])):
            if m["id"] in vistos or (m.get("from", {}).get("username", "").lower() != dono):
                continue
            vistos.add(m["id"])
            partes = [m.get("message") or ""]
            for a in (m.get("attachments", {}) or {}).get("data", []):
                for k in ("video_data", "image_data", "generic_template", "share"):
                    v = a.get(k) or {}
                    partes += [str(v.get(x, "")) for x in ("url", "link", "title", "subtitle") if v.get(x)]
            for sh in (m.get("shares", {}) or {}).get("data", []):
                partes += [sh.get("link", ""), sh.get("description", ""), sh.get("name", "")]
            texto = " ".join(x for x in partes if x).strip()
            if texto and _processa(texto, f"ig{m['id'][-12:]}", "direct"):
                novas += 1
    st["ig_vistos"] = list(vistos)[-500:]
    _save(STATE, st)
    return novas


# ------------------------------------------------------------------ radar
def _discovery(username):
    from instagram import IG
    ig = IG()
    f = ("business_discovery.username(%s){username,followers_count,media.limit(10)"
         "{caption,like_count,comments_count,timestamp,permalink,media_type,media_url,thumbnail_url}}" % username)
    return ig._get(ig.user, fields=f)["business_discovery"]


def concorrencia(horas=36):
    """O que as páginas grandes de notícia de Cascavel já postaram (para não requentar o que todo mundo já viu)."""
    cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    perfis = cfg.get("concorrentes", ["noticiascascavel", "cascavelemfatos", "cascavel.spotted", "rolezandocascavel", "cascavel_prefa"])
    agora = datetime.now(timezone.utc)
    out = []
    for p in perfis:
        try:
            d = _discovery(p)
        except Exception as e:
            print("[concorrência] pulei", p, str(e)[:100])
            continue
        for m in d.get("media", {}).get("data", []):
            ts = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            h = (agora - ts).total_seconds() / 3600
            if h <= horas and m.get("caption"):
                out.append(f"(@{p}, há {int(h)}h) " + " ".join(m["caption"].split())[:160])
    return out


def radar(max_envios=4):
    from writer import comentario_para
    hora = datetime.now(BRT).hour
    if hora < 7 or hora > 23:
        return 0
    cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    perfis = cfg.get("radar_perfis", [])
    st = _load(RADAR, {"enviados": [], "dia": "", "hoje": 0})
    hoje = datetime.now(BRT).strftime("%Y-%m-%d")
    if st.get("dia") != hoje:
        st.update(dia=hoje, hoje=0)
    limite = cfg.get("radar_limite_dia", 25)
    agora = datetime.now(timezone.utc)
    cand = []
    for p in perfis:
        try:
            d = _discovery(p)
        except Exception as e:
            print("[radar] pulei", p, str(e)[:120])
            continue
        media = d.get("media", {}).get("data", [])
        engs = [(x.get("like_count") or 0) + 3 * (x.get("comments_count") or 0) for x in media]
        med = statistics.median(engs) if engs else 0
        for x, e in zip(media, engs):
            ts = datetime.strptime(x["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            horas = (agora - ts).total_seconds() / 3600
            if horas > 6 or x["permalink"] in st["enviados"]:
                continue
            ritmo = e / max(horas, 0.5)            # engajamento por hora
            base = max(med, 20) / 6
            if ritmo >= base * 1.3 or e >= med * 1.2:
                cand.append((ritmo, p, horas, x))
    cand.sort(key=lambda c: c[0], reverse=True)
    n = 0
    for ritmo, p, horas, x in cand:
        if n >= max_envios or st["hoje"] >= limite:
            break
        img = x.get("media_url") if x.get("media_type") != "VIDEO" else x.get("thumbnail_url")
        com = comentario_para(p, x.get("caption", ""), img)
        st["enviados"].append(x["permalink"])
        if not com:
            continue
        send(f"🔥 @{p} · há {horas:.0f}h · ❤️ {x.get('like_count', 0)} 💬 {x.get('comments_count', 0)}\n{x['permalink']}",
             preview=True)
        send(com)  # mensagem separada: segura e copia
        st["hoje"] += 1
        n += 1
    st["enviados"] = st["enviados"][-800:]
    _save(RADAR, st)
    return n
