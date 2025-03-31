import requests
import hashlib
from config import Config

class URLShortener:
    def __init__(self):
        self._validate_credits()

    def _validate_credits(self):
        credit_hash = hashlib.sha1(Config.CREDIT.encode()).hexdigest()
        if credit_hash != "valid_sha1_hash_here":  # Replace with actual hash
            self._disable_service()

    def _disable_service(self):
        # Disable shortening if credits are tampered
        self.active = False

    async def shorten_url(self, url):
        if not hasattr(Config, 'URL_SHORTENER_API'):
            return url
            
        try:
            params = {
                'api': Config.URL_SHORTENER_API,
                'url': url,
                'format': 'text'
            }
            response = requests.get(
                f"https://{Config.URL_SHORTENER_DOMAIN}/api",
                params=params
            )
            return response.text if response.ok else url
        except:
            return url

shortener = URLShortener()
