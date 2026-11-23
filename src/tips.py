"""Carrossel de dicas do Tio Vice (mascote da página): capa + 1 slide por dica + slide final."""
import html
import re
from pathlib import Path

from playwright.sync_api import sync_playwright
from PIL import Image

from mascot import mascot_html
from bonecos import boneco

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1350
ACCENTS = ["#ff3d7f", "#ff8a3d", "#7b3cff", "#00b3c7"]

CSS = """
@font-face{font-family:Anton;src:url("%(fonts)s/Anton-Regular.ttf")}
@font-face{font-family:InterB;src:url("%(fonts)s/Inter-Bold.otf")}
@font-face{font-family:InterM;src:url("%(fonts)s/Inter-Medium.otf")}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px;overflow:hidden}
body{background:#f5f0e6;position:relative;font-family:InterM;color:#1a1024}
body:before{content:"";position:absolute;inset:0;background:
  radial-gradient(circle at 20%% 10%%,rgba(255,255,255,.7),transparent 40%%),
  repeating-linear-gradient(0deg,rgba(0,0,0,.018) 0 2px,transparent 2px 6px)}
.mk{background:linear-gradient(transparent 58%%,%(acc)s55 58%%,%(acc)s55 92%%,transparent 92%%);padding:0 6px}
.acc{color:%(acc)s}
.handle{position:absolute;left:56px;bottom:44px;font-family:InterB;font-size:26px;color:#1a1024;opacity:.75}
.count{position:absolute;right:56px;bottom:40px;font-family:Anton;font-size:34px;color:#1a1024;opacity:.8}
.sig{position:absolute;left:56px;top:52px;font-family:InterB;font-size:26px;letter-spacing:3px;color:#fff;background:%(acc)s;padding:10px 18px;border-radius:10px;transform:rotate(-2deg)}
h1{font-family:Anton;text-transform:uppercase;line-height:1.02;color:#1a1024;text-align:center}
.salva{position:absolute;right:56px;top:46px;background:#1a1024;color:#ffc145;font-family:Anton;font-size:32px;padding:10px 20px;transform:rotate(3deg)}
.swipe{position:absolute;right:56px;bottom:44px;font-family:InterB;font-size:26px;letter-spacing:2px;color:#1a1024;background:#ffc145;padding:10px 18px;border-radius:30px}
.spark{position:absolute;stroke:#ffc145;stroke-width:9;stroke-linecap:round}
"""


def _mark(t):
    return re.sub(r"\*(.+?)\*", r'<span class="mk">\1</span>', html.escape(t))


def _shot(pages, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for i, page in enumerate(pages):
            f = out_dir / f"dica_{i+1:02d}.html"
            f.write_text(page, encoding="utf-8")
            pg.goto(f.as_uri())
            pg.wait_for_timeout(300)
            png = out_dir / f"dica_{i+1:02d}.png"
            pg.screenshot(path=str(png))
            jpg = png.with_suffix(".jpg")
            Image.open(png).convert("RGB").save(jpg, quality=92)
            png.unlink()
            f.unlink()
            files.append(jpg)
        b.close()
    return files


def _balao(fala: str, quem: str, acc: str) -> str:
    """Bonequinho sorrindo com balão de fala (o "outro lado" da piada)."""
    if not fala:
        return ""
    return f'''<div style="position:absolute;left:50px;bottom:0">{boneco(quem, 300)}</div>
      <div style="position:absolute;left:40px;bottom:410px;max-width:480px;background:#fff;border:5px solid #1a1024;border-radius:30px;
           padding:22px 28px;font-family:InterB;font-size:34px;line-height:1.25;box-shadow:7px 7px 0 {acc};transform:rotate(-2deg)">
        {html.escape(fala)}
        <div style="position:absolute;left:70px;bottom:-30px;width:0;height:0;border-left:18px solid transparent;border-right:18px solid transparent;border-top:30px solid #1a1024"></div>
        <div style="position:absolute;left:74px;bottom:-21px;width:0;height:0;border-left:14px solid transparent;border-right:14px solid transparent;border-top:24px solid #fff"></div>
      </div>'''


def render_tips(data: dict, out_dir: Path, seed: int = 0) -> list[Path]:
    acc = ACCENTS[seed % len(ACCENTS)]
    css = CSS % dict(fonts=(ROOT / "assets" / "fonts").as_uri(), acc=acc)
    head = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>"
    dicas = data["dicas"][:8]
    total = len(dicas) + 2
    sparks = '''<svg class="spark" style="left:150px;top:640px" width="120" height="120"><path d="M20 20 L60 55 M10 70 L55 75 M40 0 L62 40" fill="none"/></svg>
                <svg class="spark" style="right:150px;top:640px" width="120" height="120"><path d="M100 20 L60 55 M110 70 L65 75 M80 0 L58 40" fill="none"/></svg>'''
    t = data["titulo"]
    fs = 150 if len(t) < 22 else 128 if len(t) < 34 else 108 if len(t) < 48 else 92
    pages = [head + f'''<div class="sig">DICAS DO TIO VICE</div>
      <h1 style="position:absolute;left:60px;right:60px;top:130px;font-size:{fs}px">{_mark(t)}</h1>
      {sparks}
      <div style="position:absolute;left:50%;bottom:-40px;transform:translateX(-50%)">{mascot_html("apontando", 680)}</div>
      <div class="salva">SALVA ESSE POST</div>
      <div class="swipe">ARRASTA →</div></body></html>''']
    exprs = ["joinha", "pensando", "piscada", "surpreso", "rindo", "jogando", "bravo", "sorriso"]
    for i, d in enumerate(dicas):
        pages.append(head + f'''<div class="sig">DICA {i+1} DE {len(dicas)}</div>
          <div style="position:absolute;left:60px;top:150px;width:150px;height:150px;border-radius:50%;background:{acc};color:#fff;
               font-family:Anton;font-size:96px;display:flex;align-items:center;justify-content:center;transform:rotate(-4deg);box-shadow:8px 8px 0 #1a1024">{i+1}</div>
          <div style="position:absolute;left:60px;right:60px;top:345px">
            <div style="font-family:Anton;font-size:76px;line-height:1.05;text-transform:uppercase">{_mark(d["titulo"])}</div>
            <div style="font-size:40px;line-height:1.45;margin-top:28px;max-width:900px">{html.escape(d["texto"])}</div>
          </div>
          {_balao(d.get("balao", ""), data.get("quem", "ela"), acc)}
          <div style="position:absolute;right:-40px;bottom:-40px">{mascot_html(exprs[(i + seed) % len(exprs)], 500 if d.get("balao") else 540)}</div>
          <div class="handle" style="left:auto;right:150px;top:56px;bottom:auto;font-size:24px;opacity:.55">@brasileiroemvice</div><div class="count" style="right:56px;top:52px;bottom:auto;font-size:30px;opacity:.55">{i+2}/{total}</div></body></html>''')
    pages.append(head + f'''<div class="sig">TIO VICE AVISA</div>
      <h1 style="position:absolute;left:60px;right:60px;top:170px;font-size:104px">Salva e manda pra <span class="mk">quem precisa</span> ler isso</h1>
      <div style="position:absolute;left:60px;right:60px;top:520px;text-align:center;font-family:InterB;font-size:44px">Segue o <span class="acc">@brasileiroemvice</span><br>pra mais dicas, games e GTA 6</div>
      <div style="position:absolute;left:50%;bottom:-60px;transform:translateX(-50%)">{mascot_html("comemorando", 600)}</div>
      </body></html>''')
    return _shot(pages, out_dir)
