"""
settings_window.py
Ayarlar penceresi — IGDB credentials ve uygulama tercihleri.
"""

import threading
import customtkinter as ctk
from tkinter import messagebox

from src.core import config
from src.core.scraper import IGDBScraper


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Ayarlar")
        self.geometry("480x560")
        self.minsize(480, 560)
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self._cfg = config.load()
        self._build_ui()
        self._load_values()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=24, pady=20)
        main.grid_columnconfigure(0, weight=1)

        row = 0

        ctk.CTkLabel(
            main, text="IGDB API (Twitch)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        ctk.CTkLabel(
            main,
            text="dev.twitch.tv/console adresinden aldığın bilgileri gir.",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        ).grid(row=row, column=0, sticky="w", pady=(0, 16))
        row += 1

        ctk.CTkLabel(main, text="Client ID", font=ctk.CTkFont(size=12)).grid(
            row=row, column=0, sticky="w")
        row += 1

        self.client_id_entry = ctk.CTkEntry(main, height=36, font=ctk.CTkFont(size=13))
        self.client_id_entry.grid(row=row, column=0, sticky="ew", pady=(4, 12))
        row += 1

        ctk.CTkLabel(main, text="Client Secret", font=ctk.CTkFont(size=12)).grid(
            row=row, column=0, sticky="w")
        row += 1

        self.client_secret_entry = ctk.CTkEntry(
            main, height=36, font=ctk.CTkFont(size=13), show="•")
        self.client_secret_entry.grid(row=row, column=0, sticky="ew", pady=(4, 8))
        row += 1

        self.show_secret_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            main, text="Secret'ı göster",
            variable=self.show_secret_var,
            font=ctk.CTkFont(size=12),
            command=self._toggle_secret,
        ).grid(row=row, column=0, sticky="w", pady=(0, 16))
        row += 1

        self.test_btn = ctk.CTkButton(
            main, text="Bağlantıyı Test Et",
            height=34, font=ctk.CTkFont(size=13),
            fg_color="transparent", border_width=1,
            command=self._test_credentials,
        )
        self.test_btn.grid(row=row, column=0, sticky="w", pady=(0, 6))
        row += 1

        self.test_label = ctk.CTkLabel(main, text="", font=ctk.CTkFont(size=12))
        self.test_label.grid(row=row, column=0, sticky="w", pady=(0, 20))
        row += 1

        ctk.CTkFrame(main, height=1, fg_color=("gray70", "gray35")).grid(
            row=row, column=0, sticky="ew", pady=(0, 16))
        row += 1

        ctk.CTkLabel(
            main, text="Scrape Ayarları",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=row, column=0, sticky="w", pady=(0, 10))
        row += 1

        self.auto_scrape_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            main,
            text="ROM eklendiğinde otomatik scrape yap",
            variable=self.auto_scrape_var,
            font=ctk.CTkFont(size=13),
        ).grid(row=row, column=0, sticky="w", pady=(0, 30))
        row += 1

        # Butonlar
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame, text="İptal",
            width=100, height=36,
            fg_color="transparent", border_width=1,
            command=self._on_close,
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Kaydet",
            width=100, height=36,
            command=self._save,
        ).grid(row=0, column=2)

    def _load_values(self):
        self.client_id_entry.insert(0, self._cfg.get("igdb_client_id", ""))
        self.client_secret_entry.insert(0, self._cfg.get("igdb_client_secret", ""))
        self.auto_scrape_var.set(self._cfg.get("auto_scrape", True))

    def _toggle_secret(self):
        self.client_secret_entry.configure(show="" if self.show_secret_var.get() else "•")

    def _test_credentials(self):
        cid = self.client_id_entry.get().strip()
        sec = self.client_secret_entry.get().strip()

        if not cid or not sec:
            self.test_label.configure(
                text="⚠  Client ID ve Secret gerekli", text_color="#e0a000")
            return

        self.test_btn.configure(state="disabled", text="Test ediliyor...")
        self.test_label.configure(text="")

        def do_test():
            scraper = IGDBScraper(cid, sec)
            ok = scraper.test_credentials()
            self.after(0, lambda: self._on_test_result(ok))

        threading.Thread(target=do_test, daemon=True).start()

    def _on_test_result(self, ok: bool):
        self.test_btn.configure(state="normal", text="Bağlantıyı Test Et")
        if ok:
            self.test_label.configure(text="✓  Bağlantı başarılı", text_color="#2ecc71")
        else:
            self.test_label.configure(
                text="✕  Client ID veya Secret hatalı", text_color="#e74c3c")

    def _save(self):
        self._cfg["igdb_client_id"]     = self.client_id_entry.get().strip()
        self._cfg["igdb_client_secret"] = self.client_secret_entry.get().strip()
        self._cfg["auto_scrape"]        = self.auto_scrape_var.get()

        if config.save(self._cfg):
            self.destroy()
        else:
            messagebox.showerror("Hata", "Ayarlar kaydedilemedi.")

    def _on_close(self):
        self.destroy()
