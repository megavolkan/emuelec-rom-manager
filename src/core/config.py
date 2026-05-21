"""
config.py
Uygulama ayarlarını JSON dosyasında saklar.
"""

import os
import json
import base64

CONFIG_DIR  = os.path.expanduser("~/.emuelec-rom-manager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    "igdb_client_id":     "",
    "igdb_client_secret": "",
    "auto_scrape":        True,
    "scrape_language":    "tr",
    "scrape_region":      "wor",
}


def _encode(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def _decode(value: str) -> str:
    try:
        return base64.b64decode(value.encode()).decode()
    except Exception:
        return value


def load() -> dict:
    if not os.path.isfile(CONFIG_FILE):
        return DEFAULTS.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = DEFAULTS.copy()
        config.update(data)

        if config.get("igdb_client_secret"):
            config["igdb_client_secret"] = _decode(config["igdb_client_secret"])

        return config
    except Exception:
        return DEFAULTS.copy()


def save(config: dict) -> bool:
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)

        data = config.copy()
        if data.get("igdb_client_secret"):
            data["igdb_client_secret"] = _encode(data["igdb_client_secret"])

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False


def get(key: str, default=None):
    return load().get(key, default)


def set(key: str, value) -> bool:
    config = load()
    config[key] = value
    return save(config)
