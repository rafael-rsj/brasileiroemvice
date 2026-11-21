"""Gera as artes (feed 4:5 e story 9:16) a partir do template HTML com o HUD próprio."""
import html
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "card.html"

TAGS = {
    "NOTICIA": "NOTÍCIA",
    "OFICIAL": "OFICIAL",
    "RUMOR": "RUMOR • NÃO CONFIRMADO",
    "COMPARACAO": "6 vs 5 vs 4",
    "CURIOSIDADE": "VOCÊ SABIA?",
}

FORMATS = {
    "feed": {"W": 1080, "H": 1350, "CONTENT_B": 130, "FS_BASE": 92},
    "story": {"W": 1080, "H": 1920, "CONTENT_B": 330, "FS_BASE": 100},
}


def _title_html(title: str) -> str:
    """Escapa o título e pinta de amarelo o trecho entre *asteriscos*."""
    t = html.escape(title)
    return re.sub(r"\*(.+?)\*", r"<mark>\1</mark>", t)


def _font_size(title: str, base: int) -> int:
    n = len(title.replace("*", ""))
    if n <= 40:
        return base + 12
    if n <= 70:
        return base
    if n <= 100:
        return int(base * 0.82)
    return int(base * 0.7)


def render(out_path: Path, *, title: str, sub: str = "", tag: str = "NOTICIA",
           source: str = "", image_url: str | None = None, fmt: str = "feed",
           ai_image: bool = False, stars: int = 3, kicker: str = "PLANTÃO GTA 6",
           live: str = "AO VIVO") -> Path:
    f = FORMATS[fmt]
    stars = max(0, min(5, stars))
    star_html = "".join('<span>★</span>' for _ in range(stars)) + "".join(
        '<span class="off">★</span>' for _ in range(5 - stars))
    bg = f'<img src="{html.escape(image_url)}">' if image_url else ""
    values = {
        "W": f["W"], "H": f["H"], "CONTENT_B": f["CONTENT_B"],
        "FS": _font_size(title, f["FS_BASE"]),
        "FONTS": (ROOT / "assets" / "fonts").as_uri(),
        "ASSETS": (ROOT / "assets").as_uri(),
        "BG": bg,
        "TAG": tag if tag in TAGS else "NOTICIA",
        "TAG_LABEL": TAGS.get(tag, "NOTÍCIA"),
        "TITLE": _title_html(title),
        "SUB": html.escape(sub),
        "SOURCE": html.escape(f"Fonte: {source}" if source else ""),
        "STARS": star_html,
        "KICKER": html.escape(kicker),
        "LIVE": html.escape(live),
        "AI": '<div class="ai">IMAGEM GERADA POR IA</div>' if ai_image else "",
    }
    page = TEMPLATE.read_text(encoding="utf-8")
    for k, v in values.items():
        page = page.replace("{{" + k + "}}", str(v))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".html")
    tmp.write_text(page, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": f["W"], "height": f["H"]})
        pg.goto(tmp.as_uri())
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(out_path.with_suffix(".png")), type="png")
        b.close()
    tmp.unlink(missing_ok=True)
    # Instagram exige JPEG para imagens de feed
    from PIL import Image
    jpg = out_path.with_suffix(".jpg")
    Image.open(out_path.with_suffix(".png")).convert("RGB").save(jpg, quality=92)
    out_path.with_suffix(".png").unlink()
    return jpg
