import json
import os
import stat
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".credit-checker"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> Optional[dict]:
    """Return parsed config dict, or None if no config file exists."""
    if not CONFIG_FILE.exists():
        return None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """Persist config to disk, creating the directory if necessary."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    # Restrict permissions to owner-only on Unix systems.
    if os.name != "nt":
        os.chmod(CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)
