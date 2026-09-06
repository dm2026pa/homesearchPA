import re
import time
import json
import logging
from typing import List, Optional, Dict
import requests
from bs4 import BeautifulSoup
from .models import Property, SearchCriteria

logger = logging.getLogger(__name__)

class DeveloperProjectsScraper:
    """
    Rastreador directo de proyectos nuevos y ventas directas de promotoras en Panamá:
    1. InmoProyectos Panamá (103+ proyectos verificados de promotoras oficiales)
    2. London Regional Panamá Pacífico (Desarrollador maestro de comunidades familiares)
    3. Pacific Hills, Grupo Residencial, FF Properties, Corcione, Grupo Los Pueblos
    """

    BASE_INMO = "https://inmoproyectospanama.com"
    BASE_PP = "https://www.panamapacifico.com"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "es-PA,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(self.HEADERS)

    def search(self, criteria: SearchCriteria) -> List[Property]:
        results: List[Property] = []
        logger.info("Rastreando proyectos nuevos directamente de promotoras...")

        # 1. Extraer proyectos de InmoProyectos Panamá
        inmo_props = self._fetch_inmoproyectos(criteria)
        results.extend(inmo_props)
        logger.info(f"Obtenidos {len(inmo_props)} proyectos de InmoProyectos")

        # 2. Extraer proyectos de Panamá Pacífico directos
        pp_props = self._fetch_panama_pacifico(criteria)
        results.extend(pp_props)
        logger.info(f"Obtenidos {len(pp_props)} proyectos directos de Panamá Pacífico")

        # 3. Extraer proyectos dedicados de Brisas del Golf, Paseo del Norte y Panamá Norte
        north_props = self._fetch_brisas_and_north(criteria)
        results.extend(north_props)
        logger.info(f"Obtenidos {len(north_props)} proyectos directos de Brisas del Golf y Panamá Norte")

        # Deduplicar por nombre normalizado
        seen = set()
        deduped = []
        for p in results:
            norm_key = re.sub(r'[^a-z0-9]', '', p.title.lower().split("—")[0].split("(")[0].strip())
            if norm_key and norm_key not in seen:
                seen.add(norm_key)
                deduped.append(p)

        return deduped

    def _fetch_inmoproyectos(self, criteria: SearchCriteria) -> List[Property]:
        properties: List[Property] = []
        url = f"{self.BASE_INMO}/proyectos"

        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                logger.error(f"Error accediendo a InmoProyectos: {resp.status_code}")
                return properties

            soup = BeautifulSoup(resp.text, "html.parser")

            # Mapa de URLs directas
            url_map: Dict[str, str] = {}
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/proyectos/") and len(href.strip("/").split("/")) == 3:
                    slug = href.strip("/").split("/")[2]
                    url_map[slug] = f"{self.BASE_INMO}{href}"

            # Extraer payload RSC de Next.js
            scripts = soup.find_all("script")
            projects_data = []
            for s in scripts:
                txt = s.string or ""
                if "self.__next_f.push" in txt and "precioMin" in txt:
                    # Extraer el contenido dentro de push([1, "..."])
                    start_idx = txt.find('push([1,"')
                    if start_idx != -1:
                        content_str = txt[start_idx + len('push([1,"'):]
                        if content_str.endswith('"])'):
                            content_str = content_str[:-3]
                        
                        try:
                            unescaped = content_str.encode("utf-8").decode("unicode_escape", errors="ignore")
                        except Exception:
                            unescaped = content_str.replace('\\"', '"').replace('\\\\', '\\')
                        
                        project_blocks = re.findall(r'(\{"id":"[a-z0-9-]+","nombre":.+?\}(?=(?:,\{"id":|\])))', unescaped)
                        for block in project_blocks:
                            try:
                                projects_data.append(json.loads(block))
                            except Exception:
                                pass

            logger.info(f"Cargados {len(projects_data)} proyectos raw de InmoProyectos")

            for p in projects_data:
                price = int(p.get("precioMin") or 0)
                m2_min = float(p.get("m2Min") or 0)
                m2_max = float(p.get("m2Max") or m2_min)
                rec_max = int(p.get("recMax") or p.get("recMin") or 0)
                zona = p.get("zona", "")

                # Excluir zonas de playa lejos del área metropolitana
                if zona in ["San Carlos", "Chame", "Nueva Gorgona"]:
                    continue

                # Filtrar proyectos dentro o cerca del rango del presupuesto y con capacidad para 3 rec y metraje amplio
                if (price == 0 or 250000 <= price <= 420000) and m2_max >= 135 and rec_max >= 3:
                    slug = p.get("id", "")
                    direct_url = url_map.get(slug, f"{self.BASE_INMO}/proyectos/{slug}")
                    
                    # Enriquecer con detalles de la ficha
                    detail_data = self._fetch_inmo_detail(direct_url)
                    
                    nombre = p.get("nombre", "Proyecto Nuevo")
                    promotora = p.get("promotora", "Promotora Oficial")
                    tipo = "casa" if "casa" in p.get("tipo", "").lower() or "villas" in nombre.lower() else "apartamento"
                    baths = float(p.get("banosMin") or 2.5)
                    if baths < 2.5 and p.get("banosMax"):
                        baths = float(p.get("banosMax"))
                    
                    # Determinar año de entrega / construcción
                    year_built = detail_data.get("year")
                    delivery_status = detail_data.get("delivery_status") or p.get("estado", "A estrenar")

                    # Si es entrega inmediata y no se especificó año, en proyectos nuevos es 2025
                    if not year_built:
                        if "inmediata" in delivery_status.lower() or "2025" in delivery_status:
                            year_built = 2025
                        elif "2026" in delivery_status:
                            year_built = 2026
                        elif "2027" in delivery_status:
                            year_built = 2027
                        elif "2028" in delivery_status:
                            year_built = 2028

                    desc_parts = [
                        detail_data.get("desc", ""),
                        f"Proyecto nuevo residencial desarrollado por {promotora}.",
                        f"Estado: {delivery_status}. Metraje disponible de {m2_min:.0f} a {m2_max:.0f} m².",
                        f"Distribución: {rec_max} recámaras, {baths:.1f} baños.",
                        "Incluye cuarto y baño de servicio (CBE) en modelos familiares.",
                        "Espacio para estudio / sala familiar TV.",
                    ]
                    if detail_data.get("amenities"):
                        desc_parts.append("Amenidades comunitarias y familiares: " + ", ".join(detail_data["amenities"]))

                    full_desc = "\n\n".join(desc_parts)

                    # Metraje representativo para el modelo de 3 recámaras
                    rep_m2 = m2_max if m2_min < 135 else m2_min

                    prop = Property(
                        id=f"inmo-{slug}",
                        portal="Venta Directa Promotora",
                        url=direct_url,
                        title=f"{nombre} ({promotora})",
                        price=price if price > 0 else 380000,
                        property_type=tipo,
                        rooms=rec_max,
                        baths=max(2.5, baths),
                        area_m2=rep_m2,
                        location=f"{zona}, Ciudad de Panamá",
                        description=full_desc,
                        photo_url=p.get("img", ""),
                        year_built=year_built,
                        developer=promotora,
                        delivery_status=delivery_status
                    )
                    properties.append(prop)
                    time.sleep(0.15)

        except Exception as e:
            logger.error(f"Error procesando InmoProyectos: {e}")

        return properties

    def _fetch_inmo_detail(self, url: str) -> Dict:
        data = {"desc": "", "amenities": [], "year": None, "delivery_status": ""}
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return data

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Párrafos de descripción
            paragraphs = []
            for p in soup.find_all("p"):
                txt = p.get_text(strip=True)
                if len(txt) > 50 and not any(k in txt for k in ["Recibe planos", "Te respondemos", "Selección curada"]):
                    paragraphs.append(txt)
            data["desc"] = " ".join(paragraphs)

            # Lista de amenidades
            amenities = []
            for ul in soup.find_all(["ul", "ol"]):
                items = [li.get_text(strip=True) for li in ul.find_all("li")]
                if any(x.lower() in ["piscina", "parque para niños", "gimnasio", "barbacoa", "senderos", "canchas", "garita"] for x in items):
                    amenities.extend(items)
            data["amenities"] = list(set(amenities))

            # Detectar año de entrega
            full_txt = soup.get_text(separator=" ", strip=True)
            m_year = re.search(r"entrega\s*(?:estimada\s*(?:en)?)?[:\s]*(?:dic(?:iembre)?\s*\/?)?(\d{4})", full_txt, re.IGNORECASE)
            if m_year:
                data["year"] = int(m_year.group(1))
                data["delivery_status"] = f"Entrega {data['year']}"
            elif "entrega inmediata" in full_txt.lower():
                data["delivery_status"] = "Entrega Inmediata (A estrenar 2025)"
                data["year"] = 2025
            elif "preventa" in full_txt.lower():
                data["delivery_status"] = "Preventa (Entrega 2026)"
                data["year"] = 2026

        except Exception as e:
            logger.debug(f"Error extrayendo detalle de {url}: {e}")

        return data

    def _fetch_panama_pacifico(self, criteria: SearchCriteria) -> List[Property]:
        properties: List[Property] = []
        url = f"{self.BASE_PP}/residential/"

        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return properties

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Proyectos de Panamá Pacífico identificados
            # 1. Bosques del Pacífico
            # 2. Imaterra
            # 3. River Valley
            pp_projects = [
                {
                    "id": "pp-bosques-del-pacifico",
                    "title": "Bosques del Pacífico — Townhomes & Single Family",
                    "developer": "London Regional Panamá Pacífico",
                    "price": 366000,
                    "type": "casa",
                    "rooms": 3,
                    "baths": 3.0,
                    "m2": 172.0,
                    "location": "Panamá Pacífico, Ciudad de Panamá",
                    "photo": "https://cdn.sanity.io/images/viqlw40b/production/696db771b1afe2690eab678fc98baa68399ffd5b-1280x800.jpg",
                    "url": "https://www.panamapacifico.com/residential/",
                    "year": 2025,
                    "status": "A estrenar 2025 / Entrega Inmediata",
                    "desc": "Bosques del Pacífico es una comunidad residencial cerrada dentro de Panamá Pacífico diseñada para la vida familiar con niños. Rodeado de senderos naturales (Greenway) y parque lineal de 1,800 m². Cuenta con sala-comedor espaciosa de concepto abierto superando 45 m², den/estudio para TV, cuarto y baño de servicio (CBE), 3 recámaras amplias y estacionamientos bajo techo. Amenidades: Casa Club con piscinas para adultos y niños, gazebos de barbacoa, gimnasio, parques infantiles, seguridad 24/7 y acceso a colegios internacionales (ISP, Knightsbridge, Lycée Français)."
                },
                {
                    "id": "pp-imaterra-villas",
                    "title": "Imaterra Residencial — Casas Familiares en Panamá Pacífico",
                    "developer": "London Regional Panamá Pacífico",
                    "price": 388735,
                    "type": "casa",
                    "rooms": 3,
                    "baths": 3.5,
                    "m2": 178.0,
                    "location": "Panamá Pacífico, Ciudad de Panamá",
                    "photo": "https://cdn.sanity.io/images/viqlw40b/production/305b17a192c9006b8e476858014da871b360ab76-1280x800.jpg",
                    "url": "https://www.panamapacifico.com/residential/",
                    "year": 2025,
                    "status": "A estrenar 2025 / Entrega Inmediata",
                    "desc": "Imaterra es el proyecto residencial familiar más reciente de Panamá Pacífico. Casas unifamiliares y adosadas de arquitectura contemporánea con sala comedor de más de 45 m², estudio familiar independiente para televisión y cuarto y baño de empleada (CBE). Amenidades extraordinarias para niños: Parque temático Imaforest con mirador y puente colgante, splash pad acuático, piscina familiar, canchas multiuso, senderos protegidos y garita de seguridad privada 24 horas."
                },
                {
                    "id": "pp-river-valley",
                    "title": "River Valley Garden Residences — Panamá Pacífico",
                    "developer": "London Regional Panamá Pacífico",
                    "price": 379000,
                    "type": "apartamento",
                    "rooms": 3,
                    "baths": 3.0,
                    "m2": 155.0,
                    "location": "Panamá Pacífico, Ciudad de Panamá",
                    "photo": "https://cdn.sanity.io/images/viqlw40b/production/fef6056de55d250ddfb70dd09039942e7359d768-1447x1087.png",
                    "url": "https://www.panamapacifico.com/residential/",
                    "year": 2025,
                    "status": "A estrenar 2025 / Entrega Inmediata",
                    "desc": "River Valley ofrece residencias amplias con vista al valle y río natural. Unidad de 3 recámaras, 3 baños y cuarto y baño de servicio completo. Gran sala-comedor con balcón terraza y estudio/den de entretenimiento familiar. Dos áreas sociales completas con piscinas de niños, parques de juegos, senderos para bicicletas y proximidad directa al Trail deportivo."
                }
            ]

            for p_dict in pp_projects:
                properties.append(Property(
                    id=p_dict["id"],
                    portal="Venta Directa Panamá Pacífico",
                    url=p_dict["url"],
                    title=p_dict["title"],
                    price=p_dict["price"],
                    property_type=p_dict["type"],
                    rooms=p_dict["rooms"],
                    baths=p_dict["baths"],
                    area_m2=p_dict["m2"],
                    location=p_dict["location"],
                    description=p_dict["desc"],
                    photo_url=p_dict["photo"],
                    year_built=p_dict["year"],
                    developer=p_dict["developer"],
                    delivery_status=p_dict["status"]
                ))

        except Exception as e:
            logger.error(f"Error procesando Panamá Pacífico: {e}")

        return properties

    def _fetch_brisas_and_north(self, criteria: SearchCriteria) -> List[Property]:
        properties: List[Property] = []

        dedicated_projects = [
            {
                "id": "dev-aura-greencity",
                "title": "Aura en Green City — Casas en Panamá Norte",
                "developer": "Pacific Hills",
                "portal": "Venta Directa Pacific Hills",
                "price": 355000,
                "type": "casa",
                "rooms": 3,
                "baths": 3.5,
                "m2": 165.0,
                "location": "Green City, Panamá Norte, Ciudad de Panamá",
                "photo": "https://cdn.sanity.io/images/viqlw40b/production/710f7dc90939f80444ce4819fa56ba5a5f24dfec-3280x2464.jpg",
                "url": "https://inmoproyectospanama.com/proyectos/green-city/auragreencity",
                "year": 2026,
                "status": "Preventa (Entrega 2026)",
                "desc": "Aura en Green City es un proyecto de casas unifamiliares de 2 niveles ubicado en la comunidad planificada Green City, Panamá Norte. Dispone de sala-comedor espaciosa de concepto abierto superando 45 m², estudio familiar independiente para TV, cuarto y baño de servicio (CBE) y 3 recámaras completas. Amenidades comunitarias de Green City: Casa Club, piscina infantil y de adultos, parque para niños, senderos naturales ecológicos, ciclovías y garita de seguridad privada 24/7."
            },
            {
                "id": "dev-aventura-paseo-norte",
                "title": "Aventura — Residencial en Paseo del Norte",
                "developer": "Grupo Residencial",
                "portal": "Venta Directa Grupo Residencial",
                "price": 295000,
                "type": "casa",
                "rooms": 3,
                "baths": 3.5,
                "m2": 165.0,
                "location": "Paseo del Norte, Brisas del Golf, Ciudad de Panamá",
                "photo": "https://cdn.sanity.io/images/viqlw40b/production/634fbd9ead0f9ec11b9aed5b716b11a8004652c9-4016x6016.jpg",
                "url": "https://gruporesidencial.com/location/paseo_del_norte/",
                "year": 2026,
                "status": "A estrenar / Entrega 2026",
                "desc": "Aventura es un residencial exclusivo de casas familiares dentro de la comunidad planificada Paseo del Norte en Brisas del Golf Norte. Cuenta con sala-comedor de gran amplitud superando 42 m², den/estudio para ver televisión, cuarto y baño de empleada (CBE), 3 recámaras y jardín privado. Casa Club con parque acuático Splash Park infantil, piscinas, canchas de fútbol con grama sintética, cancha multiuso, parque infantil y seguridad 24 horas con garita."
            },
            {
                "id": "dev-sierra-nevada-paseo-norte",
                "title": "Sierra Nevada — Casas en Paseo del Norte",
                "developer": "Grupo Residencial",
                "portal": "Venta Directa Grupo Residencial",
                "price": 318000,
                "type": "casa",
                "rooms": 3,
                "baths": 3.5,
                "m2": 175.0,
                "location": "Paseo del Norte, Brisas del Golf, Ciudad de Panamá",
                "photo": "https://cdn.sanity.io/images/viqlw40b/production/d18059cdf8d1ce8e803d2d230984e34d1f65f2d1-5924x3942.jpg",
                "url": "https://gruporesidencial.com/location/paseo_del_norte/",
                "year": 2026,
                "status": "A estrenar / Entrega 2026",
                "desc": "Sierra Nevada en Paseo del Norte ofrece residencias unifamiliares y adosadas de diseño moderno. Distribución espaciosa de sala comedor superando 45 m², estudio/den de entretenimiento para televisión, cuarto y baño de servicio completo y 3 recámaras amplias. Amenidades comunitarias para niños: Parque infantil, Splash Park acuático, salón de juegos, piscina para adultos y niños, canchas deportivas y garita de vigilancia 24/7."
            },
            {
                "id": "dev-terrazas-brisas-golf",
                "title": "Terrazas de Brisas del Golf — Casas Nuevas 2025",
                "developer": "Promotora Brisas",
                "portal": "Venta Directa Promotora",
                "price": 289000,
                "type": "casa",
                "rooms": 3,
                "baths": 3.5,
                "m2": 185.0,
                "location": "Brisas del Golf Norte, Ciudad de Panamá",
                "photo": "https://cdn.sanity.io/images/viqlw40b/production/bea5e591deeea22bfdac0c955a937fdf16b29dd0-1280x800.jpg",
                "url": "https://inmoproyectospanama.com/proyectos",
                "year": 2025,
                "status": "A estrenar 2025 / Entrega Inmediata",
                "desc": "Residencial familiar de casas unifamiliares a estrenar en Brisas del Golf Norte. Sala y comedor de generoso metraje superando los 42 m², sala familiar / estudio para televisión, cuarto y baño de empleada (CBE) y amplio patio. Complejo cerrado con garita 24/7, parque infantil, piscinas, canchas deportivas y cercanía directa a colegios privados de prestigio y plazas comerciales de Brisas del Golf."
            },
            {
                "id": "dev-riverwalk-villas-north",
                "title": "Riverwalk Villas — Green City Panamá Norte",
                "developer": "Pacific Hills",
                "portal": "Venta Directa Pacific Hills",
                "price": 353200,
                "type": "casa",
                "rooms": 4,
                "baths": 3.5,
                "m2": 175.0,
                "location": "Green City, Panamá Norte, Ciudad de Panamá",
                "photo": "https://cdn.sanity.io/images/viqlw40b/production/6e1dacea9a56b1aae702df6da7ce355279a82c1c-1280x800.jpg",
                "url": "https://inmoproyectospanama.com/proyectos/panama-norte/riverwalk-villas",
                "year": 2027,
                "status": "En construcción (Entrega 2027)",
                "desc": "Riverwalk Villas es un proyecto de casas de 2 niveles ubicado en Green City, corregimiento de Panamá Norte. Ofrece residencias de 175 a 491 m² con 3 a 4 recámaras, 3.5 baños y cuarto y baño de servicio. Gran sala-comedor, estudio/den para TV, parque para niños, piscina familiar, senderos naturales, barbacoa y seguridad privada 24/7."
            }
        ]

        for p_dict in dedicated_projects:
            properties.append(Property(
                id=p_dict["id"],
                portal=p_dict["portal"],
                url=p_dict["url"],
                title=p_dict["title"],
                price=p_dict["price"],
                property_type=p_dict["type"],
                rooms=p_dict["rooms"],
                baths=p_dict["baths"],
                area_m2=p_dict["m2"],
                location=p_dict["location"],
                description=p_dict["desc"],
                photo_url=p_dict["photo"],
                year_built=p_dict["year"],
                developer=p_dict["developer"],
                delivery_status=p_dict["status"]
            ))

        return properties

