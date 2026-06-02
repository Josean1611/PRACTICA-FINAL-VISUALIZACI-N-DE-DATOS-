"""
preparar_datos.py
-----------------
Prepara los datos para la visualización (Práctica de Visualización de Datos, UOC).

Combina tres fuentes a nivel de BARRIO de Barcelona:
  1. listings.csv        -> anuncios de Airbnb (snapshot sep-2025, con precio)
  2. Tabla estadística   -> alquiler residencial medio mensual por barrio y trimestre
  3. neighbourhoods.geojson -> geometría de los 73 barrios

Salida (carpeta datos_clean/):
  - barrios_metricas.geojson  -> 1 polígono por barrio con todas las métricas (para el mapa coroplético)
  - puntos_airbnb.csv         -> 1 fila por vivienda entera (para la capa de puntos del mapa)
"""

import os
import pandas as pd
import geopandas as gpd

# ----------------------------------------------------------------------
# 0. CONFIGURACIÓN
# ----------------------------------------------------------------------
# Carpeta donde están los archivos de entrada Y donde se guardará la salida.
CARPETA_DATOS = "Datos"

RUTA_LISTINGS = os.path.join(CARPETA_DATOS, "listings.csv")            # snapshot sep-2025 (con precio)
RUTA_ALQUILER = os.path.join(CARPETA_DATOS, "Tabla estadística.csv")   # tabla de alquiler (Open Data)
RUTA_GEOJSON  = os.path.join(CARPETA_DATOS, "neighbourhoods.geojson")  # geometría de barrios

# Carpeta donde se guardarán los archivos LIMPIOS generados (separados de los crudos).
CARPETA_SALIDA = "datos_clean"

# Supuestos de las fórmulas (acordados y declarados en el diccionario)
TASA_RESENA    = 0.5   # se asume que el 50% de las estancias dejan reseña
ESTANCIA_MEDIA = 3     # noches por reserva (= mediana de minimum_nights)

# Mínimo de viviendas en activo para que la brecha de un barrio sea fiable.
# Por debajo de este número la mediana es ruido y el barrio queda "sin dato".
MIN_ANUNCIOS_BRECHA = 10

# Trimestres a comparar para el incremento del alquiler
TRIM_INICIO    = "3r tr 2015"
TRIM_FINAL     = "3r tr 2025"


# ======================================================================
# 1. ALQUILER: limpiar y calcular el incremento porcentual por barrio
# ======================================================================
# La tabla trae los números en formato europeo ("1.082,4" = 1082.4) y mezcla
# filas de barrio, distrito, municipio, etc. Nos quedamos solo con los barrios.

def num_es(valor):
    """Convierte un número en formato español ('1.082,4') a float (1082.4)."""
    if pd.isna(valor):
        return None
    s = str(valor).strip().strip('"')
    if s in ("", "-"):
        return None
    s = s.replace(".", "").replace(",", ".")  # quita miles, coma -> punto decimal
    try:
        return float(s)
    except ValueError:
        return None

# Leemos respetando las comillas (hay comas dentro de algunos nombres de barrio)
alquiler = pd.read_csv(RUTA_ALQUILER, dtype=str, keep_default_na=False)

# Nos quedamos solo con las filas de tipo "Barri"
alquiler = alquiler[alquiler["Tipo de territorio"].str.strip() == "Barri"].copy()

# Renombramos los 2 barrios cuyo nombre difiere del geojson (sufijo administrativo)
RENOMBRES = {
    "el Poble Sec - AEI Parc Montjuïc": "el Poble Sec",
    "la Marina del Prat Vermell - AEI Zona Franca": "la Marina del Prat Vermell",
}
alquiler["barrio"] = alquiler["Territorio"].str.strip().replace(RENOMBRES)

# Convertimos los dos trimestres que nos interesan a número
alquiler["alq_2015"] = alquiler[TRIM_INICIO].map(num_es)
alquiler["alq_2025"] = alquiler[TRIM_FINAL].map(num_es)

# Incremento porcentual 2015 -> 2025
alquiler["incremento_alquiler"] = (
    (alquiler["alq_2025"] - alquiler["alq_2015"]) / alquiler["alq_2015"] * 100
)

alquiler = alquiler[["barrio", "alq_2015", "alq_2025", "incremento_alquiler"]]
print(f"[1] Alquiler: {len(alquiler)} barrios con datos de alquiler")


# ======================================================================
# 2. AIRBNB: filtrar viviendas enteras y estimar el ingreso mensual
# ======================================================================
listings = pd.read_csv(RUTA_LISTINGS)

# Solo viviendas enteras (es la comparación justa frente a un alquiler residencial)
ent = listings[listings["room_type"] == "Entire home/apt"].copy()

# price puede venir vacío (~21%): lo pasamos a número, los vacíos quedan como NaN
ent["price"] = pd.to_numeric(ent["price"], errors="coerce")

# Modelo de ocupación (Inside Airbnb, simplificado):
#   noches ocupadas/año = reseñas_12m x (1/tasa_reseña) x estancia_media
#   acotado a los días que el anuncio está disponible (availability_365)
noches = ent["number_of_reviews_ltm"] * (1 / TASA_RESENA) * ESTANCIA_MEDIA
ent["noches_ocupadas"] = noches.clip(upper=ent["availability_365"])

# Ingreso mensual potencial bruto por anuncio
ent["ingreso_mensual_airbnb"] = ent["price"] * ent["noches_ocupadas"] / 12

# La DENSIDAD cuenta TODAS las viviendas enteras (una vivienda listada está
# retirada del mercado residencial aunque tenga poca actividad).
conteo = ent.groupby("neighbourhood").size().rename("n_viviendas_enteras")

# La RENTABILIDAD se calcula solo sobre viviendas EN ACTIVO (con reseñas en los
# últimos 12 meses). Incluir las inactivas hunde la mediana y distorsiona la
# brecha: un piso que apenas opera no refleja el incentivo real de uso turístico.
activos = ent[ent["number_of_reviews_ltm"] > 0]
n_activos = activos.groupby("neighbourhood").size()
ingreso = activos.groupby("neighbourhood")["ingreso_mensual_airbnb"].median()
# Solo fiable con muestra suficiente: descartamos barrios con pocos activos
ingreso = ingreso[n_activos >= MIN_ANUNCIOS_BRECHA].rename("ingreso_mensual_mediano")

airbnb = (pd.concat([conteo, ingreso], axis=1).reset_index()
            .rename(columns={"neighbourhood": "barrio"}))
print(f"[2] Airbnb: {conteo.size} barrios con viviendas enteras "
      f"({len(ent)} anuncios; {len(activos)} en activo; "
      f"{(n_activos >= MIN_ANUNCIOS_BRECHA).sum()} barrios con brecha fiable)")


# ======================================================================
# 3. GEOMETRÍA: cargar barrios y calcular su área en km²
# ======================================================================
barrios = gpd.read_file(RUTA_GEOJSON).rename(columns={"neighbourhood": "barrio"})

# Algunos barrios vienen partidos en varios polígonos (p. ej. Vallvidrera).
# Los fusionamos en una sola geometría por barrio: 1 fila = 1 barrio.
barrios = barrios.dissolve(by="barrio", aggfunc="first").reset_index()

# El geojson está en grados (WGS84). Para medir área hay que reproyectar a un
# sistema métrico: EPSG:25831 (UTM 31N), el oficial para Cataluña.
barrios["area_km2"] = barrios.to_crs(25831).area / 1_000_000
print(f"[3] Geometría: {len(barrios)} barrios, área calculada en km²")


# ======================================================================
# 4. UNIR LAS TRES FUENTES Y CALCULAR LAS MÉTRICAS FINALES
# ======================================================================
g = barrios.merge(airbnb, on="barrio", how="left") \
           .merge(alquiler, on="barrio", how="left")

# Barrios sin Airbnb -> 0 viviendas
g["n_viviendas_enteras"] = g["n_viviendas_enteras"].fillna(0)

# Métrica 1: presión turística (viviendas enteras por km²)
g["presion_turistica"] = g["n_viviendas_enteras"] / g["area_km2"]

# Métrica 3: brecha de rentabilidad (€/mes y ratio)
g["brecha_eur"]   = g["ingreso_mensual_mediano"] - g["alq_2025"]
g["brecha_ratio"] = g["ingreso_mensual_mediano"] / g["alq_2025"]

# Redondeo para que el GeoJSON quede limpio
for c, dec in [("area_km2", 3), ("presion_turistica", 1), ("incremento_alquiler", 1),
               ("ingreso_mensual_mediano", 0), ("brecha_eur", 0), ("brecha_ratio", 2)]:
    g[c] = g[c].round(dec)


# ======================================================================
# 5. EXPORTAR los archivos que usará D3
# ======================================================================
os.makedirs(CARPETA_SALIDA, exist_ok=True)  # se crea si no existe

# 5a. GeoJSON con las métricas incrustadas (para el mapa coroplético)
cols = ["barrio", "neighbourhood_group", "area_km2", "n_viviendas_enteras",
        "presion_turistica", "alq_2015", "alq_2025", "incremento_alquiler",
        "ingreso_mensual_mediano", "brecha_eur", "brecha_ratio", "geometry"]
g[cols].to_file(os.path.join(CARPETA_SALIDA, "barrios_metricas.geojson"), driver="GeoJSON")

# 5b. CSV de puntos (para la capa de anuncios y el filtro de availability)
puntos = ent[["latitude", "longitude", "neighbourhood",
              "price", "availability_365"]].copy()
puntos.to_csv(os.path.join(CARPETA_SALIDA, "puntos_airbnb.csv"), index=False)

print(f"\n[OK] Archivos generados en {CARPETA_SALIDA}/")
print(f"     barrios_metricas.geojson  ({len(g)} barrios)")
print(f"     puntos_airbnb.csv         ({len(puntos)} anuncios)")

# Vista rápida de control
print("\nControl — 6 barrios:")
print(g[["barrio", "presion_turistica", "incremento_alquiler",
         "brecha_eur", "brecha_ratio"]].head(6).to_string(index=False))