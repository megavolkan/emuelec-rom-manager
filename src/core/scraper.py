"""
scraper.py
IGDB API entegrasyonu.
ROM metadata ve kapak resmi çekme işlemleri.
"""

import os
import re
import requests

# IGDB API sabitleri
IGDB_CLIENT_ID     = ""  # Ayarlardan gelecek
IGDB_CLIENT_SECRET = ""  # Ayarlardan gelecek
TWITCH_TOKEN_URL   = "https://id.twitch.tv/oauth2/token"
IGDB_API_BASE      = "https://api.igdb.com/v4"

# EmuELEC sistem adı → IGDB platform ID
PLATFORM_IDS = {
    "atari2600":      59,
    "atari7800":      60,
    "c64":            15,
    "dreamcast":      23,
    "gamegear":       35,
    "gb":             33,
    "gba":            24,
    "gbc":            22,
    "genesis":        29,
    "mastersystem":   64,
    "megadrive":      29,
    "n64":            4,
    "nds":            20,
    "neogeo":         80,
    "nes":            18,
    "ngp":            119,
    "ngpc":           120,
    "pce":            128,
    "pcengine":       128,
    "psp":            38,
    "psx":            7,
    "saturn":         32,
    "sega32x":        30,
    "segacd":         78,
    "snes":           19,
    "tg16":           128,
    "gb":             33,
    "virtualboy":     87,
    "wonderswan":     57,
    "wonderswancolor":123,
}


class ScraperError(Exception):
    pass


class IGDBScraper:
    """IGDB API istemcisi."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id     = client_id
        self.client_secret = client_secret
        self._access_token = None
        self._session      = requests.Session()
        self._session.timeout = 30

    def _get_token(self) -> str:
        """Twitch OAuth token alır (cache'li)."""
        if self._access_token:
            return self._access_token

        r = self._session.post(TWITCH_TOKEN_URL, params={
            "client_id":     self.client_id,
            "client_secret": self.client_secret,
            "grant_type":    "client_credentials",
        })
        r.raise_for_status()
        self._access_token = r.json()["access_token"]
        return self._access_token

    def _headers(self) -> dict:
        return {
            "Client-ID":     self.client_id,
            "Authorization": f"Bearer {self._get_token()}",
        }

    def test_credentials(self) -> bool:
        """Client ID ve Secret'ı doğrular."""
        try:
            self._access_token = None  # Token cache'i temizle
            self._get_token()
            return True
        except Exception:
            return False

    def scrape_rom(self, rom_path: str, system_name: str) -> "IGDBResult":
        """
        ROM dosya adından oyun adını çıkarıp IGDB'de arar.
        Raises: ScraperError
        """
        platform_id = PLATFORM_IDS.get(system_name.lower())
        filename = os.path.basename(rom_path)
        search_name = _clean_rom_name(filename)

        if not search_name:
            raise ScraperError("Oyun adı çıkarılamadı")

        # Platform filtreli arama
        query = f"""
            search "{search_name}";
            fields name, summary, first_release_date, involved_companies.company.name,
                   involved_companies.developer, involved_companies.publisher,
                   genres.name, cover.image_id, rating, game_modes.name;
            limit 5;
        """
        if platform_id:
            query = f"""
                search "{search_name}";
                fields name, summary, first_release_date, involved_companies.company.name,
                       involved_companies.developer, involved_companies.publisher,
                       genres.name, cover.image_id, rating, game_modes.name;
                where platforms = ({platform_id});
                limit 5;
            """

        try:
            r = self._session.post(
                f"{IGDB_API_BASE}/games",
                headers=self._headers(),
                data=query,
            )
            r.raise_for_status()
            games = r.json()
        except Exception as e:
            raise ScraperError(f"API hatası: {e}")

        if not games:
            # Platform filtresi olmadan tekrar dene
            if platform_id:
                return self._scrape_without_platform(search_name)
            raise ScraperError("Oyun bulunamadı")

        return IGDBResult(games[0])

    def _scrape_without_platform(self, search_name: str) -> "IGDBResult":
        query = f"""
            search "{search_name}";
            fields name, summary, first_release_date, involved_companies.company.name,
                   involved_companies.developer, involved_companies.publisher,
                   genres.name, cover.image_id, rating;
            limit 3;
        """
        r = self._session.post(
            f"{IGDB_API_BASE}/games",
            headers=self._headers(),
            data=query,
        )
        r.raise_for_status()
        games = r.json()
        if not games:
            raise ScraperError("Oyun bulunamadı")
        return IGDBResult(games[0])

    def download_image(self, image_id: str, dest_path: str,
                       size: str = "cover_big") -> bool:
        """
        IGDB kapak resmini indirir.
        size: thumb, cover_small, cover_big, screenshot_med, screenshot_big
        """
        url = f"https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg"
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            r = self._session.get(url, timeout=60)
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return True
        except Exception:
            return False


class IGDBResult:
    """Bir ROM için çekilen IGDB metadata."""

    def __init__(self, data: dict):
        self._data = data

    @property
    def name(self) -> str:
        return self._data.get("name", "")

    @property
    def description(self) -> str:
        return self._data.get("summary", "")

    @property
    def developer(self) -> str:
        companies = self._data.get("involved_companies", [])
        for c in companies:
            if c.get("developer"):
                return c.get("company", {}).get("name", "")
        return ""

    @property
    def publisher(self) -> str:
        companies = self._data.get("involved_companies", [])
        for c in companies:
            if c.get("publisher"):
                return c.get("company", {}).get("name", "")
        return ""

    @property
    def genre(self) -> str:
        genres = self._data.get("genres", [])
        if genres:
            return genres[0].get("name", "")
        return ""

    @property
    def release_date(self) -> str:
        ts = self._data.get("first_release_date")
        if not ts:
            return ""
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%Y%m%dT000000")

    @property
    def rating(self) -> str:
        r = self._data.get("rating")
        if r is None:
            return ""
        return str(round(r / 100, 2))

    @property
    def players(self) -> str:
        return ""

    @property
    def cover_image_id(self) -> str | None:
        cover = self._data.get("cover")
        if not cover:
            return None
        return cover.get("image_id")

    def to_gamelist_dict(self) -> dict:
        return {
            "name":        self.name,
            "desc":        self.description,
            "developer":   self.developer,
            "publisher":   self.publisher,
            "genre":       self.genre,
            "releasedate": self.release_date,
            "rating":      self.rating,
            "players":     self.players,
        }


def _clean_rom_name(filename: str) -> str:
    """
    ROM dosya adından arama için temiz bir oyun adı çıkarır.
    'Super Mario World (USA) (Rev 1).sfc' → 'Super Mario World'
    """
    # Uzantıyı kaldır
    name = os.path.splitext(filename)[0]
    # Parantez içindeki bölgeleri, revizyonları vb. kaldır
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'\[[^\]]*\]', '', name)
    # Tirelerden sonraki kısmı kaldır (bazı ROM'larda disk numarası vb.)
    # Çoklu boşlukları temizle
    name = re.sub(r'\s+', ' ', name).strip()
    return name


# Geriye dönük uyumluluk için alias
ScraperResult = IGDBResult
ScreenScraper = IGDBScraper
