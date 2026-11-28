"""Página do Facebook "Guizo Cascavel": publica o mesmo post do Instagram com legenda para o público de 30 a 60 anos.

Usa o token da Meta que o robô já tem (IG_ACCESS_TOKEN). Se ele não tiver permissão de Página
(pages_manage_posts), a publicação no Facebook é pulada e o motivo aparece no log, sem atrapalhar o Instagram.
"""
import os

import requests

API = "https://graph.facebook.com/v23.0"


def _page_token(page_id: str) -> str:
    tok = os.environ["IG_ACCESS_TOKEN"].strip()
    r = requests.get(f"{API}/{page_id}", params={"fields": "access_token", "access_token": tok}, timeout=30).json()
    if "access_token" in r:
        return r["access_token"]
    r = requests.get(f"{API}/me/accounts", params={"access_token": tok, "limit": 50}, timeout=30).json()
    for p in r.get("data", []):
        if p.get("id") == page_id:
            return p["access_token"]
    raise RuntimeError(f"sem token da Página: {r}")


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
