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


def _caption(data, cfg):
    all_tags = cfg["perfil"]["hashtags_fixas"] + [h if h.startswith("#") else "#" + h for h in data.get("hashtags", [])]
    seen_t, uniq = set(), []
    for t in all_tags:
        if t.lower() not in seen_t:
            seen_t.add(t.lower())
            uniq.append(t)
    tags = " ".join(uniq[:12])
    src = data.get("fonte_principal", "")
    rumor = "\n⚠️ Rumor, ainda não confirmado pela Rockstar." if data["tag"] == "RUMOR" else ""
    return f"{data['legenda']}{rumor}\n\n📰 Fonte: {src}\n\n{tags}"[:2200]


def cmd_post():
    from writer import pick_and_write
    cfg = load_cfg()
    hist = _load(HISTORY, [])
    items = collect()
    data = pick_and_write(items, [h["titulo"] for h in hist])
    if not data:
        print("Nada relevante agora. Pulando este horário.")
        mark_seen([i["key"] for i in items])
        return
    img, credit = None, ""
    # 1) foto da própria matéria (sites diretos como IGN Brasil, TecMundo, Eurogamer)
    for u in data["used"]:
        img = og_image(u["link"])
        if img:
            credit = f"IMAGEM: {u['source'].upper()}"
            break
    # 2) galeria de imagens oficiais do jogo (assets/game), girando a cada post
    if not img:
        gal = sorted(p for p in (ROOT / "assets" / "game").glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
        if gal:
            img = gal[len(hist) % len(gal)].as_uri()
            credit = "IMAGEM: ROCKSTAR GAMES"
    # 3) sem foto: o render usa um cenário ilustrado próprio
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    base = ROOT / "media" / stamp[:6] / stamp
    common = dict(title=data["titulo"], sub=data.get("subtitulo", ""), tag=data["tag"],
                  source=data.get("fonte_principal", ""), image_url=img, stars=int(data.get("estrelas", 3)),
                  seed=len(hist))  # cada post novo gira cenário, paleta e layout
    # --- carrossel: capa + detalhes + siga ---
    cover_layout = "l-center" if img else None
    feed = render(base.with_name(stamp + "-feed"), fmt="feed", layout=cover_layout, credit=credit, **common)
    slides = [feed]
    if data.get("slide2_texto"):
        rot, val = data.get("slide2_rotulo", "").strip(), data.get("slide2_valor", "").strip()
        t2 = f"{rot} *{val}*" if val else (rot or "Entenda:")
        d = dict(common, title=t2, sub=data["slide2_texto"])
        slides.append(render(base.with_name(stamp + "-2"), fmt="feed", layout="l-detail",
                             sign="Brasileiro em Vice", credit=credit, **{k: v for k, v in d.items()}))
    slides.append(render(base.with_name(stamp + "-3"), fmt="feed", layout="l-cta", tag="NOTICIA",
                         title="Siga o *@brasileiroemvice*", sub="Tudo de GTA 6 todo dia: notícias, segredos e comparações.",
                         source="", image_url=None, stars=0, seed=len(hist) + 7))
    story = render(base.with_name(stamp + "-story"), fmt="story", kicker="NOVO POST NO FEED",
                   live="VEJA NO FEED", **common)
    caption = _caption(data, cfg)
    q = _load(QUEUE, [])
    q.append({"file": story.relative_to(ROOT).as_posix(), "created": stamp})
    _save(QUEUE, q)
    mark_seen([i["key"] for i in items])
    hist.append({"titulo": data["titulo"], "tag": data["tag"], "quando": stamp,
                 "links": [u["link"] for u in data["used"]]})
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
             "story": [] if DRY else ["IG_ACCESS_TOKEN", "IG_USER_ID"], "refresh": ["IG_ACCESS_TOKEN"]}
    if not DRY and cmd == "post":
        needs["post"] += ["IG_ACCESS_TOKEN", "IG_USER_ID"]
    missing = [k for k in needs.get(cmd, []) if not os.environ.get(k)]
    if missing:
        print(f"Aguardando configuração: faltam os secrets {missing}. Nada foi feito.")
        sys.exit(0)
    {"post": cmd_post, "story": cmd_story, "comments": cmd_comments,
     "refresh": cmd_refresh, "demo": cmd_demo}[sys.argv[1] if len(sys.argv) > 1 else "demo"]()
