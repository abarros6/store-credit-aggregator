from .base import BaseScraper, get_new_shopify_credit


class EACollectiblesScraper(BaseScraper):
    BASE_URL = "https://www.eacollectibles.com"

    async def get_balance(self, page) -> str:
        return await get_new_shopify_credit(page, self.BASE_URL)
