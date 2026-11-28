"""Robô do guizo (@guizocascavel) — o que acontece em Cascavel (PR).

  python src/main.py post      -> escolhe a melhor pauta, faz a arte (capa + detalhes + chamada) e publica
  python src/main.py agenda    -> carrossel "O que fazer em Cascavel" do fim de semana
  python src/main.py reel      -> transforma o último post em reel
  python src/main.py story     -> publica o próximo story da fila
  python src/main.py clima     -> story "Bom dia, Cascavel" com a previsão do dia
  python src/main.py comments  -> responde comentários novos
  python src/main.py fontes    -> testa todas as fontes (não publica nada)
  python src/main.py demo      -> artes de exemplo em media/demo

DRY_RUN=1 gera tudo mas não publica (sobe só uma prévia em media/preview).
"""
import json
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from news import collect, load_cfg, mark_seen, og_image  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "state" / "story_queue.json"
HISTORY = ROOT / "state" / "history.json"
REPLIED = ROOT / "state" / "replied.json"
AGENDAS = ROOT / "state" / "agendas.json"
DRY = os.environ.get("DRY_RUN") == "1"
BRT = timezone(timedelta(hours=-3))

CTAS = [
    "📣 Viu algo acontecendo em Cascavel? Manda no direct\n🔁 Compartilha com quem precisa saber\n➕ Segue o @guizocascavel",
    "👇 Conta nos comentários\n📌 Salva pra não esquecer\n➕ Segue o @guizocascavel: o que acontece em Cascavel, todo dia",
    "💬 Comenta o que você acha\n👥 Marca alguém de Cascavel\n📣 Tem novidade no seu bairro? Manda pra gente no direct",
]


def _load(p, default):
    return json.loads(p.read_text()) if p.exists() else default


def _save(p, data):
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False))


def _git(paths, msg):
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    subprocess.run(["git", "config", "user.name", "guizo-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@users.noreply.github.com"], check=True)
    paths = [x for x in paths if (ROOT / x).exists()]  # na 1ª vez a pasta state ainda não existe
    if not paths:
        return
    subprocess.run(["git", "add", *paths], check=True)
    subprocess.run(["git", "commit", "-m", msg], check=False)
    subprocess.run(["git", "pull", "--rebase"], check=False)
    subprocess.run(["git", "push"], check=True)


def _push(msg):
    """Sobe mídias e memória (o Instagram baixa a imagem por URL pública)."""
    if DRY:
        return
    _git(["media", "state"], msg)
    time.sleep(8)


def _preview(files, caption):
    if not os.environ.get("GITHUB_ACTIONS"):
        print("prévia local:", [str(f) for f in files])
        return
    prev = ROOT / "media" / "preview"
    shutil.rmtree(prev, ignore_errors=True)
    prev.mkdir(parents=True)
    for n, f in enumerate(files):
        shutil.copy(f, prev / (f"slide{n + 1}{f.suffix}"))
    (prev / "legenda.txt").write_text(caption, encoding="utf-8")
    _git(["media/preview"], "prévia (teste)")


def _url(path: Path) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "rafael-rsj/brasileiroemvice")
    return f"https://raw.githubusercontent.com/{repo}/main/{path.relative_to(ROOT).as_posix()}"


def _tags(cfg, extra):
    seen, out = set(), []
    for t in cfg["perfil"]["hashtags_fixas"] + [h if h.startswith("#") else "#" + h for h in extra]:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return " ".join(out[:10])


def _stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")


# ------------------------------------------------------------------ post
def _janela():
    """Até quantas horas atrás uma notícia ainda serve: o 1º post da manhã pega o que aconteceu desde as 19h de ontem
    (madrugada incluída); os outros horários só pegam as últimas 8 horas. O que foi, foi."""
    h = datetime.now(BRT).hour
    return (max(h + 5, 6), "primeiro post do dia (bom dia): vale o que aconteceu de ontem à noite, na madrugada e hoje cedo") \
        if h < 10 else (8, f"post das {h}h: vale o que aconteceu hoje, nas últimas horas")


def cmd_post(itens_forcados=None, urgente=None):
    import art
    from writer import pick_and_write, engajamento
    cfg = load_cfg()
    hist = _load(HISTORY, [])
    horas, momento = _janela()
    items = itens_forcados or collect(max_age_h=horas)
    pfile = ROOT / "config" / "pautas.yaml"  # pautas que o dono da página quer ver postadas primeiro
    if pfile.exists() and not itens_forcados:
        import yaml
        feitas = {h.get("pauta") for h in hist}
        for pa in yaml.safe_load(pfile.read_text(encoding="utf-8")) or []:
            if pa.get("id") not in feitas:
                items.insert(0, {"key": f"pauta-{pa['id']}", "title": pa["titulo"], "summary": pa.get("resumo", ""),
                                 "link": pa.get("link", ""), "source": pa.get("fonte", "guizo"), "trusted": True, "pauta": pa["id"]})
                break
    data = pick_and_write(items, [] if urgente == "atualizacao" else [h["titulo"] for h in hist], momento)
    if data and urgente:
        data["urgente"] = urgente
    hoje = datetime.now(BRT).strftime("%Y%m%d")
    if not data and not itens_forcados and not any(h.get("engajamento") and h.get("quando", "").startswith(hoje) for h in hist):
        # sem notícia fresca que preste: post de conversa (debate, POV, complete a frase), no máximo 1 por dia
        data = engajamento([h["titulo"] for h in hist], momento)
        if data:
            data["engajamento"] = True
            print("Sem notícia nova boa: post de engajamento.")
    if not data:
        print("Nada bom para postar agora.")
        mark_seen([i["key"] for i in items])
        return
    img, credit = None, ""
    for u in data["used"]:
        f = og_image(u["link"]) if u.get("link") else None
        if f:
            img, credit = f, f"Foto: {u['source']}"
            break
    if not img and data["tipo"] != "ALERTA" and len(hist) % 2 == 0:  # metade das sem foto ganha foto ilustrativa
        from news import stock_photo
        img, credit = stock_photo(data.get("busca_foto", ""))
    kind = "alert" if data["tipo"] == "ALERTA" else ("photo" if img else "text")
    carrossel = bool(data.get("slide2_texto")) and (len(hist) % 3 != 2)  # 2 de cada 3 em carrossel
    cover = {"photo": lambda: art.cover_photo(data, img, credit, swipe=carrossel),
             "alert": lambda: art.cover_alert(data, swipe=carrossel),
             "text": lambda: art.cover_text(data, swipe=carrossel)}[kind]()
    pages = [cover] + ([art.detail(data), art.cta()] if carrossel else [])
    stamp = _stamp()
    out = ROOT / "media" / stamp[:6] / stamp
    slides = art.shoot(pages, out, "post")
    story = art.shoot([art.story_from(kind, data, img, credit)], out, "story", h=1920)[0]
    fonte = f"\n\n📰 Fonte: {data['fonte_principal']}" if data.get("fonte_principal") else ""
    caption = (f"{data['legenda']}\n\n{CTAS[len(hist) % len(CTAS)]}{fonte}"
               f"\n\n{_tags(cfg, data.get('hashtags', []))}")[:2200]
    print("LEGENDA:\n" + caption)
    if DRY:
        _preview(slides + [story], caption)
        return
    if not urgente:
        q = _load(QUEUE, [])
        q.append({"file": story.relative_to(ROOT).as_posix(), "created": stamp})
        _save(QUEUE, q)
    mark_seen([i["key"] for i in items])
    hist.append({"titulo": data["titulo"], "tipo": data["tipo"], "quando": stamp, "engajamento": bool(data.get("engajamento")), "links": [u.get("link") for u in data["used"]],
                 "pauta": next((u.get("pauta") for u in data["used"] if u.get("pauta")), None),
                 "reel": {"titulo": data["titulo"], "tipo": data["tipo"], "selo": data.get("selo", ""), "onde": data.get("onde", ""),
                          "quando": data.get("quando", ""), "img": img, "credit": credit, "texto": data.get("slide2_texto", ""),
                          "roteiro": data.get("reel_roteiro", ""), "narrar": bool(data.get("reel_narrar", True)),
                          "legenda": caption, "feito": bool(data.get("engajamento"))}})
    _save(HISTORY, hist[-300:])
    _push(f"post {stamp}")
    from instagram import IG
    ig = IG()
    mid = ig.post_carousel([_url(x) for x in slides], caption) if len(slides) > 1 else ig.post_image(_url(slides[0]), caption)
    print("Publicado:", mid)
    page = cfg.get("facebook_page_id")
    if page:
        try:
            import facebook
            fb_txt = (data.get("legenda_facebook") or data["legenda"]) + (f"\n\nFonte: {data['fonte_principal']}" if data.get("fonte_principal") else "") + "\n\nSiga o Guizo Cascavel para saber tudo da cidade."
            print("Facebook:", facebook.publicar(str(page), [_url(x) for x in slides], fb_txt))
        except Exception as e:
            print("Facebook pulado:", e)
    if urgente:
        try:
            print("Story urgente:", ig.post_story(_url(story)))
        except Exception as e:
            print("Story urgente falhou:", e)


# ------------------------------------------------------------------ agenda
def _periodo():
    now = datetime.now(BRT)
    sexta = now + timedelta(days=(4 - now.weekday()) % 7)
    domingo = sexta + timedelta(days=2)
    return f"fim de semana de {sexta.day:02d}/{sexta.month:02d} a {domingo.day:02d}/{domingo.month:02d}", \
        f"{sexta.day} a {domingo.day}/{domingo.month:02d}" if sexta.month == domingo.month else f"{sexta.day}/{sexta.month:02d} a {domingo.day}/{domingo.month:02d}"


def cmd_agenda():
    import art
    from events import read_sources
    from writer import write_agenda
    cfg = load_cfg()
    hist = _load(AGENDAS, [])
    periodo_ia, periodo_arte = _periodo()
    srcs = read_sources()
    a = write_agenda(srcs, periodo_ia, [h["titulo"] for h in hist])
    if not a:
        print("Poucos eventos confiáveis para montar a agenda.")
        return
    evs = a["eventos"][:8]
    pages = [art.agenda_cover(a, periodo_arte)] + [art.agenda_item(e, i + 2, len(evs) + 2) for i, e in enumerate(evs)] + [art.cta()]
    stamp = _stamp()
    out = ROOT / "media" / stamp[:6] / f"{stamp}-agenda"
    slides = art.shoot(pages, out, "agenda")
    caption = f"{a['legenda']}\n\n{_tags(cfg, a.get('hashtags', []) + ['agendacascavel', 'oquefazeremcascavel'])}"[:2200]
    print("LEGENDA:\n" + caption)
    if DRY:
        _preview(slides, caption)
        return
    hist.append({"titulo": periodo_ia, "quando": stamp, "eventos": [e["nome"] for e in evs]})
    _save(AGENDAS, hist[-100:])
    _push(f"agenda {stamp}")
    from instagram import IG
    print("Agenda publicada:", IG().post_carousel([_url(x) for x in slides], caption))


# ------------------------------------------------------------------ reel / story / clima
def cmd_reel():
    from reel import make_reel
    hist = _load(HISTORY, [])
    pend = [h for h in hist if h.get("reel") and not h["reel"].get("feito")]
    if not pend:
        print("Nenhum post novo para virar reel.")
        return
    h = pend[-1]
    r = dict(h["reel"])
    narrar = r.get("narrar", True) if random.random() > 0.2 else not r.get("narrar", True)
    out = ROOT / "media" / "reels" / f"{h['quando']}.mp4"
    make_reel(r, out, narrar=narrar, seed=len(hist) * 7 + 3)
    if DRY:
        _preview([out], r.get("legenda", ""))
        return
    h["reel"]["feito"] = True
    _save(HISTORY, hist)
    from instagram import IG
    print("Reel publicado:", IG().post_reel_file(out, r.get("legenda", h["titulo"])))
    out.unlink(missing_ok=True)
    _push("reel publicado")


def cmd_story():
    q = _load(QUEUE, [])
    if not q:
        print("Fila de stories vazia.")
        return
    item = q.pop(0)
    if DRY:
        print("DRY_RUN story:", item)
        return
    _save(QUEUE, q)
    _push("story publicado")
    from instagram import IG
    print("Story publicado:", IG().post_story(_url(ROOT / item["file"])))


def cmd_clima():
    """07:10. Segunda: stories "A semana em Cascavel". Todo dia: story do tempo só se o clima fugir do normal."""
    import art
    from weather import today
    if datetime.now(BRT).weekday() == 0:
        try:
            cmd_semana()
        except Exception as e:  # a agenda não pode derrubar o clima
            print("Semana falhou:", e)
    w = today()
    print("Clima:", w)
    if not w.get("extremo") and not os.environ.get("FORCAR_CLIMA"):
        print("Tempo normal hoje: sem story de clima.")
        return
    stamp = _stamp()
    f = art.shoot([art.story_weather(w)], ROOT / "media" / stamp[:6] / f"{stamp}-clima", "clima", h=1920)[0]
    if DRY:
        _preview([f], json.dumps(w, ensure_ascii=False))
        return
    _push(f"clima {stamp}")
    from instagram import IG
    print("Story do clima publicado:", IG().post_story(_url(f)))


DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _semana():
    now = datetime.now(BRT)
    seg = now - timedelta(days=now.weekday())
    dom = seg + timedelta(days=6)
    return (f"semana de segunda {seg.day:02d}/{seg.month:02d} a domingo {dom.day:02d}/{dom.month:02d}",
            f"{seg.day:02d}/{seg.month:02d} a {dom.day:02d}/{dom.month:02d}")


PLANTAO = ROOT / "state" / "plantao.json"


def cmd_plantao():
    """De hora em hora (6h–23h): se acontecer algo urgente, posta na hora, fora da grade (com limite por dia)."""
    from writer import plantao
    agora = datetime.now(BRT)
    if agora.hour < 6 or agora.hour > 23:
        return
    st = _load(PLANTAO, {"vistos": [], "dia": "", "hoje": 0})
    if st.get("dia") != agora.strftime("%Y-%m-%d"):
        st.update(dia=agora.strftime("%Y-%m-%d"), hoje=0)
    items = [i for i in collect(max_age_h=4) if i["key"] not in st["vistos"]]
    st["vistos"] = (st["vistos"] + [i["key"] for i in items])[-1500:]
    _save(PLANTAO, st)
    if not items or st["hoje"] >= load_cfg().get("plantao_limite_dia", 3):
        print("Plantão: nada novo." if not items else "Plantão: limite do dia atingido.")
        return
    hist = _load(HISTORY, [])
    hoje = [f"{h['quando'][9:11]}:{h['quando'][11:13]} UTC — {h['titulo']}" for h in hist
            if h.get("quando", "").startswith(datetime.now(timezone.utc).strftime("%Y%m%d"))]
    r = plantao(items, hoje)
    print("Plantão:", r)
    if not r.get("urgente"):
        return
    sel = [items[i] for i in r.get("indices", []) if 0 <= i < len(items)]
    if not sel:
        return
    st["hoje"] += 1
    _save(PLANTAO, st)
    cmd_post(itens_forcados=sel, urgente=r.get("modo", "novo"))


def cmd_hoje():
    """Sábado e domingo de manhã: o que tem pra fazer HOJE em Cascavel, em stories."""
    cmd_semana(hoje=True)


def cmd_semana(hoje=False):
    """Segunda de manhã: o que vai ter na semana, em stories (fica no destaque A SEMANA, que você fixa na mão)."""
    import art
    from events import read_sources
    from writer import write_agenda
    hist = _load(AGENDAS, [])
    periodo_ia, periodo_arte = _semana()
    if hoje:
        d = datetime.now(BRT)
        periodo_ia = f"hoje, {DIAS_PT[d.weekday()]} {d.day:02d}/{d.month:02d} (só eventos de hoje, inclusive à noite)"
        periodo_arte = f"{DIAS_PT[d.weekday()]}, {d.day:02d}/{d.month:02d}"
    a = write_agenda(read_sources(), periodo_ia, [h["titulo"] for h in hist])
    if not a:
        print("Poucos eventos confiáveis para a semana.")
        return
    evs = a["eventos"][:7]
    from news import event_photo
    for e in evs:
        if not e.get("img"):
            e["img"], e["credito"] = event_photo(e["nome"])
    pages = [art.story_semana_cover(periodo_arte, evs, "Hoje em" if hoje else "A semana em")] + [art.story_semana_item(e, i + 1, len(evs)) for i, e in enumerate(evs)]
    stamp = _stamp()
    files = art.shoot(pages, ROOT / "media" / stamp[:6] / f"{stamp}-semana", "semana", h=1920)
    if DRY:
        _preview(files, json.dumps(evs, ensure_ascii=False)[:2000])
        return
    hist.append({"titulo": periodo_ia, "quando": stamp, "eventos": [e["nome"] for e in evs]})
    _save(AGENDAS, hist[-100:])
    _push(f"semana {stamp}")
    from instagram import IG
    ig = IG()
    for f in files:
        print("Story da semana:", ig.post_story(_url(f)))
        time.sleep(20)


def cmd_comments():
    from instagram import IG
    from writer import reply_comment
    ig = IG()
    done = set(_load(REPLIED, []))
    me = load_cfg()["perfil"]["usuario"]
    budget = 15
    for m in ig.recent_media(limit=6):
        for c in ig.comments(m["id"]):
            if budget <= 0:
                break
            if c["id"] in done or c.get("username") == me:
                continue
            if any(r.get("username") == me for r in c.get("replies", {}).get("data", [])):
                done.add(c["id"])
                continue
            txt = reply_comment(m.get("caption", ""), c.get("text", ""))
            done.add(c["id"])
            if txt and not DRY:
                ig.reply(c["id"], txt)
                budget -= 1
                time.sleep(20)
            print(f"@{c.get('username')}: {c.get('text')!r} -> {txt!r}")
    _save(REPLIED, list(done)[-5000:])
    import radar
    if radar.ativo():
        for f in (radar.inbox, radar.ig_inbox, radar.radar):
            try:
                print(f.__name__, "->", f())
            except Exception as e:
                print(f.__name__, "falhou:", e)
    _git(["state", "config/pautas.yaml"], "comentários e telegram")


# ------------------------------------------------------------------ testes
def cmd_fontes():
    """Testa cada fonte e mostra o que veio (sem gastar IA e sem publicar)."""
    items = collect(max_age_h=72)
    for i in items[:40]:
        print(f"- ({i['source']}) {i['title']}")
    from events import read_sources
    for s in read_sources():
        print(f"\n### {s['fonte']}: {len(s['texto'])} caracteres\n{s['texto'][:600]}")


def cmd_lancamento():
    """Publica o post e o story de lançamento (uma vez só)."""
    import art
    from lancamento import LEGENDA, launch
    stamp = _stamp()
    out = ROOT / "media" / stamp[:6] / f"{stamp}-lancamento"
    post = art.shoot([launch(1350)], out, "post")[0]
    story = art.shoot([launch(1920)], out, "story", h=1920)[0]
    if DRY:
        _preview([post, story], LEGENDA)
        return
    _push(f"lancamento {stamp}")
    from instagram import IG
    ig = IG()
    print("Post de lançamento:", ig.post_image(_url(post), LEGENDA))
    time.sleep(30)
    print("Story de lançamento:", ig.post_story(_url(story)))


def cmd_fblancamento():
    """Publica na Página do Facebook a arte de lançamento já usada no Instagram (uma vez só)."""
    import facebook
    from lancamento import LEGENDA_FB
    feito = ROOT / "state" / "fb_lancamento.txt"
    if feito.exists():
        print("Lançamento já publicado no Facebook:", feito.read_text())
        return
    arte = sorted(ROOT.glob("media/*/*-lancamento/post_01.jpg"))[-1]
    page = str(load_cfg().get("facebook_page_id", ""))
    if DRY:
        print("Publicaria no Facebook:", _url(arte), "\n", LEGENDA_FB)
        return
    pid = facebook.publicar(page, [_url(arte)], LEGENDA_FB)
    print("Facebook lançamento:", pid)
    feito.parent.mkdir(exist_ok=True)
    feito.write_text(pid)
    _git(["state"], "facebook: lançamento publicado")


def cmd_fbteste():
    """Só confere se o robô consegue falar com a Página do Facebook (não publica nada)."""
    import facebook
    page = str(load_cfg().get("facebook_page_id", ""))
    try:
        facebook._page_token(page)
        print("Facebook OK: o robô tem acesso à Página", page)
    except Exception as e:
        print("Facebook SEM acesso:", e)


def cmd_demo():
    import art
    d = {"tipo": "NOVIDADE", "selo": "NOVIDADE NA CIDADE", "titulo": "Abriu o primeiro *bar no terraço* do Centro",
         "subtitulo": "Vista para a Avenida Brasil e música ao vivo de quarta a domingo.", "onde": "Rua Paraná, 2000",
         "quando": "qua a dom, 18h", "slide2_texto": "O espaço fica no 12º andar e tem capacidade para 200 pessoas.",
         "fonte_principal": "Exemplo", "dados": [{"rotulo": "LIMITE", "valor": "50 km/h"}, {"rotulo": "VALE DESDE", "valor": "hoje"}]}
    alert = dict(d, tipo="ALERTA", selo="RADAR NOVO", titulo="Radar *novo* na Av. Brasil", onde="Av. Brasil x R. Pres. Bernardes")
    pages = [art.cover_text(d, swipe=True), art.cover_alert(alert), art.detail(d), art.cta()]
    print(art.shoot(pages, ROOT / "media" / "demo", "demo"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    ig = [] if DRY else ["IG_ACCESS_TOKEN", "IG_USER_ID"]
    needs = {"post": ["ANTHROPIC_API_KEY"] + ig, "agenda": ["ANTHROPIC_API_KEY"] + ig, "reel": ig, "story": ig,
             "clima": ["ANTHROPIC_API_KEY"] + ig, "semana": ["ANTHROPIC_API_KEY"] + ig, "hoje": ["ANTHROPIC_API_KEY"] + ig, "plantao": ["ANTHROPIC_API_KEY"] + ig, "lancamento": ig, "comments": ["ANTHROPIC_API_KEY", "IG_ACCESS_TOKEN", "IG_USER_ID"]}
    if not DRY and cmd not in ("fontes", "demo", "lancamento", "fbteste", "fblancamento") and not load_cfg().get("ativo", False):
        print("Robô pausado (ativo: false em config/settings.yaml). Nada foi publicado.")
        sys.exit(0)
    missing = [k for k in needs.get(cmd, []) if not os.environ.get(k)]
    if missing:
        print(f"Aguardando configuração: faltam os secrets {missing}. Nada foi feito.")
        sys.exit(0)
    # Feed não leva agenda (é temporária): o horário da quinta vira post normal; a agenda sai em stories na segunda.
    {"post": cmd_post, "agenda": cmd_post, "semana": cmd_semana, "hoje": cmd_hoje, "plantao": cmd_plantao, "reel": cmd_reel, "story": cmd_story, "clima": cmd_clima,
     "comments": cmd_comments, "lancamento": cmd_lancamento, "fbteste": cmd_fbteste, "fblancamento": cmd_fblancamento, "fontes": cmd_fontes, "demo": cmd_demo}[cmd]()
