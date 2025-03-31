import requests
from config import Config

def shorten_url(url: str) -> str:
    if not Config.URL_SHORTENER_API:
        return url
    
    try:
        response = requests.post(
            f"https://{Config.URL_SHORTENER_DOMAIN}/api",
            json={
                "api_key": Config.URL_SHORTENER_API,
                "url": url
            },
            timeout=5
        )
        return response.json().get("shortened_url", url)
    except Exception:
        return url
