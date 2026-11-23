"""Ponto de entrada do robô do Brasileiro em Vice.

Uso:
  python src/main.py post       -> busca notícia, gera arte e publica no feed (+ guarda story na fila)
  python src/main.py story      -> publica o próximo story da fila
  python src/main.py comments   -> responde comentários novos nos posts recentes
  python src/main.py refresh    -> renova o token do Instagram (imprime o novo)
  python src/main.py demo       -> só gera artes de exemplo em media/demo (não publica)

DRY_RUN=1 gera tudo mas não publica nada.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from news import collect, mark_seen, og_image, load_cfg  # noqa: E402
from render import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "state" / "story_queue.json"
HISTORY = ROOT / "state" / "history.json"
REPLIED = ROOT / "state" / "replied.json"
DRY = os.environ.get("DRY_RUN") == "1"


def _load(p, default):
    return json.loads(p.read_text()) if p.exists() else default


def _save(p, data):
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False))


def _git_push(msg):
    """Sobe as mídias para o repositório (o Instagram baixa a imagem por URL pública)."""
    if DRY or not os.environ.get("GITHUB_ACTIONS"):
        return
    subprocess.run(["git", "config", "user.name", "brasileiroemvice-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", "media", "state"], check=True)
    subprocess.run(["git", "commit", "-m", msg], check=False)
    subprocess.run(["git", "pull", "--rebase"], check=False)
    subprocess.run(["git", "push"], check=True)
    time.sleep(8)  # tempo para o raw.githubusercontent atualizar


def _preview(files, caption):
    """No modo teste, sobe só uma prévia (media/preview) para conferir a arte, sem salvar memória nem publicar."""
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    import shutil
    prev = ROOT / "media" / "preview"
    prev.mkdir(parents=True, exist_ok=True)
    for f in prev.glob("*.jpg"):
        f.unlink()
    for n, f in enumerate(files):
        shutil.copy(f, prev / ("story.jpg" if "story" in f.name else f"slide{n+1}.jpg"))
    (prev / "legenda.txt").write_text(caption, encoding="utf-8")
    subprocess.run(["git", "config", "user.name", "brasileiroemvice-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", "media/preview"], check=True)
    subprocess.run(["git", "commit", "-m", "prévia (teste)"], check=False)
    subprocess.run(["git", "pull", "--rebase"], check=False)
    subprocess.run(["git", "push"], check=True)


def _public_url(path: Path) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "SEU_USUARIO/brasileiroemvice")
    rel = path.relative_to(ROOT).as_posix()
    return f"https://raw.githubusercontent.com/{repo}/main/{rel}"


CTAS = [
    ["💬 Comenta o que você achou", "📌 Salva pra não perder", "🔁 Manda pro parça que joga junto", "➕ Segue @brasileiroemvice pra mais GTA 6 todo dia"],
    ["👇 Deixa sua opinião aqui embaixo", "📌 Salva esse post", "👥 Marca quem vai querer saber disso", "🔔 Segue @brasileiroemvice e ativa as notificações"],
    ["💬 Responde aí nos comentários", "🔁 Compartilha com quem tá esperando o GTA 6", "📌 Salva pra consultar depois", "➕ Segue @brasileiroemvice: notícia, segredo e dica todo dia"],
]


def _tags(cfg, extra, more=()):
    all_tags = cfg["perfil"]["hashtags_fixas"] + list(more) + [h if h.startswith("#") else "#" + h for h in extra]
    seen_t, uniq = set(), []
    for t in all_tags:
        if t.lower() not in seen_t:
            seen_t.add(t.lower())
            uniq.append(t)
    return " ".join(uniq[:12])


def _cta(seed):
    return "\n".join(CTAS[seed % len(CTAS)])


def _caption(data, cfg, seed=0):
    src = data.get("fonte_principal", "")
    rumor = "\n⚠️ Rumor, ainda não confirmado pela Rockstar." if data["tag"] == "RUMOR" else ""
    return f"{data['legenda']}{rumor}\n\n{_cta(seed)}\n\n📰 Fonte: {src}\n\n{_tags(cfg, data.get('hashtags', []))}"[:2200]


def cmd_post():
    from writer import pick_and_write
    cfg = load_cfg()
    hist = _load(HISTORY, [])
    items = collect()
    # pautas sugeridas pelo dono da página (config/pautas.yaml) entram na frente
    pfile = ROOT / "config" / "pautas.yaml"
    if pfile.exists():
        import yaml
        pautas = yaml.safe_load(pfile.read_text(encoding="utf-8")) or []
        feitas = {h.get("pauta") for h in hist}
        for pa in pautas:
            if pa.get("id") not in feitas:
                items.insert(0, {"key": "pauta-" + str(pa["id"]), "title": pa["titulo"], "summary": pa.get("resumo", ""),
                                 "link": pa.get("link", ""), "source": pa.get("fonte", ""), "trusted": True,
                                 "pauta": pa["id"], "published": None})
                break
    data = pick_and_write(items, [h["titulo"] for h in hist])
    if not data:
        print("Nada relevante agora. Pulando este horário.")
        mark_seen([i["key"] for i in items])
        return
    img, credit = None, ""
    from gallery import pick
    tipo = data.get("imagem", "jogo")

    def foto_materia():
        for u in data["used"]:
            f = og_image(u["link"])
            if f:
                return f, u["source"]
        return None, ""
    if tipo in ("hardware", "misto"):
        # assunto é console/PC: a capa mostra o aparelho (foto da matéria); o 2º slide mistura com o jogo
        img, src = foto_materia()
        credit = f"IMAGEM: {src.upper()}" if img else ""
    if not img:
        # cena oficial do jogo que combine com o assunto; se não tiver, foto da matéria
        g = pick(data["titulo"] + " " + data.get("subtitulo", ""), seed=len(hist))
        if g:
            img, credit = g.as_uri(), "IMAGEM: ROCKSTAR GAMES"
        else:
            img, src = foto_materia()
            credit = f"IMAGEM: {src.upper()}" if img else ""
    # 3) sem foto: o render usa um cenário ilustrado próprio
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    base = ROOT / "media" / stamp[:6] / stamp
    common = dict(title=data["titulo"], sub=data.get("subtitulo", ""), tag=data["tag"],
                  source=data.get("fonte_principal", ""), image_url=img, stars=int(data.get("estrelas", 3)),
                  seed=len(hist))  # cada post novo gira cenário, paleta e layout
    # --- carrossel: capa + detalhes + siga ---
    cover_layout = "l-center" if img else None
    carrossel = len(hist) % 2 == 0  # metade dos posts em carrossel, metade em imagem única
    feed = render(base.with_name(stamp + "-feed"), fmt="feed", layout=cover_layout, credit=credit,
                  swipe="ARRASTA PRO LADO" if carrossel else "", **common)
    slides = [feed]
    if carrossel and data.get("slide2_texto"):
        from mascot import mascot_html
        rot, val = data.get("slide2_rotulo", "").strip(), data.get("slide2_valor", "").strip()
        t2 = f"{rot} *{val}*" if val else (rot or "Entenda:")
        g2 = pick(data["titulo"], seed=len(hist) + 1, avoid={Path(img).name} if img else None)
        img2, credit2 = (g2.as_uri(), "IMAGEM: ROCKSTAR GAMES") if g2 else (img, credit)
        tio = data.get("comentario_tio", "").strip()
        extra, lay = "", "l-detail"
        if tio:
            import html as _h
            expr = ["surpreso", "pensando", "rindo", "joinha", "piscada"][len(hist) % 5]
            extra = (f'<div class="tio">{mascot_html(expr, 420)}</div>'
                     f'<div class="bubble"><b>TIO VICE COMENTA</b>{_h.escape(tio)}</div>')
            lay = "l-detail has-tio"
        d = dict(common, title=t2, sub=data["slide2_texto"], image_url=img2)
        slides.append(render(base.with_name(stamp + "-2"), fmt="feed", layout=lay, extra=extra,
                             sign="Brasileiro em Vice", credit=credit2, **d))
    if carrossel:
        from guide import cta_page, shot
        g3 = pick("leonida", seed=len(hist) + 2)
        slides += shot([cta_page("#ffc145", len(slides) + 1, len(slides) + 1, bg=g3.as_uri() if g3 else None)],
                       base.parent / (stamp + "-cta"), "cta")
    story = render(base.with_name(stamp + "-story"), fmt="story", kicker="NOVO POST NO FEED",
                   live="VEJA NO FEED", **common)
    caption = _caption(data, cfg, len(hist))
    q = _load(QUEUE, [])
    q.append({"file": story.relative_to(ROOT).as_posix(), "created": stamp})
    _save(QUEUE, q)
    mark_seen([i["key"] for i in items])
    img_ref = img
    if img and img.startswith("file:"):
        img_ref = Path(img.replace("file://", "")).relative_to(ROOT).as_posix()
    hist.append({"titulo": data["titulo"], "tag": data["tag"], "quando": stamp,
                 "links": [u["link"] for u in data["used"]],
                 "pauta": next((u.get("pauta") for u in data["used"] if u.get("pauta")), None),
                 "reel": {"titulo": data["titulo"], "tag": data["tag"], "fonte": data.get("fonte_principal", ""),
                          "img": img_ref, "credit": credit, "rotulo": data.get("slide2_rotulo", ""),
                          "valor": data.get("slide2_valor", ""), "texto": data.get("slide2_texto", "") or data.get("subtitulo", ""),
                          "roteiro": data.get("reel_roteiro", ""), "narrar": bool(data.get("reel_narrar", True)),
                          "legenda": caption, "feito": False}})
    _save(HISTORY, hist[-200:])
    print("LEGENDA:\n" + caption)
    _git_push(f"post {stamp}")
    if DRY:
        _preview(slides + [story], caption)
        print("DRY_RUN: não publicado", feed)
        return
    from instagram import IG
    ig = IG()
    if len(slides) > 1:
        mid = ig.post_carousel([_public_url(x) for x in slides], caption)
    else:
        mid = ig.post_image(_public_url(feed), caption)
    print("Publicado no feed:", mid)


def cmd_story():
    q = _load(QUEUE, [])
    if not q:
        print("Fila de stories vazia.")
        return
    item = q.pop(0)
    _save(QUEUE, q)
    path = ROOT / item["file"]
    _git_push("story publicado")
    if DRY:
        print("DRY_RUN story:", path)
        return
    from instagram import IG
    print("Story publicado:", IG().post_story(_public_url(path)))


def cmd_comments():
    from instagram import IG
    from writer import reply_comment
    ig = IG()
    done = set(_load(REPLIED, []))
    me = load_cfg()["perfil"]["usuario"]
    budget = 15  # máximo de respostas por execução (evita parecer spam)
    for m in ig.recent_media(limit=6):
        for c in ig.comments(m["id"]):
            if budget <= 0:
                break
            if c["id"] in done or c.get("username") == me:
                continue
            replies = c.get("replies", {}).get("data", [])
            if any(r.get("username") == me for r in replies):
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
    _git_push("comentários")


def cmd_reel():
    """Transforma a notícia mais recente (ainda sem reel) em um reel animado e publica."""
    import random
    from reel import make_reel
    hist = _load(HISTORY, [])
    pend = [h for h in hist if h.get("reel") and not h["reel"].get("feito")]
    if not pend:
        print("Nenhuma notícia nova para virar reel.")
        return
    h = pend[-1]
    r = dict(h["reel"])
    if r.get("img") and not r["img"].startswith("http"):
        r["img"] = (ROOT / r["img"]).as_uri()
    # narração: segue a sugestão da IA na maioria das vezes, mas varia de vez em quando
    narrar = r.get("narrar", True)
    if random.random() < 0.2:
        narrar = not narrar
    seed = len(hist) * 7 + 3
    out = ROOT / "media" / "reels" / f"{h['quando']}.mp4"
    make_reel(r, out, narrar=narrar, seed=seed)
    h["reel"]["feito"] = True
    _save(HISTORY, hist)
    caption = r.get("legenda", h["titulo"])
    if DRY:
        if os.environ.get("GITHUB_ACTIONS"):
            import shutil
            prev = ROOT / "media" / "preview"
            prev.mkdir(parents=True, exist_ok=True)
            shutil.copy(out, prev / "reel.mp4")
            subprocess.run(["git", "config", "user.name", "brasileiroemvice-bot"], check=True)
            subprocess.run(["git", "config", "user.email", "bot@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", "media/preview/reel.mp4"], check=True)
            subprocess.run(["git", "commit", "-m", "prévia do reel (teste)"], check=False)
            subprocess.run(["git", "pull", "--rebase"], check=False)
            subprocess.run(["git", "push"], check=True)
        print("DRY_RUN reel:", out, "narrado:", narrar)
        return
    from instagram import IG
    print("Reel publicado:", IG().post_reel_file(out, caption))
    out.unlink(missing_ok=True)  # não guarda vídeo no repositório
    _git_push("reel publicado")


def cmd_dicas():
    """Carrossel de dicas do Tio Vice."""
    from tips import render_tips
    from writer import write_tips
    cfg = load_cfg()
    hist = _load(ROOT / "state" / "dicas.json", [])
    data = write_tips([h["titulo"] for h in hist], seed=len(hist))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    slides = render_tips(data, ROOT / "media" / stamp[:6] / f"{stamp}-dicas", seed=len(hist))
    caption = f"{data['legenda']}\n\n{_cta(len(hist) + 1)}\n\n{_tags(cfg, data.get('hashtags', []), ['#TioVice'])}"[:2200]
    hist.append({"titulo": data["titulo"], "publico": data.get("publico"), "quando": stamp})
    _save(ROOT / "state" / "dicas.json", hist[-200:])
    print("DICAS:", data["titulo"], "| público:", data.get("publico"))
    if DRY:
        _preview(slides, caption)
        return
    _git_push(f"dicas {stamp}")
    from instagram import IG
    print("Carrossel de dicas publicado:", IG().post_carousel([_public_url(x) for x in slides], caption))


def cmd_guia():
    """Carrossel estilo portal (guia, lista, segredos) com imagens oficiais. Sem pauta boa, vira post normal."""
    from gallery import pick
    from guide import render_guide
    from writer import write_guide
    cfg = load_cfg()
    hist = _load(HISTORY, [])
    items = collect()
    data = write_guide(items, [h["titulo"] for h in hist])
    if not data:
        print("Nenhuma matéria rende guia agora. Fazendo post de notícia.")
        return cmd_post()
    seed = len(hist)
    used = set()
    imgs = []
    for txt in [data.get("tema", data["titulo"])] + [s.get("cena", s["titulo"]) for s in data["slides"][:8]] + ["vice city"]:
        g = pick(txt + " " + data["titulo"], seed=seed + len(imgs), avoid=used)
        if g:
            used.add(g.name)
            imgs.append(g.as_uri())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    slides = render_guide(data, imgs, ROOT / "media" / stamp[:6] / f"{stamp}-guia", seed=seed)
    caption = (f"{data['legenda']}\n\n{_cta(seed)}\n\n📰 Fonte: {data['fonte']}\n📸 Imagens: Rockstar Games\n\n"
               f"{_tags(cfg, data.get('hashtags', []))}")[:2200]
    print("GUIA:", data["titulo"], "| fonte:", data["fonte"])
    print("LEGENDA:\n" + caption)
    if DRY:
        _preview(slides, caption)
        return
    mark_seen([u["key"] for u in data["used"]])
    hist.append({"titulo": data["titulo"], "tag": "GUIA", "quando": stamp, "links": [u["link"] for u in data["used"]]})
    _save(HISTORY, hist[-200:])
    _git_push(f"guia {stamp}")
    from instagram import IG
    print("Guia publicado:", IG().post_carousel([_public_url(x) for x in slides], caption))


def _push_paths(paths, msg):
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    subprocess.run(["git", "config", "user.name", "brasileiroemvice-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", *paths], check=True)
    subprocess.run(["git", "commit", "-m", msg], check=False)
    subprocess.run(["git", "pull", "--rebase"], check=False)
    subprocess.run(["git", "push"], check=True)


def cmd_galeria():
    from gallery import fetch_gallery
    fetch_gallery()
    _push_paths(["assets/game"], "galeria de imagens oficiais")


def cmd_mascote():
    from mascot_ai import make_kit
    print("Poses geradas:", make_kit())
    _push_paths(["assets/mascote", "media/preview"], "kit de poses do Tio Vice")


def cmd_refresh():
    from instagram import IG
    print(IG().refresh_token())


def cmd_demo():
    out = ROOT / "media" / "demo"
    render(out / "demo-feed", fmt="feed", tag="OFICIAL", stars=5, source="Rockstar Games",
           title="GTA 6 *chegou*: Leonida está aberta a partir de hoje",
           sub="Lançamento mundial no PS5 e Xbox Series X|S nesta quinta, 19 de novembro.")
    render(out / "demo-rumor", fmt="feed", tag="RUMOR", stars=3, source="Reddit r/GTA6",
           title="Jogadores dizem ter achado *easter egg* de Vice City antiga",
           sub="Ainda não há confirmação. Você acredita?")
    render(out / "demo-story", fmt="story", tag="NOTICIA", stars=4, source="IGN",
           kicker="NOVO POST NO FEED", live="VEJA NO FEED",
           title="O mapa de Leonida é *maior* que o de GTA 5?",
           sub="Comparamos tamanho, cidades e regiões.")
    print("Demos em", out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    needs = {"post": ["ANTHROPIC_API_KEY"], "comments": ["ANTHROPIC_API_KEY", "IG_ACCESS_TOKEN", "IG_USER_ID"],
             "story": [] if DRY else ["IG_ACCESS_TOKEN", "IG_USER_ID"], "refresh": ["IG_ACCESS_TOKEN"],
             "reel": [] if DRY else ["IG_ACCESS_TOKEN", "IG_USER_ID"],
             "dicas": ["ANTHROPIC_API_KEY"] + ([] if DRY else ["IG_ACCESS_TOKEN", "IG_USER_ID"]),
             "mascote": ["GEMINI_API_KEY"]}
    needs["guia"] = needs["post"]
    if not DRY and cmd in ("post", "guia"):
        needs["post"] += ["IG_ACCESS_TOKEN", "IG_USER_ID"]
    missing = [k for k in needs.get(cmd, []) if not os.environ.get(k)]
    if missing:
        print(f"Aguardando configuração: faltam os secrets {missing}. Nada foi feito.")
        sys.exit(0)
    {"post": cmd_post, "story": cmd_story, "comments": cmd_comments, "reel": cmd_reel, "dicas": cmd_dicas,
     "guia": cmd_guia, "galeria": cmd_galeria, "mascote": cmd_mascote, "refresh": cmd_refresh, "demo": cmd_demo}[sys.argv[1] if len(sys.argv) > 1 else "demo"]()
