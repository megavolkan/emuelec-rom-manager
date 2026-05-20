    def _on_add_complete(self, results):
        print(f"[DEBUG add_complete] success={len(results['success'])} fail={len(results['failed'])} skip={len(results['skipped'])} cancelled={results.get('cancelled')}")
        for f in results['failed']:
            print(f"  FAIL: {f}")
        self._hide_progress()
        self.add_btn.configure(state="normal")

        ok   = len(results["success"])
        skip = len(results["skipped"])
        fail = len(results["failed"])
        cancelled = results.get("cancelled", False)

        parts = []
        if ok:        parts.append(f"{ok} eklendi")
        if skip:      parts.append(f"{skip} atlandı")
        if fail:      parts.append(f"{fail} başarısız")
        if cancelled: parts.append("iptal edildi")
        self._set_status(" · ".join(parts) if parts else "İşlem tamamlandı")

        if cancelled:
            self.toast.info("Kopyalama iptal edildi")
        elif fail == 0 and ok > 0:
            msg = f"{ok} ROM eklendi"
            if skip: msg += f"  ({skip} atlandı)"
            self.toast.success(msg)
        elif ok == 0 and fail == 0:
            self.toast.info(f"{skip} ROM zaten mevcut, atlandı")
        elif fail > 0 and ok == 0:
            self.toast.error(f"{fail} ROM eklenemedi")
        else:
            self.toast.warning(f"{ok} eklendi · {fail} başarısız")

        if self.current_system:
            self._on_system_selected(self.current_system)