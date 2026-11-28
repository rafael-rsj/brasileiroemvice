"""Lê as páginas de agenda de Cascavel (com navegador, porque muitas montam a lista via JavaScript)
e devolve o texto de cada uma para a IA montar a agenda do fim de semana."""
import re

from playwright.sync_api import sync_playwright

from news import _fetch_feed, load_cfg


# Fotos dos cards de evento (banner da divulgação), com o texto do card para a IA casar com o evento certo
IMGS_JS = """() => [...document.images].filter(i => (i.naturalWidth || i.width) >= 300)
  .map(i => { const a = i.closest('a') || i.parentElement; let src = i.currentSrc || i.src;
    return {src, link: (i.closest('a') || {}).href || '', t: ((i.alt || '') + ' ' + (a ? a.innerText : '')).replace(/\\s+/g, ' ').trim().slice(0, 90)} })
  .filter(x => x.src.startsWith('http') && !/logo|icon|avatar|sprite|banner-app/i.test(x.src))"""


def read_sources(max_chars: int = 9000) -> list[dict]:
    cfg = load_cfg()
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(locale="pt-BR", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
        pg = ctx.new_page()
        for src in cfg.get("agenda", []):
            try:
                if "news.google." in src["url"]:
                    feed = _fetch_feed(src["url"])
                    txt = "\n".join(f"- {e.get('title', '')}" for e in feed.entries[:40])
                    # cada notícia vira um "card": a foto da matéria (quase sempre do próprio evento) é buscada depois
                    imgs = [{"src": "", "link": e.get("link", ""), "t": e.get("title", "")[:90]} for e in feed.entries[:40]]
                else:
                    pg.goto(src["url"], timeout=45000, wait_until="domcontentloaded")
                    pg.wait_for_timeout(4000)
                    for _ in range(3):  # rola para carregar mais eventos
                        pg.mouse.wheel(0, 4000)
                        pg.wait_for_timeout(1200)
                    txt = pg.inner_text("body")
                    imgs = pg.evaluate(IMGS_JS)
                txt = re.sub(r"\n{2,}", "\n", txt)[:max_chars]
                print(f"[agenda] {src['nome']}: {len(txt)} caracteres")
                if len(txt) > 200:
                    out.append({"fonte": src["nome"], "url": src["url"], "texto": txt,
                                "imagens": imgs[:40]})
            except Exception as e:
                print(f"[agenda falhou] {src['nome']}: {e}")
        b.close()
    return out
