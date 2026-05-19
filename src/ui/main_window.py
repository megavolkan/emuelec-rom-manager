"""
main_window.py
Ana uygulama penceresi — Aşama 2
"""

import os
import threading
import platform
import customtkinter as ctk
from tkinter import Canvas, filedialog, messagebox

from src.core.drive_detector import (
    detect_emuelec_drives,
    get_system_roms,
    format_size,
)
from src.core.rom_manager import add_roms, delete_games, build_file_dialog_filter

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

COLOR_ROW_EVEN     = "#383838"
COLOR_ROW_ODD      = "#2e2e2e"
COLOR_ROW_SELECTED = "#1f538d"
COLOR_ROW_HOVER    = "#444444"
COLOR_TEXT         = "#e0e0e0"
COLOR_TEXT_DIM     = "#888888"
COLOR_EMPTY_TEXT   = "#666666"
COLOR_BG           = "#1a1a1a"


class VirtualListbox(ctk.CTkFrame):
    """
    Canvas tabanlı sanal liste — tüm ROM'ları anında render eder.
    Scroll sonrası görünür alanı yeniden çizer (virtual rendering).
    """

    def __init__(self, master, on_selection_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._items = []
        self._selected = set()
        self._last_clicked = None
        self._hover_idx = None
        self._row_height = ROW_HEIGHT
        self._on_selection_change = on_selection_change

        self._canvas = Canvas(
            self, bg=COLOR_BG, bd=0, highlightthickness=0, relief="flat",
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")

        # Scrollbar — yview komutunu yakalayarak _redraw'u tetikliyoruz
        self._scrollbar = ctk.CTkScrollbar(self, command=self._yview_and_redraw)
        self._scrollbar.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Motion>", self._on_hover)
        self._canvas.bind("<Leave>", self._on_leave)

    def _yview_and_redraw(self, *args):
        """Scrollbar'dan gelen yview komutunu canvas'a iletir ve yeniden çizer."""
        self._canvas.yview(*args)
        self._redraw()

    def scroll(self, delta):
        """Dışarıdan çağrılabilir scroll (global handler için)."""
        self._canvas.yview_scroll(int(-delta), "units")
        self._redraw()

    # ─── PUBLIC API ──────────────────────────────────────────────────────────

    def set_items(self, items):
        self._items = items
        self._selected = set()
        self._last_clicked = None
        self._hover_idx = None
        self._canvas.yview_moveto(0)
        self._redraw()
        if self._on_selection_change:
            self._on_selection_change([])

    def clear(self):
        self._items = []
        self._selected = set()
        self._last_clicked = None
        self._hover_idx = None
        self._canvas.delete("all")
        self._canvas.configure(scrollregion=(0, 0, 0, 0))
        if self._on_selection_change:
            self._on_selection_change([])

    def show_message(self, text):
        self._canvas.delete("all")
        self._canvas.update_idletasks()
        w = self._canvas.winfo_width() or 600
        h = self._canvas.winfo_height() or 400
        self._canvas.create_text(
            w // 2, h // 2, text=text,
            fill=COLOR_EMPTY_TEXT, font=("Helvetica", 14), anchor="center"
        )

    def get_selected_items(self):
        return [self._items[i] for i in sorted(self._selected) if i < len(self._items)]

    def select_all(self):
        self._selected = set(range(len(self._items)))
        self._redraw()
        if self._on_selection_change:
            self._on_selection_change(self.get_selected_items())

    def deselect_all(self):
        self._selected = set()
        self._redraw()
        if self._on_selection_change:
            self._on_selection_change([])

    def is_under_cursor(self, x_root, y_root):
        try:
            x = self._canvas.winfo_rootx()
            y = self._canvas.winfo_rooty()
            w = self._canvas.winfo_width()
            h = self._canvas.winfo_height()
            return x <= x_root <= x + w and y <= y_root <= y + h
        except Exception:
            return False

    # ─── EVENTS ──────────────────────────────────────────────────────────────

    def _on_mousewheel(self, event):
        if IS_MAC:
            self._canvas.yview_scroll(int(-event.delta), "units")
        else:
            self._canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
        self._redraw()

    def _on_click(self, event):
        if not self._items:
            return
        idx = self._canvas_y_to_index(event.y)
        if idx is None or idx >= len(self._items):
            return

        multi = (event.state & 0x8) if IS_MAC else (event.state & 0x4)
        shift = event.state & 0x1

        if shift and self._last_clicked is not None:
            lo, hi = sorted([self._last_clicked, idx])
            if not multi:
                self._selected = set()
            for i in range(lo, hi + 1):
                self._selected.add(i)
        elif multi:
            if idx in self._selected:
                self._selected.discard(idx)
            else:
                self._selected.add(idx)
        else:
            self._selected = {idx}

        self._last_clicked = idx
        self._redraw()
        if self._on_selection_change:
            self._on_selection_change(self.get_selected_items())

    def _on_hover(self, event):
        idx = self._canvas_y_to_index(event.y)
        if idx != self._hover_idx:
            self._hover_idx = idx
            self._redraw()

    def _on_leave(self, event):
        self._hover_idx = None
        self._redraw()

    def _on_resize(self, event):
        self._redraw()

    def _canvas_y_to_index(self, canvas_y):
        """Canvas widget koordinatını (scroll dahil) liste indeksine çevirir."""
        abs_y = self._canvas.canvasy(canvas_y)
        idx = int(abs_y // self._row_height)
        return idx if 0 <= idx < len(self._items) else None

    # ─── RENDER ──────────────────────────────────────────────────────────────

    def _redraw(self):
        self._canvas.delete("all")
        if not self._items:
            return

        w = self._canvas.winfo_width() or 800
        h = self._canvas.winfo_height() or 600
        total_h = len(self._items) * self._row_height

        # scrollregion'ı güncelle
        self._canvas.configure(scrollregion=(0, 0, w, total_h))

        # Görünür aralığı hesapla
        scroll_top = self._canvas.canvasy(0)
        scroll_bot = self._canvas.canvasy(h)
        first = max(0, int(scroll_top // self._row_height))
        last  = min(len(self._items), int(scroll_bot // self._row_height) + 2)

        for i in range(first, last):
            rom = self._items[i]
            y0 = i * self._row_height
            y1 = y0 + self._row_height

            if i in self._selected:
                bg = COLOR_ROW_SELECTED
            elif i == self._hover_idx:
                bg = COLOR_ROW_HOVER
            elif i % 2 == 0:
                bg = COLOR_ROW_EVEN
            else:
                bg = COLOR_ROW_ODD

            self._canvas.create_rectangle(0, y0, w, y1, fill=bg, outline="")

            self._canvas.create_text(
                12, y0 + self._row_height // 2,
                text=os.path.splitext(rom["name"])[0],
                anchor="w", fill=COLOR_TEXT, font=("Helvetica", FONT_SIZE),
            )
            self._canvas.create_text(
                w - 12, y0 + self._row_height // 2,
                text=format_size(rom["size"]),
                anchor="e", fill=COLOR_TEXT_DIM, font=("Helvetica", 11),
            )


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EmuELEC ROM Manager")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.current_drive = None
        self.current_system = None
        self.all_roms = []
        self.filtered_roms = []
        self.emuelec_drives = []
        self._loading_system = None
        self._selected_roms = []

        self._build_ui()
        self._setup_global_scroll()
        self._scan_drives()

    # ─── GLOBAL SCROLL ───────────────────────────────────────────────────────

    def _setup_global_scroll(self):
        self.tk.createcommand("_global_scroll_handler", self._handle_tk_scroll)
        self.tk.eval("""
            bind all <MouseWheel> {
                _global_scroll_handler %D %X %Y
            }
        """)

    def _handle_tk_scroll(self, delta, x_root, y_root):
        delta = int(delta)
        x_root = int(x_root)
        y_root = int(y_root)

        if hasattr(self, "rom_list") and self.rom_list.is_under_cursor(x_root, y_root):
            self.rom_list.scroll(delta)
            return

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

    # ─── UI BUILDER ──────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_left_panel()
        self._build_right_panel()
        self._build_toolbar()
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
        for child in self.systems_scroll.winfo_children():
            if child.winfo_class() == "Canvas":
                self._systems_canvas = child
                return

    def _build_right_panel(self):
        self.right_panel = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.right_panel.grid(row=1, column=1, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        topbar = ctk.CTkFrame(self.right_panel, height=48, fg_color=("gray88", "gray18"), corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)

        ctk.CTkEntry(
            topbar, placeholder_text="🔍  ROM ara...",
            textvariable=self.search_var,
            height=34, font=ctk.CTkFont(size=13),
            border_width=0, fg_color=("gray80", "gray25"),
        ).grid(row=0, column=0, padx=12, pady=7, sticky="ew")

        self.select_all_btn = ctk.CTkButton(
            topbar, text="Tümü", width=60, height=30,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", border_width=1,
            command=self._on_select_all,
        )
        self.select_all_btn.grid(row=0, column=1, padx=(0, 8), pady=9)

        self.progress_bar = ctk.CTkProgressBar(self.right_panel, mode="indeterminate", height=4, corner_radius=0)
        self.progress_bar.grid(row=0, column=0, sticky="sew")
        self.progress_bar.grid_remove()

        self.rom_list = VirtualListbox(
            self.right_panel,
            on_selection_change=self._on_selection_changed,
        )
        self.rom_list.grid(row=1, column=0, sticky="nsew")
        self.rom_list.show_message("← Soldan bir sistem seçin")

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color=("gray83", "gray18"))
        toolbar.grid(row=2, column=1, sticky="ew")
        toolbar.grid_propagate(False)

        self.add_btn = ctk.CTkButton(
            toolbar, text="＋  ROM Ekle",
            width=130, height=36, font=ctk.CTkFont(size=13),
            command=self._on_add_roms, state="disabled",
        )
        self.add_btn.pack(side="left", padx=12, pady=8)

        self.delete_btn = ctk.CTkButton(
            toolbar, text="🗑  Seçilileri Sil",
            width=150, height=36, font=ctk.CTkFont(size=13),
            fg_color="#8b1a1a", hover_color="#a02020",
            command=self._on_delete_roms, state="disabled",
        )
        self.delete_btn.pack(side="left", padx=(0, 12), pady=8)

        self.selection_label = ctk.CTkLabel(
            toolbar, text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        )
        self.selection_label.pack(side="left", padx=4)

    def _build_statusbar(self):
        statusbar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color=("gray80", "gray15"))
        statusbar.grid(row=3, column=0, columnspan=2, sticky="ew")
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
        self._selected_roms = []

        self._populate_systems(self.current_drive["emuelec"]["systems"])
        self.rom_list.clear()
        self.rom_list.show_message("← Soldan bir sistem seçin")
        self._hide_progress()
        self.rom_count_label.configure(text="")
        self._update_toolbar()
        self._set_status(f"Cihaz: {self.current_drive.get('label', 'SD Kart')} — {self.current_drive['mountpoint']}")

    def _on_system_selected(self, system_name):
        for name, btn in self.system_buttons.items():
            btn.configure(fg_color=("gray70", "gray35") if name == system_name else "transparent")

        self.current_system = system_name
        self._loading_system = system_name
        self.all_roms = []
        self.filtered_roms = []
        self._selected_roms = []
        self.search_var.set("")

        self.rom_list.clear()
        self.rom_list.show_message(f"{SYSTEM_LABELS.get(system_name, system_name.upper())} yükleniyor...")
        self._show_progress()
        self.rom_count_label.configure(text="")
        self._update_toolbar()
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

    def _on_selection_changed(self, selected_items):
        self._selected_roms = selected_items
        self._update_toolbar()

    def _on_select_all(self):
        if len(self._selected_roms) == len(self.filtered_roms) and self.filtered_roms:
            self.rom_list.deselect_all()
        else:
            self.rom_list.select_all()

    # ─── ROM EKLE ────────────────────────────────────────────────────────────

    def _on_add_roms(self):
        if not self.current_system:
            return

        file_types = build_file_dialog_filter(self.current_system)
        paths = filedialog.askopenfilenames(
            title=f"ROM Ekle — {SYSTEM_LABELS.get(self.current_system, self.current_system.upper())}",
            filetypes=file_types,
        )
        if not paths:
            return

        dest = os.path.join(
            self.current_drive["emuelec"]["games_path"],
            self.current_system
        )

        self._set_status(f"{len(paths)} ROM kopyalanıyor...")
        self.add_btn.configure(state="disabled")
        self._show_progress()

        threading.Thread(
            target=self._add_roms_thread,
            args=(list(paths), dest),
            daemon=True
        ).start()

    def _add_roms_thread(self, paths, dest):
        results = add_roms(paths, dest)
        self.after(0, lambda: self._on_add_complete(results))

    def _on_add_complete(self, results):
        self._hide_progress()
        self.add_btn.configure(state="normal")

        parts = []
        if results["success"]:
            parts.append(f"{len(results['success'])} ROM eklendi")
        if results["skipped"]:
            parts.append(f"{len(results['skipped'])} zaten vardı")
        if results["failed"]:
            parts.append(f"{len(results['failed'])} başarısız")

        self._set_status(" · ".join(parts) if parts else "İşlem tamamlandı")

        if self.current_system:
            self._on_system_selected(self.current_system)

    # ─── ROM SİL ─────────────────────────────────────────────────────────────

    def _on_delete_roms(self):
        if not self._selected_roms:
            return

        count = len(self._selected_roms)
        names = "\n".join(f"  • {os.path.splitext(r['name'])[0]}" for r in self._selected_roms[:8])
        if count > 8:
            names += f"\n  ... ve {count - 8} oyun daha"

        confirm = messagebox.askyesno(
            "Oyun Sil",
            f"{count} oyun kalıcı olarak silinecek:\n\n{names}\n\n"
            f"ROM dosyası, kapak resimleri, videolar ve\n"
            f"gamelist.xml kaydı birlikte silinecek.\n\n"
            f"Devam edilsin mi?",
            icon="warning",
        )
        if not confirm:
            return

        system_path = os.path.join(
            self.current_drive["emuelec"]["games_path"],
            self.current_system
        )

        self._set_status(f"{count} oyun siliniyor...")
        self.delete_btn.configure(state="disabled")
        self._show_progress()

        threading.Thread(
            target=self._delete_roms_thread,
            args=(self._selected_roms, system_path),
            daemon=True
        ).start()

    def _delete_roms_thread(self, roms, system_path):
        results = delete_games(roms, system_path)
        self.after(0, lambda: self._on_delete_complete(results))

    def _on_delete_complete(self, results):
        self._hide_progress()

        parts = []
        if results["success"]:
            parts.append(f"{len(results['success'])} oyun silindi")
        if results["failed"]:
            parts.append(f"{len(results['failed'])} silinemedi")

        self._set_status(" · ".join(parts) if parts else "İşlem tamamlandı")

        if self.current_system:
            self._on_system_selected(self.current_system)

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

    # ─── TOOLBAR ─────────────────────────────────────────────────────────────

    def _update_toolbar(self):
        has_system = self.current_system is not None
        has_selection = len(self._selected_roms) > 0

        self.add_btn.configure(state="normal" if has_system else "disabled")
        self.delete_btn.configure(state="normal" if has_selection else "disabled")

        if has_selection:
            self.selection_label.configure(text=f"{len(self._selected_roms)} oyun seçili")
        else:
            self.selection_label.configure(text="")

    # ─── PROGRESS ────────────────────────────────────────────────────────────

    def _show_progress(self):
        self.progress_bar.grid()
        self.progress_bar.start()

    def _hide_progress(self):
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

    def _set_status(self, text):
        self.status_label.configure(text=text)
