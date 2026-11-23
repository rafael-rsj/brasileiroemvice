"""Galeria de imagens oficiais do GTA 6 (screenshots publicados pela Rockstar em rockstargames.com/VI).

python src/main.py galeria  -> baixa as imagens, reduz o tamanho e salva em assets/game/
pick(texto)                 -> escolhe uma imagem que combine com o assunto, sem repetir as últimas
"""
import io
import json
import re
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "assets" / "game"
USED = ROOT / "state" / "used_images.json"
PAGE = "https://www.rockstargames.com/VI/downloads/screenshots"
BASE = "https://www.rockstargames.com/VI/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0 Safari/537.36", "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"}

# palavra no assunto -> categorias de imagem que combinam
TOPICS = {
    "jason": ["Jason_Duval", "Jason_and_Lucia"], "lucia": ["Lucia_Caminos", "Jason_and_Lucia"],
    "casal": ["Jason_and_Lucia"], "protagonista": ["Jason_and_Lucia"], "personage": ["Jason_and_Lucia", "Cal_Hampton",
    "Boobie_Ike", "DreQuan_Priest", "Real_Dimez", "Raul_Bautista", "Brian_Heder"],
    "cal": ["Cal_Hampton"], "boobie": ["Boobie_Ike"], "drequan": ["DreQuan_Priest"], "dimez": ["Real_Dimez"],
    "raul": ["Raul_Bautista"], "brian": ["Brian_Heder"],
    "vice city": ["Vice_City"], "cidade": ["Vice_City"], "praia": ["Vice_City", "Leonida_Keys"], "carro": ["Vice_City"],
    "keys": ["Leonida_Keys"], "ilha": ["Leonida_Keys"], "barco": ["Leonida_Keys", "Port_Gellhorn"],
    "port gellhorn": ["Port_Gellhorn"], "ambrosia": ["Ambrosia"], "grassrivers": ["Grassrivers"],
    "jacaré": ["Grassrivers"], "jacare": ["Grassrivers"], "pântano": ["Grassrivers"], "pantano": ["Grassrivers"],
    "kalaga": ["Mount_Kalaga_National_Park"], "caça": ["Mount_Kalaga_National_Park"], "pé grande": ["Mount_Kalaga_National_Park"],
    "natureza": ["Mount_Kalaga_National_Park", "Grassrivers"], "mapa": ["Vice_City", "Leonida_Keys", "Grassrivers"],
    "leonida": ["Vice_City", "Leonida_Keys", "Grassrivers", "Ambrosia", "Port_Gellhorn", "Mount_Kalaga_National_Park"],
}


def fetch_gallery(max_w: int = 1440) -> int:
    """Baixa todos os screenshots oficiais (menos os de edição especial) para assets/game/."""
    GAME.mkdir(parents=True, exist_ok=True)
    html = requests.get(PAGE, headers=UA, timeout=30).text
    paths = sorted(set(re.findall(r"_next/static/media/([A-Za-z_]+_\d+)\.[^\"\\\s]+?\.jpg", html)))
    full = {m.group(1): m.group(0) for m in re.finditer(r"_next/static/media/([A-Za-z_]+_\d+)\.[^\"\\\s]+?\.jpg", html)}
    n = 0
    for name in paths:
        if name.startswith(("ULTIMATE", "VINTAGE")):
            continue
        out = GAME / f"{name}.jpg"
        if out.exists():
            continue
        try:
            r = requests.get(BASE + full[name], headers=UA, timeout=30)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if im.width > max_w:
                im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
            im.save(out, quality=84, optimize=True, progressive=True)
            n += 1
        except Exception as e:  # uma imagem falhar não derruba as outras
            print("falhou", name, e)
    print(f"{n} imagens novas na galeria ({len(list(GAME.glob('*.jpg')))} no total)")
    return n


def _all() -> list[Path]:
    return sorted(p for p in GAME.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))


def pick(text: str = "", seed: int = 0, avoid: set | None = None) -> Path | None:
    """Imagem oficial que combine com o assunto. Não repete as 40 últimas usadas."""
    imgs = _all()
    if not imgs:
        return None
    used = json.loads(USED.read_text()) if USED.exists() else []
    avoid = set(avoid or ()) | set(used[-40:])
    t = (text or "").lower()
    cats = [c for k, cs in TOPICS.items() if k in t for c in cs]
    pool = [p for p in imgs if cats and any(p.stem.startswith(c + "_") for c in cats)]
    fresh = [p for p in pool if p.name not in avoid] or [p for p in imgs if p.name not in avoid] or imgs
    choice = fresh[(seed * 7919) % len(fresh)]
    used.append(choice.name)
    USED.parent.mkdir(exist_ok=True)
    USED.write_text(json.dumps(used[-200:]))
    return choice
