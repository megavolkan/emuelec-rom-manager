"""
rom_manager.py
ROM ekleme, silme ve dosya işlemleri.
Bir ROM = dosya + Apple Double (._) + media + gamelist.xml kaydı
"""

import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


ROM_EXTENSIONS = {
    "atari2600": [".a26", ".bin", ".rom"],
    "atari7800": [".a78", ".bin"],
    "c64": [".d64", ".t64", ".prg", ".p00", ".crt"],
    "dreamcast": [".cdi", ".gdi", ".chd"],
    "fba": [".zip", ".7z"],
    "fds": [".fds", ".zip"],
    "gamegear": [".gg", ".bin", ".zip"],
    "gb": [".gb", ".zip"],
    "gba": [".gba", ".zip"],
    "gbc": [".gbc", ".zip"],
    "genesis": [".md", ".bin", ".gen", ".zip", ".smd"],
    "mame": [".zip", ".7z"],
    "mastersystem": [".sms", ".bin", ".zip"],
    "megadrive": [".md", ".bin", ".gen", ".zip", ".smd"],
    "n64": [".z64", ".n64", ".v64", ".zip"],
    "nds": [".nds", ".zip"],
    "neogeo": [".zip", ".7z"],
    "nes": [".nes", ".zip", ".unf"],
    "ngp": [".ngp", ".zip"],
    "ngpc": [".ngc", ".zip"],
    "pce": [".pce", ".zip"],
    "pcengine": [".pce", ".zip"],
    "psp": [".iso", ".cso", ".pbp"],
    "psx": [".bin", ".cue", ".iso", ".img", ".pbp", ".chd"],
    "saturn": [".bin", ".iso", ".mdf", ".chd"],
    "scummvm": [".zip"],
    "sega32x": [".32x", ".bin", ".zip"],
    "segacd": [".bin", ".iso", ".chd"],
    "snes": [".sfc", ".smc", ".zip", ".fig"],
    "supergrafx": [".pce", ".zip"],
    "tg16": [".pce", ".zip"],
    "vectrex": [".vec", ".bin", ".zip"],
    "virtualboy": [".vb", ".zip"],
    "wonderswan": [".ws", ".zip"],
    "wonderswancolor": [".wsc", ".zip"],
    "x68000": [".dim", ".xdf", ".hdm", ".zip"],
    "zxspectrum": [".z80", ".tap", ".tzx", ".zip"],
}

DEFAULT_EXTENSIONS = [".zip", ".7z", ".bin", ".iso"]

MEDIA_SUBDIRS = [
    "images", "videos", "screenshots", "thumbnails",
    "marquees", "wheels", "fanart", "boxart",
]


def get_allowed_extensions(system_name):
    return ROM_EXTENSIONS.get(system_name.lower(), DEFAULT_EXTENSIONS)


def build_file_dialog_filter(system_name):
    exts = get_allowed_extensions(system_name)
    pattern = " ".join(f"*{e}" for e in exts)
    return [
        ("ROM Dosyaları", pattern),
        ("Tüm Dosyalar", "*.*"),
    ]


# ─── APPLE DOUBLE TEMİZLİĞİ ──────────────────────────────────────────────────

def remove_apple_double(rom_path):
    """
    ROM dosyasıyla aynı klasörde olan ._<romadı> dosyasını siler.
    Örneğin: Super Mario World (USA).zip → ._Super Mario World (USA).zip
    Dosya yoksa sessizce geçer.
    """
    rom_dir = os.path.dirname(rom_path)
    rom_filename = os.path.basename(rom_path)
    apple_double_path = os.path.join(rom_dir, f"._{rom_filename}")

    if os.path.isfile(apple_double_path):
        try:
            os.remove(apple_double_path)
            return True
        except Exception:
            return False
    return True  # Yoksa sorun değil


# ─── GAMELIST XML ─────────────────────────────────────────────────────────────

def remove_from_gamelist(rom_path, system_path):
    gamelist_path = os.path.join(system_path, "gamelist.xml")
    if not os.path.isfile(gamelist_path):
        return True

    stem = os.path.splitext(os.path.basename(rom_path))[0].lower()

    try:
        tree = ET.parse(gamelist_path)
        root = tree.getroot()

        to_remove = [
            game for game in root.findall("game")
            if (path_el := game.find("path")) is not None
            and os.path.splitext(os.path.basename(path_el.text))[0].lower() == stem
        ]
        for game in to_remove:
            root.remove(game)

        ET.indent(tree, space="  ")
        tree.write(gamelist_path, encoding="utf-8", xml_declaration=True)
        return True
    except Exception:
        return False


def remove_media_files(rom_path, system_path):
    stem = os.path.splitext(os.path.basename(rom_path))[0].lower()
    results = {"deleted": [], "failed": []}

    media_root = os.path.join(system_path, "media")
    for subdir in MEDIA_SUBDIRS:
        subdir_path = os.path.join(media_root, subdir)
        if not os.path.isdir(subdir_path):
            continue
        for entry in os.listdir(subdir_path):
            if os.path.splitext(entry)[0].lower() == stem:
                full_path = os.path.join(subdir_path, entry)
                try:
                    os.remove(full_path)
                    results["deleted"].append(full_path)
                except Exception as e:
                    results["failed"].append({"file": full_path, "error": str(e)})

    return results


# ─── EKLEME ──────────────────────────────────────────────────────────────────

def add_roms(source_paths, dest_system_path, progress_callback=None):
    results = {"success": [], "failed": [], "skipped": []}
    total = len(source_paths)

    for i, src in enumerate(source_paths):
        filename = os.path.basename(src)
        dest = os.path.join(dest_system_path, filename)

        if progress_callback:
            progress_callback(i + 1, total, filename)

        if os.path.exists(dest):
            results["skipped"].append(filename)
            continue

        try:
            shutil.copy2(src, dest)
            results["success"].append(filename)
        except Exception as e:
            results["failed"].append({"file": filename, "error": str(e)})

    return results


# ─── SİLME ───────────────────────────────────────────────────────────────────

def delete_games(roms, system_path, progress_callback=None):
    """
    Bir oyunu tüm bileşenleriyle siler:
      1. Apple Double dosyası (._romadı) — varsa
      2. Media dosyaları (resim, video, screenshot...)
      3. gamelist.xml kaydı
      4. ROM dosyası
    """
    results = {"success": [], "failed": []}
    total = len(roms)

    for i, rom in enumerate(roms):
        name = os.path.splitext(rom["name"])[0]
        rom_path = rom["path"]

        if progress_callback:
            progress_callback(i + 1, total, name)

        errors = []

        # 1. Apple Double (._) dosyası
        remove_apple_double(rom_path)  # Hata olsa bile devam et

        # 2. Media dosyaları
        media_result = remove_media_files(rom_path, system_path)
        if media_result["failed"]:
            errors.append(f"media: {len(media_result['failed'])} silinemedi")

        # 3. gamelist.xml kaydı
        if not remove_from_gamelist(rom_path, system_path):
            errors.append("gamelist.xml güncellenemedi")

        # 4. ROM dosyası
        try:
            os.remove(rom_path)
            if errors:
                results["failed"].append({"file": rom["name"], "error": ", ".join(errors)})
            else:
                results["success"].append(rom["name"])
        except Exception as e:
            errors.append(f"rom: {str(e)}")
            results["failed"].append({"file": rom["name"], "error": ", ".join(errors)})

    return results
