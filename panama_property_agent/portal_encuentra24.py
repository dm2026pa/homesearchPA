import re
import time
import logging
from typing import List, Optional, Dict
import requests
from bs4 import BeautifulSoup
from .models import Property, SearchCriteria

logger = logging.getLogger(__name__)

class Encuentra24Scraper:
    BASE_URL = "https://www.encuentra24.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    }

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(self.HEADERS)

    def search(self, criteria: SearchCriteria, max_pages_per_category: int = 3) -> List[Property]:
        results: Dict[str, Property] = {}

        categories = [
            ("apartamento", "/panama-es/bienes-raices-venta-de-propiedades-apartamentos", ""),
            ("casa", "/panama-es/bienes-raices-venta-de-propiedades-casas", ""),
            ("casa", "/panama-es/bienes-raices-venta-de-propiedades-casas", "|keyword.brisas"),
            ("casa", "/panama-es/bienes-raices-venta-de-propiedades-casas", "|keyword.panama%20norte")
        ]

        base_filter = f"f_price.{criteria.min_price}-{criteria.max_price}|f_rooms.{criteria.min_bedrooms}.|f_area.{int(criteria.min_total_area_m2)}-"

        for prop_type, cat_path, extra_filter in categories:
            filter_str = f"{base_filter}{extra_filter}"
            pages_to_scan = 1 if extra_filter else max_pages_per_category
            for page in range(1, pages_to_scan + 1):
                url = f"{self.BASE_URL}{cat_path}"
                params = {
                    "page": page,
                    "q": filter_str
                }
                logger.info(f"Querying {prop_type} {extra_filter or 'general'} page {page}...")

                try:
                    resp = self.session.get(url, params=params, timeout=15)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("a", class_=lambda c: c and "item-card-link" in c)
                    logger.info(f"Found {len(cards)} cards on {prop_type} page {page}")

                    for card in cards:
                        prop = self._parse_card(card, prop_type)
                        if prop and prop.id not in results and prop.price > 0 and prop.rooms >= 3:
                            results[prop.id] = prop

                    time.sleep(0.3)
                except Exception as e:
                    logger.error(f"Failed query on {url}: {e}")

        property_list = list(results.values())
        logger.info(f"Total unique properties fetched across real pages: {len(property_list)}")

        # Enrich descriptions
        for p in property_list:
            if len(p.description) < 400 or not any(k in p.description.lower() for k in ["parque", "piscina", "cancha", "niños", "juegos", "estrenar", "remodelado"]):
                self._enrich_property_details(p)
                time.sleep(0.2)

        return property_list

    def _parse_card(self, a_tag, prop_type: str) -> Optional[Property]:
        href = a_tag.get("href", "")
        if not href:
            return None

        full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
        parts = href.strip("/").split("/")
        prop_id = parts[-1] if parts else href

        text = a_tag.get_text(separator=" | ", strip=True)
        tokens = [t.strip() for t in text.split(" | ") if t.strip()]

        price = 0
        rooms = 0
        baths = 0.0
        m2 = 0.0
        location = ""
        title = ""
        description = ""
        maint_fee = None

        for i, t in enumerate(tokens):
            t_clean = t.strip()
            t_lower = t_clean.lower()

            if t_clean == "$" and i + 1 < len(tokens):
                cand = tokens[i+1].replace(",", "").strip()
                if cand.isdigit() and int(cand) > 30000 and price == 0:
                    price = int(cand)

            m_r = re.match(r"^(\d+)\s*rec[aá]maras?$", t_clean, re.IGNORECASE)
            if m_r:
                rooms = int(m_r.group(1))

            m_b = re.match(r"^(\d+[\.,]?\d*)\s*ba[nñ]os?$", t_clean, re.IGNORECASE)
            if m_b:
                baths = float(m_b.group(1).replace(",", "."))

            m_a = re.match(r"^(\d+[\.,]?\d*)\s*m[2²]$", t_clean, re.IGNORECASE)
            if m_a:
                m2 = float(m_a.group(1).replace(",", "."))

            if "mantenimiento" in t_lower:
                m_m = re.search(r"\$\s*(\d+[\.,]?\d*)", t_clean)
                if m_m:
                    maint_fee = float(m_m.group(1).replace(",", ""))

            if any(k in t_lower for k in ["provincia", "ciudad de panamá", "ciudad de panama", "san francisco", "costa del este", "bella vista", "betania", "ancón", "punta pacífica", "san miguelito", "parque lefevre"]):
                if not location and len(t_clean) < 90:
                    location = t_clean

            if len(t_clean) > 120 and not description:
                description = t_clean
                if i > 0 and len(tokens[i-1]) < 120 and not any(k in tokens[i-1].lower() for k in ["recámara", "baño", "m²", "m2", "$", "slide"]):
                    title = tokens[i-1]

        if not title:
            slug = parts[-2] if len(parts) >= 2 else prop_id
            title = slug.replace("-", " ").title()

        img = a_tag.find("img")
        photo_url = img.get("src", "") if img else ""

        return Property(
            id=prop_id,
            portal="Encuentra24",
            url=full_url,
            title=title,
            price=price,
            property_type=prop_type,
            rooms=rooms,
            baths=baths,
            area_m2=m2,
            location=location,
            description=description,
            photo_url=photo_url,
            maintenance_fee=maint_fee
        )

    def _enrich_property_details(self, prop: Property) -> None:
        try:
            resp = self.session.get(prop.url, timeout=10)
            if resp.status_code != 200:
                return

            soup = BeautifulSoup(resp.text, "html.parser")
            
            full_desc_parts = []
            for p in soup.find_all("p"):
                txt = p.get_text(strip=True)
                if len(txt) > 40 and "Encuentra24 nunca solicita" not in txt:
                    full_desc_parts.append(txt)
            
            if full_desc_parts:
                prop.description = "\n\n".join(full_desc_parts)

            if not prop.maintenance_fee:
                m = re.search(r"mantenimiento[:\s]*\$?\s*(\d+[\.,]?\d*)", prop.description, re.IGNORECASE)
                if m:
                    prop.maintenance_fee = float(m.group(1).replace(",", ""))

            m_park = re.search(r"(\d+)\s*(?:estacionamiento|parking|cochera)", prop.description, re.IGNORECASE)
            if m_park:
                prop.parking_spaces = int(m_park.group(1))

        except Exception as e:
            logger.debug(f"Could not enrich {prop.id}: {e}")
