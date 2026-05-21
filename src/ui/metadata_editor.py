"""
metadata_editor.py
ROM metadata düzenleme penceresi.
"""

import os
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox

from src.core.gamelist import get_game_metadata, write_game_entry


class MetadataEditor(ctk.CTkToplevel):
    def __init__(self, parent, rom: dict, system_path: str, on_save=None):
        super().__init__(parent)

        self._rom = rom
        self._system_path = system_path
        self._on_save = on_save

        rom_name = os.path.splitext(rom["name"])[0]
        self.title(f"Metadata — {rom_name}")
        self.geometry("520x580")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self._build_ui()
        self._load_existing()

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=20, pady=(16, 0))
        main.grid_columnconfigure(1, weight=1)

        fields = [
            ("Ad",          "name",        False),
            ("Geliştirici", "developer",   False),
            ("Yayıncı",     "publisher",   False),
            ("Tür",         "genre",       False),
            ("Çıkış Tarihi","releasedate", False),
            ("Oyuncu",      "players",     False),
            ("Puan (0-1)",  "rating",      False),
            ("Açıklama",    "desc",        True),
        ]

        self._entries = {}
        row = 0

        for label, key, multiline in fields:
            ctk.CTkLabel(
                main, text=label,
                font=ctk.CTkFont(size=12),
                anchor="e", width=100,
            ).grid(row=row, column=0, padx=(0, 10), pady=(8, 0), sticky="ne")

            if multiline:
                widget = ctk.CTkTextbox(main, height=100, font=ctk.CTkFont(size=13))
                widget.grid(row=row, column=1, pady=(8, 0), sticky="ew")
            else:
                widget = ctk.CTkEntry(main, height=34, font=ctk.CTkFont(size=13))
                widget.grid(row=row, column=1, pady=(8, 0), sticky="ew")

            self._entries[key] = (widget, multiline)
            row += 1

        # Alt butonlar
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=12)
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame, text="İptal",
            width=100, height=36,
            fg_color="transparent", border_width=1,
            command=self.destroy,
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Kaydet",
            width=100, height=36,
            command=self._save,
        ).grid(row=0, column=2)

    def _load_existing(self):
        """Mevcut gamelist.xml verisini yükler."""
        meta = get_game_metadata(self._system_path, self._rom["name"])
        if not meta:
            return

        for key, (widget, multiline) in self._entries.items():
            value = meta.get(key, "")
            if not value:
                continue
            # Tarih alanını okunabilir formata çevir
            if key == "releasedate":
                value = _emuelec_date_to_display(value)
            if multiline:
                widget.delete("1.0", "end")
                widget.insert("1.0", value)
            else:
                widget.delete(0, "end")
                widget.insert(0, value)

    def _save(self):
        metadata = {}
        for key, (widget, multiline) in self._entries.items():
            if multiline:
                value = widget.get("1.0", "end").strip()
            else:
                value = widget.get().strip()
            # Tarihi EmuELEC formatına geri çevir
            if key == "releasedate" and value:
                value = _display_date_to_emuelec(value)
            metadata[key] = value

        ok = write_game_entry(
            self._system_path,
            self._rom["name"],
            metadata,
        )

        if ok:
            if self._on_save:
                self._on_save()
            self.destroy()
        else:
            messagebox.showerror("Hata", "Metadata kaydedilemedi.")


def _emuelec_date_to_display(date_str: str) -> str:
    """
    EmuELEC tarih formatını okunabilire çevirir.
    '19950805T000000' → '05.08.1995'
    """
    try:
        dt = datetime.strptime(date_str[:8], "%Y%m%d")
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return date_str


def _display_date_to_emuelec(date_str: str) -> str:
    """
    Okunabilir tarihi EmuELEC formatına çevirir.
    '05.08.1995' → '19950805T000000'
    Farklı format denemelerini destekler: DD.MM.YYYY, YYYY-MM-DD, YYYY
    """
    formats = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y%m%dT000000")
        except ValueError:
            continue
    # Sadece yıl girilmişse
    if date_str.strip().isdigit() and len(date_str.strip()) == 4:
        return f"{date_str.strip()}0101T000000"
    # Geçersiz format — orijinali döndür
    return date_str
