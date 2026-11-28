"""Prepara a marca do guizo a partir das imagens geradas no GPT (assets/brand/src/<pasta>/*.png).

src/logo    -> simbolo.png (guizo com contorno, fundo transparente)
src/folha   -> selo.png (cápsula preta "guizo") — folha 2x2 das variações da logo
src/mascote -> mascote.png
src/poses   -> mascote_atencao, mascote_apontando, mascote_festa, mascote_frio (folha 2x2)
src/cidade  -> fundo_cidade.jpg (1080x1350)
Roda no GitHub Actions: Actions -> Tarefas -> comando "recortar".
"""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "assets" / "brand"


def first(pasta):
    fs = sorted((B / "src" / pasta).glob("*.png")) + sorted((B / "src" / pasta).glob("*.jpg"))
    return fs[0] if fs else None


def crop_alpha(im, pad=8):
    b = im.getchannel("A").point(lambda v: 255 if v > 30 else 0).getbbox()
    return im.crop((max(0, b[0] - pad), max(0, b[1] - pad), min(im.width, b[2] + pad), min(im.height, b[3] + pad)))


def no_white(im):
    """Fundo branco/creme ligado às bordas vira transparente (se a imagem não veio transparente)."""
    a = np.array(im.convert("RGBA")).astype(float)
    if (a[..., 3] < 10).mean() > 0.05:
        return im.convert("RGBA")
    rgb = a[..., :3]
    near = (rgb.min(-1) > 215) & ((rgb.max(-1) - rgb.min(-1)) < 30)
    lab, _ = ndimage.label(near)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    a[..., 3] = np.where(np.isin(lab, list(border)), 0, 255)
    out = Image.fromarray(a.astype(np.uint8), "RGBA")
    out.putalpha(out.getchannel("A").filter(ImageFilter.GaussianBlur(0.7)))
    return out


def main():
    f = first("logo")
    if f:
        crop_alpha(no_white(Image.open(f))).save(B / "simbolo.png", optimize=True)
    f = first("folha")
    if f:  # selo = maior região escura no quadrante de baixo à direita
        im = Image.open(f).convert("RGB")
        a = np.array(im).astype(int)
        h, w = a.shape[:2]
        dark = np.zeros(a.shape[:2], bool)
        dark[h // 2:, w // 2:] = a[h // 2:, w // 2:].max(-1) < 60
        filled = ndimage.binary_fill_holes(dark)
        lab, _ = ndimage.label(filled)
        sizes = ndimage.sum(filled, lab, range(1, lab.max() + 1))
        k = int(np.argmax(sizes)) + 1
        sl = ndimage.find_objects(lab)[k - 1]
        arr = np.array(im.convert("RGBA"))
        arr[..., 3] = np.where(lab == k, 255, 0)
        o = Image.fromarray(arr, "RGBA").crop((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
        o.putalpha(o.getchannel("A").filter(ImageFilter.GaussianBlur(0.8)))
        o.save(B / "selo.png", optimize=True)
    f = first("mascote")
    if f:
        im = crop_alpha(no_white(Image.open(f)))
        im.thumbnail((900, 900))
        im.save(B / "mascote.png", optimize=True)
    f = first("poses")
    if f:
        p = no_white(Image.open(f))
        A = np.array(p.getchannel("A")) > 30
        lab, _ = ndimage.label(A)
        W, H = p.size
        quad = {q: np.zeros_like(A) for q in range(4)}
        for i in range(1, lab.max() + 1):
            m = lab == i
            if m.sum() < 150:
                continue
            cy, cx = ndimage.center_of_mass(m)
            quad[int(cy > H / 2) * 2 + int(cx > W / 2)] |= m
        arr = np.array(p)
        for q, n in enumerate(["mascote_atencao", "mascote_apontando", "mascote_festa", "mascote_frio"]):
            x = arr.copy()
            x[..., 3] = np.where(ndimage.binary_dilation(quad[q], iterations=2), x[..., 3], 0)
            crop_alpha(Image.fromarray(x, "RGBA")).save(B / f"{n}.png", optimize=True)
    f = first("cidade")
    if f:
        Image.open(f).convert("RGB").resize((1080, 1350), Image.LANCZOS).save(B / "fundo_cidade.jpg", quality=88)
    print("marca pronta:", sorted(p.name for p in B.glob("*.*")))
    subprocess.run(["git", "config", "user.name", "guizo-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", "assets/brand"], check=True)
    subprocess.run(["git", "commit", "-m", "marca do guizo recortada"], check=False)
    subprocess.run(["git", "pull", "--rebase"], check=False)
    subprocess.run(["git", "push"], check=True)


if __name__ == "__main__":
    main()
