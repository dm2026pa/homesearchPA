# search_agent.py
import argparse
import sys
import os
import re
import logging

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from panama_property_agent.models import SearchCriteria
from panama_property_agent.portal_encuentra24 import Encuentra24Scraper
from panama_property_agent.portal_developers import DeveloperProjectsScraper
from panama_property_agent.analyzer import PropertyAnalyzer
from panama_property_agent.reporter import PropertyReporter

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        level=level
    )

def main():
    parser = argparse.ArgumentParser(
        description="Agente de Búsqueda Inmobiliaria Restructurado (Comunidad Niños + Nuevas por Estrenar [Año 2025+] vs Usados/Remodelados [<2025])"
    )
    parser.add_argument("--budget", type=int, default=None, help="Presupuesto objetivo (alias directo de --target-price)")
    parser.add_argument("--target-price", type=int, default=380000, help="Presupuesto objetivo (default: 380000)")
    parser.add_argument("--max-price", type=int, default=None, help="Precio máximo de búsqueda (default: +10% sobre presupuesto)")
    parser.add_argument("--min-price", type=int, default=None, help="Precio mínimo de búsqueda (default: -35% sobre presupuesto)")
    parser.add_argument("--min-m2", type=float, default=140.0, help="Metraje total mínimo en m² (default: 140)")
    parser.add_argument("--pages", type=int, default=2, help="Páginas a escanear en portales (default: 2)")
    parser.add_argument("--skip-devs", action="store_true", help="Omitir venta directa de promotoras")
    parser.add_argument("--verbose", action="store_true", help="Mostrar logs detallados")

    args = parser.parse_args()
    setup_logging(args.verbose)

    target_price = args.budget if args.budget is not None else args.target_price
    max_price = args.max_price if args.max_price is not None else int(target_price * 1.10)
    min_price = args.min_price if args.min_price is not None else int(target_price * 0.68)

    print("=" * 88)
    print(">> AGENTE INMOBILIARIO REESTRUCTURADO — CIUDAD DE PANAMÁ")
    print(f">> Presupuesto Objetivo: ${target_price:,.0f} USD (Rango: ${min_price:,.0f} - ${max_price:,.0f} USD)")
    print(">> FILTRO OBLIGATORIO: 3 Rec + 2.5+B + CBE + Sala ≥42m² + Estudio TV ≥15m² + COMUNIDAD NIÑOS")
    print(">> REGLA ESTRICTA DE AÑO: Nuevas por Estrenar = Año de Construcción/Entrega ≥ 2025")
    print(">>                        Usados o Remodelados = Año < 2025 o Reventas Consolidadas")
    print("=" * 88)

    criteria = SearchCriteria(
        min_price=min_price,
        max_price=max_price,
        target_price=target_price,
        min_total_area_m2=args.min_m2,
        require_kids_community=True
    )

    raw_properties = []

    # 1. Portales Inmobiliarios (Encuentra24)
    print("\n[1/3] Rastreando portales inmobiliarios (Encuentra24: apartamentos y casas)...")
    scraper_e24 = Encuentra24Scraper()
    e24_props = scraper_e24.search(criteria, max_pages_per_category=args.pages)
    raw_properties.extend(e24_props)
    print(f"      -> {len(e24_props)} propiedades recolectadas de portales.")

    # 2. Venta Directa de Promotoras y Proyectos Nuevos
    if not args.skip_devs:
        print("\n[2/3] Rastreando sitios directos de promotoras e InmoProyectos Panamá...")
        dev_scraper = DeveloperProjectsScraper()
        dev_props = dev_scraper.search(criteria)
        raw_properties.extend(dev_props)
        print(f"      -> {len(dev_props)} proyectos directos de promotoras obtenidos.")
    else:
        print("\n[2/3] Búsqueda directa en promotoras omitida por parámetro.")

    print(f"\n[3/4] Aplicando filtros estrictos y regla de año (≥2025) sobre {len(raw_properties)} inmuebles...")
    analyzer = PropertyAnalyzer(criteria)
    evaluated_properties = []
    
    for p in raw_properties:
        ev = analyzer.evaluate(p)
        # Only keep properties that pass all strict criteria
        if ev is not None and p.price > 0 and p.rooms >= 3 and p.area_m2 >= criteria.min_total_area_m2:
            evaluated_properties.append(p)

    # Deduplicar por nombre normalizado (priorizando venta directa de promotora)
    seen_keys = set()
    deduped_evaluated = []
    # Priorizar orden: promotoras directas primero
    evaluated_properties.sort(
        key=lambda x: (
            1 if x.portal.startswith("Venta Directa") else 0,
            x.evaluation.overall_score if x.evaluation else 0
        ),
        reverse=True
    )
    for p in evaluated_properties:
        norm = re.sub(r'[^a-z0-9]', '', p.title.lower().split("—")[0].split("(")[0].strip())
        # Truncar claves largas o genéricas
        norm_key = norm[:15] if len(norm) > 15 else norm
        if norm_key not in seen_keys:
            seen_keys.add(norm_key)
            deduped_evaluated.append(p)

    evaluated_properties = deduped_evaluated

    # Sort primarily by overall match score descending
    evaluated_properties.sort(
        key=lambda x: (
            x.evaluation.overall_score if x.evaluation else 0,
            -x.price
        ),
        reverse=True
    )

    nuevas = [p for p in evaluated_properties if p.evaluation.category_group == "nuevas_estrenar"]
    usados = [p for p in evaluated_properties if p.evaluation.category_group == "usados_remodelados"]

    print(f"\n[4/4] Generando Portal Web Local y reportes estructurados...")
    reporter = PropertyReporter(criteria)
    
    portal_dir = "portal_inmobiliario"
    html_path = "propiedades_encontradas.html"
    json_path = "propiedades_encontradas.json"
    md_path = "propiedades_recomendadas.md"

    reporter.export_web_portal(evaluated_properties, portal_dir)
    reporter.export_json(evaluated_properties, json_path)
    reporter.export_markdown(evaluated_properties, md_path)

    print("\n" + "=" * 94)
    print(f">> RESULTADOS CLASIFICADOS: {len(evaluated_properties)} Propiedades Calificadas al 100%")
    print(f"   • ✨ Nuevas por Estrenar (Año ≥2025):  {len(nuevas)} propiedades")
    print(f"   • 🔄 Usados o Remodelados (Año <2025): {len(usados)} propiedades")
    print("=" * 94)

    if nuevas:
        print("\n✨ --- 1. NUEVAS POR ESTRENAR (AÑO 2025 EN ADELANTE) ---")
        print(f"{'#':<3} | {'PRECIO':<10} | {'M²':<5} | {'REC/B':<7} | {'AÑO':<6} | {'PROMOTORA / PH':<24} | {'UBICACIÓN':<20}")
        print("-" * 90)
        for i, p in enumerate(nuevas, 1):
            rec_b = f"{p.rooms}R/{p.baths:.1f}B"
            yr = str(p.year_built or "2025+")[:6]
            promo = (p.developer or p.title.split("(")[-1].replace(")", "") or p.portal)[:23]
            loc = (p.location or "Ciudad de Panamá").replace("Panamá Provincia, Ciudad de Panamá, ", "")[:19]
            print(f"{i:<3} | ${p.price:<9,} | {p.area_m2:<5.0f} | {rec_b:<7} | {yr:<6} | {promo:<24} | {loc:<20}")

    if usados:
        print("\n🔄 --- 2. USADOS O REMODELADOS (AÑO ANTERIOR A 2025) ---")
        print(f"{'#':<3} | {'PRECIO':<10} | {'M²':<5} | {'REC/B':<7} | {'CONDICIÓN':<22} | {'AMENIDADES NIÑOS':<20} | {'UBICACIÓN':<18}")
        print("-" * 94)
        for i, p in enumerate(usados[:12], 1):
            rec_b = f"{p.rooms}R/{p.baths:.1f}B"
            cond = p.evaluation.newness_status[:21]
            am_str = ", ".join([a.split(" ")[-1] for a in p.evaluation.kids_amenities[:2]])[:19]
            loc = (p.location or "Ciudad de Panamá").replace("Panamá Provincia, Ciudad de Panamá, ", "")[:17]
            print(f"{i:<3} | ${p.price:<9,} | {p.area_m2:<5.0f} | {rec_b:<7} | {cond:<22} | {am_str:<20} | {loc:<18}")

    print("\n📂 Portal Web Local y Archivos Actualizados:")
    print(f"  • 🌐 Portal Web Local:  http://localhost:8080 (o {os.path.abspath(os.path.join(portal_dir, 'index.html'))})")
    print(f"  • 📄 Reporte Markdown:   {os.path.abspath(md_path)}")
    print(f"  • 🗄️ Base de Datos JSON: {os.path.abspath(json_path)}")
    print("\n💡 Puedes ver los cambios de inmediato en tu navegador:")
    print("   • Abre http://localhost:8080")
    print("   • O haz doble clic en 'portal_inmobiliario\\index.html'")

if __name__ == "__main__":
    main()
