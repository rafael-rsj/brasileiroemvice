"""Recorta as poses do Tio Vice a partir das imagens geradas no ChatGPT (assets/mascote/originais/).

originais/1/*.png -> 1 pose (sorriso)
originais/2/*.png -> grade 2x2: apontando, joinha, piscada, surpreso
originais/3/*.png -> grade 2x2: pensando, rindo, jogando, comemorando
Tira o fundo (transparente ou branco), separa cada pose e salva em assets/mascote/<pose>.png
"""
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "assets" / "mascote"
GRADES = {"1": ["sorriso"], "2": ["apontando", "joinha", "piscada", "surpreso"],
          "3": ["pensando", "rindo", "jogando", "comemorando"]}
EXTRA = {"bravo": "jogando"}  # pose que não veio: usa a mais parecida


def sem_fundo(im: Image.Image) -> Image.Image:
    """Mantém a transparência que já existe e remove o fundo branco ligado às bordas."""
    a = np.array(im.convert("RGBA")).astype(float)
    al = a[..., 3:4] / 255.0
    rgb = a[..., :3] * al + 255 * (1 - al)
    mx, mn = rgb.max(-1), rgb.min(-1)
    near = (mn > 222) & ((mx - mn) < 28)
    lab, _ = ndimage.label(near)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    alpha = np.where(bg, 0, a[..., 3]).astype(np.uint8)
    out = Image.fromarray(np.dstack([a[..., :3].astype(np.uint8), alpha]), "RGBA")
    out.putalpha(out.getchannel("A").filter(ImageFilter.GaussianBlur(0.7)))
    return out


def recorte(o: Image.Image, pad: int = 6) -> Image.Image:
    box = o.getchannel("A").point(lambda v: 255 if v > 30 else 0).getbbox()
    return o.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(o.width, box[2] + pad), min(o.height, box[3] + pad)))


def separar(o: Image.Image, nomes: list[str]):
    if len(nomes) == 1:
        im = recorte(o)
        im.thumbnail((900, 900))
        im.save(M / f"{nomes[0]}.png", optimize=True)
        return
    A = np.array(o.getchannel("A")) > 30
    lab, _ = ndimage.label(A)
    W, H = o.size
    partes = {q: np.zeros_like(A) for q in range(4)}
    for i in range(1, lab.max() + 1):
        m = lab == i
        if m.sum() < 200:
            continue
        cy, cx = ndimage.center_of_mass(m)
        partes[int(cy > H / 2) * 2 + int(cx > W / 2)] |= m
    arr = np.array(o)
    for q, nome in enumerate(nomes):
        m = ndimage.binary_dilation(partes[q], iterations=3)
        x = arr.copy()
        x[..., 3] = np.where(m, x[..., 3], 0)
        recorte(Image.fromarray(x, "RGBA")).save(M / f"{nome}.png", optimize=True)


def folha():
    poses = [p for p in sorted(M.glob("*.png")) if not p.name.startswith("_")]
    cell, cols = 360, 5
    s = Image.new("RGB", (cell * cols, cell * ((len(poses) + cols - 1) // cols)), (40, 15, 70))
    for i, p in enumerate(poses):
        im = Image.open(p)
        im.thumbnail((cell - 10, cell - 10))
        s.paste(im, ((i % cols) * cell + (cell - im.width) // 2, (i // cols) * cell + cell - im.height), im)
    prev = ROOT / "media" / "preview"
    prev.mkdir(parents=True, exist_ok=True)
    s.save(prev / "mascote.jpg", quality=88)


def main():
    for pasta, nomes in GRADES.items():
        arqs = sorted((M / "originais" / pasta).glob("*.png"))
        if arqs:
            separar(sem_fundo(Image.open(arqs[0])), nomes)
            print("ok:", nomes)
    for nome, base in EXTRA.items():
        if (M / f"{base}.png").exists():
            shutil.copy(M / f"{base}.png", M / f"{nome}.png")
    folha()
    subprocess.run(["git", "config", "user.name", "brasileiroemvice-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", "assets/mascote", "media/preview"], check=True)
    subprocess.run(["git", "commit", "-m", "Tio Vice: poses recortadas"], check=False)
    subprocess.run(["git", "pull", "--rebase"], check=False)
    subprocess.run(["git", "push"], check=True)


if __name__ == "__main__":
    main()
