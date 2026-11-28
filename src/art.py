"""Artes do guizo (feed 1080x1350 e story 1080x1920), desenhadas em HTML e fotografadas com Playwright.

Identidade: preto #111, amarelo guizo #FFD21F, vermelho alerta #FF4D2E, papel #F4F1EA, fonte Montserrat Black.
"""
import html
import re
from pathlib import Path

import requests
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
Y, K, R, P = "#FFD21F", "#111111", "#FF4D2E", "#F4F1EA"
HANDLE = "@guizocascavel"

GUIZO = """<svg width="{w}" height="{h}" viewBox="0 0 200 260" style="color:{c};transform:rotate(-14deg);flex:none">
<g stroke="#111" stroke-width="12" stroke-linejoin="round" fill="currentColor">
<path d="M100 20C140 20 160 34 160 54C160 74 140 84 100 84C60 84 40 74 40 54C40 34 60 20 100 20Z"/>
<path d="M100 74C136 74 154 88 154 108C154 128 136 138 100 138C64 138 46 128 46 108C46 88 64 74 100 74Z"/>
<path d="M100 128C130 128 146 141 146 159C146 177 130 186 100 186C70 186 54 177 54 159C54 141 70 128 100 128Z"/>
<path d="M100 176C124 176 136 188 136 203C136 219 124 230 100 244C76 230 64 219 64 203C64 188 76 176 100 176Z"/></g></svg>"""


# ---------------------------------------------------------------- textura de fundo
# Curvas do guizo bem grandes e discretas no fundo escuro. São 8 composições diferentes que se alternam
# (com giro e posição variando), então um post não fica igual ao do lado e o padrão só repete depois de um tempo.
SEG = ["M100 20C140 20 160 34 160 54C160 74 140 84 100 84C60 84 40 74 40 54C40 34 60 20 100 20Z",
       "M100 74C136 74 154 88 154 108C154 128 136 138 100 138C64 138 46 128 46 108C46 88 64 74 100 74Z",
       "M100 128C130 128 146 141 146 159C146 177 130 186 100 186C70 186 54 177 54 159C54 141 70 128 100 128Z",
       "M100 176C124 176 136 188 136 203C136 219 124 230 100 244C76 230 64 219 64 203C64 188 76 176 100 176Z"]
ARCS = ["M178 30C196 50 196 80 178 100", "M196 14C224 46 224 96 196 128",
        "M22 30C4 50 4 80 22 100", "M4 14C-24 46 -24 96 4 128"]
_VAR = {"n": None}


def set_variant(n):
    """main.py chama com o número do post, para a textura ir mudando em sequência."""
    _VAR["n"] = n


def _seed(key):
    if _VAR["n"] is not None:
        return _VAR["n"]
    return sum(ord(ch) * (i + 1) for i, ch in enumerate(str(key))) % 997


def _rattle(x, y, size, rot, stroke, op, sw=3, fill="none", arcs=False):
    sc = size / 260
    paths = "".join(f'<path d="{d}"/>' for d in SEG)
    a = "".join(f'<path d="{d}"/>' for d in ARCS) if arcs else ""
    return (f'<g transform="translate({x} {y}) rotate({rot}) scale({sc:.3f}) translate(-100 -130)" '
            f'stroke="{stroke}" stroke-opacity="{op}" fill="{fill}" stroke-width="{sw / sc:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round">{paths}{a}</g>')


def texture(key="", w=1080, h=1350, tone="dark"):
    n = _seed(key)
    # stories (1920) usam as 8 composições; no feed só as que não brigam com o texto
    v = n % 8 if h >= 1900 else [1, 2, 3, 5, 7, 0][n % 6]
    j = (n // 8) % 5 - 2  # pequeno giro extra, muda a cada volta completa
    dark = tone == "dark"
    line = Y if dark else K
    g = ""
    if v == 0:    # guizo amarelo sólido gigante, cortado no canto
        g = _rattle(w * 1.06, h * 1.02, h * .5, -18 + j * 3, K, 1, 10, fill=Y)
    elif v == 1:  # anéis grossos saindo do canto de baixo
        for i in range(6):
            r = 180 + i * 150
            g += (f'<ellipse cx="{w * .95}" cy="{h * 1.02}" rx="{r * 1.5}" ry="{r}" fill="none" stroke="{line}" '
                  f'stroke-opacity="{.30 - i * .04:.2f}" stroke-width="{12 - i}" transform="rotate({-12 + j * 3} {w * .95} {h * 1.02})"/>')
    elif v == 2:  # contorno gigante e grosso pela direita
        g = _rattle(w * .9, h * .72, h * .95, -14 + j * 3, line, .22, 9)
    elif v == 3:  # padrão diagonal de guizos pequenos
        for yy in range(-1, int(h / 230) + 2):
            for xx in range(-1, int(w / 230) + 2):
                g += _rattle(xx * 230 + (115 if yy % 2 else 0), yy * 230, 120, -14 + j * 4, line, .09, 3)
    elif v == 4:  # faixa amarela diagonal com guizos recortados
        g = (f'<g transform="rotate({-16 + j * 2} {w / 2} {h * .78 + 75})"><rect x="{-w}" y="{h * .78}" width="{w * 3}" height="150" fill="{Y}"/>'
             + "".join(_rattle(-200 + i * 150, h * .78 + 75, 100, 90, K, .9, 6) for i in range(int(w * 2.4 / 150))) + '</g>')
    elif v == 5:  # guizo tom sobre tom com as ondas de vibração em amarelo
        g = (_rattle(w * .9, h * .9, h * .48, -20 + j * 2, "#2a2a2a" if dark else "#d9d4c8", 1, 8, fill="#1b1b1b" if dark else "#ebe6da")
             + f'<g transform="translate({w * .9} {h * .9}) rotate({-20 + j * 2}) scale({h * .48 / 260:.3f}) translate(-100 -130)" fill="none" '
             f'stroke="{Y}" stroke-width="{8 / (h * .48 / 260):.1f}" stroke-linecap="round">' + "".join(f'<path d="{d}"/>' for d in ARCS) + '</g>')
    elif v == 6:  # ondas amarelas empilhadas no pé
        for i in range(4):
            yy = h - 14 - i * 34
            g += (f'<path d="M-20 {yy} Q {w * .25} {yy - 40} {w * .5} {yy} T {w + 20} {yy}" fill="none" stroke="{Y}" '
                  f'stroke-opacity="{.9 - i * .2:.2f}" stroke-width="{12 - i * 2.5}" stroke-linecap="round"/>')
    else:         # guizo deitado atravessando o fundo, contorno grosso
        g = _rattle(w * .5, h * .9, w * 1.25, 76 + j * 2, line, .2, 9)
    return (f'<svg class="abs" style="left:0;top:0;pointer-events:none" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">{g}</svg>')

def _font() -> Path:
    f = FONTS / "Montserrat.ttf"
    if not f.exists():
        FONTS.mkdir(parents=True, exist_ok=True)
        f.write_bytes(requests.get(FONT_URL, timeout=60).content)
    return f


BRAND = ROOT / "assets" / "brand"


def asset(name):
    f = BRAND / name
    return f if f.exists() else None


def mascot(name, width, style=""):
    """Cobrinha do guizo (poses em assets/brand). Sem a imagem, não desenha nada."""
    f = asset(f"{name}.png") or asset("mascote.png")
    return (f'<img src="{f.as_uri()}" style="width:{width}px;display:block;'
            f'filter:drop-shadow(0 14px 22px rgba(0,0,0,.35));{style}">') if f else ""


def guizo(w=40, c=Y):
    return GUIZO.format(w=w, h=int(w * 1.3), c=c)


def seal(dark=True, size=40):
    selo = asset("selo.png")
    if dark and selo:
        return f'<img src="{selo.as_uri()}" style="height:{int(size * 1.9)}px;display:block">'
    bg, fg, ic = (K, "#fff", Y) if dark else (Y, K, K)
    return (f'<div class="seal" style="background:{bg}">{guizo(size, ic)}'
            f'<span style="color:{fg};font-size:{int(size * 1.02)}px">guizo</span></div>')


def mark(t: str, color=Y, bg=None) -> str:
    style = f"color:{color}" + (f";background:{bg};padding:0 12px;-webkit-box-decoration-break:clone;box-decoration-break:clone" if bg else "")
    return re.sub(r"\*(.+?)\*", rf'<span style="{style}">\1</span>', html.escape(t or ""))


def plain(t: str) -> str:
    return (t or "").replace("*", "")


def fs(t: str, steps) -> int:
    n = len(plain(t))
    for lim, size in steps:
        if n <= lim:
            return size
    return steps[-1][1]


def esc(t):
    return html.escape(t or "")


def css(w, h):
    return f"""@font-face{{font-family:G;src:url("{_font().as_uri()}");font-weight:100 900}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{w}px;height:{h}px;overflow:hidden;font-family:G;color:#fff;background:{K}}}
.seal{{display:inline-flex;align-items:center;gap:10px;padding:12px 26px 12px 18px;border-radius:60px}}
.seal span{{font-weight:900;letter-spacing:-2px;line-height:1}}
h1{{font-weight:900;letter-spacing:-3px;line-height:.98}}
.tag{{display:inline-block;font-weight:800;font-size:28px;letter-spacing:4px;padding:11px 22px;border-radius:10px}}
.abs{{position:absolute}}
.handle{{position:absolute;left:56px;bottom:48px;font-weight:700;font-size:24px;opacity:.8}}
.swipe{{position:absolute;right:56px;bottom:46px;font-weight:800;font-size:26px;letter-spacing:3px}}
.credit{{position:absolute;right:18px;font-weight:500;font-size:13px;letter-spacing:1px;color:rgba(255,255,255,.55);text-shadow:0 1px 2px rgba(0,0,0,.7)}}
.zebra{{position:absolute;left:0;right:0;height:110px;background:repeating-linear-gradient(-45deg,{Y} 0 40px,{K} 40px 80px)}}
.box{{background:#1c1c1c;border-left:10px solid {Y};border-radius:16px;padding:30px 36px}}
.lbl{{font-weight:800;font-size:26px;letter-spacing:3px;color:{Y}}}
.val{{font-weight:600;font-size:38px;margin-top:6px;line-height:1.25}}
.big{{font-weight:900;font-size:84px;line-height:1;margin-top:4px}}
"""


def page(body, w=1080, h=1350):
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css(w, h)}</style></head><body>{body}</body></html>"


# ---------------------------------------------------------------- feed
# Sistema de categorias (v1): toda capa traz a etiqueta da categoria no MESMO lugar (em cima do título),
# sempre com a mesma cor. Quem olha a grade acha rápido o tipo de post que procura.
CATS = {
    "NOVIDADE": (Y, K, ""),
    "BOMBOU": ("#fff", K, ""),
    "POLICIA": (R, "#fff", ""),
    "ALERTA": (R, "#fff", ""),
    "CIDADE": ("transparent", Y, f"border:3px solid {Y};"),
    "EVENTO": ("transparent", "#fff", "border:3px solid #fff;"),
}
NOMES = {"POLICIA": "POLÍCIA"}


def cat_tag(d, size=28):
    tipo = (d.get("tipo") or "NOVIDADE").upper().replace("Í", "I")
    bg, fg, extra = CATS.get(tipo, CATS["NOVIDADE"])
    return (f'<span class="tag" style="background:{bg};color:{fg};font-size:{size}px;{extra}">'
            f'{NOMES.get(tipo, tipo)}</span>')


def cover_photo(d, img, credit="", swipe=False, h=1350):
    """Capa com foto (novidade, evento, cidade)."""
    t = d["titulo"]
    info = " · ".join(x for x in [d.get("onde"), d.get("quando")] if x)
    return page(f'''<img class="abs" src="{esc(img)}" style="inset:0;width:100%;height:100%;object-fit:cover">
      <div class="abs" style="inset:0;background:linear-gradient(180deg,rgba(0,0,0,.45) 0,rgba(0,0,0,0) 22%,rgba(0,0,0,0) 42%,rgba(0,0,0,.86) 70%,#000 100%)"></div>
      <div class="abs" style="left:56px;top:52px">{seal()}</div>
      <div class="abs" style="left:56px;right:56px;bottom:{150 if h == 1350 else 380}px">
        {cat_tag(d)}
        <h1 style="font-size:{fs(t, [(34, 128), (52, 110), (999, 92)])}px;margin-top:26px">{mark(t)}</h1>
        {f'<div style="font-weight:600;font-size:34px;color:rgba(255,255,255,.88);margin-top:24px">📍 {esc(info)}</div>' if info else ''}
      </div>
      {f'<div class="credit" style="bottom:{20 if h == 1350 else 250}px">{esc(credit)}</div>' if credit else ''}
      <div class="handle">{HANDLE}</div>{'<div class="swipe" style="color:' + Y + '">ARRASTA →</div>' if swipe else ''}''', h=h)


def cover_alert(d, swipe=False, h=1350):
    """Capa de alerta (radar, trânsito, obra, falta de água/luz): faixa zebrada e quadro de informações."""
    t = d["titulo"]
    rows = ""
    if d.get("onde"):
        rows += f'<div class="lbl">📍 ONDE</div><div class="val" style="margin-bottom:22px">{esc(d["onde"])}</div>'
    dados = [x for x in d.get("dados", []) if x.get("valor")][:2]
    if dados:
        rows += '<div style="display:flex;gap:60px">' + "".join(
            f'<div><div class="lbl">{esc(x["rotulo"]).upper()}</div><div class="big">{esc(x["valor"])}</div></div>' for x in dados) + "</div>"
    elif d.get("quando"):
        rows += f'<div class="lbl">🗓 QUANDO</div><div class="val">{esc(d["quando"])}</div>'
    top = 0 if h == 1350 else 120
    return page(f'''{texture(t, 1080, h)}<div class="zebra" style="top:{top}px"></div>
      <div class="abs" style="left:56px;top:{top + 170}px">{cat_tag(d)}</div>
      <h1 class="abs" style="left:56px;right:56px;top:{top + 270}px;font-size:{fs(t, [(26, 140), (44, 118), (999, 96)])}px">{mark(t)}</h1>
      {f'<div class="abs box" style="left:56px;right:56px;bottom:{170 if h == 1350 else 420}px">{rows}</div>' if rows else ''}
      <div class="abs" style="left:56px;bottom:{40 if h == 1350 else 260}px">{seal(dark=False)}</div>
      <div class="abs" style="right:56px;bottom:{62 if h == 1350 else 282}px;font-weight:700;font-size:22px;color:rgba(255,255,255,.5)">{esc("Fonte: " + d.get("fonte_principal", "")) if d.get("fonte_principal") else ""}</div>
''', h=h)


def cover_text(d, swipe=False, h=1350):
    """Capa sem foto: ilustração da cidade (assets/brand/fundo_cidade.jpg) ou fundo amarelo."""
    t = d["titulo"]
    info = " · ".join(x for x in [d.get("onde"), d.get("quando")] if x)
    bg = asset("fundo_cidade.jpg")
    if bg:
        return page(f'''<div class="abs" style="inset:0;background:{K}"></div>
      <img class="abs" src="{bg.as_uri()}" style="left:0;top:{-170 if h == 1350 else 0}px;width:1080px;height:1350px">
      <div class="abs" style="left:0;right:0;top:{440 if h == 1350 else 750}px;height:260px;background:linear-gradient(180deg,rgba(17,17,17,0),#111)"></div>
      <div class="abs" style="left:56px;top:52px">{seal()}</div>
      <div class="abs" style="left:56px;right:56px;bottom:{150 if h == 1350 else 380}px">
        {cat_tag(d)}
        <h1 style="font-size:{fs(t, [(34, 124), (52, 106), (999, 90)])}px;margin-top:26px">{mark(t)}</h1>
        <div style="font-weight:600;font-size:34px;color:rgba(255,255,255,.85);margin-top:22px;line-height:1.3">{esc(d.get("subtitulo", ""))}</div>
        {f'<div style="font-weight:700;font-size:32px;color:{Y};margin-top:14px">📍 {esc(info)}</div>' if info else ''}
      </div>
      <div class="handle">{HANDLE}</div>{'<div class="swipe" style="color:' + Y + '">ARRASTA →</div>' if swipe else ''}''', h=h)
    return page(f'''<div class="abs" style="inset:0;background:{Y}"></div>
      <div class="abs" style="left:56px;top:52px">{seal()}</div>
      <div class="abs" style="right:56px;top:66px;font-weight:800;font-size:28px;letter-spacing:3px;color:{K}">{esc(d.get("selo", ""))}</div>
      <h1 class="abs" style="left:56px;right:56px;top:{230 if h == 1350 else 420}px;font-size:{fs(t, [(30, 150), (50, 124), (999, 100)])}px;color:{K}">{mark(t, Y, K)}</h1>
      <div class="abs" style="left:56px;right:56px;bottom:{170 if h == 1350 else 420}px;font-weight:700;font-size:38px;color:{K};line-height:1.3">{esc(d.get("subtitulo", ""))}{('<br><span style="font-weight:800">📍 ' + esc(info) + '</span>') if info else ''}</div>
      <div class="handle" style="color:{K}">{HANDLE}</div>{'<div class="swipe" style="color:' + K + '">ARRASTA →</div>' if swipe else ''}''', h=h)


def detail(d):
    """2º slide: o que se sabe, em fundo papel."""
    txt = d.get("slide2_texto", "")
    return page(f'''<div class="abs" style="inset:0;background:{P}"></div>{texture(txt, tone="light")}
      <div class="abs" style="left:56px;top:56px">{seal()}</div>
      <div class="abs" style="left:56px;right:56px;top:210px;color:{K}">
        <div style="font-weight:900;font-size:70px;letter-spacing:-2px">O que se <span style="background:{Y};padding:0 10px">sabe</span></div>
        <div style="font-weight:600;font-size:44px;line-height:1.42;margin-top:40px">{esc(txt)}</div>
      </div>
      <div class="abs" style="left:56px;bottom:56px;font-weight:700;font-size:24px;color:#555">{esc("Fonte: " + d.get("fonte_principal", "")) if d.get("fonte_principal") else ""}</div>
      <div class="swipe" style="color:{K}">ARRASTA →</div>''')


def cta(n=None, total=None):
    """Último slide: chama o seguidor a mandar pauta (é assim que a página cresce)."""
    return page(f'''<div class="abs" style="inset:0;background:{K}"></div>{texture("cta")}
      <div class="abs" style="left:0;right:0;top:120px;display:flex;justify-content:center">{guizo(170)}</div>
      <h1 class="abs" style="left:56px;right:56px;top:450px;text-align:center;font-size:96px">Viu algo <span style="color:{Y}">acontecendo</span> em Cascavel?</h1>
      <div class="abs" style="left:80px;right:80px;top:790px;text-align:center;font-weight:700;font-size:40px;line-height:1.4;color:#ddd">
        Manda no direct ou marca o <span style="color:{Y}">{HANDLE}</span> no seu story que a gente espalha 📣</div>
      <div class="abs" style="left:0;right:0;bottom:90px;display:flex;justify-content:center;gap:18px">
        <span class="tag" style="background:{Y};color:{K}">SEGUE</span><span class="tag" style="background:#222;color:#fff">SALVA</span>
        <span class="tag" style="background:#222;color:#fff">COMPARTILHA</span></div>''')


# ---------------------------------------------------------------- agenda
EMO = {"SHOW": "🎤", "FESTA": "🎉", "TEATRO": "🎭", "FEIRA": "🛍", "GASTRONOMIA": "🍔", "ESPORTE": "⚽", "FAMÍLIA": "👨‍👩‍👧", "CULTURA": "🎨"}


def agenda_cover(a, periodo):
    cats = []
    for e in a["eventos"]:
        c = e.get("categoria", "").upper()
        if c and c not in cats:
            cats.append(c)
    tags = "".join(f'<span class="tag" style="background:rgba(255,255,255,.1);color:#fff;border:2px solid rgba(255,255,255,.2)">{esc(c)}</span>' for c in cats[:4])
    return page(f'''<div class="abs" style="inset:0;background:radial-gradient(110% 70% at 90% 100%,#2a2a2a,{K} 60%)"></div>{texture(periodo)}
      <div class="abs" style="left:56px;top:52px">{seal()}</div>
      <div class="abs" style="right:56px;top:66px;font-weight:800;font-size:30px;letter-spacing:3px;color:{Y}">{esc(periodo.upper())}</div>
      <h1 class="abs" style="left:56px;right:56px;top:200px;font-size:172px;color:#fff">O QUE<br>FAZER EM<br><span style="background:{Y};color:{K};padding:0 16px">CASCAVEL</span></h1>
      <div class="abs" style="left:56px;top:800px;font-weight:800;font-size:50px;color:#fff">{len(a["eventos"])} rolês pra você 👇</div>
      <div class="abs" style="left:56px;right:56px;bottom:130px;display:flex;gap:16px;flex-wrap:wrap">{tags}</div>
      <div class="handle">{HANDLE}</div><div class="swipe" style="color:{Y}">ARRASTA →</div>''')


def agenda_item(e, i, total):
    rows = "".join(f'<div style="margin-top:26px"><div class="lbl">{lbl}</div><div class="val">{esc(v)}</div></div>'
                   for lbl, v in [("🗓 QUANDO", e.get("quando")), ("📍 ONDE", e.get("onde")), ("🎟 ENTRADA", e.get("preco"))] if v)
    cat = e.get("categoria", "").upper()
    return page(f'''<div class="abs" style="inset:0;background:{K}"></div>{texture(e.get("nome", ""))}
      <div class="abs" style="left:56px;top:52px">{seal(dark=False)}</div>
      <div class="abs" style="right:56px;top:66px;font-weight:800;font-size:28px;color:#777">{i}/{total}</div>
      <div class="abs" style="left:56px;top:190px"><span class="tag" style="background:{Y};color:{K}">{EMO.get(cat, "✨")} {esc(cat or "ROLÊ")}</span></div>
      <h1 class="abs" style="left:56px;right:56px;top:290px;font-size:{fs(e["nome"], [(18, 120), (32, 98), (999, 80)])}px">{esc(e["nome"])}</h1>
      <div class="abs box" style="left:56px;right:56px;bottom:270px">{rows}</div>
      <div class="abs" style="left:56px;right:56px;bottom:150px;font-weight:700;font-size:36px;color:{Y}">{esc(e.get("por_que_ir", ""))}</div>
      <div class="abs" style="left:56px;bottom:56px;font-weight:600;font-size:22px;color:#777">{esc("Fonte: " + e.get("fonte", "")) if e.get("fonte") else ""}</div>
      <div class="swipe" style="color:{Y}">PRÓXIMO →</div>''')


# ---------------------------------------------------------------- story
def story_from(kind, d, img=None, credit=""):
    """Versão 9:16 do post para o story, com chamada para o feed."""
    fn = {"photo": lambda: cover_photo(d, img, credit, h=1920), "alert": lambda: cover_alert(d, h=1920),
          "text": lambda: cover_text(d, h=1920)}[kind]
    body = fn()
    banner = (f'<div class="abs" style="left:0;right:0;bottom:120px;display:flex;justify-content:center">'
              f'<span class="tag" style="background:{Y};color:{K};font-size:32px">👆 POST NOVO NO FEED</span></div>')
    return body.replace("</body>", banner + "</body>")


def story_semana_cover(periodo, eventos):
    """1º story da segunda: a semana em Cascavel (vai para o destaque A SEMANA)."""
    lista = "".join(f'<div style="display:flex;gap:22px;align-items:baseline;margin-top:26px">'
                    f'<span style="font-weight:800;font-size:30px;color:{Y};min-width:150px">{esc(e.get("dia", ""))}</span>'
                    f'<span style="font-weight:700;font-size:38px;line-height:1.2">{esc(e["nome"])}</span></div>' for e in eventos[:7])
    return page(f'''<div class="abs" style="inset:0;background:{K}"></div>{texture(periodo, 1080, 1920)}
      <div class="abs" style="left:56px;top:130px">{seal()}</div>
      <div class="abs" style="left:56px;right:56px;top:300px">
        <div style="font-weight:800;font-size:34px;letter-spacing:4px;color:{Y}">{esc(periodo.upper())}</div>
        <h1 style="font-size:130px;margin-top:20px">A semana em<br><span style="background:{Y};color:{K};padding:0 14px">Cascavel</span></h1>
        <div style="margin-top:60px">{lista}</div>
      </div>
''', h=1920)


def story_semana_item(e, i, total):
    rows = "".join(f'<div style="margin-top:34px"><div class="lbl">{lbl}</div><div class="val" style="font-size:46px">{esc(v)}</div></div>'
                   for lbl, v in [("QUANDO", e.get("quando")), ("ONDE", e.get("onde")), ("ENTRADA", e.get("preco"))] if v)
    cat = (e.get("categoria") or "ROLÊ").upper()
    return page(f'''<div class="abs" style="inset:0;background:{K}"></div>{texture(e["nome"] + str(i), 1080, 1920)}
      <div class="abs" style="left:56px;top:130px">{seal()}</div>
      <div class="abs" style="right:56px;top:150px;font-weight:800;font-size:30px;color:#777">{i}/{total}</div>
      <div class="abs" style="left:56px;right:56px;top:380px">
        <span class="tag" style="background:transparent;color:#fff;border:3px solid #fff;font-size:30px">{esc(cat)}</span>
        <h1 style="font-size:{fs(e["nome"], [(18, 140), (32, 112), (999, 92)])}px;margin-top:34px">{esc(e["nome"])}</h1>
        <div class="box" style="margin-top:60px">{rows}</div>
        <div style="font-weight:700;font-size:42px;color:{Y};margin-top:50px;line-height:1.3">{esc(e.get("por_que_ir", ""))}</div>
      </div>
      <div class="abs" style="left:56px;bottom:150px;font-weight:600;font-size:26px;color:#777">{esc("Fonte: " + e.get("fonte", "")) if e.get("fonte") else ""}</div>''', h=1920)


def story_weather(w):
    """Story das 7h: tempo do dia em Cascavel (fundo escuro, amarelo só no destaque)."""
    tag = 'background:rgba(255,255,255,.1);color:#fff;font-size:34px;border:2px solid rgba(255,255,255,.18)'
    return page(f'''<div class="abs" style="inset:0;background:radial-gradient(120% 70% at 85% 95%,#2a2a2a,{K} 60%)"></div>{texture(w["dia"], 1080, 1920)}
      <div class="abs" style="left:56px;top:120px">{seal()}</div>
      <div class="abs" style="left:56px;right:56px;top:300px;color:#fff">
        <div style="font-weight:800;font-size:44px">Bom dia, <span style="color:{Y}">Cascavel</span></div>
        <div style="font-weight:700;font-size:36px;margin-top:10px;color:#9a9a9a">{esc(w["dia"])}</div>
        <div style="font-weight:900;font-size:330px;letter-spacing:-14px;line-height:1;margin-top:60px;color:{Y}">{w["max"]}°</div>
        <div style="font-weight:800;font-size:56px">mínima de {w["min"]}° · {esc(w["descricao"])}</div>
        <div style="margin-top:70px;display:flex;gap:24px;flex-wrap:wrap">
          <span class="tag" style="{tag}">☔ chuva {w["chuva"]}%</span>
          <span class="tag" style="{tag}">💨 vento {w["vento"]} km/h</span></div>
        <div style="font-weight:800;font-size:46px;margin-top:90px;line-height:1.25;max-width:520px">{esc(w["dica"])}</div>
      </div>
      <div class="abs" style="right:0;bottom:150px">{mascot("mascote_frio" if w["min"] <= 12 else "mascote", 540)}</div>
      <div class="abs" style="left:56px;bottom:120px;font-weight:700;font-size:28px;color:#777">{HANDLE} · fonte: Open-Meteo</div>''',
                h=1920)


# ---------------------------------------------------------------- render
def shoot(pages: list[str], out_dir: Path, prefix: str, h=1350) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": h})
        for i, html_ in enumerate(pages):
            hh = 1920 if "height:1920px" in html_[:2000] else h
            pg.set_viewport_size({"width": 1080, "height": hh})
            f = out_dir / f"{prefix}_{i + 1:02d}.html"
            f.write_text(html_, encoding="utf-8")
            pg.goto(f.as_uri())
            try:
                pg.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            pg.wait_for_timeout(400)
            png = f.with_suffix(".png")
            pg.screenshot(path=str(png))
            jpg = png.with_suffix(".jpg")
            Image.open(png).convert("RGB").save(jpg, quality=90)
            png.unlink()
            f.unlink()
            files.append(jpg)
        b.close()
    return files
