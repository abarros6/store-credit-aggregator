# store-credit-aggregator

CLI tool that fetches TCG store credit balances using Playwright persistent browser sessions.

## Stack

- Python 3.12, asyncio
- Playwright async API (persistent Chromium context)
- Rich (table output, prompts)
- Setuptools (packaged as `store-credit` console command)

## Running

```bash
source .venv/bin/activate
store-credit              # fetch balances
store-credit --login      # re-authenticate
store-credit --debug      # visible browser + tracebacks
store-credit --reconfigure
```

Or without the installed command: `python main.py [flags]`

## Key files

| File | Purpose |
|---|---|
| `cli.py` | Argument parsing, setup flow, login flow, balance fetcher |
| `config.py` | Read/write `~/.credit-checker/config.json` |
| `scrapers/base.py` | `BaseScraper` ABC + `get_binder_credit()` + `get_new_shopify_credit()` |
| `scrapers/__init__.py` | Store registry (`STORE_NAMES`, `BASE_URLS`, `_SCRAPER_CLASSES`) |
| `diagnose.py` | DOM inspector — run directly to dump element IDs / dollar amounts / iframes |
| `pyproject.toml` | Package definition; `store-credit = "cli:run"` |

## Session storage

- Browser profile: `~/.credit-checker/browser-profile/`
- Config: `~/.credit-checker/config.json`

## Store implementations

### Realm Hoppers / EA Collectibles — New Shopify accounts
`get_new_shopify_credit(page, base_url)` in `base.py`:
1. Navigate to `/account` → follows redirect to `shopify.com/{id}/account`
2. Navigate to `/account/profile`
3. Find `img[alt="storecredit"]`, walk up DOM to find `$XX.XX` span

### Mana Lounge — BinderPOS on Shopify
`scrapers/manalounge.py`:
1. Navigate to `https://www.manalounge.ca/?country=CA&sso=silent` — silently authenticates using saved Shopify session via SSO handoff
2. Wait 4s for BinderPOS to inject `#binderpos-open-credit`
3. Click button, then poll all `page.frames` for `.creditAmount` > spans (symbol + value)

### Players C&C — Custom platform
`scrapers/playerscandc.py`:
1. Navigate to `/account`
2. Wait for `span.credit` to be visible, return its text

## Adding a store

1. Create `scrapers/newstore.py` subclassing `BaseScraper`
2. Add to `scrapers/__init__.py`: `STORE_NAMES`, `BASE_URLS`, `_SCRAPER_CLASSES`
3. Add key to `STORE_ORDER` list in `cli.py`
4. Use `get_new_shopify_credit` (new Shopify), `get_binder_credit` (BinderPOS), or write custom scraper

## Debugging a failing store

Run `diagnose.py` — it navigates to each store, waits 8s, and dumps:
- All element IDs (visible/hidden)
- All dollar amounts in the DOM (text node scan)
- Shadow DOM matches (credit/binder/loyalty/point)
- All iframe contents

```bash
python diagnose.py
```

## Packaging

Installed with `pip install -e .` (editable). `pyproject.toml` defines:
- `py-modules = ["cli", "config"]`
- `packages = ["scrapers"]`
- `store-credit = "cli:run"` console script
