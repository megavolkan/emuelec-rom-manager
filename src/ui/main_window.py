"""
main_window.py
Ana uygulama penceresi — Aşama 1
"""

import os
import threading
import platform
import customtkinter as ctk
from tkinter import Canvas

from src.core.drive_detector import (
    detect_emuelec_drives,
    get_system_roms,
    format_size,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SYSTEM_LABELS = {
    "atari2600": "Atari 2600", "atari7800": "Atari 7800", "c64": "Commodore 64",
    "dreamcast": "Dreamcast", "fba": "FBA", "fds": "Famicom Disk",
    "gamegear": "Game Gear", "gb": "Game Boy", "gba": "Game Boy Advance",
    "gbc": "Game Boy Color", "genesis": "Genesis", "mame": "MAME",
    "mastersystem": "Master System", "megadrive": "Mega Drive", "n64": "Nintendo 64",
    "nds": "Nintendo DS", "neogeo": "Neo Geo", "nes": "NES",
    "ngp": "Neo Geo Pocket", "ngpc": "Neo Geo Pocket Color", "pce": "PC Engine",
    "pcengine": "PC Engine", "psp": "PSP", "psx": "PlayStation",
    "saturn": "Saturn", "scummvm": "ScummVM", "sega32x": "Sega 32X",
    "segacd": "Sega CD", "snes": "SNES", "supergrafx": "SuperGrafx",
    "tg16": "TurboGrafx-16", "vectrex": "Vectrex", "virtualboy": "Virtual Boy",
    "wonderswan": "WonderSwan", "wonderswancolor": "WonderSwan Color",
    "x68000": "X68000", "zxspectrum": "ZX Spectrum",
}

IS_MAC = platform.system() == "Darwin"
ROW_HEIGHT = 36
FONT_SIZE = 13


class VirtualListbox(ctk.CTkFrame):
    """
    Canvas tabanlı sanal liste — binlerce ROM'u anında render eder.
    Her satır için widget oluşturmaz, doğrudan canvas'a çizer.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._items = []
        self._row_height = ROW_HEIGHT

        self._canvas = Canvas(
            self, bg="#1a1a1a", bd=0, highlightthickness=0, relief="flat",
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._scrollbar = ctk.CTkScrollbar(self, command=self._canvas.yview)
        self._scrollbar.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._canvas.bind("<Configure>", self._on_resize)

        # Canvas'ın kendi MouseWheel event'i (scrollbar üzerindeyken)
        self._canvas.bind("<MouseWheel>", self._scroll)

    def scroll(self, delta):
        """Dışarıdan çağrılabilir scroll metodu."""
        self._canvas.yview_scroll(int(-delta), "units")

    def _scroll(self, event):
        if IS_MAC:
            self._canvas.yview_scroll(int(-event.delta), "units")
        else:
            self._canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

    def set_items(self, items):
        self._items = items
        self._redraw()

    def clear(self):
        self._items = []
        self._canvas.delete("all")
        self._canvas.configure(scrollregion=(0, 0, 0, 0))

    def show_message(self, text):
        """Canvas ortasına mesaj gösterir."""
        self._canvas.delete("all")
        self._canvas.update_idletasks()
        w = self._canvas.winfo_width() or 600
        h = self._canvas.winfo_height() or 400
        self._canvas.create_text(
            w // 2, h // 2, text=text,
            fill="#666666", font=("Helvetica", 14), anchor="center"
        )

    def _redraw(self):
        self._canvas.delete("all")
        w = self._canvas.winfo_width() or 800
        total_height = len(self._items) * self._row_height

        for i, rom in enumerate(self._items):
            y = i * self._row_height
            bg = "#383838" if i % 2 == 0 else "#2e2e2e"
            self._canvas.create_rectangle(0, y, w, y + self._row_height, fill=bg, outline="")

            name = os.path.splitext(rom["name"])[0]
            size = format_size(rom["size"])

            self._canvas.create_text(
                12, y + self._row_height // 2,
                text=name, anchor="w",
                fill="#e0e0e0", font=("Helvetica", FONT_SIZE),
            )
            self._canvas.create_text(
                w - 12, y + self._row_height // 2,
                text=size, anchor="e",
                fill="#888888", font=("Helvetica", 11),
            )

        self._canvas.configure(scrollregion=(0, 0, w, total_height))

    def _on_resize(self, event):
        if self._items:
            self._redraw()

    def is_under_cursor(self, x_root, y_root):
        """Verilen ekran koordinatı bu widget'ın canvas'ı üzerinde mi?"""
        try:
            x = self._canvas.winfo_rootx()
            y = self._canvas.winfo_rooty()
            w = self._canvas.winfo_width()
            h = self._canvas.winfo_height()
            return x <= x_root <= x + w and y <= y_root <= y + h
        except Exception:
            return False


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EmuELEC ROM Manager")
        self.geometry("1100x680")
        self.minsize(900, 580)

        self.current_drive = None
        self.current_system = None
        self.all_roms = []
        self.filtered_roms = []
        self.emuelec_drives = []
        self._loading_system = None

        self._build_ui()

        # Global mousewheel — tk seviyesinde bağla (CTk'nın bind_all kısıtlaması yok)
        self.tk.call("bind", "all", "<MouseWheel>", "")  # Önce temizle
        self._tk_widget = self.tk
        self.bind("<MouseWheel>", self._on_global_scroll)
        # tk.Widget düzeyinde global binding
        self._setup_global_scroll()

        self._scan_drives()

    def _setup_global_scroll(self):
        """Tkinter'ın alt seviye bind mekanizmasını kullanarak global scroll kurar."""
        # CTk'nın bind_all yasağını aşmak için doğrudan tk interpreter'a bind
        self.tk.createcommand("_global_scroll_handler", self._handle_tk_scroll)
        # Tüm widget'lar için MouseWheel event'ini yönlendir
        self.tk.eval("""
            bind all <MouseWheel> {
                _global_scroll_handler %D %X %Y
            }
        """)

    def _handle_tk_scroll(self, delta, x_root, y_root):
        """Tk'dan gelen global scroll event'ini işler."""
        delta = int(delta)
        x_root = int(x_root)
        y_root = int(y_root)

        # ROM listesi üzerinde mi?
        if hasattr(self, "rom_list") and self.rom_list.is_under_cursor(x_root, y_root):
            self.rom_list.scroll(delta)
            return

        # Sol panel (systems_scroll) üzerinde mi?
        if hasattr(self, "_systems_canvas") and self._systems_canvas:
            try:
                x = self._systems_canvas.winfo_rootx()
                y = self._systems_canvas.winfo_rooty()
                w = self._systems_canvas.winfo_width()
                h = self._systems_canvas.winfo_height()
                if x <= x_root <= x + w and y <= y_root <= y + h:
                    self._systems_canvas.yview_scroll(int(-delta / 20), "units")
            except Exception:
                pass

    def _on_global_scroll(self, event):
        pass  # _handle_tk_scroll halleder

    def _get_systems_canvas(self):
        """CTkScrollableFrame içindeki canvas'ı bulur."""
        for child in self.systems_scroll.winfo_children():
            if child.winfo_class() == "Canvas":
                return child
        return None

    # ─── UI BUILDER ──────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_left_panel()
        self._build_right_panel()
        self._build_statusbar()

    def _build_topbar(self):
        topbar = ctk.CTkFrame(self, height=56, corner_radius=0, fg_color=("gray85", "gray20"))
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            topbar, text="🎮 EmuELEC ROM Manager",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=16, pady=14, sticky="w")

        drive_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        drive_frame.grid(row=0, column=1, padx=16, pady=10, sticky="e")

        ctk.CTkLabel(drive_frame, text="Cihaz:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))

        self.drive_var = ctk.StringVar(value="Taranıyor...")
        self.drive_menu = ctk.CTkOptionMenu(
            drive_frame, variable=self.drive_var,
            values=["Taranıyor..."], command=self._on_drive_selected,
            width=220, font=ctk.CTkFont(size=13),
        )
        self.drive_menu.pack(side="left")

        self.refresh_btn = ctk.CTkButton(
            drive_frame, text="↻  Yenile", width=90,
            command=self._scan_drives, font=ctk.CTkFont(size=13),
        )
        self.refresh_btn.pack(side="left", padx=(10, 0))

    def _build_left_panel(self):
        self.left_panel = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=("gray90", "gray17"))
        self.left_panel.grid(row=1, column=0, sticky="nsew")
        self.left_panel.grid_propagate(False)
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.left_panel, text="SİSTEMLER",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray50", "gray60")
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.systems_scroll = ctk.CTkScrollableFrame(
            self.left_panel, fg_color="transparent", corner_radius=0
        )
        self.systems_scroll.grid(row=1, column=0, sticky="nsew")
        self.systems_scroll.grid_columnconfigure(0, weight=1)
        self.system_buttons = {}
        self._systems_canvas = None
        self.after(200, self._find_systems_canvas)

    def _find_systems_canvas(self):
        self._systems_canvas = self._get_systems_canvas()

    def _build_right_panel(self):
        right = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        search_bar = ctk.CTkFrame(right, height=48, fg_color=("gray88", "gray18"), corner_radius=0)
        search_bar.grid(row=0, column=0, sticky="ew")
        search_bar.grid_propagate(False)
        search_bar.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)

        ctk.CTkEntry(
            search_bar, placeholder_text="🔍  ROM ara...",
            textvariable=self.search_var,
            height=34, font=ctk.CTkFont(size=13),
            border_width=0, fg_color=("gray80", "gray25"),
        ).grid(row=0, column=0, padx=12, pady=7, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(right, mode="indeterminate", height=4, corner_radius=0)
        self.progress_bar.grid(row=1, column=0, sticky="ew")
        self.progress_bar.grid_remove()

        self.rom_list = VirtualListbox(right)
        self.rom_list.grid(row=2, column=0, sticky="nsew")

        self.rom_list.show_message("← Soldan bir sistem seçin")

    def _build_statusbar(self):
        statusbar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color=("gray80", "gray15"))
        statusbar.grid(row=2, column=0, columnspan=2, sticky="ew")
        statusbar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            statusbar, text="Hazır",
            font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
        )
        self.status_label.pack(side="left", padx=12, pady=6)

        self.rom_count_label = ctk.CTkLabel(
            statusbar, text="",
            font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
        )
        self.rom_count_label.pack(side="right", padx=12, pady=6)

    # ─── DRIVE SCAN ──────────────────────────────────────────────────────────

    def _scan_drives(self):
        self._set_status("Sürücüler taranıyor...")
        self.refresh_btn.configure(state="disabled")
        self.drive_menu.configure(values=["Taranıyor..."])
        self.drive_var.set("Taranıyor...")
        threading.Thread(target=self._scan_drives_thread, daemon=True).start()

    def _scan_drives_thread(self):
        drives = detect_emuelec_drives()
        self.after(0, lambda: self._on_scan_complete(drives))

    def _on_scan_complete(self, drives):
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
        label = drive.get("label") or "SD Kart"
        size = format_size(drive["total"])
        count = len(drive["emuelec"]["systems"])
        return f"{label} — {count} sistem ({size})"

    # ─── EVENT HANDLERS ───────────────────────────────────────────────────────

    def _on_drive_selected(self, display_name):
        try:
            idx = list(self.drive_menu.cget("values")).index(display_name)
        except ValueError:
            return
        if idx >= len(self.emuelec_drives):
            return

        self.current_drive = self.emuelec_drives[idx]
        self.current_system = None
        self.all_roms = []
        self.filtered_roms = []
        self._loading_system = None

        self._populate_systems(self.current_drive["emuelec"]["systems"])
        self.rom_list.clear()
        self.rom_list.show_message("← Soldan bir sistem seçin")
        self._hide_progress()
        self.rom_count_label.configure(text="")
        self._set_status(f"Cihaz: {self.current_drive.get('label', 'SD Kart')} — {self.current_drive['mountpoint']}")

    def _on_system_selected(self, system_name):
        for name, btn in self.system_buttons.items():
            btn.configure(fg_color=("gray70", "gray35") if name == system_name else "transparent")

        self.current_system = system_name
        self._loading_system = system_name
        self.all_roms = []
        self.filtered_roms = []
        self.search_var.set("")

        self.rom_list.clear()
        self.rom_list.show_message(f"{SYSTEM_LABELS.get(system_name, system_name.upper())} yükleniyor...")
        self._show_progress()
        self.rom_count_label.configure(text="")
        self._set_status(f"Yükleniyor: {SYSTEM_LABELS.get(system_name, system_name.upper())}...")

        games_path = self.current_drive["emuelec"]["games_path"]
        threading.Thread(
            target=self._load_roms_thread,
            args=(system_name, games_path),
            daemon=True
        ).start()

    def _load_roms_thread(self, system_name, games_path):
        roms = get_system_roms(games_path, system_name)
        self.after(0, lambda: self._on_roms_loaded(system_name, roms))

    def _on_roms_loaded(self, system_name, roms):
        if self._loading_system != system_name:
            return
        self._hide_progress()
        self.all_roms = roms
        self._apply_filter()
        system_label = SYSTEM_LABELS.get(system_name, system_name.upper())
        self._set_status(f"{system_label} — {len(roms)} ROM")

    def _on_search_changed(self, *args):
        self._apply_filter()

    def _apply_filter(self):
        term = self.search_var.get().lower().strip()
        self.filtered_roms = [r for r in self.all_roms if term in r["name"].lower()] if term else self.all_roms[:]
        self._populate_rom_list(self.filtered_roms)

    # ─── POPULATE ────────────────────────────────────────────────────────────

    def _populate_systems(self, systems):
        for widget in self.systems_scroll.winfo_children():
            widget.destroy()
        self.system_buttons = {}

        for i, system in enumerate(systems):
            label = SYSTEM_LABELS.get(system, system.upper())
            btn = ctk.CTkButton(
                self.systems_scroll, text=label, anchor="w",
                height=36, corner_radius=6, fg_color="transparent",
                hover_color=("gray75", "gray30"), text_color=("gray10", "gray90"),
                font=ctk.CTkFont(size=13),
                command=lambda s=system: self._on_system_selected(s),
            )
            btn.grid(row=i, column=0, padx=8, pady=2, sticky="ew")
            self.system_buttons[system] = btn

    def _populate_rom_list(self, roms):
        self.rom_list.clear()

        if not roms:
            if self.current_system and not self.all_roms:
                msg = "Bu sistemde henüz ROM yok"
            elif self.current_system and self.all_roms:
                msg = f'"{self.search_var.get()}" için sonuç bulunamadı'
            else:
                msg = "← Soldan bir sistem seçin"
            self.rom_list.show_message(msg)
            self.rom_count_label.configure(text="")
            return

        system_label = SYSTEM_LABELS.get(self.current_system, self.current_system.upper()) if self.current_system else ""
        self.rom_count_label.configure(text=f"{system_label} — {len(roms)} ROM")
        self.rom_list.set_items(roms)

    # ─── PROGRESS ────────────────────────────────────────────────────────────

    def _show_progress(self):
        self.progress_bar.grid()
        self.progress_bar.start()

    def _hide_progress(self):
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

    def _set_status(self, text):
        self.status_label.configure(text=text)
