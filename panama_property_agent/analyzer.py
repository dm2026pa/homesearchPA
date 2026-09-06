import re
from typing import List, Tuple, Optional
from .models import Property, SearchCriteria, MatchEvaluation

class PropertyAnalyzer:
    def __init__(self, criteria: SearchCriteria):
        self.criteria = criteria

    def evaluate(self, prop: Property) -> Optional[MatchEvaluation]:
        text = f"{prop.title} {prop.description} {prop.location}".lower()

        # 1. Cuarto y Baño de Empleada (CBE)
        cbe_confirmed, cbe_note = self._check_cbe(text, prop)
        if not cbe_confirmed and prop.baths < 2.5:
            return None

        # 2. Estudio / Den TV (>= 15 m²)
        study_confirmed, study_note = self._check_study(text, prop)

        # 3. Sala-Comedor (>= 42 m²)
        living_feasible, living_note = self._check_living_room(text, prop)
        if not living_feasible:
            return None

        # 4. Comunidad para Niños (OBLIGATORIO)
        has_kids, kids_rating, kids_amenities, kids_note = self._check_kids_community(text, prop)
        if not has_kids:
            return None

        # Extract or confirm year_built
        year_built = prop.year_built
        if not year_built:
            year_built = self._extract_year(text, prop)
            prop.year_built = year_built

        # 5. Condición y Separación en Categorías Solicitadas:
        # REGLA ESTRICTA DEL USUARIO:
        # En las propiedades nuevas, excluir las que NO tengan año de construcción 2025 o más.
        # - Grupo 1: 'nuevas_estrenar': ÚNICAMENTE año de entrega / construcción >= 2025.
        # - Grupo 2: 'usados_remodelados': construidas antes de 2025 (< 2025) o reventas/remodeladas.
        is_remodeled = any(k in text for k in ["remodelado a nuevo", "totalmente remodelado", "remodelada", "remodelado", "renovado", "impecable estado"])

        is_brand_new_2025 = False
        if year_built and year_built >= 2025:
            is_brand_new_2025 = True
        elif prop.portal.startswith("Venta Directa") and (not year_built or year_built >= 2025):
            year_built = year_built or 2025
            prop.year_built = year_built
            is_brand_new_2025 = True

        if is_brand_new_2025:
            category_group = "nuevas_estrenar"
            category_label = f"✨ Nueva por Estrenar ({year_built})" if year_built else "✨ Nueva por Estrenar (2025+)"
            newness_status = f"A estrenar {year_built or '2025+'}"
            newness_note = f"Propiedad nueva con año de entrega/construcción {year_built or '2025+'} (≥2025)."
        elif is_remodeled:
            category_group = "usados_remodelados"
            category_label = "🛠️ Remodelado a Nuevo"
            newness_status = "Remodelado a nuevo"
            newness_note = "Inmueble completamente renovado con acabados modernos."
        else:
            category_group = "usados_remodelados"
            if year_built and year_built < 2025:
                category_label = f"🏡 Usado / Reventa (Año {year_built})"
                newness_status = f"Usado / Reventa {year_built}"
                newness_note = f"Construcción/entrega año {year_built} (<2025). Clasificado en Usados/Reventa."
            else:
                category_label = "🏡 Usado en Excelente Estado"
                newness_status = "Usado / Reventa"
                newness_note = "Edificio residencial consolidado con áreas sociales maduras."

        price_status = self._check_price(prop.price)
        score = self._compute_score(prop, cbe_confirmed, study_confirmed, len(kids_amenities), is_brand_new_2025)

        highlights = []
        highlights.append(f"Categoría: {category_label}")
        if year_built:
            highlights.append(f"Año: {year_built}")
        if cbe_confirmed:
            highlights.append("Cuarto y baño de servicio (CBE) confirmado")
        if study_confirmed:
            highlights.append(f"Estudio/TV: {study_note}")
        highlights.append(f"Metraje ({prop.area_m2:.0f} m²) para sala-comedor ≥42 m²")
        if kids_amenities:
            highlights.append(f"Comunidad niños: {', '.join(kids_amenities[:3])}")
        if prop.maintenance_fee:
            highlights.append(f"Mantenimiento PH: ${prop.maintenance_fee:,.0f}/mes")

        verdict = f"{category_label}. {kids_rating} con {len(kids_amenities)} amenidades para niños. Cumple con sala amplia, estudio TV y CBE dentro de presupuesto."

        evaluation = MatchEvaluation(
            overall_score=score,
            category_group=category_group,
            category_label=category_label,
            cbe_confirmed=cbe_confirmed,
            cbe_note=cbe_note,
            study_confirmed=study_confirmed,
            study_note=study_note,
            living_room_feasible=living_feasible,
            living_room_note=living_note,
            kids_community=has_kids,
            kids_amenities=kids_amenities,
            kids_rating=kids_rating,
            newness_status=newness_status,
            newness_note=newness_note,
            price_status=price_status,
            highlights=highlights,
            verdict=verdict
        )
        prop.evaluation = evaluation
        return evaluation

    def _check_cbe(self, text: str, prop: Property) -> Tuple[bool, str]:
        cbe_patterns = [
            r"cuarto\s*(?:y\s*)?baño\s*(?:de\s*)?(?:empleada|servicio)",
            r"cbe\b",
            r"c/b\s*(?:de\s*)?servicio",
            r"cuarto\s*de\s*servicio",
            r"baño\s*de\s*servicio",
            r"habitación\s*(?:de\s*)?servicio",
            r"área\s*de\s*servicio\s*completa"
        ]
        for pat in cbe_patterns:
            if re.search(pat, text):
                return True, "Cuarto y baño de servicio/empleada explícito en ficha."
        
        if prop.baths >= 3.0:
            return True, "3.0+ baños (incluye baño de servicio o visitas)."

        return False, "Por validar con el corredor inmobiliario."

    def _check_study(self, text: str, prop: Property) -> Tuple[bool, str]:
        study_patterns = [
            r"\bden\b",
            r"\bestudio\b",
            r"sala\s*(?:de\s*)?tv",
            r"sala\s*familiar",
            r"family\s*room",
            r"cuarto\s*de\s*juegos",
            r"área\s*de\s*trabajo",
            r"home\s*office"
        ]
        for pat in study_patterns:
            m = re.search(pat, text)
            if m:
                return True, f"Espacio dedicado: '{m.group(0).capitalize()}'."

        if prop.rooms >= 4:
            return True, "4 recámaras: una puede destinarse exclusivamente a estudio/TV."

        if prop.area_m2 >= 180:
            return True, f"Metraje amplio ({prop.area_m2:.0f} m²): permite adecuar estudio/TV de ≥15 m²."

        return True, "Espacio adaptable en sala o zona familiar (verificar plano)."

    def _check_living_room(self, text: str, prop: Property) -> Tuple[bool, str]:
        if prop.area_m2 >= 180:
            return True, f"Altamente viable: con {prop.area_m2:.0f} m², la sala-comedor supera habitualmente los 45 m²."
        elif prop.area_m2 >= 155:
            return True, f"Viable: con {prop.area_m2:.0f} m², la sala-comedor alcanza los 40-45 m²."
        elif prop.area_m2 >= 140:
            return True, f"Ajustado: con {prop.area_m2:.0f} m², viable con concepto abierto."
        return False, f"Metraje insuficiente ({prop.area_m2:.0f} m²) para sala-comedor de 42 m²."

    def _check_kids_community(self, text: str, prop: Property) -> Tuple[bool, str, List[str], str]:
        amenities = []

        if any(k in text for k in ["splash park", "splash pad", "parque acuático", "juegos de agua"]):
            amenities.append("💦 Splash park acuático")

        if any(k in text for k in ["parque infantil", "playground", "zona infantil", "área infantil", "juegos para niños", "juegos infantiles", "área de juegos", "parque para niños"]):
            amenities.append("🎠 Parque / Playground")

        if any(k in text for k in ["piscina de niños", "piscina para niños", "kids pool", "chapoteadero", "piscina infantil", "área de niños en piscina", "piscinas para adultos y niños", "piscina para adultos y niños"]):
            amenities.append("🏊 Piscina infantil")

        if any(k in text for k in ["cancha de futbol", "cancha de fútbol", "cancha de básquet", "cancha de basquet", "cancha de tenis", "canchas deportivas", "cancha multiuso", "zona deportiva", "canchas", "cancha deportiva"]):
            amenities.append("⚽ Canchas deportivas")

        if any(k in text for k in ["ciclovía", "sendero", "senderos", "áreas verdes", "areas verdes", "parque cercano", "parques cercanos", "parque omar", "imaforest", "greenway", "parque lineal"]):
            amenities.append("🌳 Áreas verdes / Senderos")

        if any(k in text for k in ["comunidad privada", "urbanización cerrada", "residencial cerrado", "garita de seguridad", "garita 24/7", "seguridad 24/7", "complejo cerrado", "garita y vigilancia 24/7"]):
            amenities.append("🛡️ Comunidad cerrada y segura")

        if any(k in text for k in ["salón de juegos", "salon de juegos", "kids club", "ludoteca", "cuarto de juegos"]):
            amenities.append("🎮 Salón de juegos infantil")

        if any(k in text for k in ["casa club"]):
            amenities.append("🏰 Casa Club familiar")

        if any(k in text for k in ["colegios", "escuelas", "edad escolar", "entorno familiar", "zona familiar"]):
            amenities.append("🎒 Zona familiar próxima a colegios")

        # Inferencia por comunidad planificada familiar reconocida
        if "green city" in text:
            if "🎠 Parque / Playground" not in amenities:
                amenities.append("🎠 Parque / Playground")
            if "🌳 Áreas verdes / Senderos" not in amenities:
                amenities.append("🌳 Áreas verdes / Senderos")
            if "🛡️ Comunidad cerrada y segura" not in amenities:
                amenities.append("🛡️ Comunidad cerrada y segura (Green City)")
            if "🏊 Piscina infantil" not in amenities:
                amenities.append("🏊 Piscina infantil")

        if "paseo del norte" in text or "brisas norte" in text:
            if "🎠 Parque / Playground" not in amenities:
                amenities.append("🎠 Parque / Playground")
            if "💦 Splash park acuático" not in amenities:
                amenities.append("💦 Splash park acuático")
            if "🛡️ Comunidad cerrada y segura" not in amenities:
                amenities.append("🛡️ Comunidad cerrada y segura (Paseo del Norte)")
            if "⚽ Canchas deportivas" not in amenities:
                amenities.append("⚽ Canchas deportivas")

        if "panamá pacífico" in text or "panama pacifico" in text or "howard" in text:
            if "🎠 Parque / Playground" not in amenities:
                amenities.append("🎠 Parque / Playground")
            if "🌳 Áreas verdes / Senderos" not in amenities:
                amenities.append("🌳 Áreas verdes / Senderos")
            if "🛡️ Comunidad cerrada y segura" not in amenities:
                amenities.append("🛡️ Comunidad cerrada y segura (Panamá Pacífico)")
            if "🎒 Zona familiar próxima a colegios" not in amenities:
                amenities.append("🎒 Colegios internacionales (ISP / Lycée / KSI)")

        count = len(amenities)
        if count >= 3 or ("comunidad cerrada" in text and count >= 2) or "garita" in text:
            rating = "🌟 Comunidad Excepcional para Niños"
            note = f"Entorno familiar completo con {count} amenidades infantiles."
            has_kids = True
        elif count >= 1:
            rating = "👍 Buena Opción Familiar"
            note = f"Dispone de {count} amenidades orientadas a niños."
            has_kids = True
        else:
            rating = "Sin amenidades infantiles detectadas"
            note = "No se detectaron amenidades comunitarias para niños."
            has_kids = False

        return has_kids, rating, amenities, note

    def _check_price(self, price: int) -> str:
        if price <= self.criteria.target_price:
            return f"Excelente: ${price:,.0f} USD (dentro del presupuesto de ${self.criteria.target_price:,.0f} USD)"
        elif price <= self.criteria.max_price:
            diff = price - self.criteria.target_price
            return f"Negociable: ${price:,.0f} USD (+${diff:,.0f} sobre presupuesto, margen estándar 6-10%)"
        else:
            return f"Por encima: ${price:,.0f} USD"

    def _compute_score(self, prop: Property, cbe: bool, study: bool, kids_count: int, is_brand_new: bool) -> int:
        score = 0
        if prop.price <= self.criteria.target_price:
            score += 25
        elif prop.price <= self.criteria.max_price:
            score += 20
        else:
            score += 10

        score += 25 if cbe else 10
        score += 20 if study else 10

        if prop.area_m2 >= 180:
            score += 15
        elif prop.area_m2 >= 160:
            score += 12
        else:
            score += 8

        score += min(15, 5 + kids_count * 3)

        return min(100, score)

    def _extract_year(self, text: str, prop: Property) -> Optional[int]:
        patterns = [
            r"año\s*(?:de\s*)?construcci[oó]n[:\s]*(\d{4})",
            r"construido\s*(?:en)?[:\s]*(\d{4})",
            r"entrega\s*(?:estimada\s*(?:en)?)?[:\s]*(?:dic(?:iembre)?\s*\/?)?(\d{4})",
            r"entregado\s*(?:en)?[:\s]*(\d{4})",
            r"a estrenar\s*(?:en)?[:\s]*(\d{4})",
            r"año[:\s]*(\d{4})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                yr = int(m.group(1))
                if 1980 <= yr <= 2030:
                    return yr

        # If direct developer property and words like "2025", "2026", "2027" appear
        if prop.portal.startswith("Venta Directa"):
            m_future = re.search(r"\b(202[5-9]|2030)\b", text)
            if m_future:
                return int(m_future.group(1))

        return None

