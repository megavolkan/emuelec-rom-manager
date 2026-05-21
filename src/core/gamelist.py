"""
gamelist.py
EmuELEC gamelist.xml okuma ve yazma işlemleri.
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime


def read_gamelist(system_path: str) -> dict:
    """
    gamelist.xml dosyasını okur.

    Returns:
        {rom_stem: {name, desc, image, developer, ...}, ...}
        rom_stem: uzantısız dosya adı (küçük harf)
    """
    gamelist_path = os.path.join(system_path, "gamelist.xml")
    if not os.path.isfile(gamelist_path):
        return {}

    try:
        tree = ET.parse(gamelist_path)
        root = tree.getroot()
    except Exception:
        return {}

    games = {}
    for game in root.findall("game"):
        path_el = game.find("path")
        if path_el is None:
            continue

        stem = os.path.splitext(os.path.basename(path_el.text or ""))[0].lower()
        if not stem:
            continue

        games[stem] = {
            "path":        path_el.text or "",
            "name":        _text(game, "name"),
            "desc":        _text(game, "desc"),
            "image":       _text(game, "image"),
            "video":       _text(game, "video"),
            "developer":   _text(game, "developer"),
            "publisher":   _text(game, "publisher"),
            "genre":       _text(game, "genre"),
            "releasedate": _text(game, "releasedate"),
            "rating":      _text(game, "rating"),
            "players":     _text(game, "players"),
        }

    return games


def write_game_entry(system_path: str, rom_filename: str, metadata: dict,
                     image_path: str = None) -> bool:
    """
    gamelist.xml'e bir oyun kaydı yazar veya günceller.

    Args:
        system_path: Sistem klasörü (gamelist.xml buradadır)
        rom_filename: ROM dosyasının adı (uzantılı)
        metadata: {name, desc, developer, publisher, genre, releasedate, rating, players}
        image_path: Kapak resminin sistem_path'e göre göreli yolu (opsiyonel)
    """
    gamelist_path = os.path.join(system_path, "gamelist.xml")

    # Mevcut XML'i yükle veya yeni oluştur
    if os.path.isfile(gamelist_path):
        try:
            tree = ET.parse(gamelist_path)
            root = tree.getroot()
        except Exception:
            root = ET.Element("gameList")
            tree = ET.ElementTree(root)
    else:
        root = ET.Element("gameList")
        tree = ET.ElementTree(root)

    # Mevcut kaydı bul veya yeni oluştur
    stem = os.path.splitext(rom_filename)[0].lower()
    existing = None
    for game in root.findall("game"):
        path_el = game.find("path")
        if path_el is not None:
            existing_stem = os.path.splitext(os.path.basename(path_el.text or ""))[0].lower()
            if existing_stem == stem:
                existing = game
                break

    if existing is None:
        existing = ET.SubElement(root, "game")

    # Alanları yaz
    _set_text(existing, "path", f"./{rom_filename}")
    _set_text(existing, "name", metadata.get("name", ""))
    _set_text(existing, "desc", metadata.get("desc", ""))

    if image_path:
        _set_text(existing, "image", image_path)

    for field in ["developer", "publisher", "genre", "releasedate", "rating", "players"]:
        val = metadata.get(field, "")
        if val:
            _set_text(existing, field, val)

    # Kaydet
    try:
        ET.indent(tree, space="  ")
        tree.write(gamelist_path, encoding="utf-8", xml_declaration=True)
        return True
    except Exception:
        return False


def get_game_metadata(system_path: str, rom_filename: str) -> dict | None:
    """Tek bir ROM'un metadata'sını döndürür. Bulunamazsa None."""
    stem = os.path.splitext(rom_filename)[0].lower()
    games = read_gamelist(system_path)
    return games.get(stem)


def _text(element, tag: str) -> str:
    el = element.find(tag)
    return (el.text or "").strip() if el is not None else ""


def _set_text(parent, tag: str, value: str):
    el = parent.find(tag)
    if el is None:
        el = ET.SubElement(parent, tag)
    el.text = value
