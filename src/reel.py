"""Reels verticais (1080x1920) do guizo a partir de um post já publicado.

Fundo: foto da matéria com zoom lento (ou fundo listrado da marca).
Camadas animadas: selo, título, explicação e "segue o guizo".
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

from music import make_track

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30
VOZES = ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural"]

def _layers(d, tmp):
    from art import css, guizo, seal, mark, esc, fs, HANDLE, Y, K, R
    base = css(W, H).replace(f"background:{K}", "background:transparent")
    selo = esc(d.get("selo", "NOVIDADE"))
    cor_selo = R if d.get("tipo") == "ALERTA" else Y
    txt_selo = "#fff" if d.get("tipo") == "ALERTA" else K
    info = " · ".join(x for x in [d.get("onde"), d.get("quando")] if x)
    pages = {
        "hud": f'''<div class="abs" style="left:56px;top:90px">{seal(size=46)}</div>
                  {f'<div class="credit" style="top:110px;right:30px;font-size:15px">{esc(d["credit"])}</div>' if d.get("credit") else ""}
                  <div class="abs" style="left:56px;bottom:70px;font-weight:700;font-size:30px;opacity:.85">{HANDLE}</div>''',
        "title": f'''<div class="abs" style="left:60px;right:60px;bottom:360px"><span class="tag" style="background:{cor_selo};color:{txt_selo};font-size:32px">{selo}</span>
                   <h1 style="font-size:{fs(d["titulo"], [(34, 132), (56, 112), (999, 94)])}px;margin-top:30px;text-shadow:0 4px 18px rgba(0,0,0,.5)">{mark(d["titulo"])}</h1>
                   {f'<div style="font-weight:700;font-size:40px;margin-top:26px">📍 {esc(info)}</div>' if info else ""}</div>''',
        "text": f'''<div class="abs box" style="left:56px;right:56px;bottom:330px;background:rgba(17,17,17,.88)">
                   <div style="font-weight:600;font-size:46px;line-height:1.42">{esc(d.get("texto", ""))}</div></div>''',
        "cta": f'''<div class="abs" style="inset:0;background:rgba(17,17,17,.82)"></div>
                  <div class="abs" style="left:0;right:0;top:520px;display:flex;justify-content:center">{guizo(190)}</div>
                  <h1 class="abs" style="left:60px;right:60px;top:880px;text-align:center;font-size:110px">segue o <span style="color:{Y}">guizo</span></h1>
                  <div class="abs" style="left:60px;right:60px;top:1040px;text-align:center;font-weight:700;font-size:44px;color:#ddd">tudo o que acontece em Cascavel</div>''',
    }
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for name, body in pages.items():
            f = tmp / f"{name}.html"
            f.write_text(f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{base}</style></head><body>{body}</body></html>", encoding="utf-8")
            pg.goto(f.as_uri())
            pg.wait_for_timeout(300)
            out[name] = tmp / f"{name}.png"
            pg.screenshot(path=str(out[name]), omit_background=True)
        bgf = tmp / "bg.html"
        inner = (f'<img src="{html.escape(d["img"])}" style="width:100%;height:100%;object-fit:cover">' if d.get("img")
                 else f'<div style="width:100%;height:100%;background:repeating-linear-gradient(-45deg,#1a1a1a 0 60px,#111 60px 120px)"></div>')
        bgf.write_text(f"<html><body style='margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#111'>{inner}"
                       f"<div style='position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.5),rgba(0,0,0,.05) 28%,rgba(0,0,0,.2) 52%,rgba(0,0,0,.92))'></div></body></html>", encoding="utf-8")
        pg2 = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg2.goto(bgf.as_uri())
        try:
            pg2.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
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

    L = _layers(d, tmp)
    music = make_track(tmp / "musica.wav", D + 0.5, seed)

    # linha do tempo das camadas
    has_dat = False
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
