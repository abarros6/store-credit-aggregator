from .base import BaseScraper, TIMEOUT


class PlayersCandCScraper(BaseScraper):
    BASE_URL = "https://playerscandc.com"

    async def get_balance(self, page) -> str:
        await page.goto(f"{self.BASE_URL}/account", timeout=TIMEOUT)
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        if "/account/login" in page.url:
            raise ValueError("Session expired — run: python main.py --login")

        credit_element = page.locator("span.credit")
        await credit_element.wait_for(state="visible", timeout=TIMEOUT)
        return await credit_element.inner_text(timeout=TIMEOUT)
