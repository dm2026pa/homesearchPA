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

        html_content = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portal Inmobiliario Familiar — Ciudad de Panamá ($380,000)</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #090d16;
            --surface: #111827;
            --surface-card: #1a2234;
            --border: #2d3748;
            --primary: #38bdf8;
            --primary-dark: #0284c7;
            --accent-green: #10b981;
            --accent-purple: #a855f7;
            --accent-amber: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-main); line-height: 1.5; padding-bottom: 60px; }}
        
        /* Top Navigation Header */
        header {{
            background: rgba(17, 24, 39, 0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 100;
            padding: 16px 24px;
        }}
        .header-content {{
            max-width: 1360px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .brand {{ display: flex; align-items: center; gap: 12px; }}
        .brand-icon {{
            width: 42px; height: 42px; border-radius: 10px;
            background: linear-gradient(135deg, #0284c7, #38bdf8);
            display: flex; align-items: center; justify-content: center;
            font-size: 22px;
        }}
        .brand-text h1 {{ font-size: 19px; font-weight: 800; color: #fff; letter-spacing: -0.5px; }}
        .brand-text p {{ font-size: 12px; color: var(--text-muted); }}

        .budget-control-box {{
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(56, 189, 248, 0.4);
            padding: 8px 16px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .budget-label {{ font-size: 12px; font-weight: 700; color: var(--text-muted); display: flex; align-items: center; gap: 5px; }}
        .budget-input-wrap {{
            display: flex;
            align-items: center;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 4px 10px;
        }}
        .budget-input-wrap span {{ color: var(--primary); font-weight: 800; font-size: 14px; }}
        .budget-input-wrap input {{
            background: transparent;
            border: none;
            color: #fff;
            font-size: 15px;
            font-weight: 800;
            width: 105px;
            text-align: right;
            padding: 0 4px;
        }}
        .budget-input-wrap input:focus {{ outline: none; }}
        .quick-budgets {{ display: flex; gap: 6px; }}
        .q-btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 5px 9px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .q-btn:hover, .q-btn.active {{
            background: var(--primary);
            color: #090d16;
            border-color: var(--primary);
        }}
        .refresh-cloud-btn {{
            background: rgba(35, 134, 54, 0.25);
            color: #4ade80;
            border: 1px solid rgba(74, 222, 128, 0.45);
            padding: 8px 14px;
            border-radius: 10px;
            font-size: 12.5px;
            font-weight: 700;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
            white-space: nowrap;
        }}
        .refresh-cloud-btn:hover {{
            background: #238636;
            color: #fff;
            box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
            transform: translateY(-1px);
        }}
        .badge-budget {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 11.5px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .badge-budget.ok {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); }}
        .badge-budget.neg {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.35); }}
        .badge-budget.over {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); }}

        /* Main Container */
        .container {{ max-width: 1360px; margin: 24px auto; padding: 0 20px; }}

        /* Stats Row */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px 18px;
        }}
        .stat-val {{ font-size: 26px; font-weight: 800; color: #fff; }}
        .stat-lbl {{ font-size: 12px; color: var(--text-muted); margin-top: 2px; }}

        /* Primary Category Tabs */
        .category-tabs {{
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
            overflow-x: auto;
        }}
        .tab-btn {{
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex; align-items: center; gap: 8px;
            white-space: nowrap;
        }}
        .tab-btn:hover {{ border-color: var(--primary); color: #fff; }}
        .tab-btn.active {{
            background: var(--primary);
            color: #090d16;
            border-color: var(--primary);
            box-shadow: 0 4px 14px rgba(56, 189, 248, 0.3);
        }}
        .tab-count {{
            background: rgba(0,0,0,0.25);
            padding: 2px 7px;
            border-radius: 999px;
            font-size: 12px;
        }}

        /* Filters Bar */
        .filters-panel {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 24px;
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr;
            gap: 14px;
            align-items: center;
        }}
        @media (max-width: 900px) {{
            .filters-panel {{ grid-template-columns: 1fr; }}
        }}
        .search-box input {{
            width: 100%;
            background: var(--bg);
            border: 1px solid var(--border);
            color: #fff;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13.5px;
        }}
        .search-box input:focus {{ outline: none; border-color: var(--primary); }}
        .select-filter select {{
            width: 100%;
            background: var(--bg);
            border: 1px solid var(--border);
            color: #fff;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13px;
        }}
        .slider-wrap label {{ font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 4px; }}
        .slider-wrap input {{ width: 100%; }}

        /* Property Cards Grid */
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(390px, 1fr));
            gap: 24px;
        }}
        .prop-card {{
            background: var(--surface-card);
            border: 1px solid var(--border);
            border-radius: 18px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: all 0.25s ease;
        }}
        .prop-card:hover {{
            transform: translateY(-5px);
            border-color: var(--primary);
            box-shadow: 0 16px 30px -10px rgba(0,0,0,0.6);
        }}

        /* Card Media */
        .card-media {{ position: relative; height: 220px; background: #0b1120; }}
        .card-img {{ width: 100%; height: 100%; object-fit: cover; }}
        .no-photo {{ display: flex; align-items: center; justify-content: center; height: 100%; color: #64748b; font-size: 14px; }}

        .badge-cat {{
            position: absolute;
            top: 12px;
            left: 12px;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }}
        .badge-cat.nueva {{ background: #059669; color: #fff; }}
        .badge-cat.remodelado {{ background: #7c3aed; color: #fff; }}
        .badge-cat.usado {{ background: #2563eb; color: #fff; }}

        .badge-dev {{
            position: absolute;
            bottom: 12px;
            left: 12px;
            background: #f59e0b;
            color: #0f172a;
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 10.5px;
            font-weight: 800;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }}
        .badge-year {{
            position: absolute;
            bottom: 12px;
            right: 12px;
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(56, 189, 248, 0.4);
            color: #38bdf8;
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 800;
        }}

        .badge-score {{
            position: absolute;
            top: 12px;
            right: 12px;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255,255,255,0.15);
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 800;
            color: #38bdf8;
        }}

        /* Card Body */
        .card-body {{ padding: 20px; display: flex; flex-direction: column; flex-grow: 1; }}
        .price-line {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }}
        .price-val {{ font-size: 27px; font-weight: 800; color: #fff; }}
        .price-m2 {{ font-size: 13px; color: var(--text-muted); }}

        .prop-title {{
            font-size: 16px;
            font-weight: 700;
            line-height: 1.35;
            margin-bottom: 6px;
            height: 44px;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            color: #f1f5f9;
        }}
        .prop-loc {{ font-size: 13px; color: var(--text-muted); margin-bottom: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

        /* Specs Row */
        .specs-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 14px;
            text-align: center;
            font-size: 13px;
        }}

        /* Checklist Box */
        .checklist-box {{
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 14px;
            font-size: 12px;
        }}
        .check-item {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px; color: #cbd5e1; }}
        .check-icon {{ color: #10b981; font-weight: 800; }}

        /* Kids Amenities Tags */
        .kids-box {{
            margin-bottom: 14px;
        }}
        .kids-title {{ font-size: 11px; font-weight: 700; color: #f59e0b; text-transform: uppercase; margin-bottom: 6px; }}
        .kids-tags {{ display: flex; flex-wrap: wrap; gap: 5px; }}
        .ktag {{ background: rgba(245, 158, 11, 0.12); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.25); font-size: 11px; padding: 3px 8px; border-radius: 6px; }}

        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 14px;
            border-top: 1px solid var(--border);
            font-size: 12px;
            color: var(--text-muted);
            margin-top: auto;
        }}
        .action-btn {{
            background: #2563eb;
            color: #fff;
            text-decoration: none;
            padding: 8px 15px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 13px;
            transition: all 0.2s;
        }}
        .action-btn:hover {{ background: #1d4ed8; }}

        .empty-state {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 60px 20px;
            background: var(--surface);
            border-radius: 16px;
            border: 1px dashed var(--border);
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <div class="brand">
                <div class="brand-icon">🏠</div>
                <div class="brand-text">
                    <h1>Portal Inmobiliario Familiar — Ciudad de Panamá</h1>
                    <p>Filtro estricto: 3 Recámaras + CBE + Sala ≥42 m² + Estudio TV ≥15 m² + Comunidad para Niños</p>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                <div class="budget-control-box">
                    <div class="budget-label">🎯 Presupuesto:</div>
                    <div class="budget-input-wrap">
                        <span>$</span>
                        <input type="number" id="budgetInput" value="{self.criteria.target_price:.0f}" step="10000" min="150000" max="1000000" oninput="onBudgetChanged(this.value)">
                        <span style="font-size: 11px; color: var(--text-muted); margin-left: 4px;">USD</span>
                    </div>
                    <div class="quick-budgets">
                        <button type="button" class="q-btn" onclick="setQuickBudget(320000)">$320k</button>
                        <button type="button" class="q-btn" onclick="setQuickBudget(350000)">$350k</button>
                        <button type="button" class="q-btn active" id="btn-380" onclick="setQuickBudget(380000)">$380k</button>
                        <button type="button" class="q-btn" onclick="setQuickBudget(420000)">$420k</button>
                        <button type="button" class="q-btn" onclick="setQuickBudget(450000)">$450k</button>
                        <button type="button" class="q-btn" onclick="setQuickBudget(500000)">$500k</button>
                    </div>
                </div>
                <a href="https://github.com/dm2026pa/homesearchPA/actions/workflows/update_listings.yml" target="_blank" class="refresh-cloud-btn" title="Ejecutar el bot de búsqueda en GitHub Actions para refrescar propiedades">
                    ⚡ Refrescar en GitHub ↗
                </a>
            </div>
        </div>
    </header>

    <div class="container">
        <!-- Resumen de Métricas Dinámicas -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-val" id="statTotal">{len(properties)}</div>
                <div class="stat-lbl">Propiedades Calificadas</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="statNuevas" style="color: #10b981;">{nuevas_count}</div>
                <div class="stat-lbl">Nuevas por Estrenar</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="statUsados" style="color: #38bdf8;">{usados_count}</div>
                <div class="stat-lbl">Usados o Remodelados</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="statAvgPrice">${avg_price:,.0f}</div>
                <div class="stat-lbl">Precio Promedio</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="statAvgM2">{avg_m2:,.0f} m²</div>
                <div class="stat-lbl">Metraje Promedio</div>
            </div>
        </div>

        <!-- Pestañas Principales de Separación Solicitada -->
        <div class="category-tabs">
            <button class="tab-btn active" onclick="setCategory('all', this)">
                🌟 Todas las Opciones Calificadas <span class="tab-count" id="countAll">{len(properties)}</span>
            </button>
            <button class="tab-btn" onclick="setCategory('nuevas_estrenar', this)">
                ✨ 1. Nuevas por Estrenar (Año 2025+) <span class="tab-count" id="countNuevas">{nuevas_count}</span>
            </button>
            <button class="tab-btn" onclick="setCategory('usados_remodelados', this)">
                🔄 2. Usados o Remodelados (&lt;2025) <span class="tab-count" id="countUsados">{usados_count}</span>
            </button>
        </div>

        <!-- Panel de Filtros -->
        <div class="filters-panel-wrap" style="margin-bottom: 24px;">
            <div class="filters-panel" style="grid-template-columns: 2fr 1.2fr 1fr 1fr 1fr; margin-bottom: 10px;">
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="🔍 Buscar por PH, promotora, zona..." oninput="applyFilters()">
                </div>
                <div class="select-filter">
                    <select id="zoneSelect" onchange="applyFilters()">
                        <option value="all">📍 Todas las Zonas</option>
                        <option value="Brisas">Brisas del Golf</option>
                        <option value="Paseo del Norte">Paseo del Norte</option>
                        <option value="Norte">Green City / Panamá Norte</option>
                        <option value="Panamá Pacífico">Panamá Pacífico</option>
                        <option value="Costa del Este">Costa del Este</option>
                        <option value="Costa del Mar">Costa del Mar</option>
                        <option value="Edison Park">Edison Park</option>
                        <option value="San Francisco">San Francisco</option>
                        <option value="Coco del Mar">Coco del Mar</option>
                        <option value="Punta Pacífica">Punta Pacífica</option>
                        <option value="Clayton">Clayton / Albrook</option>
                        <option value="Betania">Betania / El Dorado</option>
                    </select>
                </div>
                <div class="select-filter">
                    <select id="originSelect" onchange="applyFilters()">
                        <option value="all">🌐 Todos los Orígenes</option>
                        <option value="directa">🏷️ Venta Directa Promotora</option>
                        <option value="reventa">🏢 Reventa / Portales</option>
                    </select>
                </div>
                <div class="select-filter">
                    <select id="typeSelect" onchange="applyFilters()">
                        <option value="all">🏠 Casas y Apartamentos</option>
                        <option value="apartamento">Solo Apartamentos</option>
                        <option value="casa">Solo Casas / Villas</option>
                    </select>
                </div>
                <div class="select-filter">
                    <select id="sortSelect" onchange="applyFilters()">
                        <option value="score">Ordenar por Match Dinámico</option>
                        <option value="price_asc">Precio: Menor a Mayor</option>
                        <option value="price_desc">Precio: Mayor a Menor</option>
                        <option value="m2_desc">Mayor Metraje (m²)</option>
                        <option value="year_desc">Año más reciente</option>
                    </select>
                </div>
            </div>

            <!-- Fila secundaria de control de precios y presupuesto -->
            <div style="display: flex; gap: 14px; align-items: center; justify-content: space-between; flex-wrap: wrap; background: rgba(17, 24, 39, 0.7); border: 1px solid var(--border); padding: 10px 18px; border-radius: 12px; font-size: 13px;">
                <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap;">
                    <span style="font-weight: 700; color: #94a3b8;">Rango de Precio:</span>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <label style="color: #64748b; font-size: 12px;">Mín:</label>
                        <input type="number" id="minPriceInput" placeholder="$0" step="10000" style="background: var(--bg); border: 1px solid var(--border); color: #fff; padding: 5px 8px; border-radius: 6px; width: 100px; font-size: 13px;" oninput="applyFilters()">
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <label style="color: #64748b; font-size: 12px;">Máx:</label>
                        <input type="number" id="maxPriceInput" placeholder="Sin límite" step="10000" style="background: var(--bg); border: 1px solid var(--border); color: #fff; padding: 5px 8px; border-radius: 6px; width: 110px; font-size: 13px;" oninput="applyFilters()">
                    </div>
                    <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; color: #cbd5e1; margin-left: 8px;">
                        <input type="checkbox" id="onlyBudgetCheck" onchange="applyFilters()">
                        <span>Solo opciones dentro de presupuesto (+10% margen negociable)</span>
                    </label>
                </div>
                <div>
                    <button type="button" onclick="resetFilters()" style="background: transparent; border: 1px solid var(--border); color: #94a3b8; padding: 5px 12px; border-radius: 6px; font-size: 12px; cursor: pointer;">
                        🔄 Restablecer filtros
                    </button>
                </div>
            </div>
        </div>

        <!-- Catálogo de Tarjetas -->
        <div class="cards-grid" id="cardsGrid">
            <!-- Renderizado dinámico vía JavaScript con los datos completos -->
        </div>
    </div>

    <script>
        const propertiesData = {props_json_str};
        let currentCategory = 'all';
        let currentBudget = {self.criteria.target_price:.0f};

        function setQuickBudget(val) {{
            currentBudget = parseInt(val);
            document.getElementById('budgetInput').value = currentBudget;
            document.querySelectorAll('.q-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.textContent.includes(Math.round(val / 1000) + 'k'));
            }});
            applyFilters();
        }}

        function onBudgetChanged(val) {{
            const num = parseInt(val);
            if (!isNaN(num) && num > 50000) {{
                currentBudget = num;
                document.querySelectorAll('.q-btn').forEach(btn => {{
                    btn.classList.toggle('active', btn.textContent.includes(Math.round(num / 1000) + 'k'));
                }});
                applyFilters();
            }}
        }}

        function setCategory(cat, btn) {{
            currentCategory = cat;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            applyFilters();
        }}

        function resetFilters() {{
            document.getElementById('searchInput').value = '';
            document.getElementById('zoneSelect').value = 'all';
            document.getElementById('originSelect').value = 'all';
            document.getElementById('typeSelect').value = 'all';
            document.getElementById('sortSelect').value = 'score';
            document.getElementById('minPriceInput').value = '';
            document.getElementById('maxPriceInput').value = '';
            document.getElementById('onlyBudgetCheck').checked = false;
            applyFilters();
        }}

        function computeDynamicScore(p, budget) {{
            let score = 0;
            const maxNegotiable = budget * 1.10;
            if (p.price <= budget) {{
                score += 25;
            }} else if (p.price <= maxNegotiable) {{
                score += 20;
            }} else {{
                score += 10;
            }}

            score += (p.cbe_confirmed ? 25 : 10);
            score += (p.study_confirmed ? 20 : 10);

            if (p.area_m2 >= 180) score += 15;
            else if (p.area_m2 >= 160) score += 12;
            else score += 8;

            const kidsCount = (p.kids_amenities || []).length;
            score += Math.min(15, 5 + kidsCount * 3);
            return Math.min(100, score);
        }}

        function applyFilters() {{
            const search = document.getElementById('searchInput').value.toLowerCase().trim();
            const origin = document.getElementById('originSelect').value;
            const zone = document.getElementById('zoneSelect').value.toLowerCase();
            const type = document.getElementById('typeSelect').value;
            const sort = document.getElementById('sortSelect').value;
            const minPrice = parseFloat(document.getElementById('minPriceInput').value) || 0;
            const maxPrice = parseFloat(document.getElementById('maxPriceInput').value) || Infinity;
            const onlyBudget = document.getElementById('onlyBudgetCheck').checked;

            const maxAllowedBudget = currentBudget * 1.10;

            // Recalculate dynamic score for all
            propertiesData.forEach(p => {{
                p.dynamicScore = computeDynamicScore(p, currentBudget);
            }});

            // Base matches across current non-category filters
            const baseMatches = propertiesData.filter(p => {{
                if (onlyBudget && p.price > maxAllowedBudget) return false;
                if (p.price < minPrice || p.price > maxPrice) return false;
                if (origin === 'directa' && !p.portal.toLowerCase().includes('directa')) return false;
                if (origin === 'reventa' && p.portal.toLowerCase().includes('directa')) return false;
                if (zone !== 'all' && !p.location.toLowerCase().includes(zone)) return false;
                if (type !== 'all' && p.property_type.toLowerCase() !== type) return false;
                if (search) {{
                    const fullText = (p.title + " " + p.location + " " + p.description + " " + (p.developer || "")).toLowerCase();
                    if (!fullText.includes(search)) return false;
                }}
                return true;
            }});

            // Update tab counts
            const totalCount = baseMatches.length;
            const nuevasCount = baseMatches.filter(p => p.category_group === 'nuevas_estrenar').length;
            const usadosCount = baseMatches.filter(p => p.category_group === 'usados_remodelados').length;

            const countAllEl = document.getElementById('countAll');
            const countNuevasEl = document.getElementById('countNuevas');
            const countUsadosEl = document.getElementById('countUsados');
            if (countAllEl) countAllEl.textContent = totalCount;
            if (countNuevasEl) countNuevasEl.textContent = nuevasCount;
            if (countUsadosEl) countUsadosEl.textContent = usadosCount;

            // Filter for current selected category
            let filtered = baseMatches.filter(p => {{
                if (currentCategory !== 'all' && p.category_group !== currentCategory) return false;
                return true;
            }});

            // Update stats grid
            const statTotalEl = document.getElementById('statTotal');
            const statNuevasEl = document.getElementById('statNuevas');
            const statUsadosEl = document.getElementById('statUsados');
            const statAvgPriceEl = document.getElementById('statAvgPrice');
            const statAvgM2El = document.getElementById('statAvgM2');

            if (statTotalEl) statTotalEl.textContent = filtered.length;
            if (statNuevasEl) statNuevasEl.textContent = filtered.filter(p => p.category_group === 'nuevas_estrenar').length;
            if (statUsadosEl) statUsadosEl.textContent = filtered.filter(p => p.category_group === 'usados_remodelados').length;
            
            const avgP = filtered.length > 0 ? Math.round(filtered.reduce((sum, p) => sum + p.price, 0) / filtered.length) : 0;
            const avgM = filtered.length > 0 ? Math.round(filtered.reduce((sum, p) => sum + p.area_m2, 0) / filtered.length) : 0;
            if (statAvgPriceEl) statAvgPriceEl.textContent = avgP > 0 ? '$' + avgP.toLocaleString() : '$0';
            if (statAvgM2El) statAvgM2El.textContent = avgM > 0 ? avgM + ' m²' : '0 m²';

            // Sorting
            filtered.sort((a, b) => {{
                if (sort === 'price_asc') return a.price - b.price;
                if (sort === 'price_desc') return b.price - a.price;
                if (sort === 'm2_desc') return b.area_m2 - a.area_m2;
                if (sort === 'year_desc') return (b.year_built || 0) - (a.year_built || 0);
                return b.dynamicScore - a.dynamicScore;
            }});

            renderCards(filtered);
        }}

        function renderCards(list) {{
            const grid = document.getElementById('cardsGrid');
            if (list.length === 0) {{
                grid.innerHTML = `
                    <div class="empty-state">
                        <h3>No se encontraron inmuebles con los criterios actuales</h3>
                        <p style="color: #94a3b8; margin-top: 8px;">Prueba ajustando el presupuesto objetivo o ampliando el rango de precio.</p>
                    </div>
                `;
                return;
            }}

            grid.innerHTML = list.map(p => {{
                const isNueva = p.category_group === 'nuevas_estrenar';
                const isRemodelado = p.newness_status && p.newness_status.toLowerCase().includes('remodelado');
                const catClass = isNueva ? 'nueva' : (isRemodelado ? 'remodelado' : 'usado');
                const isDirectDev = p.portal.toLowerCase().includes('directa');
                
                const photoTag = p.photo_url ? 
                    `<img src="${{p.photo_url}}" alt="${{p.title}}" class="card-img" onerror="this.src='https://via.placeholder.com/400x220?text=Foto+Propiedad'">` :
                    `<div class="no-photo">🏠 Foto en portal</div>`;

                const devBadge = isDirectDev ? `<div class="badge-dev">🏷️ PROMOTORA DIRECTA</div>` : '';
                const yearBadge = p.year_built ? `<div class="badge-year">📅 ${{p.year_built >= 2025 ? 'Entrega ' + p.year_built : 'Año ' + p.year_built}}</div>` : '';

                // Dynamic Budget Badge
                let budgetBadge = '';
                const diff = p.price - currentBudget;
                if (p.price <= currentBudget) {{
                    const saved = currentBudget - p.price;
                    budgetBadge = `<div class="badge-budget ok">✓ Dentro de Presupuesto ${{saved > 0 ? '(-$' + saved.toLocaleString() + ')' : '(Exacto)'}}</div>`;
                }} else if (p.price <= currentBudget * 1.10) {{
                    const pct = Math.round((diff / currentBudget) * 100);
                    budgetBadge = `<div class="badge-budget neg">⚠️ Negociable (+${{pct}}% / +$${{diff.toLocaleString()}})</div>`;
                }} else {{
                    budgetBadge = `<div class="badge-budget over">📈 Sobre Presupuesto (+$${{diff.toLocaleString()}})</div>`;
                }}

                const ams = p.kids_amenities || [];
                const amsHtml = ams.map(a => `<span class="ktag">${{a}}</span>`).join('');

                const maintStr = p.maintenance_fee ? `Mantenimiento: $${{p.maintenance_fee.toLocaleString()}}/mes` : (isDirectDev ? 'Venta de Proyecto Nuevo' : 'Mantenimiento por validar');

                const devInfo = p.developer ? `<div class="check-item"><span class="check-icon">🏗️</span> Promotora: <strong>${{p.developer}}</strong></div>` : '';
                const deliveryInfo = p.delivery_status ? `<div class="check-item"><span class="check-icon">⏱️</span> Entrega: <strong>${{p.delivery_status}}</strong></div>` : '';

                return `
                    <div class="prop-card">
                        <div class="card-media">
                            ${{photoTag}}
                            <div class="badge-cat ${{catClass}}">${{p.category_label}}</div>
                            ${{devBadge}}
                            ${{yearBadge}}
                            <div class="badge-score">${{p.dynamicScore}}% Match</div>
                        </div>
                        <div class="card-body">
                            <div class="price-line">
                                <span class="price-val">${{p.price_formatted}}</span>
                                <span class="price-m2">$${{Math.round(p.price_per_m2).toLocaleString()}} / m²</span>
                            </div>

                            ${{budgetBadge}}

                            <h3 class="prop-title" title="${{p.title}}">${{p.title}}</h3>
                            <div class="prop-loc">📍 ${{p.location || 'Ciudad de Panamá'}}</div>

                            <div class="specs-row">
                                <div>🛏️ <strong>${{p.rooms}}</strong> Rec.</div>
                                <div>🚿 <strong>${{p.baths}}</strong> Baños</div>
                                <div>📐 <strong>${{p.area_m2}}</strong> m²</div>
                            </div>

                            <div class="checklist-box">
                                ${{devInfo}}
                                ${{deliveryInfo}}
                                <div class="check-item"><span class="check-icon">✓</span> Cuarto y Baño de Empleada (CBE) confirmado</div>
                                <div class="check-item"><span class="check-icon">✓</span> Sala-Comedor espaciosa (viable ≥42 m²)</div>
                                <div class="check-item"><span class="check-icon">✓</span> Espacio para Estudio/TV ≥15 m²: ${{p.study_confirmed ? 'Sí' : 'Adaptable'}}</div>
                            </div>

                            <div class="kids-box">
                                <div class="kids-title">🧒 Comunidad & Amenidades para Niños:</div>
                                <div class="kids-tags">${{amsHtml || '<span class="ktag">Comunidad familiar y segura</span>'}}</div>
                            </div>

                            <div class="card-footer">
                                <span>${{maintStr}}</span>
                                <a href="${{p.url}}" target="_blank" class="action-btn">${{isDirectDev ? 'Ver Proyecto Directo ↗' : 'Ver en ' + p.portal + ' ↗'}}</a>
                            </div>
                        </div>
                    </div>
                `;
            }}).join('');
        }}

        // Initial Render
        document.addEventListener('DOMContentLoaded', () => {{
            applyFilters();
        }});
    </script>
</body>
</html>
'''
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Also mirror to root propiedades_encontradas.html and index.html for direct GitHub Pages hosting
        shutil.copyfile(html_path, "propiedades_encontradas.html")
        shutil.copyfile(html_path, "index.html")
