import re
from abc import ABC, abstractmethod
from pathlib import Path

TIMEOUT = 15_000
PROFILE_DIR = Path.home() / ".credit-checker" / "browser-profile"


class BaseScraper(ABC):
    @abstractmethod
    async def get_balance(self, page) -> str:
        raise NotImplementedError


async def get_binder_credit(page) -> str:
    """Click the BinderPOS widget and return the balance string.

    Clicking #binderpos-open-credit causes an iframe.binderpos-credit-frame to
    be injected into the page.  The credit amount lives inside that iframe in:
        div.creditAmount > span#customerCurrency  (currency symbol)
        div.creditAmount > span                   (numeric value)
    """
    binder_btn = page.locator("#binderpos-open-credit")
    await binder_btn.wait_for(state="attached", timeout=30_000)
    await binder_btn.click(timeout=TIMEOUT)

    # Wait for the credit iframe element to be added to the DOM.
    await page.locator("iframe.binderpos-credit-frame").wait_for(
        state="attached", timeout=TIMEOUT
    )

    # Poll page.frames until the frame containing .creditAmount is ready.
    for _ in range(20):
        for frame in page.frames:
            try:
                ca = frame.locator(".creditAmount")
                if await ca.count() == 0:
                    continue
                await ca.wait_for(state="visible", timeout=5_000)
                spans = ca.locator("span")
                symbol = await spans.nth(0).inner_text(timeout=TIMEOUT)
                value = await spans.nth(1).inner_text(timeout=TIMEOUT)
                return f"{symbol.strip()}{value.strip()}"
            except Exception:
                continue
        await page.wait_for_timeout(500)

    raise ValueError(".creditAmount not found inside binderpos-credit-frame")


async def get_new_shopify_credit(page, store_base_url: str) -> str:
    """Extract store credit from the new Shopify customer accounts experience.

    These stores redirect /account to shopify.com/{store-id}/account.
    The credit balance lives on the profile tab and is anchored by an
    <img alt="storecredit"> element.
    """
    # Step 1: land on the store's /account page and follow the redirect to shopify.com.
    await page.goto(f"{store_base_url}/account", timeout=TIMEOUT)
    await page.wait_for_load_state("load", timeout=TIMEOUT)

    if "login" in page.url:
        raise ValueError("Session expired — run: python main.py --login")

    # Step 2: if we've been redirected to shopify.com, build the profile URL.
    m = re.match(r"(https://shopify\.com/\d+)", page.url)
    if m:
        profile_url = f"{m.group(1)}/account/profile"
    else:
        # Fallback: try appending /profile on the store domain.
        profile_url = f"{store_base_url}/account/profile"

    await page.goto(profile_url, timeout=TIMEOUT)
    await page.wait_for_load_state("load", timeout=TIMEOUT)

    # Step 3: wait for the React page to render, then extract the balance.
    await page.wait_for_timeout(3_000)

    balance = await page.evaluate("""() => {
        // Use the stable storecredit image as the anchor point.
        const img = document.querySelector('img[alt="storecredit"]');
        if (!img) return null;

        // Walk up the DOM until we find a container that also holds a $ span.
        let el = img;
        for (let i = 0; i < 8; i++) {
            el = el.parentElement;
            if (!el) break;
            for (const span of el.querySelectorAll('span')) {
                const t = span.textContent.trim();
                if (/^[$][0-9,]+[.]?[0-9]*$/.test(t)) return t;
            }
        }
        return null;
    }""")

    if balance:
        return balance

    raise ValueError("Store credit element (img[alt='storecredit']) not found on profile page")
