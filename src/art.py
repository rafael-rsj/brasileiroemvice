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


def _font() -> Path:
    f = FONTS / "Montserrat.ttf"
    if not f.exists():
        FONTS.mkdir(parents=True, exist_ok=True)
        f.write_bytes(requests.get(FONT_URL, timeout=60).content)
    return f


def guizo(w=40, c=Y):
    return GUIZO.format(w=w, h=int(w * 1.3), c=c)


def seal(dark=True, size=40):
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
def cover_photo(d, img, credit="", swipe=False, h=1350):
    """Capa com foto (novidade, evento, cidade)."""
    t = d["titulo"]
    info = " · ".join(x for x in [d.get("onde"), d.get("quando")] if x)
    return page(f'''<img class="abs" src="{esc(img)}" style="inset:0;width:100%;height:100%;object-fit:cover">
      <div class="abs" style="inset:0;background:linear-gradient(180deg,rgba(0,0,0,.45) 0,rgba(0,0,0,0) 22%,rgba(0,0,0,0) 42%,rgba(0,0,0,.86) 70%,#000 100%)"></div>
      <div class="abs" style="left:56px;top:52px">{seal()}</div>
      <div class="abs" style="left:56px;right:56px;bottom:{150 if h == 1350 else 380}px">
        <span class="tag" style="background:{Y};color:{K}">{esc(d.get("selo", "NOVIDADE"))}</span>
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
    return page(f'''<div class="zebra" style="top:{top}px"></div>
      <div class="abs" style="left:56px;top:{top + 170}px"><span class="tag" style="background:{R};color:#fff">⚠ {esc(d.get("selo", "ALERTA"))}</span></div>
      <h1 class="abs" style="left:56px;right:56px;top:{top + 270}px;font-size:{fs(t, [(26, 140), (44, 118), (999, 96)])}px">{mark(t)}</h1>
      {f'<div class="abs box" style="left:56px;right:56px;bottom:{170 if h == 1350 else 420}px">{rows}</div>' if rows else ''}
      <div class="abs" style="left:56px;bottom:{40 if h == 1350 else 260}px">{seal(dark=False)}</div>
      <div class="abs" style="right:56px;bottom:{62 if h == 1350 else 282}px;font-weight:700;font-size:22px;color:rgba(255,255,255,.5)">{esc("Fonte: " + d.get("fonte_principal", "")) if d.get("fonte_principal") else ""}</div>
''', h=h)


def cover_text(d, swipe=False, h=1350):
    """Capa só com tipografia (quando não tem foto boa)."""
    t = d["titulo"]
    info = " · ".join(x for x in [d.get("onde"), d.get("quando")] if x)
    return page(f'''<div class="abs" style="inset:0;background:{Y}"></div>
      <div class="abs" style="left:56px;top:52px">{seal()}</div>
      <div class="abs" style="right:56px;top:66px;font-weight:800;font-size:28px;letter-spacing:3px;color:{K}">{esc(d.get("selo", ""))}</div>
      <h1 class="abs" style="left:56px;right:56px;top:{230 if h == 1350 else 420}px;font-size:{fs(t, [(30, 150), (50, 124), (999, 100)])}px;color:{K}">{mark(t, Y, K)}</h1>
      <div class="abs" style="left:56px;right:56px;bottom:{170 if h == 1350 else 420}px;font-weight:700;font-size:38px;color:{K};line-height:1.3">{esc(d.get("subtitulo", ""))}{('<br><span style="font-weight:800">📍 ' + esc(info) + '</span>') if info else ''}</div>
      <div class="handle" style="color:{K}">{HANDLE}</div>{'<div class="swipe" style="color:' + K + '">ARRASTA →</div>' if swipe else ''}''', h=h)


def detail(d):
    """2º slide: o que se sabe, em fundo papel."""
    txt = d.get("slide2_texto", "")
    return page(f'''<div class="abs" style="inset:0;background:{P}"></div>
      <div class="abs" style="left:56px;top:56px">{seal()}</div>
      <div class="abs" style="left:56px;right:56px;top:210px;color:{K}">
        <div style="font-weight:900;font-size:70px;letter-spacing:-2px">O que se <span style="background:{Y};padding:0 10px">sabe</span></div>
        <div style="font-weight:600;font-size:44px;line-height:1.42;margin-top:40px">{esc(txt)}</div>
      </div>
      <div class="abs" style="left:56px;bottom:56px;font-weight:700;font-size:24px;color:#555">{esc("Fonte: " + d.get("fonte_principal", "")) if d.get("fonte_principal") else ""}</div>
      <div class="swipe" style="color:{K}">ARRASTA →</div>''')


def cta(n=None, total=None):
    """Último slide: chama o seguidor a mandar pauta (é assim que a página cresce)."""
    return page(f'''<div class="abs" style="inset:0;background:{K}"></div>
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
    tags = "".join(f'<span class="tag" style="background:{K};color:#fff">{esc(c)}</span>' for c in cats[:4])
    return page(f'''<div class="abs" style="inset:0;background:{Y}"></div>
      <div class="abs" style="left:56px;top:52px">{seal()}</div>
      <div class="abs" style="right:56px;top:66px;font-weight:800;font-size:30px;letter-spacing:3px;color:{K}">{esc(periodo.upper())}</div>
      <h1 class="abs" style="left:56px;right:56px;top:200px;font-size:172px;color:{K}">O QUE<br>FAZER EM<br><span style="background:{K};color:{Y};padding:0 16px">CASCAVEL</span></h1>
      <div class="abs" style="left:56px;top:800px;font-weight:800;font-size:50px;color:{K}">{len(a["eventos"])} rolês pra você 👇</div>
      <div class="abs" style="left:56px;right:56px;bottom:130px;display:flex;gap:16px;flex-wrap:wrap">{tags}</div>
      <div class="handle" style="color:{K}">{HANDLE}</div><div class="swipe" style="color:{K}">ARRASTA →</div>''')


def agenda_item(e, i, total):
    rows = "".join(f'<div style="margin-top:26px"><div class="lbl">{lbl}</div><div class="val">{esc(v)}</div></div>'
                   for lbl, v in [("🗓 QUANDO", e.get("quando")), ("📍 ONDE", e.get("onde")), ("🎟 ENTRADA", e.get("preco"))] if v)
    cat = e.get("categoria", "").upper()
    return page(f'''<div class="abs" style="inset:0;background:{K}"></div>
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


def story_weather(w):
    """Story das 7h: tempo do dia em Cascavel."""
    return page(f'''<div class="abs" style="inset:0;background:{Y}"></div>
      <div class="abs" style="left:56px;top:120px">{seal()}</div>
      <div class="abs" style="left:56px;right:56px;top:300px;color:{K}">
        <div style="font-weight:800;font-size:44px">Bom dia, Cascavel ☀️</div>
        <div style="font-weight:700;font-size:36px;margin-top:10px;opacity:.75">{esc(w["dia"])}</div>
        <div style="font-weight:900;font-size:330px;letter-spacing:-14px;line-height:1;margin-top:60px">{w["max"]}°</div>
        <div style="font-weight:800;font-size:56px">mínima de {w["min"]}° · {esc(w["descricao"])}</div>
        <div style="margin-top:70px;display:flex;gap:24px;flex-wrap:wrap">
          <span class="tag" style="background:{K};color:#fff;font-size:34px">☔ chuva {w["chuva"]}%</span>
          <span class="tag" style="background:{K};color:#fff;font-size:34px">💨 vento {w["vento"]} km/h</span></div>
        <div style="font-weight:800;font-size:46px;margin-top:90px;line-height:1.25">{esc(w["dica"])}</div>
      </div>
      <div class="abs" style="left:56px;bottom:120px;font-weight:700;font-size:28px;color:{K};opacity:.7">{HANDLE} · fonte: Open-Meteo</div>''',
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
