import json
import os
import shutil
from typing import List
from .models import Property, SearchCriteria

class PropertyReporter:
    def __init__(self, criteria: SearchCriteria):
        self.criteria = criteria

    def export_json(self, properties: List[Property], file_path: str) -> None:
        data = [p.to_dict() for p in properties]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_markdown(self, properties: List[Property], file_path: str) -> None:
        nuevas = [p for p in properties if p.evaluation and p.evaluation.category_group == "nuevas_estrenar"]
        usados = [p for p in properties if p.evaluation and p.evaluation.category_group == "usados_remodelados"]

        lines = [
            "# Catálogo Inmobiliario Filtrado — Ciudad de Panamá",
            f"**Presupuesto:** ${self.criteria.target_price:,.0f} USD (Rango: ${self.criteria.min_price:,.0f} - ${self.criteria.max_price:,.0f} USD)",
            "**Criterios Estrictos Obligatorios:**",
            "  1. ✅ Mínimo 3 Recámaras + Cuarto y Baño de Empleada (CBE)",
            "  2. ✅ Mínimo 2 Baños familiares completos + Baño de servicio",
            "  3. ✅ Sala-Comedor de al menos 42 m² (metraje total amplio)",
            "  4. ✅ Estudio / Den para TV de al menos 15 m²",
            "  5. ✅ Opciones de comunidad para niños (playgrounds, canchas, piscinas infantiles, áreas verdes, seguridad)",
            f"\n**Total Propiedades Calificadas:** {len(properties)} (Nuevas por Estrenar: {len(nuevas)} | Usados o Remodelados: {len(usados)})\n",
            "=" * 78,
            ""
        ]

        # SECCIÓN 1: NUEVAS POR ESTRENAR (AÑO >= 2025)
        lines.append(f"## 🌟 SECCIÓN 1: NUEVAS POR ESTRENAR — AÑO 2025 O MÁS ({len(nuevas)} propiedades)")
        lines.append("Proyectos nuevos y ventas directas de promotoras con año de entrega o construcción 2025 en adelante, con comunidades para niños y amplios espacios.\n")
        
        if not nuevas:
            lines.append("_No se detectaron unidades con año 2025+ en este lote exacto con los filtros estrictos._\n")
        else:
            for i, p in enumerate(nuevas, 1):
                self._append_property_md(lines, i, p)

        lines.append("\n" + "=" * 78 + "\n")

        # SECCIÓN 2: USADOS O REMODELADOS (AÑO < 2025)
        lines.append(f"## 🔄 SECCIÓN 2: USADOS O REMODELADOS — AÑO ANTERIOR A 2025 ({len(usados)} propiedades)")
        lines.append("Inmuebles entregados antes de 2025, reventas consolidadas o remodelados a nuevo con gran metraje y áreas infantiles.\n")

        for i, p in enumerate(usados, 1):
            self._append_property_md(lines, i, p)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _append_property_md(self, lines: List[str], index: int, p: Property) -> None:
        ev = p.evaluation
        score = ev.overall_score if ev else 0
        year_str = f" | **Año:** {p.year_built}" if p.year_built else ""
        dev_str = f" | **Promotora:** {p.developer}" if p.developer else ""
        lines.append(f"### {index}. {p.title}")
        lines.append(f"- **Categoría:** {ev.category_label if ev else 'Inmueble'}{year_str}{dev_str}")
        lines.append(f"- **Origen:** {p.portal}")
        lines.append(f"- **Precio:** ${p.price:,.0f} USD (~${p.price_per_m2:,.0f}/m²)")
        lines.append(f"- **Ubicación:** {p.location or 'Ciudad de Panamá'}")
        lines.append(f"- **Metraje:** {p.area_m2:.0f} m² | **Distribución:** {p.rooms} Recámaras, {p.baths:.1f} Baños")
        if p.delivery_status:
            lines.append(f"- **Estado de Entrega:** {p.delivery_status}")
        if p.maintenance_fee:
            lines.append(f"- **Mantenimiento PH:** ${p.maintenance_fee:,.0f}/mes")
        lines.append(f"- **Score de Afinidad:** **{score}%**")
        
        if ev:
            lines.append(f"- **Cuarto/Baño de Empleada (CBE):** {'✅ SÍ' if ev.cbe_confirmed else '⚠️ Por validar'}")
            lines.append(f"- **Estudio / Den TV (≥15 m²):** {'✅ SÍ' if ev.study_confirmed else '⚠️ Adaptable'} ({ev.study_note})")
            lines.append(f"- **Sala-Comedor (≥42 m²):** ✅ {ev.living_room_note}")
            lines.append(f"- **Comunidad para Niños:** 🧒 **{ev.kids_rating}**")
            if ev.kids_amenities:
                lines.append(f"  - Amenidades infantiles: {', '.join(ev.kids_amenities)}")
            lines.append(f"- **Veredicto:** {ev.verdict}")
        
        lines.append(f"- **Enlace Directo:** [Ver publicación o proyecto ({p.portal})]({p.url})")
        lines.append("")

    def export_web_portal(self, properties: List[Property], portal_dir: str) -> None:
        os.makedirs(portal_dir, exist_ok=True)
        json_path = os.path.join(portal_dir, "propiedades.json")
        html_path = os.path.join(portal_dir, "index.html")

        # Export properties JSON into portal dir
        self.export_json(properties, json_path)

        props_json_str = json.dumps([p.to_dict() for p in properties], ensure_ascii=False)

        nuevas_count = sum(1 for p in properties if p.evaluation and p.evaluation.category_group == "nuevas_estrenar")
        usados_count = sum(1 for p in properties if p.evaluation and p.evaluation.category_group == "usados_remodelados")
        avg_price = int(sum(p.price for p in properties)/len(properties)) if properties else 0
        avg_m2 = int(sum(p.area_m2 for p in properties)/len(properties)) if properties else 0

        template_path = os.path.join(os.path.dirname(__file__), "portal_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        html_content = (
            template_content
            .replace("__PROPERTIES_JSON__", props_json_str)
            .replace("__TARGET_PRICE__", f"{self.criteria.target_price:.0f}")
            .replace("__TARGET_PRICE_FORMATTED__", f"${self.criteria.target_price:,.0f}")
            .replace("__TOTAL_COUNT__", str(len(properties)))
            .replace("__NUEVAS_COUNT__", str(nuevas_count))
            .replace("__USADOS_COUNT__", str(usados_count))
            .replace("__AVG_PRICE__", f"${avg_price:,.0f}")
            .replace("__AVG_M2__", str(avg_m2))
        )

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Mirror to root propiedades_encontradas.html and index.html for direct GitHub Pages hosting
        shutil.copyfile(html_path, "propiedades_encontradas.html")
        shutil.copyfile(html_path, "index.html")
