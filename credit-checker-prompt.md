# Claude Code Prompt: TCG Store Credit Checker

Build a cross-platform TUI application in Python called **credit-checker** that aggregates store credit balances from multiple Canadian TCG (trading card game) stores. The app must run on both Windows and macOS.

---

## Tech Stack

- **TUI framework:** `Textual` (interactive widgets, forms, data tables)
- **Browser automation:** `Playwright` (async, Chromium, headless)
- **Config persistence:** `config.json` stored in the user's home directory under `~/.credit-checker/config.json`
- **Language:** Python 3.11+

---

## Project Structure

```
credit-checker/
├── main.py                  # Entry point
├── config.py                # Config read/write helpers
├── scrapers/
│   ├── base.py              # Abstract base scraper class
│   ├── realmhoppers.py
│   ├── eacollectibles.py
│   ├── manalounge.py
│   └── playerscandc.py
├── ui/
│   ├── app.py               # Main Textual app
│   ├── screens/
│   │   ├── onboarding.py    # First-run setup screen
│   │   ├── dashboard.py     # Main screen with balances + fetch button
│   │   └── settings.py      # Edit existing config
├── requirements.txt
└── README.md
```

---

## Config Format

Store config at `~/.credit-checker/config.json`. The schema is:

```json
{
  "stores": {
    "realmhoppers": {
      "enabled": true,
      "email": "user@example.com",
      "password": "..."
    },
    "eacollectibles": {
      "enabled": true,
      "email": "user@example.com",
      "password": "..."
    },
    "manalounge": {
      "enabled": true,
      "email": "user@example.com",
      "password": "..."
    },
    "playerscandc": {
      "enabled": true,
      "email": "user@example.com",
      "password": "..."
    }
  }
}
```

---

## Application Flow

### First Run (no config file exists)
Launch directly into an **onboarding screen**. The onboarding screen should:
- Display a welcome message explaining what the app does
- Present each store as a toggle (enabled/disabled) with email and password fields beneath it that show or hide based on the toggle state
- Require at least one store to be enabled before allowing the user to proceed
- Save the completed config to `~/.credit-checker/config.json` on submission
- Transition to the dashboard screen after saving

### Subsequent Runs (config file exists)
Launch directly into the **dashboard screen**.

---

## Dashboard Screen

The main screen should display:
- A title bar: "TCG Store Credit Checker"
- A table showing each enabled store with columns: `Store`, `Balance`, `Status`
- Initial state: all balance cells show `—` and status shows `Pending`
- A **"Fetch Balances"** button that triggers all enabled scrapers concurrently using `asyncio.gather`
- During fetching, each row's status should update to `Fetching...` in real time as scraping begins, then update to `Done` or `Error` when complete, with the balance populated
- A **"Settings"** button that navigates to the settings screen
- A **"Quit"** button or keyboard shortcut `q` to exit

### Error Handling in the Dashboard
If a scraper fails for any reason (login failure, element not found, timeout), that store's row should show `Error` in the status column and a short reason if available, without crashing the rest of the app.

---

## Settings Screen

Allow the user to:
- Enable or disable individual stores
- Update email and password per store
- Save changes back to `config.json`
- Navigate back to the dashboard without saving (cancel)

---

## Scrapers

All scrapers should follow the abstract base class:

```python
class BaseScraper:
    async def get_balance(self) -> str:
        raise NotImplementedError
```

Each scraper receives the store's config dict (email, password) on initialization. All scrapers use **Playwright async API with headless Chromium**.

### Realm Hoppers (`https://www.realmhoppers.com/`)
- This is a Shopify store. Navigate to the login page, log in with email and password, navigate to the account page, and locate the store credit balance element. Inspect the account page DOM to find the correct selector — Shopify account pages typically expose store credit in an element with text like "Store credit" near a dollar amount.
- If the element is not found, also check for a BinderPOS widget: click the element with id `binderpos-open-credit` if present, wait for the credit modal to load, then read the balance from `.creditAmount` (concatenating the currency symbol span and the value span).

### EA Collectibles (`https://www.eacollectibles.com/`)
- Same logic as Realm Hoppers — try the Shopify account page first, then fall back to checking for `#binderpos-open-credit`.

### Mana Lounge (`https://www.manalounge.ca/`)
- Navigate to the store homepage while logged in
- Wait for the element with id `binderpos-open-credit` to be present in the DOM
- Click it
- Wait for the credit modal/iframe to load and the `.creditAmount` element to become visible
- Extract the balance by concatenating the text content of the two child spans inside `.creditAmount`: the first contains the currency symbol (`$`) and the second contains the numeric value (e.g. `29.48`). Return the combined string e.g. `$29.48`

### Players C&C (`https://playerscandc.com/`)
- Log in and navigate to the user account/purchases page
- Locate the element matching the CSS selector `span.credit`
- Return its inner text as the balance

---

## Cross-Platform Notes

- Use `pathlib.Path.home()` for all file paths — never hardcode OS-specific paths
- Playwright's Chromium installation via `playwright install chromium` works on both platforms; include this step in the README setup instructions
- Do not use any OS-specific shell commands

---

## requirements.txt

```
textual
playwright
asyncio
```

---

## README

Include setup instructions:
1. `pip install -r requirements.txt`
2. `playwright install chromium`
3. `python main.py`

---

## Additional Notes

- All Playwright operations should have explicit timeouts (recommend 15 seconds) rather than waiting indefinitely
- Passwords should never be logged or printed to stdout at any point
- The config file should be created with `0o600` permissions on Unix systems (owner read/write only); on Windows this is not enforced but note it in the README
- Scraper concurrency should use `asyncio.gather` with `return_exceptions=True` so one failure does not cancel others
