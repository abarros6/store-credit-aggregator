# store-credit-aggregator

A command-line tool that checks your store credit balances across multiple Canadian TCG stores at once, displayed in a clean table.

**Supported stores**
- Realm Hoppers
- EA Collectibles
- Mana Lounge
- Players C&C

---

## How it works

The tool opens a hidden browser, logs in to each store on your behalf, reads your credit balance, and prints everything in a table. Because all four stores use email-based two-factor authentication (2FA), you log in manually the first time — the session is then saved so future runs happen automatically without any interaction.

---

## Requirements

- **macOS** (these instructions are written for macOS)
- **Python 3.11 or newer** — check by opening Terminal and running:
  ```
  python3 --version
  ```
  If it says `Python 3.11.x` or higher, you're good. If not, download Python from [python.org](https://www.python.org/downloads/).

- **Homebrew** — a package manager for macOS. If you don't have it, install it by running this in Terminal:
  ```
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

---

## Installation

Open **Terminal** and follow these steps in order. Copy and paste each command exactly.

### Step 1 — Download the project

If you have the project folder already, skip to Step 2. Otherwise, navigate to wherever you want to keep it (e.g. your home folder) and clone it:

```bash
cd ~
git clone <repository-url> store-credit-aggregator
cd store-credit-aggregator
```

### Step 2 — Install pipx

pipx is a tool that installs Python command-line apps so they work globally in any Terminal window.

```bash
brew install pipx
pipx ensurepath
```

After running `pipx ensurepath`, **close Terminal and reopen it** before continuing. This ensures the new command is available.

### Step 3 — Install the store-credit command

```bash
pipx install ~/store-credit-aggregator
```

> If you saved the project folder somewhere other than your home directory, replace `~/store-credit-aggregator` with the correct path.

### Step 4 — Install the browser

The tool uses a hidden browser to log in to stores. Install it with:

```bash
~/.local/pipx/venvs/store-credit-aggregator/bin/playwright install chromium
```

---

## First-time setup

You only need to do this once.

### Step 1 — Select your stores

Open Terminal and run:

```bash
store-credit
```

The app will ask which stores you have accounts with. Type `y` and press Enter for yes, `n` and press Enter for no. If you make a mistake, type `back` to go to the previous question.

### Step 2 — Log in to your stores

```bash
store-credit --login
```

A browser window will open with one tab for each store you selected. Log in to each tab as you normally would — check your email for any 2FA codes. When every tab is logged in, come back to Terminal and press **Enter**.

Your sessions are now saved. You won't need to log in again unless a session expires (usually after a few weeks).

### Step 3 — Check your balances

```bash
store-credit
```

That's it. You'll see a table like this:

```
TCG Store Credit Checker  v1.0

  Store                     Balance         Status
  Realm Hoppers             $49.15          Done
  EA Collectibles           $36.00          Done
  Mana Lounge               $29.48          Done
  Players C&C               $8.16           Done
```

---

## Daily usage

Any time you want to check your balances, open Terminal and run:

```bash
store-credit
```

---

## All commands

| Command | What it does |
|---|---|
| `store-credit` | Fetch and display all balances |
| `store-credit --login` | Log in again (run this if you see a "session expired" error) |
| `store-credit --reconfigure` | Change which stores are enabled |
| `store-credit --debug` | Show the browser window and detailed error info (for troubleshooting) |
| `store-credit --help` | Show a quick usage guide |

---

## If something goes wrong

**"Session expired" error**

Sessions saved during login expire after a few weeks. Just run:

```bash
store-credit --login
```

Log in to each tab again, press Enter, and you're good.

**A balance shows "Error" instead of a dollar amount**

Run with `--debug` to see what's happening:

```bash
store-credit --debug
```

This opens a visible browser window so you can watch what the tool does, and prints the full error details in Terminal.

**The `store-credit` command is not found**

If Terminal says `command not found: store-credit`, the PATH may not have updated. Run:

```bash
pipx ensurepath
```

Then close and reopen Terminal.

---

## Files saved to your computer

| Location | What's stored |
|---|---|
| `~/.credit-checker/config.json` | Which stores are enabled |
| `~/.credit-checker/browser-profile/` | Your saved login sessions |

The config file is locked to your user account only (no passwords are stored — only which stores are enabled).

---

## Project structure (for developers)

```
store-credit-aggregator/
├── pyproject.toml          # Package config — defines the store-credit command
├── main.py                 # Direct-run entry point (python main.py)
├── cli.py                  # CLI logic, argument parsing, Rich output
├── config.py               # Read/write ~/.credit-checker/config.json
├── scrapers/
│   ├── __init__.py         # Store registry
│   ├── base.py             # Shared helpers (BinderPOS widget, new Shopify accounts)
│   ├── realmhoppers.py
│   ├── eacollectibles.py
│   ├── manalounge.py
│   └── playerscandc.py
├── diagnose.py             # Debug tool — dumps DOM/iframe contents per store
├── requirements.txt
└── README.md
```

### Adding a new store

1. Create `scrapers/newstore.py` implementing `BaseScraper.get_balance(page)`.
2. Register it in `scrapers/__init__.py` (`STORE_NAMES`, `BASE_URLS`, `_SCRAPER_CLASSES`).
3. Add its key to `STORE_ORDER` in `cli.py`.

If the store uses Shopify's new customer accounts, use `get_new_shopify_credit` from `scrapers/base.py`. If it uses a BinderPOS widget, refer to `scrapers/manalounge.py`.
