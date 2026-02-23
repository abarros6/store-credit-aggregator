from .base import BaseScraper, TIMEOUT


class ManaLoungeScraper(BaseScraper):
    BASE_URL = "https://www.manalounge.ca"

    async def get_balance(self, page) -> str:
        # Auth lives on Shopify, but the BinderPOS widget is on manalounge.ca.
        # The ?sso=silent parameter triggers a silent SSO handoff from the saved
        # Shopify session so we arrive on manalounge.ca already authenticated.
        await page.goto(
            f"{self.BASE_URL}/?country=CA&sso=silent",
            timeout=TIMEOUT,
        )
        await page.wait_for_load_state("load", timeout=TIMEOUT)

        if "/account/login" in page.url:
            raise ValueError("Session expired — run: python main.py --login")

        # Give BinderPOS time to verify the session and inject the button.
        await page.wait_for_timeout(4_000)

        # Click the BinderPOS credit button.
        binder_btn = page.locator("#binderpos-open-credit")
        await binder_btn.wait_for(state="attached", timeout=30_000)
        await binder_btn.click(timeout=TIMEOUT)

        # After clicking, poll all frames (including the main frame) for
        # .creditAmount — the iframe class may differ on manalounge.ca.
        for _ in range(30):
            for frame in page.frames:
                try:
                    ca = frame.locator(".creditAmount")
                    if await ca.count() == 0:
                        continue
                    await ca.wait_for(state="visible", timeout=3_000)
                    spans = ca.locator("span")
                    symbol = await spans.nth(0).inner_text(timeout=TIMEOUT)
                    value = await spans.nth(1).inner_text(timeout=TIMEOUT)
                    return f"{symbol.strip()}{value.strip()}"
                except Exception:
                    continue
            await page.wait_for_timeout(500)

        raise ValueError(".creditAmount not found after clicking BinderPOS button")
