"""
toast.py
İşlem sonuçları için geçici bildirim (toast) sistemi.
Ekranın sağ üstünden kayarak gelir, otomatik kaybolur.
"""

import customtkinter as ctk


class Toast(ctk.CTkFrame):
    """
    Tek bir toast bildirimi.
    Türler: "success", "error", "warning", "info"
    """

    COLORS = {
        "success": ("#1a7a3a", "#1a7a3a"),
        "error":   ("#8b1a1a", "#8b1a1a"),
        "warning": ("#7a5a00", "#7a5a00"),
        "info":    ("#1a4a7a", "#1a4a7a"),
    }

    ICONS = {
        "success": "✓",
        "error":   "✕",
        "warning": "⚠",
        "info":    "ℹ",
    }

    def __init__(self, parent, message, kind="info", duration=3500):
        color = self.COLORS.get(kind, self.COLORS["info"])
        super().__init__(
            parent,
            fg_color=color,
            corner_radius=8,
        )

        icon = self.ICONS.get(kind, "ℹ")

        ctk.CTkLabel(
            self, text=icon,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=(14, 6), pady=12)

        ctk.CTkLabel(
            self, text=message,
            font=ctk.CTkFont(size=13),
            text_color="white",
            wraplength=280,
            justify="left",
        ).pack(side="left", padx=(0, 14), pady=12)

        self._duration = duration
        self._after_id = None

    def show(self, x, y):
        self.place(x=x, y=y)
        self.lift()
        self._after_id = self.after(self._duration, self.dismiss)

    def dismiss(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self.place_forget()
        self.destroy()


class ToastManager:
    """
    Toast bildirimlerini yönetir.
    Birden fazla toast üst üste yığılır.
    """

    MARGIN_RIGHT = 16
    MARGIN_TOP   = 70
    SPACING      = 10
    TOAST_WIDTH  = 340
    TOAST_HEIGHT = 58

    def __init__(self, parent):
        self._parent = parent
        self._toasts = []

    def show(self, message, kind="info", duration=3500):
        toast = Toast(self._parent, message, kind=kind, duration=duration)

        # Konumu hesapla
        self._parent.update_idletasks()
        win_w = self._parent.winfo_width()
        x = win_w - self.TOAST_WIDTH - self.MARGIN_RIGHT
        y = self.MARGIN_TOP + len(self._toasts) * (self.TOAST_HEIGHT + self.SPACING)

        self._toasts.append(toast)
        toast.show(x, y)

        # Toast kapanınca listeden çıkar
        duration_plus = duration + 200
        self._parent.after(duration_plus, lambda: self._remove(toast))

    def _remove(self, toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._reposition()

    def _reposition(self):
        """Kalan toast'ları yukarı kaydır."""
        self._parent.update_idletasks()
        win_w = self._parent.winfo_width()
        x = win_w - self.TOAST_WIDTH - self.MARGIN_RIGHT
        for i, toast in enumerate(self._toasts):
            y = self.MARGIN_TOP + i * (self.TOAST_HEIGHT + self.SPACING)
            try:
                toast.place(x=x, y=y)
            except Exception:
                pass

    def success(self, message, duration=3500):
        self.show(message, kind="success", duration=duration)

    def error(self, message, duration=4500):
        self.show(message, kind="error", duration=duration)

    def warning(self, message, duration=4000):
        self.show(message, kind="warning", duration=duration)

    def info(self, message, duration=3000):
        self.show(message, kind="info", duration=duration)
