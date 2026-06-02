# El pulso turístico de Barcelona

Visualización interactiva que explora la relación entre la **presión turística** (Airbnb) y el
**mercado del alquiler residencial** en los 73 barrios de Barcelona, combinando dos fuentes de datos
abiertos. Práctica final de la asignatura *Visualización de Datos* (UOC).

🔗 **Visualización en vivo:** https://Josean1611.github.io/PRACTICA-FINAL-VISUALIZACI-N-DE-DATOS-/

---

## Preguntas que responde

1. ¿Existe una correlación directa entre la densidad de viviendas turísticas y la subida del alquiler?
2. ¿En qué barrios es más alta la *brecha de rentabilidad* entre el uso turístico y el residencial?
3. ¿Cómo se distribuye espacialmente la presión turística (centro frente a periferia)?

## Fuentes de datos

- **Inside Airbnb** — snapshot de Barcelona, septiembre de 2025 (anuncios, geografía, disponibilidad).
- **Open Data Ajuntament de Barcelona** — precio medio mensual del alquiler residencial por barrio y trimestre.
- **Geometría de barrios** — `neighbourhoods.geojson` (Inside Airbnb).

> **Nota metodológica:** el snapshot más reciente (diciembre 2025) traía el campo de precio vacío
> por la normativa europea de visualización de precio total; se usó el de septiembre de 2025, que
> conserva los precios. El alquiler se alineó al mismo periodo (3r trimestre de 2025).

## Métricas (fórmulas)

| Métrica | Cálculo | Unidad |
|---|---|---|
| Presión turística | viviendas enteras / área del barrio | viviendas/km² |
| Incremento del alquiler | (alquiler 2025 − alquiler 2015) / alquiler 2015 × 100 | % |
| Brecha de rentabilidad | mediana(ingreso mensual Airbnb) − / ÷ alquiler mensual | €/mes y ratio |

El ingreso mensual de Airbnb se estima con el modelo de ocupación de Inside Airbnb (50% de estancias
dejan reseña, estancia media 3 noches), calculado solo sobre viviendas **en activo** y barrios con
**≥10 anuncios** activos. Es un **ingreso bruto potencial** (no descuenta gastos ni impuestos).

## Cómo ejecutar en local

```bash
pip install -r requirements.txt
python preparar_datos.py          # genera la carpeta datos_clean/
python -m http.server 8000        # sirve la web
# abrir http://localhost:8000
```

> La página carga datos con `fetch`, por lo que **debe servirse por HTTP** (no abrir el archivo con doble clic).

## Estructura del proyecto

```
.
├── index.html              # la visualización (D3.js)
├── preparar_datos.py       # limpieza, métricas y exportación
├── requirements.txt        # dependencias de Python
├── Datos/                  # datos crudos de entrada
├── datos_clean/            # datos generados que consume la web
├── assets/                 # imagen de cabecera
├── README.md
└── LICENSE
```

## Tecnología

- **Visualización:** D3.js v7 (mapa coroplético, scatterplot, scrollytelling con IntersectionObserver).
- **Preparación de datos:** Python (pandas, geopandas).

## Licencia

Código bajo licencia [MIT](LICENSE). Los datos pertenecen a sus respectivas fuentes (Inside Airbnb,
Ajuntament de Barcelona).

## Autor

José Antonio López Sánchez — UOC, 2026.
