"""
drive_detector.py
Bağlı sürücüleri tarar ve EmuELEC yapısını tanır.
"""

import os
import sys
import platform
import psutil

# EmuELEC sistemlerini tanımak için kullanılan klasör isimleri
EMUELEC_SYSTEM_DIRS = {
    "atari2600", "atari7800", "atarist", "c64", "dreamcast",
    "fba", "fds", "gamegear", "gb", "gba", "gbc", "genesis",
    "mame", "mastersystem", "megadrive", "n64", "nds", "neogeo",
    "nes", "ngp", "ngpc", "pce", "pcengine", "psp", "psx",
    "saturn", "scummvm", "sega32x", "segacd", "snes", "supergrafx",
    "tg16", "vectrex", "virtualboy", "wonderswan", "wonderswancolor",
    "x68000", "zxspectrum"
}

# Minimum kaç EmuELEC klasörü bulunursa "cihaz" sayılır
MIN_SYSTEM_MATCH = 2


def get_mounted_drives():
    """İşletim sistemine göre bağlı sürücüleri döndürür."""
    drives = []
    partitions = psutil.disk_partitions(all=False)

    for p in partitions:
        # macOS: /Volumes/... altındaki harici sürücüler
        # Windows: D:\, E:\ gibi sürücüler
        # Linux: /media/... veya /mnt/... altındaki mount noktaları
        if _is_external_drive(p):
            try:
                usage = psutil.disk_usage(p.mountpoint)
                drives.append({
                    "mountpoint": p.mountpoint,
                    "device": p.device,
                    "fstype": p.fstype,
                    "total": usage.total,
                    "free": usage.free,
                    "label": _get_drive_label(p.mountpoint),
                })
            except (PermissionError, OSError):
                continue

    return drives


def _is_external_drive(partition):
    """Bir partition'ın harici/çıkarılabilir sürücü olup olmadığını kontrol eder."""
    mp = partition.mountpoint
    system = platform.system()

    if system == "Darwin":  # macOS
        return mp.startswith("/Volumes/") and mp != "/Volumes"

    elif system == "Windows":
        # A: ve B: disket sürücüleri hariç
        drive_letter = mp[0].upper() if mp else ""
        return drive_letter not in ("A", "B", "C")

    elif system == "Linux":
        return mp.startswith(("/media/", "/mnt/", "/run/media/"))

    return False


def _get_drive_label(mountpoint):
    """Sürücünün etiketini (ismini) döndürür."""
    system = platform.system()

    if system == "Darwin":
        # /Volumes/SD_KART → "SD_KART"
        return os.path.basename(mountpoint)

    elif system == "Windows":
        try:
            import ctypes
            volume_name = ctypes.create_unicode_buffer(1024)
            ctypes.windll.kernel32.GetVolumeInformationW(
                mountpoint, volume_name, ctypes.sizeof(volume_name),
                None, None, None, None, 0
            )
            return volume_name.value or os.path.basename(mountpoint)
        except Exception:
            return mountpoint

    else:  # Linux
        return os.path.basename(mountpoint)


def detect_emuelec_drives(drives=None):
    """
    Verilen sürücü listesinden EmuELEC yapısına sahip olanları tespit eder.
    drives parametresi None ise get_mounted_drives() çağrılır.
    """
    if drives is None:
        drives = get_mounted_drives()

    emuelec_drives = []

    for drive in drives:
        result = check_emuelec_structure(drive["mountpoint"])
        if result["is_emuelec"]:
            drive["emuelec"] = result
            emuelec_drives.append(drive)

    return emuelec_drives


def check_emuelec_structure(mountpoint):
    """
    Bir mountpoint'in EmuELEC yapısına sahip olup olmadığını kontrol eder.
    Kök dizindeki klasörleri EMUELEC_SYSTEM_DIRS ile karşılaştırır.
    """
    try:
        entries = os.listdir(mountpoint)
    except (PermissionError, OSError):
        return {"is_emuelec": False, "systems": [], "games_path": None}

    found_systems = []
    for entry in entries:
        entry_lower = entry.lower()
        if entry_lower in EMUELEC_SYSTEM_DIRS:
            full_path = os.path.join(mountpoint, entry)
            if os.path.isdir(full_path):
                found_systems.append(entry_lower)

    is_emuelec = len(found_systems) >= MIN_SYSTEM_MATCH

    return {
        "is_emuelec": is_emuelec,
        "systems": sorted(found_systems),
        "games_path": mountpoint if is_emuelec else None,
    }


def get_system_roms(games_path, system_name):
    """
    Belirtilen sistem klasöründeki ROM dosyalarını listeler.
    gamelist.xml ve media klasörü hariç tutulur.
    """
    system_path = os.path.join(games_path, system_name)

    if not os.path.isdir(system_path):
        return []

    roms = []
    try:
        for entry in os.listdir(system_path):
            full_path = os.path.join(system_path, entry)
            if os.path.isfile(full_path) and entry.lower() != "gamelist.xml":
                roms.append({
                    "name": entry,
                    "path": full_path,
                    "size": os.path.getsize(full_path),
                    "system": system_name,
                })
    except (PermissionError, OSError):
        pass

    return sorted(roms, key=lambda r: r["name"].lower())


def format_size(size_bytes):
    """Byte cinsinden boyutu okunabilir formata çevirir."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
