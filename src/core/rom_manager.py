"""
rom_manager.py
ROM ekleme, silme ve dosya işlemleri.
Bir ROM = dosya + Apple Double (._) + media + gamelist.xml kaydı

EmuELEC media yapısı:
  snes/images/     (media/ ara klasörü YOK)
  snes/videos/
  snes/screenshots/
  vb.
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

# EmuELEC media klasörleri — sistem klasörünün direkt altında (media/ ara klasörü yok)
# Örnek: /Volumes/SD/snes/images/, /Volumes/SD/snes/videos/
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


def _is_valid_rom_source(path):
    filename = os.path.basename(path)
    return not (filename.startswith("._") or filename.startswith("."))


def _copy_file(src, dest):
    shutil.copyfile(src, dest)


# ─── APPLE DOUBLE ─────────────────────────────────────────────────────────────

def remove_apple_double(rom_path):
    apple_double = os.path.join(
        os.path.dirname(rom_path),
        f"._{os.path.basename(rom_path)}"
    )
    if os.path.isfile(apple_double):
        try:
            os.remove(apple_double)
        except Exception:
            pass


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
    """
    ROM'a ait media dosyalarını siler.
    EmuELEC yapısı: system_path/images/, system_path/videos/ vb.
    (media/ ara klasörü olmadan direkt sistem klasörünün altında)
    """
    stem = os.path.splitext(os.path.basename(rom_path))[0].lower()
    results = {"deleted": [], "failed": []}

    for subdir in MEDIA_SUBDIRS:
        # Doğrudan sistem klasörü altında ara
        subdir_path = os.path.join(system_path, subdir)
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


def get_media_image_path(system_path: str, rom_filename: str) -> str:
    """
    ROM için kapak resmi yolunu döndürür.
    Göreli yol: ./images/RomAdı.jpg
    """
    stem = os.path.splitext(rom_filename)[0]
    return f"./images/{stem}.jpg"


def get_media_image_dest(system_path: str, rom_filename: str) -> str:
    """
    ROM için kapak resmi tam disk yolunu döndürür.
    """
    stem = os.path.splitext(rom_filename)[0]
    return os.path.join(system_path, "images", f"{stem}.jpg")


# ─── EKLEME ──────────────────────────────────────────────────────────────────

def add_roms(source_paths, dest_system_path, conflict_callback=None):
    results = {"success": [], "failed": [], "skipped": [], "cancelled": False}

    valid_paths = [p for p in source_paths if _is_valid_rom_source(p)]

    conflicts = [
        p for p in valid_paths
        if os.path.exists(os.path.join(dest_system_path, os.path.basename(p)))
    ]
    conflict_set = set(conflicts)
    bulk_action = None

    for src in valid_paths:
        filename = os.path.basename(src)
        dest = os.path.join(dest_system_path, filename)

        if src in conflict_set:
            if bulk_action == "overwrite_all":
                action = "overwrite"
            elif bulk_action == "skip_all":
                action = "skip"
            elif conflict_callback:
                remaining = len([p for p in conflicts if p != src and p not in results["success"]])
                action = conflict_callback(filename, remaining)
                if action == "overwrite_all":
                    bulk_action = "overwrite_all"
                    action = "overwrite"
                elif action == "skip_all":
                    bulk_action = "skip_all"
                    action = "skip"
                elif action == "cancel":
                    results["cancelled"] = True
                    break
            else:
                action = "skip"

            if action == "skip":
                results["skipped"].append(filename)
                continue

            try:
                os.remove(dest)
            except Exception as e:
                results["failed"].append({"file": filename, "error": str(e)})
                continue

        try:
            _copy_file(src, dest)
            results["success"].append(filename)
        except Exception as e:
            results["failed"].append({"file": filename, "error": str(e)})

    return results


# ─── SİLME ───────────────────────────────────────────────────────────────────

def delete_games(roms, system_path, progress_callback=None):
    results = {"success": [], "failed": []}
    total = len(roms)

    for i, rom in enumerate(roms):
        name = os.path.splitext(rom["name"])[0]
        rom_path = rom["path"]

        if progress_callback:
            progress_callback(i + 1, total, name)

        errors = []

        remove_apple_double(rom_path)

        media_result = remove_media_files(rom_path, system_path)
        if media_result["failed"]:
            errors.append(f"media: {len(media_result['failed'])} silinemedi")

        if not remove_from_gamelist(rom_path, system_path):
            errors.append("gamelist.xml güncellenemedi")

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
