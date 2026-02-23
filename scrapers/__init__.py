from .realmhoppers import RealmHoppersScraper
from .eacollectibles import EACollectiblesScraper
from .manalounge import ManaLoungeScraper
from .playerscandc import PlayersCandCScraper

STORE_NAMES: dict[str, str] = {
    "realmhoppers": "Realm Hoppers",
    "eacollectibles": "EA Collectibles",
    "manalounge": "Mana Lounge",
    "playerscandc": "Players C&C",
}

BASE_URLS: dict[str, str] = {
    "realmhoppers": "https://www.realmhoppers.com",
    "eacollectibles": "https://www.eacollectibles.com",
    "manalounge": "https://www.manalounge.ca",
    "playerscandc": "https://playerscandc.com",
}

_SCRAPER_CLASSES = {
    "realmhoppers": RealmHoppersScraper,
    "eacollectibles": EACollectiblesScraper,
    "manalounge": ManaLoungeScraper,
    "playerscandc": PlayersCandCScraper,
}


def get_scraper(store_key: str) -> "RealmHoppersScraper | EACollectiblesScraper | ManaLoungeScraper | PlayersCandCScraper":
    return _SCRAPER_CLASSES[store_key]()
