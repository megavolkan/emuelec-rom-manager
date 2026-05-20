"""
dialogs.py
Uygulama genelinde kullanılan özel diyalog pencereleri.
"""

import os
import customtkinter as ctk


class OverwriteDialog(ctk.CTkToplevel):
    """
    Dosya çakışması diyaloğu.
    Tekli veya çoklu dosya için üzerine yaz / atla / iptal seçenekleri sunar.
    """

    def __init__(self, parent, filename, remaining=0):
        """
        Args:
            parent: Ana pencere
            filename: Çakışan dosyanın adı
            remaining: Bu dosyadan sonra kaç tane daha çakışma var
        """
        super().__init__(parent)

        self.result = None  # "overwrite" | "skip" | "overwrite_all" | "skip_all" | "cancel"

        self.title("Dosya Zaten Var")
        self.geometry("420x220")
        self.resizable(False, False)
        self.grab_set()  # Modal
        self.focus_set()

        # macOS'ta pencereyi öne getir
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

        # İçerik
        ctk.CTkLabel(
            self, text="⚠  Dosya zaten mevcut",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(24, 6))

        ctk.CTkLabel(
            self, text=filename,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            wraplength=380,
        ).pack(pady=(0, 16))

        # Buton alanı
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24)

        ctk.CTkButton(
            btn_frame, text="Üzerine Yaz",
            width=110, height=34,
            command=lambda: self._close("overwrite"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Atla",
            width=80, height=34,
            fg_color="transparent", border_width=1,
            command=lambda: self._close("skip"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="İptal",
            width=80, height=34,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray60"),
            command=lambda: self._close("cancel"),
        ).pack(side="right")

        # "Tümüne uygula" — sadece birden fazla çakışma varsa göster
        if remaining > 0:
            apply_frame = ctk.CTkFrame(self, fg_color="transparent")
            apply_frame.pack(fill="x", padx=24, pady=(12, 0))

            ctk.CTkLabel(
                apply_frame,
                text=f"{remaining} dosya daha çakışıyor:",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60"),
            ).pack(side="left", padx=(0, 12))

            ctk.CTkButton(
                apply_frame, text="Tümüne Üzerine Yaz",
                width=150, height=30,
                font=ctk.CTkFont(size=12),
                command=lambda: self._close("overwrite_all"),
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                apply_frame, text="Tümünü Atla",
                width=110, height=30,
                font=ctk.CTkFont(size=12),
                fg_color="transparent", border_width=1,
                command=lambda: self._close("skip_all"),
            ).pack(side="left")

        # ESC ile iptal
        self.bind("<Escape>", lambda e: self._close("cancel"))

        # Pencere kapatılırsa iptal say
        self.protocol("WM_DELETE_WINDOW", lambda: self._close("cancel"))

        self.wait_window()

    def _close(self, result):
        self.result = result
        self.destroy()
