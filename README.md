# EmuELEC ROM Manager

macOS, Windows ve Linux üzerinde çalışan, EmuELEC tabanlı retro oyun cihazları için ROM yönetim uygulaması.

## Özellikler

- 🔍 SD kart otomatik tespiti (EmuELEC yapısı tanıma)
- 🎮 Sistem bazlı ROM listeleme (SNES, NES, GBA, PSX...)
- ➕ ROM ekleme & ➖ silme (toplu işlem desteği)
- 🔎 ROM arama ve filtreleme
- 🖼️ Metadata & kapak resmi yönetimi (ScreenScraper entegrasyonu)
- 💾 Çoklu cihaz profili (R36S, G90 vb.)

## Kurulum

### Gereksinimler

- Python 3.10+
- pip

### Bağımlılıklar

```bash
pip install -r requirements.txt
```

### Çalıştırma

```bash
python main.py
```

## Geliştirme Aşamaları

- [x] Aşama 1 — Temel: Sürücü tespiti, sistem & ROM listesi
- [ ] Aşama 2 — Yönetim: ROM ekle/sil, toplu işlem, arama
- [ ] Aşama 3 — Metadata: gamelist.xml, ScreenScraper API
- [ ] Aşama 4 — Cihaz Profilleri: Çoklu cihaz, ayarlar ekranı
- [ ] Aşama 5 — Dağıtım: PyInstaller ile .app / .exe / binary

## Lisans

MIT
