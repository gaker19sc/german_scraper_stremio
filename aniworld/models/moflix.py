import re
from typing import Optional, Dict, List, Tuple
from ..config import DEFAULT_USER_AGENT, Audio, Subtitles, logger
from .common import ProviderData

class MoflixEpisode:
    def __init__(self, url: str):
        self.url = url
        self.__provider_data = None
        self.__html = None
        self.selected_provider = None
        self.selected_language = "German"

    @property
    def _id(self):
        return self.url.rstrip('/').split('/')[-1]

    @property
    def provider_data(self):
        if self.__provider_data is None:
            self.__provider_data = self.__extract_provider_data()
        return self.__provider_data

    def __extract_provider_data(self):
        api_url = f"https://moflix-stream.xyz/api/v1/videos?title_id={self._id}"
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": "https://moflix-stream.xyz/",
            "Accept": "application/json",
        }
        try:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.get(api_url, headers=headers, impersonate="chrome124", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                providers = {}
                # The API returns a list of videos under 'pagination.data'
                videos = data.get('pagination', {}).get('data', [])
                for video in videos:
                    src = video.get('src')
                    if src:
                        # Map moflix-stream.click to potential providers or use directly
                        name = video.get('name', 'Unknown')
                        providers[name] = src

                if providers:
                    return ProviderData({(Audio.GERMAN, Subtitles.NONE): providers})
        except Exception as e:
            logger.debug(f"Moflix provider extraction failed: {e}")
        return None

    @property
    def stream_url(self):
        if not self.selected_provider:
             return None

        # Resolve the redirect URL from Moflix
        # Often moflix-stream.click redirects to VOE or similar
        url = self.provider_link()
        if not url: return None

        if "moflix-stream.click" in url:
             try:
                 from curl_cffi import requests as curl_requests
                 resp = curl_requests.get(url, impersonate="chrome124", timeout=10, allow_redirects=True)
                 return resp.url # The final redirected URL
             except:
                 return url
        return url

    def provider_link(self, language=None, provider=None):
        if not self.provider_data: return None
        p = provider or self.selected_provider
        return self.provider_data.get((Audio.GERMAN, Subtitles.NONE)).get(p)
