"""Cliente da API oficial do Instagram (Instagram API with Instagram Login)."""
import os
import time

import requests

API = "https://graph.instagram.com/v23.0"


class IG:
    def __init__(self):
        self.token = os.environ["IG_ACCESS_TOKEN"]
        self.user = os.environ["IG_USER_ID"]

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

    def _wait(self, container_id, tries=40):
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
