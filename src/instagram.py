"""Cliente da API oficial do Instagram (Instagram API with Instagram Login)."""
import os
import time

import requests

class IG:
    def __init__(self):
        self.token = os.environ["IG_ACCESS_TOKEN"].strip()
        self.user = os.environ["IG_USER_ID"].strip()
        # Token "IGAA..." = login do Instagram; "EAA..." = login unificado/usuário do sistema (Facebook Graph)
        host = "graph.instagram.com" if self.token.startswith("IG") else "graph.facebook.com"
        global API
        API = f"https://{host}/v23.0"

    def _post(self, path, **data):
        data["access_token"] = self.token
        r = requests.post(f"{API}/{path}", data=data, timeout=60)
        if not r.ok:
            raise RuntimeError(f"IG {path}: {r.status_code} {r.text}")
        return r.json()

    def _get(self, path, **params):
        params["access_token"] = self.token
        r = requests.get(f"{API}/{path}", params=params, timeout=60)
        if not r.ok:
            raise RuntimeError(f"IG {path}: {r.status_code} {r.text}")
        return r.json()

    def _wait(self, container_id, tries=60):
        for _ in range(tries):
            st = self._get(container_id, fields="status_code,status")
            if st.get("status_code") == "FINISHED":
                return
            if st.get("status_code") in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container falhou: {st}")
            time.sleep(5)
        raise TimeoutError("container não ficou pronto")

    def _publish(self, container_id):
        self._wait(container_id)
        return self._post(f"{self.user}/media_publish", creation_id=container_id)["id"]

    def quota(self):
        return self._get(f"{self.user}/content_publishing_limit", fields="quota_usage,config")

    def post_image(self, image_url, caption, ai_generated=False):
        extra = {"is_ai_generated": "true"} if ai_generated else {}
        c = self._post(f"{self.user}/media", image_url=image_url, caption=caption, **extra)["id"]
        return self._publish(c)

    def post_carousel(self, image_urls, caption, ai_generated=False):
        extra = {"is_ai_generated": "true"} if ai_generated else {}
        kids = [self._post(f"{self.user}/media", image_url=u, is_carousel_item="true", **extra)["id"]
                for u in image_urls]
        c = self._post(f"{self.user}/media", media_type="CAROUSEL", children=",".join(kids),
                       caption=caption)["id"]
        return self._publish(c)

    def post_reel(self, video_url, caption, cover_url=None, ai_generated=False):
        extra = {"is_ai_generated": "true"} if ai_generated else {}
        if cover_url:
            extra["cover_url"] = cover_url
        c = self._post(f"{self.user}/media", media_type="REELS", video_url=video_url,
                       caption=caption, share_to_feed="true", **extra)["id"]
        return self._publish(c)

    def post_reel_file(self, path, caption, ai_generated=False):
        """Publica um reel enviando o arquivo direto para a Meta (upload resumível, sem precisar de URL pública)."""
        extra = {"is_ai_generated": "true"} if ai_generated else {}
        c = self._post(f"{self.user}/media", media_type="REELS", upload_type="resumable",
                       caption=caption, share_to_feed="true", **extra)
        data = open(path, "rb").read()
        uri = c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v23.0/{c['id']}"
        r = requests.post(uri, data=data, timeout=300, headers={
            "Authorization": f"OAuth {self.token}", "offset": "0", "file_size": str(len(data))})
        if not r.ok:
            raise RuntimeError(f"upload do reel falhou: {r.status_code} {r.text}")
        return self._publish(c["id"])

    def post_story(self, image_url):
        c = self._post(f"{self.user}/media", media_type="STORIES", image_url=image_url)["id"]
        return self._publish(c)

    # ---- comentários ----
    def recent_media(self, limit=10):
        return self._get(f"{self.user}/media", fields="id,caption,timestamp", limit=limit)["data"]

    def comments(self, media_id):
        return self._get(f"{media_id}/comments", fields="id,text,username,timestamp,replies{username}")["data"]

    def reply(self, comment_id, text):
        return self._post(f"{comment_id}/replies", message=text)

    # ---- token ----
    def refresh_token(self):
        r = requests.get("https://graph.instagram.com/refresh_access_token",
                         params={"grant_type": "ig_refresh_token", "access_token": self.token}, timeout=30)
        r.raise_for_status()
        return r.json()["access_token"]
