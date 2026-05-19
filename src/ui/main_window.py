"""
main_window.py
Ana uygulama penceresi — Aşama 1
"""

import os
import threading
import customtkinter as ctk
from tkinter import messagebox

from src.core.drive_detector import (
    detect_emuelec_drives,
    get_mounted_drives,
    get_system_roms,
    format_size,
)

# Tema ayarları
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Sistem etiketleri (görüntüleme isimleri)
SYSTEM_LABELS = {
    "atari2600": "Atari 2600",
    "atari7800": "Atari 7800",
    "c64": "Commodore 64",
    "dreamcast": "Dreamcast",
    "fba": "FBA",
    "fds": "Famicom Disk",
    "gamegear": "Game Gear",
    "gb": "Game Boy",
    "gba": "Game Boy Advance",
    "gbc": "Game Boy Color",
    "genesis": "Genesis",
    "mame": "MAME",
    "mastersystem": "Master System",
    "megadrive": "Mega Drive",
    "n64": "Nintendo 64",
    "nds": "Nintendo DS",
    "neogeo": "Neo Geo",
    "nes": "NES",
    "ngp": "Neo Geo Pocket",
    "ngpc": "Neo Geo Pocket Color",
    "pce": "PC Engine",
    "pcengine": "PC Engine",
    "psp": "PSP",
    "psx": "PlayStation",
    "saturn": "Saturn",
    "scummvm": "ScummVM",
    "sega32x": "Sega 32X",
    "segacd": "Sega CD",
    "snes": "SNES",
    "supergrafx": "SuperGrafx",
    "tg16": "TurboGrafx-16",
    "vectrex": "Vectrex",
    "virtualboy": "Virtual Boy",
    "wonderswan": "WonderSwan",
    "wonderswancolor": "WonderSwan Color",
    "x68000": "X68000",
    "zxspectrum": "ZX Spectrum",
}


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EmuELEC ROM Manager")
        self.geometry("1100x680")
        self.minsize(900, 580)

        # State
        self.current_drive = None
        self.current_system = None
        self.all_roms = []
        self.filtered_roms = []
        self.emuelec_drives = []

        self._build_ui()
        self._scan_drives()

    # ─── UI BUILDER ──────────────────────────────────────────────────────────

    def _build_ui(self):
        """Tüm UI bileşenlerini oluşturur."""
        self.grid_columnconfigure(0, weight=0)  # Sol panel sabit
        self.grid_columnconfigure(1, weight=1)  # Sağ panel esnek
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_left_panel()
        self._build_right_panel()
        self._build_statusbar()

    def _build_topbar(self):
        """Üst bar — Cihaz seçimi ve kontroller."""
        topbar = ctk.CTkFrame(self, height=56, corner_radius=0, fg_color=("gray85", "gray20"))
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(1, weight=1)

        # Logo / İsim
        title_label = ctk.CTkLabel(
            topbar, text="🎮 EmuELEC ROM Manager",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=16, pady=14, sticky="w")

        # Cihaz seçim dropdown
        drive_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        drive_frame.grid(row=0, column=1, padx=16, pady=10, sticky="e")

        ctk.CTkLabel(drive_frame, text="Cihaz:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))

        self.drive_var = ctk.StringVar(value="Taranıyor...")
        self.drive_menu = ctk.CTkOptionMenu(
            drive_frame,
            variable=self.drive_var,
            values=["Taranıyor..."],
            command=self._on_drive_selected,
            width=220,
            font=ctk.CTkFont(size=13),
        )
        self.drive_menu.pack(side="left")

        # Yenile butonu
        self.refresh_btn = ctk.CTkButton(
            drive_frame, text="↻  Yenile",
            width=90, command=self._scan_drives,
            font=ctk.CTkFont(size=13),
        )
        self.refresh_btn.pack(side="left", padx=(10, 0))

    def _build_left_panel(self):
        """Sol panel — Sistem listesi."""
        self.left_panel = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=("gray90", "gray17"))
        self.left_panel.grid(row=1, column=0, sticky="nsew")
        self.left_panel.grid_propagate(False)
        self.left_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.left_panel, text="SİSTEMLER",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray50", "gray60")
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.systems_scroll = ctk.CTkScrollableFrame(
            self.left_panel, fg_color="transparent", corner_radius=0
        )
        self.systems_scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.systems_scroll.grid_columnconfigure(0, weight=1)

        self.system_buttons = {}

    def _build_right_panel(self):
        """Sağ panel — ROM listesi."""
        right = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Arama barı
        search_bar = ctk.CTkFrame(right, height=48, fg_color=("gray88", "gray18"), corner_radius=0)
        search_bar.grid(row=0, column=0, sticky="ew")
        search_bar.grid_propagate(False)
        search_bar.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)

        self.search_entry = ctk.CTkEntry(
            search_bar, placeholder_text="🔍  ROM ara...",
            textvariable=self.search_var,
            height=34, font=ctk.CTkFont(size=13),
            border_width=0, fg_color=("gray80", "gray25"),
        )
        self.search_entry.grid(row=0, column=0, padx=12, pady=7, sticky="ew")

        # ROM listesi
        self.rom_frame = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.rom_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.rom_frame.grid_columnconfigure(0, weight=1)

        # Boş durum mesajı
        self.empty_label = ctk.CTkLabel(
            self.rom_frame,
            text="← Soldan bir sistem seçin",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray55"),
        )
        self.empty_label.grid(row=0, column=0, pady=80)

    def _build_statusbar(self):
        """Alt durum çubuğu."""
        statusbar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color=("gray80", "gray15"))
        statusbar.grid(row=2, column=0, columnspan=2, sticky="ew")
        statusbar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            statusbar, text="Hazır",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
        )
        self.status_label.pack(side="left", padx=12, pady=6)

        self.rom_count_label = ctk.CTkLabel(
            statusbar, text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
        )
        self.rom_count_label.pack(side="right", padx=12, pady=6)

    # ─── DRIVE SCAN ──────────────────────────────────────────────────────────

    def _scan_drives(self):
        """Sürücüleri arka planda tarar."""
        self._set_status("Sürücüler taranıyor...")
        self.refresh_btn.configure(state="disabled")
        self.drive_menu.configure(values=["Taranıyor..."])
        self.drive_var.set("Taranıyor...")

        thread = threading.Thread(target=self._scan_drives_thread, daemon=True)
        thread.start()

    def _scan_drives_thread(self):
        """Arka plan thread — sürücü tarama."""
        drives = detect_emuelec_drives()
        self.after(0, lambda: self._on_scan_complete(drives))

    def _on_scan_complete(self, drives):
        """Tarama tamamlandığında UI güncellenir."""
        self.emuelec_drives = drives
        self.refresh_btn.configure(state="normal")

        if not drives:
            self.drive_menu.configure(values=["EmuELEC cihazı bulunamadı"])
            self.drive_var.set("EmuELEC cihazı bulunamadı")
            self._set_status("Hiçbir EmuELEC cihazı bulunamadı. SD kartı taktınız mı?")
            return

        labels = [self._drive_display_name(d) for d in drives]
        self.drive_menu.configure(values=labels)
        self.drive_var.set(labels[0])
        self._on_drive_selected(labels[0])

    def _drive_display_name(self, drive):
        """Sürücü için kullanıcıya gösterilecek isim."""
        label = drive.get("label") or "SD Kart"
        size = format_size(drive["total"])
        systems_count = len(drive["emuelec"]["systems"])
        return f"{label} — {systems_count} sistem ({size})"

    # ─── EVENT HANDLERS ───────────────────────────────────────────────────────

    def _on_drive_selected(self, display_name):
        """Dropdown'dan cihaz seçilince."""
        idx = self.drive_menu.cget("values").index(display_name)
        if idx < 0 or idx >= len(self.emuelec_drives):
            return

        self.current_drive = self.emuelec_drives[idx]
        self.current_system = None
        self.all_roms = []
        self.filtered_roms = []

        self._populate_systems(self.current_drive["emuelec"]["systems"])
        self._clear_rom_list()
        self.empty_label.configure(text="← Soldan bir sistem seçin")
        self.empty_label.grid()
        self._set_status(f"Cihaz: {self.current_drive.get('label', 'SD Kart')} — {self.current_drive['mountpoint']}")

    def _on_system_selected(self, system_name):
        """Sol panelden sistem seçilince."""
        # Buton renk güncelleme
        for name, btn in self.system_buttons.items():
            if name == system_name:
                btn.configure(fg_color=("gray70", "gray35"))
            else:
                btn.configure(fg_color="transparent")

        self.current_system = system_name
        games_path = self.current_drive["emuelec"]["games_path"]
        self.all_roms = get_system_roms(games_path, system_name)
        self.search_var.set("")
        self._apply_filter()

    def _on_search_changed(self, *args):
        """Arama kutusu değişince."""
        self._apply_filter()

    def _apply_filter(self):
        """Mevcut arama terimine göre ROM listesini filtreler."""
        term = self.search_var.get().lower().strip()
        if term:
            self.filtered_roms = [r for r in self.all_roms if term in r["name"].lower()]
        else:
            self.filtered_roms = self.all_roms[:]
        self._populate_rom_list(self.filtered_roms)

    # ─── POPULATE ────────────────────────────────────────────────────────────

    def _populate_systems(self, systems):
        """Sol paneli sistemlerle doldurur."""
        for widget in self.systems_scroll.winfo_children():
            widget.destroy()
        self.system_buttons = {}

        for i, system in enumerate(systems):
            label = SYSTEM_LABELS.get(system, system.upper())
            btn = ctk.CTkButton(
                self.systems_scroll,
                text=label,
                anchor="w",
                height=36,
                corner_radius=6,
                fg_color="transparent",
                hover_color=("gray75", "gray30"),
                text_color=("gray10", "gray90"),
                font=ctk.CTkFont(size=13),
                command=lambda s=system: self._on_system_selected(s),
            )
            btn.grid(row=i, column=0, padx=8, pady=2, sticky="ew")
            self.system_buttons[system] = btn

    def _populate_rom_list(self, roms):
        """Sağ paneli ROM listesiyle doldurur."""
        for widget in self.rom_frame.winfo_children():
            widget.destroy()

        if not roms:
            label_text = "Bu sistemde ROM bulunamadı" if self.all_roms else "← Soldan bir sistem seçin"
            if self.current_system and not self.all_roms:
                label_text = "Bu sistemde henüz ROM yok"
            elif self.current_system and self.all_roms and not roms:
                label_text = f'"{self.search_var.get()}" için sonuç bulunamadı'

            empty = ctk.CTkLabel(
                self.rom_frame, text=label_text,
                font=ctk.CTkFont(size=14),
                text_color=("gray50", "gray55"),
            )
            empty.grid(row=0, column=0, pady=80)
            self.rom_count_label.configure(text="")
            return

        system_label = SYSTEM_LABELS.get(self.current_system, self.current_system.upper()) if self.current_system else ""
        self.rom_count_label.configure(
            text=f"{system_label} — {len(roms)} ROM"
        )

        for i, rom in enumerate(roms):
            self._create_rom_row(i, rom)

    def _create_rom_row(self, row_idx, rom):
        """Tek bir ROM satırı oluşturur."""
        row_color = ("gray92", "gray22") if row_idx % 2 == 0 else ("gray88", "gray20")

        frame = ctk.CTkFrame(self.rom_frame, fg_color=row_color, corner_radius=4, height=38)
        frame.grid(row=row_idx, column=0, padx=8, pady=1, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_propagate(False)

        # ROM adı (uzantısız)
        name_no_ext = os.path.splitext(rom["name"])[0]
        name_label = ctk.CTkLabel(
            frame, text=name_no_ext,
            anchor="w", font=ctk.CTkFont(size=13),
        )
        name_label.grid(row=0, column=0, padx=12, pady=0, sticky="w")

        # Boyut
        size_label = ctk.CTkLabel(
            frame, text=format_size(rom["size"]),
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray55"),
            width=70, anchor="e",
        )
        size_label.grid(row=0, column=1, padx=(0, 8), pady=0, sticky="e")

    # ─── HELPERS ─────────────────────────────────────────────────────────────

    def _clear_rom_list(self):
        """ROM listesini temizler."""
        for widget in self.rom_frame.winfo_children():
            widget.destroy()

    def _set_status(self, text):
        """Durum çubuğu metnini günceller."""
        self.status_label.configure(text=text)
