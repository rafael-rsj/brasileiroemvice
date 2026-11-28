"""Página do Facebook "Guizo Cascavel": publica o mesmo post do Instagram com legenda para o público de 30 a 60 anos.

Usa o token da Meta que o robô já tem (IG_ACCESS_TOKEN). Se ele não tiver permissão de Página
(pages_manage_posts), a publicação no Facebook é pulada e o motivo aparece no log, sem atrapalhar o Instagram.
"""
import os

import requests

API = "https://graph.facebook.com/v23.0"


def _page_token(page_id: str) -> str:
    """Devolve o token da Página. Aceita no FB_PAGE_TOKEN tanto o token da Página quanto um token de usuário
    (nesse caso troca pelo da Página), e cai no IG_ACCESS_TOKEN se precisar."""
    candidatos = [os.environ.get("FB_PAGE_TOKEN", "").strip(), os.environ.get("IG_ACCESS_TOKEN", "").strip()]
    erros = []
    for tok in [c for c in candidatos if c]:
        me = requests.get(f"{API}/me", params={"fields": "id,name", "access_token": tok}, timeout=30).json()
        if me.get("id") == page_id:  # já é o token da Página
            return tok
        r = requests.get(f"{API}/{page_id}", params={"fields": "access_token", "access_token": tok}, timeout=30).json()
        if "access_token" in r:
            return r["access_token"]
        contas = requests.get(f"{API}/me/accounts", params={"access_token": tok, "limit": 50}, timeout=30).json()
        for p in contas.get("data", []):
            if p.get("id") == page_id or "guizo" in p.get("name", "").lower():
                if p.get("id") != page_id:
                    print("Aviso: id da Página na API é", p.get("id"), "e não", page_id)
                return p["access_token"]
        erros.append({"me": me, "pagina": r, "contas": contas})
    raise RuntimeError(f"sem token da Página: {erros}")


def publicar(page_id: str, image_urls: list[str], texto: str) -> str:
    pt = _page_token(page_id)
    if len(image_urls) == 1:
        r = requests.post(f"{API}/{page_id}/photos", data={"url": image_urls[0], "message": texto, "access_token": pt}, timeout=90).json()
        if "id" not in r:
            raise RuntimeError(r)
        return r.get("post_id", r["id"])
    ids = []
    for u in image_urls[:10]:
        r = requests.post(f"{API}/{page_id}/photos", data={"url": u, "published": "false", "access_token": pt}, timeout=90).json()
        if "id" not in r:
            raise RuntimeError(r)
        ids.append(r["id"])
    data = {"message": texto, "access_token": pt}
    for i, pid in enumerate(ids):
        data[f"attached_media[{i}]"] = '{"media_fbid":"%s"}' % pid
    r = requests.post(f"{API}/{page_id}/feed", data=data, timeout=90).json()
    if "id" not in r:
        raise RuntimeError(r)
    return r["id"]
