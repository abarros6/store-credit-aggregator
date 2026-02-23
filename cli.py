import argparse
import asyncio
import traceback

from playwright.async_api import async_playwright
from rich.console import Console
from rich.live import Live
from rich.prompt import Confirm, Prompt
from rich.table import Table

from config import load_config, save_config
from scrapers import BASE_URLS, STORE_NAMES, get_scraper
from scrapers.base import PROFILE_DIR

STORE_ORDER = ["realmhoppers", "eacollectibles", "manalounge", "playerscandc"]

console = Console()


# ---------------------------------------------------------------------------
# Setup — only asks which stores are enabled, no passwords needed
# ---------------------------------------------------------------------------

def run_setup() -> dict:
    console.print("\n[bold cyan]TCG Store Credit Checker — Setup[/bold cyan]")
    console.print("[dim]Select which stores you have accounts with.[/dim]\n")

    config: dict = {"stores": {}}
    i = 0

    while i < len(STORE_ORDER):
        key = STORE_ORDER[i]
        name = STORE_NAMES[key]
        allow_back = i > 0

        if allow_back:
            console.print("[dim]  (type 'back' to return to previous store)[/dim]")

        raw = Prompt.ask(
            f"  Account at [bold]{name}[/bold]? [y/n{'/back' if allow_back else ''}]"
        ).strip().lower()

        if allow_back and raw == "back":
            i -= 1
            console.print()
            continue

        config["stores"][key] = {"enabled": raw in ("y", "yes")}
        console.print()
        i += 1

    if not any(v["enabled"] for v in config["stores"].values()):
        console.print("[red]At least one store must be enabled. Starting over.[/red]\n")
        return run_setup()

    save_config(config)
    console.print("[green]Config saved.[/green]\n")
    return config


# ---------------------------------------------------------------------------
# Browser login — opens visible browser, user logs in manually
# ---------------------------------------------------------------------------

async def do_login(config: dict) -> None:
    """Open each enabled store's login page in a visible browser and save the session."""
    enabled = [
        (k, STORE_NAMES[k], BASE_URLS[k])
        for k in STORE_ORDER
        if config["stores"].get(k, {}).get("enabled")
    ]

    if not enabled:
        console.print("[red]No stores enabled.[/red]")
        return

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )

        for key, name, base_url in enabled:
            page = await context.new_page()
            console.print(f"  Opening [bold]{name}[/bold]...")
            await page.goto(f"{base_url}/account/login", timeout=30_000)

        console.print("\n[bold cyan]Browser is open.[/bold cyan]")
        console.print("Log in to each tab, then press [bold]Enter[/bold] here to save and close.\n")

        # Use run_in_executor so the event loop stays free while waiting for input.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, input, "")

        await context.close()

    console.print("[green]Sessions saved.[/green]\n")


# ---------------------------------------------------------------------------
# Balance fetching
# ---------------------------------------------------------------------------

def _build_table(rows: dict) -> Table:
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("Store", style="white", min_width=22)
    table.add_column("Balance", style="bold green", min_width=12)
    table.add_column("Status", min_width=30)

    for _key, (name, balance, status) in rows.items():
        if status == "Pending":
            status_str = "[dim]Pending[/dim]"
        elif status == "Fetching...":
            status_str = "[yellow]Fetching...[/yellow]"
        elif status == "Done":
            status_str = "[green]Done[/green]"
        else:
            status_str = f"[red]{status}[/red]"
        table.add_row(name, balance, status_str)

    return table


async def _fetch_balances(config: dict, debug: bool = False) -> None:
    if not PROFILE_DIR.exists():
        console.print("[yellow]No saved sessions found.[/yellow]")
        console.print("Run [bold]python main.py --login[/bold] to log in first.\n")
        return

    enabled = {
        key: STORE_NAMES[key]
        for key in STORE_ORDER
        if config["stores"].get(key, {}).get("enabled")
    }

    if not enabled:
        console.print("[red]No stores enabled. Run --reconfigure.[/red]")
        return

    rows: dict = {key: (name, "—", "Pending") for key, name in enabled.items()}
    error_tracebacks: dict = {}

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=not debug,
        )

        async def fetch_one(key: str, name: str) -> None:
            rows[key] = (name, "—", "Fetching...")
            live.update(_build_table(rows))
            page = await context.new_page()
            try:
                scraper = get_scraper(key)
                balance = await scraper.get_balance(page)
                rows[key] = (name, balance, "Done")
            except Exception as exc:
                rows[key] = (name, "—", f"Error: {exc}")
                if debug:
                    error_tracebacks[key] = traceback.format_exc().strip()
            finally:
                await page.close()
            live.update(_build_table(rows))

        with Live(_build_table(rows), console=console, refresh_per_second=8) as live:
            await asyncio.gather(
                *[fetch_one(k, n) for k, n in enabled.items()],
                return_exceptions=True,
            )

        await context.close()

    if debug and error_tracebacks:
        for key, tb in error_tracebacks.items():
            console.print(f"\n[bold red]Full traceback — {STORE_NAMES[key]}:[/bold red]")
            console.print(f"[dim]{tb}[/dim]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

EPILOG = """
Typical first-time setup:

  1. store-credit                  # select which stores you have accounts with
  2. store-credit --login          # opens a browser — log in to each tab, press Enter
  3. store-credit                  # fetches and displays all balances

After setup, just run  store-credit  any time to check your balances.

Commands:
  store-credit                    Fetch balances (run setup on first launch)
  store-credit --login            Re-authenticate (sessions expire occasionally)
  store-credit --reconfigure      Change which stores are enabled
  store-credit --debug            Show the browser window + full error details
"""


def _print_banner() -> None:
    console.print()
    console.print("[bold cyan]TCG Store Credit Checker[/bold cyan]  [dim]v1.0[/dim]")
    console.print("[dim]Supported stores: Realm Hoppers · EA Collectibles · Mana Lounge · Players C&C[/dim]")
    console.print()


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="store-credit",
        description="Fetch and display store credit balances from Canadian TCG stores.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        help="Re-run store selection (choose which stores are enabled).",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help=(
            "Open a browser window to log in to your stores. "
            "Required on first run and whenever sessions expire."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show the browser window while fetching and print full error tracebacks.",
    )
    args = parser.parse_args()

    _print_banner()

    config = load_config()

    if config is None or args.reconfigure:
        config = run_setup()

    if args.login:
        console.print("[bold]Step 2 of 2 — Log in to your stores[/bold]")
        console.print(
            "A browser will open with one tab per enabled store.\n"
            "Log in to each tab (check your email for 2FA codes), "
            "then return here and press [bold]Enter[/bold].\n"
        )
        asyncio.run(do_login(config))
        console.print("[bold green]All done![/bold green] Run [bold]store-credit[/bold] to fetch your balances.\n")
        return

    # First run: no session profile saved yet — guide the user through login.
    if not PROFILE_DIR.exists():
        console.print("[yellow]No saved sessions found.[/yellow]")
        console.print(
            "You need to log in before balances can be fetched.\n"
            "A browser will open with one tab per enabled store.\n"
            "Log in to each tab, then return here and press [bold]Enter[/bold].\n"
        )
        if Confirm.ask("Open browser to log in now?", default=True):
            asyncio.run(do_login(config))
            console.print()
        else:
            console.print("[dim]Run [bold]store-credit --login[/bold] when you're ready.[/dim]\n")
            return

    asyncio.run(_fetch_balances(config, debug=args.debug))
