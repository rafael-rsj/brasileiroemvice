"""Carrossel estilo portal (guias, listas, segredos): foto oficial do jogo em cada slide, número grande,
selo de confirmado/rumor, contador de slides e slide final com o Tio Vice chamando para seguir."""
import html
import re
from pathlib import Path

from playwright.sync_api import sync_playwright
from PIL import Image

from mascot import mascot_html

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1350
ACCS = ["#ffc145", "#22e1ff", "#ff5fa2", "#ffcf4a"]
SELOS = {"CONFIRMADO": ("CONFIRMADO PELA ROCKSTAR", "#2ee59d", "#0d0624"), "RUMOR": ("RUMOR • NÃO CONFIRMADO", "#ff5e62", "#fff"),
         "DICA": ("DICA", "#ffc145", "#0d0624"), "SEGREDO": ("SEGREDO", "#b07bff", "#fff"),
         "OFICIAL": ("OFICIAL", "#2ee59d", "#0d0624"), "ATENCAO": ("ATENÇÃO", "#ff8a3d", "#0d0624")}

ICONS = {
    "comenta": '<path d="M12 14h40a6 6 0 016 6v22a6 6 0 01-6 6H30l-12 10V48h-6a6 6 0 01-6-6V20a6 6 0 016-6z"/>',
    "salva": '<path d="M18 8h28a4 4 0 014 4v46L32 46 14 58V12a4 4 0 014-4z"/>',
    "manda": '<path d="M6 30L58 8 44 58 32 38zM32 38l26-30"/>',
    "segue": '<circle cx="26" cy="22" r="11"/><path d="M6 56c0-12 9-20 20-20s20 8 20 20M50 18v20M40 28h20"/>',
}

CSS = """
@font-face{font-family:Anton;src:url("%(fonts)s/Anton-Regular.ttf")}
@font-face{font-family:InterB;src:url("%(fonts)s/Inter-Bold.otf")}
@font-face{font-family:InterM;src:url("%(fonts)s/Inter-Medium.otf")}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px;overflow:hidden;background:#0d0624;color:#fff;font-family:InterM}
.ph{position:absolute;left:0;top:0;width:1080px;object-fit:cover}
.mk{color:%(acc)s}
.brand{position:absolute;left:44px;top:40px;display:flex;align-items:center;gap:14px;background:rgba(13,6,36,.72);
  padding:8px 22px 8px 8px;border-radius:60px;font-family:Anton;font-size:30px;letter-spacing:1px}
.brand img{width:58px;height:58px;border-radius:50%%;border:3px solid #fff}
.count{position:absolute;right:44px;top:48px;font-family:InterB;font-size:26px;background:rgba(13,6,36,.72);padding:10px 20px;border-radius:40px}
.selo{display:inline-block;font-family:InterB;font-size:24px;letter-spacing:3px;padding:10px 20px;border-radius:8px}
.swipe{position:absolute;right:44px;bottom:40px;font-family:InterB;font-size:24px;letter-spacing:3px;color:%(acc)s;display:flex;gap:10px;align-items:center}
.handle{position:absolute;left:44px;bottom:40px;font-family:InterB;font-size:24px;color:rgba(255,255,255,.75)}
.src{position:absolute;left:44px;bottom:78px;font-family:InterB;font-size:18px;letter-spacing:2px;color:rgba(255,255,255,.5)}
h1{font-family:Anton;text-transform:uppercase;line-height:1.02;letter-spacing:.5px;text-shadow:0 4px 0 rgba(0,0,0,.45)}
.salva{position:absolute;right:44px;top:130px;background:%(acc)s;color:#0d0624;font-family:Anton;font-size:34px;letter-spacing:1px;
  padding:12px 22px;transform:rotate(4deg);box-shadow:6px 6px 0 #0d0624}
"""


def _mark(t):
    return re.sub(r"\*(.+?)\*", r'<span class="mk">\1</span>', html.escape(t))


def _fs(t, sizes):
    n = len(t.replace("*", ""))
    for lim, fs in sizes:
        if n <= lim:
            return fs
    return sizes[-1][1]


def shot(pages: list[str], out_dir: Path, prefix: str = "s") -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for i, page in enumerate(pages):
            f = out_dir / f"{prefix}_{i+1:02d}.html"
            f.write_text(page, encoding="utf-8")
            pg.goto(f.as_uri())
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(300)
            png = f.with_suffix(".png")
            pg.screenshot(path=str(png))
            jpg = png.with_suffix(".jpg")
            Image.open(png).convert("RGB").save(jpg, quality=90)
            png.unlink()
            f.unlink()
            files.append(jpg)
        b.close()
    return files


def head(acc: str) -> str:
    css = CSS % dict(fonts=(ROOT / "assets" / "fonts").as_uri(), acc=acc)
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>"


def brand() -> str:
    return f'<div class="brand"><img src="{(ROOT / "assets" / "perfil.png").as_uri()}">BRASILEIRO EM VICE</div>'


def cta_page(acc: str, n: int, total: int, titulo: str = "Curtiu? Então *fortalece*", bg: str | None = None) -> str:
    """Slide final: Tio Vice comemorando + 4 chamadas (comenta, salva, manda, segue)."""
    rows = [("comenta", "COMENTA", "o que você achou"), ("salva", "SALVA", "pra consultar depois"),
            ("manda", "MANDA", "pro parça que joga junto"), ("segue", "SEGUE", "@brasileiroemvice")]
    items = "".join(
        f'''<div style="display:flex;align-items:center;gap:26px;margin-top:30px">
          <svg width="84" height="84" viewBox="0 0 64 64" style="background:{acc};border-radius:22px;padding:12px;flex:none">
            <g fill="none" stroke="#0d0624" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">{ICONS[k]}</g></svg>
          <div><div style="font-family:Anton;font-size:52px;line-height:1">{a}</div>
          <div style="font-family:InterB;font-size:30px;color:rgba(255,255,255,.8);margin-top:6px">{b}</div></div></div>'''
        for k, a, b in rows)
    bgimg = (f'<img class="ph" src="{bg}" style="height:1350px;filter:blur(3px) brightness(.35) saturate(1.2)">' if bg else
             '<div style="position:absolute;inset:0;background:radial-gradient(circle at 75% 80%,#ff3d7f 0,#6a1b6e 35%,#1a0b3d 70%)"></div>')
    return head(acc) + f'''{bgimg}{brand()}<div class="count">{n}/{total}</div>
      <h1 style="position:absolute;left:60px;right:60px;top:170px;font-size:110px">{_mark(titulo)}</h1>
      <div style="position:absolute;left:60px;top:440px">{items}</div>
      <div style="position:absolute;right:-70px;bottom:-30px">{mascot_html("comemorando", 520)}</div>
      </body></html>'''


def render_guide(data: dict, images: list[str], out_dir: Path, seed: int = 0) -> list[Path]:
    """data: titulo, chamada, slides[{titulo, texto, selo}], fonte. images: URIs (capa + 1 por slide)."""
    acc = ACCS[seed % len(ACCS)]
    hd = head(acc)
    slides = data["slides"][:8]
    total = len(slides) + 2
    img = lambda i: images[i % len(images)] if images else ""
    fonte = html.escape(data.get("fonte", ""))
    credit = '<div style="position:absolute;right:44px;top:112px;font-family:InterB;font-size:16px;letter-spacing:2px;color:rgba(255,255,255,.7);background:rgba(0,0,0,.4);padding:5px 10px;border-radius:5px">IMAGEM: ROCKSTAR GAMES</div>'
    t = data["titulo"]
    pages = [hd + f'''<img class="ph" src="{img(0)}" style="height:1350px">
      <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(13,6,36,.55) 0%,rgba(13,6,36,0) 22%,rgba(13,6,36,0) 42%,rgba(13,6,36,.9) 68%,#0d0624 100%)"></div>
      {brand()}<div class="salva">SALVA ESSE POST</div>
      <div style="position:absolute;left:56px;right:56px;bottom:120px">
        <div class="selo" style="background:{acc};color:#0d0624;margin-bottom:22px">{html.escape(data.get("chamada", "GUIA GTA 6")).upper()}</div>
        <h1 style="font-size:{_fs(t, [(26, 138), (40, 118), (56, 100), (999, 86)])}px">{_mark(t)}</h1>
      </div>
      <div class="handle">@brasileiroemvice</div>
      <div class="swipe">ARRASTA PRO LADO <svg width="44" height="24" viewBox="0 0 44 24"><path d="M2 12h38M30 3l10 9-10 9" fill="none" stroke="{acc}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
      </body></html>''']
    for i, s in enumerate(slides):
        lab, bgc, fg = SELOS.get(str(s.get("selo", "")).upper(), SELOS["DICA"])
        st = s["titulo"]
        pages.append(hd + f'''<img class="ph" src="{img(i + 1)}" style="height:780px">
          <div style="position:absolute;left:0;right:0;top:520px;height:262px;background:linear-gradient(180deg,rgba(13,6,36,0),#0d0624)"></div>
          <div style="position:absolute;left:0;right:0;top:780px;bottom:0;background:linear-gradient(180deg,#0d0624,#1d0b3f)"></div>
          {brand()}<div class="count">{i + 2}/{total}</div>{credit}
          <div style="position:absolute;left:56px;top:640px;width:170px;height:170px;border-radius:50%;background:{acc};color:#0d0624;
               font-family:Anton;font-size:96px;display:flex;align-items:center;justify-content:center;transform:rotate(-5deg);
               box-shadow:8px 8px 0 rgba(0,0,0,.5)">{i + 1:02d}</div>
          <div class="selo" style="position:absolute;left:250px;top:700px;background:{bgc};color:{fg}">{lab}</div>
          <div style="position:absolute;left:56px;right:56px;top:850px">
            <h1 style="font-size:{_fs(st, [(22, 82), (36, 70), (999, 60)])}px">{_mark(st)}</h1>
            <div style="font-size:35px;line-height:1.42;margin-top:22px;color:rgba(255,255,255,.9)">{html.escape(s["texto"])}</div>
          </div>
          <div class="src">{"FONTE: " + fonte.upper() if fonte else ""}</div>
          <div class="handle">@brasileiroemvice</div>
          <div class="swipe">PRÓXIMO <svg width="44" height="24" viewBox="0 0 44 24"><path d="M2 12h38M30 3l10 9-10 9" fill="none" stroke="{acc}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
          </body></html>''')
    pages.append(cta_page(acc, total, total, bg=img(len(slides) + 1)))
    return shot(pages, out_dir, "guia")
