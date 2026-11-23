"""Gera o kit de poses do Tio Vice com a IA de imagem do Google (Gemini). Roda UMA vez (custo de centavos).

python src/main.py mascote          -> gera só as poses que ainda não existem em assets/mascote/
REFAZER=1 python src/main.py mascote -> apaga e gera tudo de novo (inclusive o rosto de referência)

Cada pose sai em PNG com fundo transparente. O carrossel de dicas e os posts usam essas imagens;
enquanto elas não existem, o robô usa o desenho vetorial antigo (mascot.py).
"""
import base64
import io
import os
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "mascote"
API = "https://generativelanguage.googleapis.com/v1beta"

PERSONAGEM = """Original cartoon mascot character called "Tio Vice": a charismatic Brazilian man around 55 years old,
warm tanned skin, friendly crow's feet, big expressive brown eyes, thick full white-grey beard, well groomed and fluffy,
short grey hair on the sides. Shirtless, athletic and well defined muscular body (strong arms, chest and abs, not
bodybuilder), covered in colorful old-school tattoos: a sunset with palm trees on the chest, a flamingo on one arm,
a compass rose and waves on the other, small stars on the shoulder. Thin gold chain necklace.
Wears a snapback baseball cap with a sunset gradient (hot pink to orange to purple) and a small white palm tree logo
on the front. Always holds a modern WHITE wireless game controller with black buttons, generic design, no brand logos.
Style: premium 3D animated feature film character, stylized but detailed, soft studio lighting, subsurface skin,
crisp clean edges, vibrant colors, friendly and funny personality, very appealing.
"""

FUNDO = """Framing: from the waist up, centered, the whole head, cap and hands fully visible with a margin around them.
Background: perfectly flat solid pure green chroma key (#00FF00), no shadows on the background, no floor, no gradient,
no text, no logos, no watermark. Do NOT use any green color on the character, cap, tattoos or controller."""

POSES = {
    "sorriso": "Big warm friendly smile looking at the viewer, holding the white controller with both hands at chest height.",
    "apontando": "Smiling confidently and pointing with his index finger up and to the left side of the image, the controller in the other hand.",
    "joinha": "Grinning and giving a big thumbs up toward the viewer with one hand, the controller in the other hand.",
    "piscada": "Winking one eye with a playful smirk, resting the controller casually on his shoulder.",
    "surpreso": "Shocked and amazed expression, eyebrows up, mouth wide open in an 'O', holding the controller close to his face.",
    "pensando": "Thinking expression, one eyebrow raised, scratching his beard with one hand, the controller in the other hand.",
    "rindo": "Laughing out loud, eyes squeezed, head slightly tilted back, holding the controller against his belly.",
    "bravo": "Playfully annoyed, frowning with a funny pout, arms crossed with the controller in one hand.",
    "jogando": "Concentrated playing a game, tongue slightly out, both thumbs on the controller, leaning forward.",
    "comemorando": "Celebrating a victory, both arms raised, the controller lifted high in one hand, huge happy smile.",
}


def _key():
    return os.environ["GEMINI_API_KEY"]


def _model() -> str:
    """Escolhe o melhor modelo de imagem do Gemini disponível na conta (o mais novo, preferindo o 'pro')."""
    wanted = os.environ.get("GEMINI_IMAGE_MODEL")
    if wanted:
        return wanted
    r = requests.get(f"{API}/models", params={"pageSize": 1000}, headers={"x-goog-api-key": _key()}, timeout=30)
    r.raise_for_status()
    ms = [m["name"].split("/")[-1] for m in r.json().get("models", [])
          if "generateContent" in m.get("supportedGenerationMethods", []) and "image" in m["name"]
          and "imagen" not in m["name"]]
    if not ms:
        raise SystemExit("Nenhum modelo de imagem do Gemini disponível nessa chave.")

    def score(n):
        import re
        v = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return (float(v.group(1)) if v else 0, "pro" in n, "preview" not in n)
    best = sorted(ms, key=score)[-1]
    print("Modelo de imagem:", best, "| disponíveis:", ms)
    return best


def _generate(model: str, prompt: str, ref: Path | None = None) -> Image.Image:
    parts = [{"text": prompt}]
    if ref:
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(ref.read_bytes()).decode()}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": "1:1"}}}
    for tent in range(4):
        r = requests.post(f"{API}/models/{model}:generateContent", json=body,
                          headers={"x-goog-api-key": _key()}, timeout=180)
        if r.status_code == 400 and "imageConfig" in r.text and "imageConfig" in body["generationConfig"]:
            body["generationConfig"].pop("imageConfig")  # modelo mais antigo: sem proporção
            continue
        if r.status_code in (429, 500, 503):
            time.sleep(20 * (tent + 1))
            continue
        r.raise_for_status()
        for c in r.json().get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                d = p.get("inline_data") or p.get("inlineData")
                if d:
                    return Image.open(io.BytesIO(base64.b64decode(d["data"]))).convert("RGB")
        print("sem imagem na resposta, tentando de novo:", str(r.json())[:300])
        time.sleep(5)
    raise RuntimeError("Gemini não devolveu imagem: " + r.text[:500])


def cutout(im: Image.Image) -> Image.Image:
    """Remove o fundo verde (só o verde ligado às bordas) e tira o reflexo verde do contorno."""
    from scipy import ndimage
    a = np.asarray(im).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g > 110) & (g - np.maximum(r, b) > 45)
    lab, _ = ndimage.label(green)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    near = ndimage.binary_dilation(bg, iterations=3) & ~bg
    # despill: no contorno o verde não passa do maior entre vermelho e azul
    g2 = np.where(near, np.minimum(g, np.maximum(r, b)), g)
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    rgba = np.dstack([r, g2, b, alpha]).clip(0, 255).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    al = out.getchannel("A").filter(ImageFilter.GaussianBlur(0.8))
    out.putalpha(al)
    box = out.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
    return out.crop(box) if box else out


def make_kit():
    OUT.mkdir(parents=True, exist_ok=True)
    if os.environ.get("REFAZER") == "1":
        for f in OUT.glob("*.png"):
            f.unlink()
    model = _model()
    ref = OUT / "_referencia.png"
    if not ref.exists():
        img = _generate(model, PERSONAGEM + "\nPose: " + POSES["sorriso"] + "\n" + FUNDO)
        img.save(ref)
    feitos = []
    for nome, pose in POSES.items():
        alvo = OUT / f"{nome}.png"
        if alvo.exists():
            continue
        prompt = ("Use the attached image as the exact character reference: SAME man, same face, same beard, same cap, "
                  "same tattoos, same controller, same art style and lighting. Only change the pose and expression.\n"
                  + PERSONAGEM + "\nPose and expression: " + pose + "\n" + FUNDO)
        try:
            img = _generate(model, prompt, ref)
        except Exception as e:
            print("falhou", nome, e)
            continue
        cutout(img).save(alvo)
        feitos.append(nome)
        print("pose pronta:", nome)
        time.sleep(4)
    _sheet()
    return feitos


def _sheet():
    """Folha de prova com todas as poses (media/preview/mascote.jpg) para conferir o resultado."""
    poses = [OUT / f"{n}.png" for n in POSES if (OUT / f"{n}.png").exists()]
    if not poses:
        return
    cell = 400
    cols = 5
    rows = (len(poses) + cols - 1) // cols
    sheet = Image.new("RGB", (cell * cols, cell * rows), (245, 240, 230))
    for i, p in enumerate(poses):
        im = Image.open(p)
        im.thumbnail((cell - 20, cell - 20))
        sheet.paste(im, ((i % cols) * cell + (cell - im.width) // 2, (i // cols) * cell + cell - im.height - 5), im)
    prev = ROOT / "media" / "preview"
    prev.mkdir(parents=True, exist_ok=True)
    sheet.save(prev / "mascote.jpg", quality=88)
