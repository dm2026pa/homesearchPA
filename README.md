# 🏠 Panama Property Agent & Portal Inmobiliario Familiar

Agente inteligente de búsqueda, análisis y filtrado inmobiliario para la **Ciudad de Panamá**, diseñado específicamente para familias que buscan inmuebles con estrictos estándares de espacio, funcionalidad y vida en comunidad infantil.

<div align="center" style="margin: 16px 0;">

[![⚡ Refrescar Catálogo en GitHub](https://img.shields.io/badge/⚡_REFRESCAR_CATÁLOGO_MANUALMENTE-Haz_Clic_Aquí-238636?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/dm2026pa/homesearchPA/actions/workflows/update_listings.yml)
&nbsp;&nbsp;
[![🌐 Abrir Portal Web en Vivo](https://img.shields.io/badge/🌐_ABRIR_PORTAL_WEB_EN_VIVO-GitHub_Pages-0969da?style=for-the-badge&logo=googlechrome&logoColor=white)](https://dm2026pa.github.io/homesearchPA/)

</div>

---

## 🎯 Criterios de Búsqueda y Filtros Estrictos

- **Presupuesto objetivo:** \$380,000 USD *(modificable en tiempo real en la web o vía CLI)*.
- **Distribución:** 3 Recámaras (principal + niños) + **Cuarto y Baño de Empleada (CBE)** indispensable.
- **Baños:** Mínimo 2.5 a 3.5 baños.
- **Áreas sociales internas:**
  - Sala-Comedor espaciosa: viable para $\ge$42 m².
  - Estudio / Den de televisión: viable para $\ge$15 m².
- **Comunidad Infantil (Filtro Obligatorio):**
  - Parques infantiles (*playgrounds*), piscinas familiares / splash parks, canchas deportivas, áreas verdes y seguridad 24/7 con garita.
- **Clasificación Estricta por Año:**
  1. ✨ **Nuevas por Estrenar:** Construcción o entrega en **Año 2025 o posterior** ($\ge$ 2025).
  2. 🔄 **Usados o Remodelados:** Construcción en año < 2025 o reventas consolidadas en excelente estado.
- **Zonas prioritarias:** Brisas del Golf, Paseo del Norte, Panamá Norte (Green City), Panamá Pacífico, Costa del Mar, Costa del Este, Edison Park, Coco del Mar, San Francisco, Clayton.

---

## 🚀 Uso Local

### 1. Requisitos Previos
- Python 3.10+
- Entorno virtual activado:

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# En Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# En Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Ejecutar el Agente de Búsqueda
El agente rastrea múltiples fuentes simultáneamente (portales como Encuentra24, InmoProyectos y venta directa de promotoras en Panamá Pacífico, Paseo del Norte, Green City, etc.):

```bash
# Búsqueda con presupuesto predeterminado ($380,000)
python search_agent.py

# Modificar el presupuesto objetivo desde consola:
python search_agent.py --budget 420000

# Parámetros adicionales:
# --budget <monto>       : Presupuesto objetivo (ajusta min y max automáticamente)
# --min-price <monto>    : Filtro mínimo de precio
# --max-price <monto>    : Filtro máximo de precio
# --min-m2 <monto>       : Metraje mínimo en m² (default: 140 m²)
# --pages <num>          : Número de páginas por sección (default: 2)
# --verbose              : Muestra logs detallados de scraping
```

### 3. Iniciar el Portal Web Local
Inicia un servidor web local y abre automáticamente la aplicación interactiva:

```bash
python serve_portal.py
```
Abre en tu navegador: **`http://localhost:8080`**

---

## 🎛️ Modificador de Presupuesto en Tiempo Real

El portal web (`portal_inmobiliario/index.html`) incluye un motor reactivo de presupuesto:
- **Input dinámico:** Cambia el presupuesto objetivo a cualquier monto y observa cómo se recalculan los scores de afinidad instantáneamente.
- **Botones rápidos:** Acceso directo con un clic a presupuestos estándar: **\$320k, \$350k, \$380k, \$420k, \$450k, \$500k**.
- **Insignias presupuestarias por tarjeta:**
  - 🟢 `✓ Dentro de Presupuesto`: Muestra ahorro respecto a tu objetivo.
  - 🟡 `⚠️ Negociable (+10%)`: Muestra el margen de negociación estándar en Panamá.
  - 🔴 `📈 Sobre Presupuesto`: Opciones que exceden el margen.
- **Filtros complementarios:** Rango mínimo y máximo personalizado, buscador de texto libre, filtro por zona, origen (promotora vs reventa) y tipo (casa vs apartamento).

---

## 📦 Subir el Proyecto a GitHub

Sigue estos comandos para inicializar y subir el proyecto a tu repositorio de GitHub:

```bash
# 1. Inicializar Git en el directorio
git init

# 2. Agregar todos los archivos (el .gitignore excluye la carpeta .venv y temporales)
git add .

# 3. Crear el commit inicial
git commit -m "feat: Panama Property Agent con portal interactivo y clasificador 2025+"

# 4. Configurar la rama principal
git branch -M main

# 5. Conectar con tu repositorio remoto en GitHub
# (Crea un repositorio vacío en github.com y reemplaza la URL)
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git

# 6. Subir los archivos
git push -u origin main
```

---

## ☁️ Despliegue en la Nube (Cloud)

El proyecto está 100% containerizado y preparado para correr en cualquier proveedor de nube.

### Opción A: Google Cloud Run (Recomendado - Serverless y Económico)

Cloud Run compilará el Dockerfile automáticamente y te otorgará una URL HTTPS segura:

```bash
# Asegúrate de tener instalado y autenticado Google Cloud SDK (gcloud)
gcloud auth login
gcloud config set project TU_PROJECT_ID

# Desplegar directamente desde el código fuente:
gcloud run deploy panama-property-portal \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080
```

### Opción B: Render.com (Despliegue Gratuito en 2 minutos)

1. Ingresa a [render.com](https://render.com/) y conecta tu cuenta de GitHub.
2. Crea un **New Web Service**.
3. Selecciona tu repositorio recién subido.
4. Render detectará automáticamente el `Dockerfile`.
5. Selecciona el plan gratuito (*Free*) y haz clic en **Create Web Service**.

### Opción C: Railway.app

1. Ingresa a [railway.app](https://railway.app/).
2. Haz clic en **New Project** -> **Deploy from GitHub repo**.
3. Selecciona tu repositorio. Railway detectará el `Dockerfile` y expondrá el puerto 8080 automáticamente.

### Opción D: Docker Local o en Servidor VPS

```bash
# Construir la imagen Docker
docker build -t panama-property-portal .

# Ejecutar el contenedor en el puerto 8080
docker run -d -p 8080:8080 --name portal-inmobiliario panama-property-portal
```

---

## 🤖 Automatización con GitHub Actions

El repositorio incluye el flujo de trabajo `.github/workflows/update_listings.yml` que:
- Se ejecuta automáticamente cada lunes y jueves a las 7:00 AM (hora Panamá).
- Permite ejecución manual bajo demanda con un clic desde la pestaña **Actions** en GitHub.
- Vuelve a ejecutar el agente de búsqueda y actualiza el catálogo en el repositorio.

---

## 📁 Estructura del Proyecto

```
├── Dockerfile                          # Configuración de contenedor para Cloud Run / Docker
├── .dockerignore                       # Exclusiones de build Docker
├── .gitignore                          # Exclusiones de control de versiones Git
├── requirements.txt                    # Dependencias Python (requests, beautifulsoup4)
├── README.md                           # Documentación completa
├── search_agent.py                     # CLI ejecutor del agente de búsqueda inmobiliaria
├── serve_portal.py                     # Servidor HTTP compatible con entornos locales y nube
├── .github/
│   └── workflows/
│       └── update_listings.yml         # Automatización de scraping periódico en GitHub
├── portal_inmobiliario/
│   ├── index.html                      # Portal web interactivo con presupuesto dinámico
│   └── propiedades.json                # Base de datos completa en JSON de inmuebles calificados
├── panama_property_agent/
│   ├── __init__.py
│   ├── models.py                       # Dataclasses (Property, SearchCriteria, MatchEvaluation)
│   ├── analyzer.py                     # Motor de evaluación: regla año 2025+, CBE, sala, estudio, comunidad
│   ├── portal_encuentra24.py           # Scraper Encuentra24 (apts, casas, Brisas, Paseo del Norte)
│   ├── portal_developers.py            # Scraper promotoras (InmoProyectos, Panamá Pacífico, Green City)
│   └── reporter.py                     # Generador de reportes Markdown y Portal Web HTML5
└── propiedades_recomendadas.md         # Informe ejecutivo en Markdown
```
"# homesearchPA" 
"# homesearchPA" 
"# homesearchPA" 
