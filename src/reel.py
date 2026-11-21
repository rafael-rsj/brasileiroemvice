"""Monta reels verticais (1080x1920) a partir de uma notícia já publicada.

Fundo: imagem do jogo (ou cenário próprio) com zoom lento.
Camadas animadas: HUD, manchete, dado em destaque, explicação e "Siga".
Áudio: trilha synthwave própria (music.py) e, quando fizer sentido, narração com voz neural grátis (edge-tts).
"""
import asyncio
import html
import json
import random
import re
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

from backgrounds import PALETTES, scene_svg
from music import make_track

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30
VOZES = ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural"]

CSS = """
@font-face{font-family:Anton;src:url("%(fonts)s/Anton-Regular.ttf")}
@font-face{font-family:InterB;src:url("%(fonts)s/Inter-Bold.otf")}
@font-face{font-family:InterM;src:url("%(fonts)s/Inter-Medium.otf")}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:transparent;overflow:hidden}
.acc{color:%(acc)s}
.top{position:absolute;top:70px;left:56px;right:56px;display:flex;justify-content:space-between;align-items:center}
.brand{display:flex;gap:18px;align-items:center}
.brand img{width:92px;height:92px;border-radius:50%%;border:5px solid #fff}
.brand b{font-family:Anton;color:#fff;font-size:46px;text-shadow:0 4px 0 #0d0624;display:block;line-height:1}
.brand i{font-style:normal;font-family:InterB;color:%(acc)s;letter-spacing:4px;font-size:22px}
.live{font-family:InterB;color:#fff;background:#ff2d55;padding:14px 22px;border-radius:10px;font-size:26px;letter-spacing:3px}
.foot{position:absolute;bottom:0;left:0;right:0;height:110px;background:linear-gradient(90deg,%(f1)s,%(f2)s);display:flex;align-items:center;justify-content:space-between;padding:0 56px;font-family:InterB;font-size:30px;color:#0d0624}
.block{position:absolute;left:60px;right:60px}
.tag{display:inline-block;font-family:InterB;font-size:30px;letter-spacing:5px;padding:12px 24px;border-radius:8px;background:%(acc)s;color:#0d0624;margin-bottom:26px}
h1{font-family:Anton;color:#fff;text-transform:uppercase;line-height:1.03;text-shadow:0 5px 0 #0d0624}
h1 mark{background:none;color:%(acc)s}
.card{background:rgba(13,6,36,.82);border:5px solid %(acc)s;border-radius:28px;padding:44px 48px}
.rot{font-family:InterB;color:#fff;font-size:48px}
.val{font-family:Anton;color:%(acc)s;font-size:170px;line-height:1.05;text-shadow:0 6px 0 #0d0624}
.txt{font-family:InterM;color:#fff;font-size:44px;line-height:1.42}
.cta{text-align:center}
.cta b{font-family:Anton;font-size:120px;color:#fff;line-height:1.05;text-shadow:0 6px 0 #0d0624;display:block}
.cta i{font-style:normal;font-family:InterB;font-size:40px;color:#fff;opacity:.9}
.credit{position:absolute;top:190px;right:56px;font-family:InterB;font-size:22px;letter-spacing:2px;color:rgba(255,255,255,.8);background:rgba(0,0,0,.4);padding:8px 14px;border-radius:8px}
"""


def _mark(t):
    return re.sub(r"\*(.+?)\*", r"<mark>\1</mark>", html.escape(t))


def _fs(t, base=128):
    n = len(t.replace("*", ""))
    return base + 16 if n <= 36 else base if n <= 60 else int(base * .82) if n <= 90 else int(base * .7)


def _layers(d, theme, tmp):
    fonts, assets = (ROOT / "assets" / "fonts").as_uri(), (ROOT / "assets").as_uri()
    css = CSS % dict(fonts=fonts, acc=theme["acc"], f1=theme["f1"], f2=theme["f2"])
    tag_label = {"OFICIAL": "OFICIAL", "RUMOR": "RUMOR • NÃO CONFIRMADO", "CURIOSIDADE": "VOCÊ SABIA?"}.get(d["tag"], "NOTÍCIA")
    credit = f'<div class="credit">{html.escape(d["credit"])}</div>' if d.get("credit") else ""
    pages = {
        "hud": f'''<div class="top"><div class="brand"><img src="{assets}/perfil.png"><div><b>BRASILEIRO EM VICE</b><i>PLANTÃO GTA 6</i></div></div><div class="live">● AO VIVO</div></div>{credit}
                  <div class="foot"><span>@brasileiroemvice</span><span>{html.escape("Fonte: " + d["fonte"]) if d.get("fonte") else ""}</span></div>''',
        "title": f'''<div class="block" style="bottom:330px"><div class="tag">{tag_label}</div><h1 style="font-size:{_fs(d["titulo"])}px">{_mark(d["titulo"])}</h1></div>''',
        "text": f'''<div class="block card" style="bottom:300px"><div class="txt">{html.escape(d.get("texto", ""))}</div></div>''',
        "cta": f'''<div class="block cta" style="top:760px"><b>SIGA O<br><span class="acc">@BRASILEIROEMVICE</span></b><i>Tudo de GTA 6, todo dia</i></div>''',
    }
    if d.get("valor"):
        pages["datum"] = f'''<div class="block card" style="top:700px;text-align:center"><div class="rot">{html.escape(d.get("rotulo", ""))}</div><div class="val">{html.escape(d["valor"])}</div></div>'''
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for name, body in pages.items():
            f = tmp / f"{name}.html"
            f.write_text(f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>", encoding="utf-8")
            pg.goto(f.as_uri())
            pg.wait_for_timeout(250)
            out[name] = tmp / f"{name}.png"
            pg.screenshot(path=str(out[name]), omit_background=True)
        # fundo: imagem do jogo ou cenário próprio, em 2x para o zoom
        bgf = tmp / "bg.html"
        inner = f'<img src="{html.escape(d["img"])}" style="width:100%;height:100%;object-fit:cover">' if d.get("img") else scene_svg(d["seed"], W, H)
        bgf.write_text(f"<html><body style='margin:0;width:{W}px;height:{H}px;overflow:hidden'>{inner}"
                       f"<div style='position:absolute;inset:0;background:linear-gradient(180deg,rgba(13,6,36,.55),rgba(13,6,36,.05) 30%,rgba(13,6,36,.15) 55%,rgba(13,6,36,.9))'></div></body></html>", encoding="utf-8")
        pg2 = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg2.goto(bgf.as_uri())
        pg2.wait_for_load_state("networkidle")
        pg2.wait_for_timeout(400)
        out["bg"] = tmp / "bg.png"
        pg2.screenshot(path=str(out["bg"]))
        b.close()
    return out


async def _tts(text, voice, path):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate="+8%").save(str(path))


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def make_reel(d: dict, out: Path, narrar: bool, seed: int) -> Path:
    """d: titulo, tag, fonte, img, credit, rotulo, valor, texto, roteiro."""
    rnd = random.Random(seed)
    pal = PALETTES[seed % len(PALETTES)]["name"]
    theme = {"sunset": dict(acc="#ffc145", f1="#ff3d7f", f2="#ff8a3d"), "miami": dict(acc="#22e1ff", f1="#ff6f91", f2="#22e1ff"),
             "night": dict(acc="#c9a7ff", f1="#7b3cff", f2="#ff3d9a"), "golden": dict(acc="#ffcf4a", f1="#ff7b39", f2="#ffcf4a")}[pal]
    d = dict(d, seed=seed)
    tmp = out.parent / (out.stem + "_tmp")
    tmp.mkdir(parents=True, exist_ok=True)

    voice = None
    if narrar and d.get("roteiro"):
        try:
            voice = tmp / "voz.mp3"
            asyncio.run(_tts(d["roteiro"], rnd.choice(VOZES), voice))
        except Exception as e:  # sem voz, segue só com música
            print("[narração indisponível]", e)
            voice = None
    vd = _dur(voice) if voice else 0
    D = max(16.0, min(45.0, vd + 4.0)) if voice else rnd.choice([15.0, 17.0, 19.0])

    L = _layers(d, theme, tmp)
    music = make_track(tmp / "musica.wav", D + 0.5, seed)

    # linha do tempo das camadas
    has_dat = "datum" in L
    t_title = (0.5, D * (0.42 if has_dat else 0.5))
    t_dat = (t_title[1], D * 0.66) if has_dat else None
    t_text = ((t_dat or t_title)[1], D - 3.2)
    t_cta = (D - 3.2, D)
    seq = [("title", t_title)] + ([("datum", t_dat)] if has_dat else []) + [("text", t_text), ("cta", t_cta)]

    inputs = ["-loop", "1", "-t", f"{D}", "-i", str(L["bg"]), "-loop", "1", "-t", f"{D}", "-i", str(L["hud"])]
    for name, _ in seq:
        inputs += ["-loop", "1", "-t", f"{D}", "-i", str(L[name])]
    inputs += ["-i", str(music)]
    if voice:
        inputs += ["-i", str(voice)]

    zoom_dir = rnd.choice(["in", "out"])
    z = "min(1+0.0009*on,1.18)" if zoom_dir == "in" else "max(1.18-0.0009*on,1)"
    fc = [f"[0:v]scale={W*2}:{H*2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(D*FPS)}:s={W}x{H}:fps={FPS},format=yuva420p[bg]",
          "[1:v]format=rgba,fade=in:st=0:d=0.5:alpha=1[hud]",
          "[bg][hud]overlay=0:0[v0]"]
    last = "v0"
    for i, (name, (a, b)) in enumerate(seq):
        idx = i + 2
        fc.append(f"[{idx}:v]format=rgba,fade=in:st={a:.2f}:d=0.35:alpha=1,fade=out:st={b-0.35:.2f}:d=0.35:alpha=1[l{i}]")
        # entra subindo um pouco
        fc.append(f"[{last}][l{i}]overlay=x=0:y='if(lt(t,{a:.2f}+0.35),40*(1-(t-{a:.2f})/0.35),0)':enable='between(t,{a:.2f},{b:.2f})'[v{i+1}]")
        last = f"v{i+1}"
    mi = 2 + len(seq)
    if voice:
        fc.append(f"[{mi}:a]volume=0.22[m];[{mi+1}:a]adelay=500|500,volume=1.6[vz];[m][vz]amix=inputs=2:duration=first:dropout_transition=0[a]")
    else:
        fc.append(f"[{mi}:a]volume=0.9[a]")
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "[a]",
           "-t", f"{D}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    (tmp / "info.json").write_text(json.dumps({"duracao": D, "narrado": bool(voice), "zoom": zoom_dir}), encoding="utf-8")
    return out
