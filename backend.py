
# -*- coding: utf-8 -*-
"""
PROYECTO dIAra - GRUPO 2
Backend para la visualización de fotografías
del Liceo de Ticabán.
"""

from pathlib import Path, PureWindowsPath
import pandas as pd


# ============================================================
# 1. CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CARPETA_IMAGENES = (
    BASE_DIR / "diara_liceo_ticaban_imagenes_web"
)

ARCHIVO_CSV = CARPETA_IMAGENES / "registro_limpieza.csv"


# ============================================================
# 2. CARGAR DATOS
# ============================================================

def cargar_datos():
    """Carga y valida el registro de fotografías."""

    if not ARCHIVO_CSV.is_file():
        raise FileNotFoundError(
            f"No se encontró el CSV: {ARCHIVO_CSV}"
        )

    datos = pd.read_csv(
        ARCHIVO_CSV,
        encoding="utf-8-sig"
    )

    columnas = {
        "archivo", "relativa", "fecha", "hora",
        "brillo", "decision", "motivo", "revisar"
    }

    faltantes = columnas - set(datos.columns)

    if faltantes:
        raise ValueError(
            f"Faltan columnas: {sorted(faltantes)}"
        )

    datos["fecha"] = pd.to_datetime(
        datos["fecha"], errors="coerce"
    )

    return datos


# ============================================================
# 3. ESTADÍSTICAS GENERALES
# ============================================================

def obtener_estadisticas(datos):
    """Calcula indicadores del registro de limpieza."""

    total = len(datos)

    conservadas = (
        datos["decision"] == "CONSERVADA"
    ).sum()

    descartadas = (
        datos["decision"] == "DESCARTADA"
    ).sum()

    revision = (
        datos["revisar"].fillna("").str.strip() != ""
    ).sum()

    porcentaje = (
        round(conservadas / total * 100, 2)
        if total else 0
    )

    return {
        "total": int(total),
        "conservadas": int(conservadas),
        "descartadas": int(descartadas),
        "revision": int(revision),
        "porcentaje_conservadas": porcentaje
    }


# ============================================================
# 4. CONSULTAR FECHAS DISPONIBLES
# ============================================================

def obtener_fechas(datos):
    """Devuelve las fechas con fotografías conservadas."""

    conservadas = datos[
        datos["decision"] == "CONSERVADA"
    ]

    fechas = (
        conservadas["fecha"]
        .dropna()
        .dt.date
        .unique()
    )

    return sorted(fechas)


# ============================================================
# 5. FILTRAR FOTOGRAFÍAS
# ============================================================

def filtrar_fotografias(
    datos, fecha_inicio=None, fecha_fin=None,
    incluir_revision=True
):
    """
    Filtra fotografías conservadas por fecha.

    Las imágenes pendientes de revisión se incluyen
    por defecto, pero pueden excluirse.
    """

    resultado = datos[
        datos["decision"] == "CONSERVADA"
    ].copy()

    if fecha_inicio is not None:
        inicio = pd.Timestamp(fecha_inicio)
        resultado = resultado[
            resultado["fecha"] >= inicio
        ]

    if fecha_fin is not None:
        fin = pd.Timestamp(fecha_fin)
        resultado = resultado[
            resultado["fecha"] < fin + pd.Timedelta(days=1)
        ]

    if not incluir_revision:
        resultado = resultado[
            resultado["revisar"].fillna("").str.strip() == ""
        ]

    return resultado.sort_values(
        ["fecha", "hora"]
    ).reset_index(drop=True)


# ============================================================
# 6. LOCALIZAR UNA FOTOGRAFÍA
# ============================================================

def obtener_ruta_imagen(registro):
    """
    Obtiene la ruta de una fotografía conservada.

    Acepta rutas relativas generadas en Windows.
    No permite acceder a archivos fuera de la carpeta
    de imágenes del proyecto.
    """

    if registro["decision"] != "CONSERVADA":
        return None

    relativa = registro["relativa"]

    if pd.isna(relativa):
        return None

    ruta_windows = PureWindowsPath(str(relativa))

    if (
        ruta_windows.is_absolute()
        or ruta_windows.drive
        or ".." in ruta_windows.parts
    ):
        return None

    ruta = CARPETA_IMAGENES.joinpath(
        *ruta_windows.parts
    ).resolve()

    carpeta = CARPETA_IMAGENES.resolve()

    if not ruta.is_relative_to(carpeta):
        return None

    if ruta.is_file():
        return ruta

    return None


# ============================================================
# 7. PRUEBAS DEL BACKEND
# ============================================================

if __name__ == "__main__":

    print("=" * 50)
    print("PROYECTO dIAra - GRUPO 2")
    print("PRUEBA DEL BACKEND")
    print("=" * 50)

    datos = cargar_datos()
    print(f"\nRegistros cargados: {len(datos)}")

    estadisticas = obtener_estadisticas(datos)

    print("\nESTADÍSTICAS GENERALES")
    print("-" * 50)

    for nombre, valor in estadisticas.items():
        print(f"{nombre}: {valor}")

    fechas = obtener_fechas(datos)

    print("\nFECHAS DISPONIBLES")
    print("-" * 50)
    print(f"Cantidad de fechas: {len(fechas)}")

    if fechas:
        print(f"Primera fecha: {fechas[0]}")
        print(f"Última fecha: {fechas[-1]}")

    fotografias = filtrar_fotografias(datos)

    print("\nCONSULTA DE FOTOGRAFÍAS")
    print("-" * 50)
    print(f"Fotografías conservadas: {len(fotografias)}")

    encontradas = 0

    for _, registro in fotografias.iterrows():
        ruta = obtener_ruta_imagen(registro)

        if ruta is not None:
            encontradas += 1

    print(f"Archivos encontrados: {encontradas}")
    print(
        f"Archivos faltantes: "
        f"{len(fotografias) - encontradas}"
    )

    print("\nBackend ejecutado correctamente.")
