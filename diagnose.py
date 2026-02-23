"""
Deep diagnostic — dumps element IDs, shadow DOM contents, dollar amounts,
and the Shopify CDN iframe content for each failing store.

    python diagnose.py
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE_DIR = Path.home() / ".credit-checker" / "browser-profile"

STORES = {
    "realmhoppers":  ("Realm Hoppers",    "https://www.realmhoppers.com/account"),
    "eacollectibles": ("EA Collectibles", "https://www.eacollectibles.com/account"),
    "manalounge":    ("Mana Lounge",      "https://www.manalounge.ca"),
}

# ── JS helpers ────────────────────────────────────────────────────────────────

# All non-empty element IDs on the page.
ALL_IDS_JS = """() => {
    return [...document.querySelectorAll('[id]')]
        .map(el => ({ tag: el.tagName.toLowerCase(), id: el.id,
                      vis: el.offsetParent !== null || getComputedStyle(el).display !== 'none' }))
        .filter(e => e.id.trim() !== '');
}"""

# Elements containing a dollar-sign amount anywhere in their text (leaf nodes only).
DOLLAR_JS = """() => {
    const results = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
        if (/\$\s*[\d,]+\.?\d*/.test(node.nodeValue)) {
            const parent = node.parentElement;
            if (!parent) continue;
            results.push({
                tag:     parent.tagName.toLowerCase(),
                id:      parent.id,
                classes: parent.className,
                text:    node.nodeValue.trim().slice(0, 120),
            });
        }
    }
    return results;
}"""

# Shallow shadow-DOM scan: elements with credit/binder in id or class inside any shadow root.
SHADOW_JS = """() => {
    const results = [];
    document.querySelectorAll('*').forEach(host => {
        if (!host.shadowRoot) return;
        host.shadowRoot.querySelectorAll('*').forEach(el => {
            const combined = ((el.id || '') + ' ' + el.className).toLowerCase();
            if (/credit|binder|loyalty|point/.test(combined)) {
                results.push({ hostTag: host.tagName, hostId: host.id,
                                tag: el.tagName, id: el.id,
                                classes: el.className,
                                text: (el.textContent || '').trim().slice(0, 120) });
            }
        });
    });
    return results;
}"""


async def scan_frame(frame, label=""):
    print(f"\n  {'[' + label + ']' if label else '[main frame]'}")

    # All IDs
    try:
        ids = await frame.evaluate(ALL_IDS_JS)
        if ids:
            print(f"  All element IDs ({len(ids)}):")
            for e in ids:
                vis = "vis" if e["vis"] else "hid"
                print(f"    <{e['tag']}> #{e['id']}  [{vis}]")
        else:
            print("  No elements with IDs found.")
    except Exception as exc:
        print(f"  Could not read IDs: {exc}")

    # Dollar amounts
    try:
        dollars = await frame.evaluate(DOLLAR_JS)
        if dollars:
            print(f"\n  Dollar amounts found ({len(dollars)}):")
            for e in dollars:
                print(f"    <{e['tag']}> #{e['id']} .{e['classes']}  →  \"{e['text']}\"")
        else:
            print("\n  No dollar amounts found.")
    except Exception as exc:
        print(f"  Could not scan for dollar amounts: {exc}")

    # Shadow DOM
    try:
        shadows = await frame.evaluate(SHADOW_JS)
        if shadows:
            print(f"\n  Shadow DOM matches ({len(shadows)}):")
            for e in shadows:
                print(f"    host <{e['hostTag']}> #{e['hostId']}  →  <{e['tag']}> #{e['id']} .{e['classes']}")
                if e["text"]:
                    print(f"      text: {e['text']}")
    except Exception as exc:
        print(f"  Could not scan shadow DOM: {exc}")


async def diagnose_store(context, key, name, url):
    SEP = "─" * 68
    print(f"\n{SEP}\n  {name}  →  {url}\n{SEP}")

    page = await context.new_page()
    try:
        await page.goto(url, timeout=30_000)
        await page.wait_for_load_state("load", timeout=30_000)
        print(f"\n  Landed on: {page.url}  (title: {await page.title()})")

        # Extra wait for lazy scripts (BinderPOS etc.)
        print("  Waiting 8 s for scripts to inject…")
        await page.wait_for_timeout(8_000)

        # Main frame
        await scan_frame(page, "main frame")

        # Every iframe
        frames = page.frames[1:]
        if frames:
            print(f"\n  {len(frames)} iframe(s):")
        for frame in frames:
            print(f"\n  iframe src: {frame.url[:100]}")
            try:
                await frame.wait_for_load_state("load", timeout=10_000)
                await frame.wait_for_timeout(3_000)
                await scan_frame(frame, f"iframe — {frame.url[:60]}")
            except Exception as exc:
                print(f"  Could not inspect iframe: {exc}")

    except Exception as exc:
        print(f"\n  ERROR: {exc}")
    finally:
        await page.close()


async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        for key, (name, url) in STORES.items():
            await diagnose_store(context, key, name, url)
        await context.close()
        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
