import re
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from app.core.config import settings


class ScraperEngine:
    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    @staticmethod
    async def scrape_url(url: str) -> Dict[str, Any]:
        """Główna metoda statyczna wywoływana przez AuditEngine."""
        engine = ScraperEngine()
        return await engine.execute(url)

    async def execute(self, url: str) -> Dict[str, Any]:
        """Pobiera i analizuje treść w pamięci RAM bez utwalania danych wrażliwych."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        html_content = await self._fetch_html(url)
        if not html_content:
            return {
                "scraped_success": False,
                "error_details": "Nie udało się połączyć ze stroną ogłoszenia.",
                "price": 0.0,
                "title": "Ogłoszenie nieosiągalne",
                "description": "",
                "images_count": 0,
                "location": "Brak danych",
                "seller_type": "Osoba Prywatna",
                "shipping_cost": 0.0,
            }

        if "olx.pl" in domain:
            return self._parse_olx(html_content, url)
        elif "otomoto.pl" in domain:
            return self._parse_otomoto(html_content, url)
        else:
            return self._parse_universal_ai(html_content, url)

    async def _fetch_html(self, url: str) -> Optional[str]:
        try:
            if settings.SCRAPERAPI_KEY:
                api_url = f"http://api.scraperapi.com?api_key={settings.SCRAPERAPI_KEY}&url={url}"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(api_url)
                    if resp.status_code == 200:
                        return resp.text

            async with httpx.AsyncClient(timeout=10.0, headers=self.headers, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.text
        except Exception as e:
            print(f"[ScraperEngine Error] {e}")
        return None

    def _parse_olx(self, html: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        title_elem = soup.find("h1", {"data-cy": "ad_title"}) or soup.find("h4") or soup.find("h3")
        title = title_elem.get_text(strip=True) if title_elem else "Ogłoszenie OLX"

        price_elem = soup.find("h3", {"data-cy": "ad_price"}) or soup.find("h2")
        price_raw = price_elem.get_text(strip=True) if price_elem else ""

        desc_elem = soup.find("div", {"data-cy": "ad_description"}) or soup.find("div", class_=re.compile("css-.*"))
        desc = desc_elem.get_text(separator="\n", strip=True) if desc_elem else ""

        # Analiza w locie: zliczamy jedynie liczbę zdjęć zamiast zapisywać ich adresy URL
        images_count = len([
            img for img in soup.find_all("img") 
            if (src := img.get("src") or img.get("data-src")) and "olx" in src and "image" in src
        ])

        loc_elem = soup.find("p", {"data-aria": "label"})
        location = loc_elem.get_text(strip=True) if loc_elem else "Polska"

        return {
            "target_url": url,
            "title": title,
            "price": self._clean_price(price_raw),
            "shipping_cost": 25.0 if "przesyłka olx" in html.lower() else 0.0,
            "seller_type": "Firma" if "firmowe" in html.lower() else "Osoba Prywatna",
            "description": desc,
            "images_count": images_count,
            "location": location,
            "parser_type": "DEDICATED_OLX",
            "scraped_success": True,
        }

    def _parse_otomoto(self, html: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        title_elem = soup.find("h1") or soup.find("title")
        title = title_elem.get_text(strip=True) if title_elem else "Ogłoszenie Otomoto"

        price_elem = soup.find("span", class_=re.compile(".*price.*")) or soup.find("h3")
        price_raw = price_elem.get_text(strip=True) if price_elem else ""

        desc = ""
        desc_elem = soup.find("div", {"data-content": "description"}) or soup.find("article")
        if desc_elem:
            desc = desc_elem.get_text(separator="\n", strip=True)

        images_count = len(soup.find_all("img", src=re.compile(".*otomoto.*")))

        return {
            "target_url": url,
            "title": title,
            "price": self._clean_price(price_raw),
            "shipping_cost": 0.0,
            "seller_type": "Firma" if "dealer" in url.lower() or "firma" in html.lower() else "Osoba Prywatna",
            "description": desc,
            "images_count": max(1, images_count),
            "location": "Polska",
            "parser_type": "DEDICATED_OTOMOTO",
            "scraped_success": True,
        }

    def _parse_universal_ai(self, html: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_price = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount")

        title = og_title["content"] if og_title and "content" in og_title.attrs else ""
        description = og_desc["content"] if og_desc and "content" in og_desc.attrs else ""
        price_raw = og_price["content"] if og_price and "content" in og_price.attrs else ""

        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else (soup.title.string if soup.title else "Ogłoszenie bez tytułu")

        if not description:
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            main_content = soup.find("main") or soup.find("article") or soup.body
            if main_content:
                paragraphs = [p.get_text(strip=True) for p in main_content.find_all(["p", "li"])]
                description = " ".join(paragraphs[:15])

        if not price_raw:
            price_match = re.search(r"(\d[\d\s\xa0]{1,}\s*(?:zł|PLN|EUR|\$))", html, re.IGNORECASE)
            if price_match:
                price_raw = price_match.group(1).strip()

        images_count = len(soup.find_all("img"))

        return {
            "target_url": url,
            "title": title,
            "price": self._clean_price(price_raw),
            "shipping_cost": 20.0,
            "seller_type": "Osoba Prywatna",
            "description": description[:3000],
            "images_count": min(15, images_count),
            "location": "Polska",
            "parser_type": "UNIVERSAL_AI_FALLBACK",
            "scraped_success": True,
        }

    @staticmethod
    def _clean_price(price_raw: str) -> float:
        if not price_raw:
            return 0.0

        cleaned = re.sub(r"[^\d,\.]", "", str(price_raw))

        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            return float(cleaned)
        except ValueError:
            return 0.0