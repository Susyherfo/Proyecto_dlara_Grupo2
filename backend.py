
# -*- coding: utf-8 -*-
"""
Proyecto dIAra - Grupo 2
Backend de consulta ciudadana de evidencia fotografica.

Fuente principal:
diara_liceo_ticaban_imagenes_web/registro_limpieza.csv

IMPORTANTE:
La cantidad de fotografias NO representa el porcentaje
de avance fisico de la construccion.
"""

from pathlib import Path, PureWindowsPath
import pandas as pd


# ============================================================
# 1. CONFIGURACION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CARPETA_IMAGENES = (
    BASE_DIR / "diara_liceo_ticaban_imagenes_web"
)

ARCHIVO_CSV = CARPETA_IMAGENES / "registro_limpieza.csv"

# Archivo opcional de detecciones reales.
# No se crea ni se inventa informacion.
ARCHIVO_ACTIVIDAD = BASE_DIR / "actividad_detectada.csv"

NOMBRE_OBRA = "Liceo de Ticaban"

FUENTE_FOTOGRAFIAS = (
    "Registro de limpieza de fotografias "
    "del proyecto dIAra"
)

ADVERTENCIA_AVANCE = (
    "Las fotografias permiten observar cambios visibles, "
    "pero no permiten calcular por si solas el porcentaje "
    "de avance fisico de la obra."
)


# ============================================================
# 2. CARGA Y VALIDACION
# ============================================================

def cargar_datos():
    """Carga el CSV y prepara las columnas necesarias."""

    if not ARCHIVO_CSV.is_file():
        raise FileNotFoundError(
            f"No se encontro el archivo: {ARCHIVO_CSV}"
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
    ).dt.normalize()

    datos["decision"] = (
        datos["decision"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    datos["revisar"] = (
        datos["revisar"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    datos["motivo"] = (
        datos["motivo"]
        .fillna("")
        .astype(str)
    )

    datos["brillo"] = pd.to_numeric(
        datos["brillo"], errors="coerce"
    )

    datos["pendiente_revision"] = (
        datos["revisar"] != ""
    )

    datos["fuente"] = FUENTE_FOTOGRAFIAS

    return datos


# ============================================================
# 3. ESTADISTICAS GENERALES
# ============================================================

def obtener_estadisticas(datos):
    """Indicadores del proceso de limpieza fotografica."""

    total = len(datos)

    conservadas = int(
        (datos["decision"] == "CONSERVADA").sum()
    )

    descartadas = int(
        (datos["decision"] == "DESCARTADA").sum()
    )

    revision = int(
        datos["pendiente_revision"].sum()
    ) if "pendiente_revision" in datos else int(
        datos["revisar"].fillna("").str.strip().ne("").sum()
    )

    porcentaje = (
        round(conservadas * 100 / total, 2)
        if total else 0
    )

    return {
        "total": total,
        "conservadas": conservadas,
        "descartadas": descartadas,
        "revision": revision,
        "porcentaje_conservadas": porcentaje
    }


# ============================================================
# 4. FECHAS DISPONIBLES
# ============================================================

def obtener_fechas(datos):
    """Fechas que tienen registros conservados."""

    fechas = datos.loc[
        datos["decision"] == "CONSERVADA",
        "fecha"
    ].dropna()

    return sorted(fechas.dt.date.unique().tolist())


def obtener_rango_fechas(datos):
    """Primera y ultima fecha del registro completo."""

    fechas = datos["fecha"].dropna()

    if fechas.empty:
        return {
            "inicio": None,
            "fin": None
        }

    return {
        "inicio": fechas.min().date(),
        "fin": fechas.max().date()
    }


def navegar_fecha(datos, fecha_actual, direccion=1):
    """
    Devuelve la fecha disponible anterior o siguiente.

    direccion = -1: anterior
    direccion =  1: siguiente
    """

    if direccion not in (-1, 1):
        raise ValueError(
            "La direccion debe ser -1 o 1."
        )

    fechas = obtener_fechas(datos)

    if not fechas:
        return None

    actual = pd.Timestamp(fecha_actual).date()

    if direccion == 1:
        siguientes = [
            fecha for fecha in fechas
            if fecha > actual
        ]
        return siguientes[0] if siguientes else None

    anteriores = [
        fecha for fecha in fechas
        if fecha < actual
    ]

    return anteriores[-1] if anteriores else None


# ============================================================
# 5. FILTROS
# ============================================================

def filtrar_fotografias(
    datos,
    fecha_inicio=None,
    fecha_fin=None,
    incluir_revision=True
):
    """Obtiene fotografias conservadas en un periodo."""

    resultado = datos.loc[
        datos["decision"] == "CONSERVADA"
    ].copy()

    if fecha_inicio is not None:
        inicio = pd.Timestamp(fecha_inicio).normalize()

        resultado = resultado.loc[
            resultado["fecha"] >= inicio
        ]

    if fecha_fin is not None:
        fin = pd.Timestamp(fecha_fin).normalize()

        resultado = resultado.loc[
            resultado["fecha"] <= fin
        ]

    if not incluir_revision:
        resultado = resultado.loc[
            resultado["revisar"].fillna("").str.strip() == ""
        ]

    return resultado.sort_values(
        ["fecha", "hora", "archivo"]
    ).reset_index(drop=True)


def obtener_fotografias_dia(
    datos,
    fecha,
    incluir_revision=True
):
    """Consulta fotografias de una fecha especifica."""

    return filtrar_fotografias(
        datos,
        fecha_inicio=fecha,
        fecha_fin=fecha,
        incluir_revision=incluir_revision
    )


# ============================================================
# 6. RUTAS SEGURAS DE IMAGENES
# ============================================================

def obtener_ruta_imagen(registro):
    """
    Localiza una fotografia conservada.

    Acepta rutas relativas de Windows y evita
    acceder a archivos externos al proyecto.
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

    carpeta = CARPETA_IMAGENES.resolve()

    ruta = carpeta.joinpath(
        *ruta_windows.parts
    ).resolve()

    if not ruta.is_relative_to(carpeta):
        return None

    return ruta if ruta.is_file() else None


def preparar_galeria(
    datos,
    fecha_inicio=None,
    fecha_fin=None,
    incluir_revision=True
):
    """
    Prepara registros para la galeria de Streamlit.

    Incluye rutas, fechas, horas y advertencias.
    """

    fotografias = filtrar_fotografias(
        datos,
        fecha_inicio,
        fecha_fin,
        incluir_revision
    )

    galeria = []

    for _, registro in fotografias.iterrows():

        ruta = obtener_ruta_imagen(registro)

        if ruta is None:
            continue

        fecha = registro["fecha"]

        galeria.append({
            "archivo": str(registro["archivo"]),
            "fecha": (
                fecha.date()
                if pd.notna(fecha) else None
            ),
            "hora": str(registro["hora"]),
            "ruta": str(ruta),
            "pendiente_revision": bool(
                str(registro["revisar"]).strip()
            ),
            "advertencia_revision": str(
                registro["revisar"]
            ),
            "fuente": FUENTE_FOTOGRAFIAS
        })

    return galeria


# ============================================================
# 7. CRONOLOGIA Y DIAS SIN EVIDENCIA
# ============================================================

def obtener_cronologia(datos):
    """
    Devuelve un DataFrame diario para graficos.

    Un dia sin imagen conservada NO implica
    que la construccion estuvo detenida.
    """

    rango = obtener_rango_fechas(datos)

    columnas = [
        "fecha",
        "registradas",
        "conservadas",
        "descartadas",
        "pendientes_revision",
        "tiene_evidencia",
        "estado"
    ]

    if rango["inicio"] is None:
        return pd.DataFrame(columns=columnas)

    fechas = pd.date_range(
        rango["inicio"],
        rango["fin"],
        freq="D"
    )

    resumen = datos.groupby("fecha").agg(
        registradas=("decision", "size"),
        conservadas=(
            "decision",
            lambda x: int((x == "CONSERVADA").sum())
        ),
        descartadas=(
            "decision",
            lambda x: int((x == "DESCARTADA").sum())
        ),
        pendientes_revision=(
            "revisar",
            lambda x: int(
                x.fillna("").astype(str).str.strip().ne("").sum()
            )
        )
    )

    cronologia = (
        resumen.reindex(fechas, fill_value=0)
        .rename_axis("fecha")
        .reset_index()
    )

    cronologia["tiene_evidencia"] = (
        cronologia["conservadas"] > 0
    )

    cronologia["estado"] = cronologia.apply(
        lambda fila: (
            "Con fotografias disponibles"
            if fila["conservadas"] > 0
            else (
                "Registros sin fotografias conservadas"
                if fila["registradas"] > 0
                else "Sin registros fotograficos"
            )
        ),
        axis=1
    )

    return cronologia[columnas]


def obtener_dias_sin_evidencia(datos):
    """Dias sin fotografias conservadas en el periodo."""

    cronologia = obtener_cronologia(datos)

    return cronologia.loc[
        ~cronologia["tiene_evidencia"]
    ].reset_index(drop=True)


# ============================================================
# 8. RESUMEN DIARIO
# ============================================================

def obtener_resumen_diario(datos, fecha):
    """Resumen ciudadano de una fecha."""

    fecha = pd.Timestamp(fecha).normalize()

    registros = datos.loc[
        datos["fecha"] == fecha
    ]

    fotos = obtener_fotografias_dia(
        datos, fecha
    )

    total = len(registros)
    conservadas = len(fotos)

    descartadas = int(
        (registros["decision"] == "DESCARTADA").sum()
    )

    revision = int(
        fotos["revisar"].fillna("").str.strip().ne("").sum()
    )

    if conservadas:
        estado = "Hay evidencia fotografica disponible."
    elif total:
        estado = (
            "Hay registros, pero ninguna fotografia "
            "conservada para esta fecha."
        )
    else:
        estado = (
            "No hay registros fotograficos "
            "para esta fecha."
        )

    return {
        "obra": NOMBRE_OBRA,
        "fecha": fecha.date(),
        "registros": total,
        "fotografias_disponibles": conservadas,
        "descartadas": descartadas,
        "pendientes_revision": revision,
        "estado": estado,
        "actividad_detectada": None,
        "estado_actividad": (
            "No hay datos de detecciones de IA "
            "en el registro fotografico."
        ),
        "avance_fisico_porcentaje": None,
        "fuente": FUENTE_FOTOGRAFIAS,
        "advertencia": ADVERTENCIA_AVANCE
    }


# ============================================================
# 9. COMPARACION ENTRE FECHAS
# ============================================================

def comparar_fechas(datos, fecha_1, fecha_2):
    """
    Prepara dos galerias para comparacion visual.

    No interpreta automaticamente cambios
    constructivos ni calcula porcentajes.
    """

    fecha_1 = pd.Timestamp(fecha_1).date()
    fecha_2 = pd.Timestamp(fecha_2).date()

    galeria_1 = preparar_galeria(
        datos, fecha_1, fecha_1
    )

    galeria_2 = preparar_galeria(
        datos, fecha_2, fecha_2
    )

    return {
        "fecha_1": fecha_1,
        "fecha_2": fecha_2,
        "fotografias_1": galeria_1,
        "fotografias_2": galeria_2,
        "cantidad_1": len(galeria_1),
        "cantidad_2": len(galeria_2),
        "comparacion_disponible": bool(
            galeria_1 and galeria_2
        ),
        "advertencia": (
            "La comparacion es visual. Las fotografias "
            "pueden tener encuadres diferentes y no "
            "demuestran por si solas el avance fisico."
        )
    }


# ============================================================
# 10. REPRODUCCION CRONOLOGICA
# ============================================================

def obtener_secuencia_temporal(
    datos,
    fecha_inicio=None,
    fecha_fin=None
):
    """
    Devuelve imagenes ordenadas para que Streamlit
    implemente un recorrido temporal.
    """

    return preparar_galeria(
        datos,
        fecha_inicio,
        fecha_fin,
        incluir_revision=True
    )


# ============================================================
# 11. DATOS OPCIONALES DE ACTIVIDAD DETECTADA
# ============================================================

def cargar_actividad_detectada():
    """
    Carga detecciones reales si el equipo proporciona
    un archivo actividad_detectada.csv.

    Estructura minima:
        fecha, personas, maquinaria

    No estima detecciones a partir de las fotografias.
    """

    columnas = [
        "fecha", "personas", "maquinaria"
    ]

    if not ARCHIVO_ACTIVIDAD.is_file():
        return pd.DataFrame(columns=columnas)

    actividad = pd.read_csv(
        ARCHIVO_ACTIVIDAD,
        encoding="utf-8-sig"
    )

    faltantes = set(columnas) - set(actividad.columns)

    if faltantes:
        raise ValueError(
            "El archivo de actividad no tiene "
            f"las columnas: {sorted(faltantes)}"
        )

    actividad["fecha"] = pd.to_datetime(
        actividad["fecha"], errors="coerce"
    ).dt.normalize()

    for columna in ("personas", "maquinaria"):
        actividad[columna] = pd.to_numeric(
            actividad[columna],
            errors="coerce"
        )

    return actividad


def obtener_actividad_diaria(actividad):
    """
    Agrupa detecciones registradas por fecha.

    Los valores representan detecciones reportadas,
    no personas unicas ni avance de obra.
    """

    columnas = [
        "fecha", "personas", "maquinaria"
    ]

    if actividad.empty:
        return pd.DataFrame(columns=columnas)

    validos = actividad.dropna(
        subset=["fecha"]
    )

    return (
        validos.groupby("fecha", as_index=False)[
            ["personas", "maquinaria"]
        ]
        .sum(min_count=1)
        .sort_values("fecha")
        .reset_index(drop=True)
    )


def obtener_serie_visualizacion(datos):
    """
    Integra la cronologia fotografica con
    detecciones reales, cuando estan disponibles.
    """

    cronologia = obtener_cronologia(datos)
    actividad = cargar_actividad_detectada()

    if actividad.empty:
        cronologia["personas"] = float("nan")
        cronologia["maquinaria"] = float("nan")
        return cronologia

    actividad_diaria = obtener_actividad_diaria(
        actividad
    )

    return cronologia.merge(
        actividad_diaria,
        on="fecha",
        how="left"
    )


# ============================================================
# 12. METADATOS Y TRAZABILIDAD
# ============================================================

def obtener_informacion_proyecto(datos):
    """Informacion general para el frontend."""

    rango = obtener_rango_fechas(datos)
    estadisticas = obtener_estadisticas(datos)

    fechas = datos.loc[
        datos["decision"] == "CONSERVADA",
        "fecha"
    ].dropna()

    return {
        "nombre": NOMBRE_OBRA,
        "fuente": FUENTE_FOTOGRAFIAS,
        "archivo_fuente": ARCHIVO_CSV.name,
        "primera_fecha": rango["inicio"],
        "ultima_fecha": rango["fin"],
        "ultima_evidencia": (
            fechas.max().date()
            if not fechas.empty else None
        ),
        "estadisticas": estadisticas,
        "advertencia": ADVERTENCIA_AVANCE,
        "avance_fisico_disponible": False
    }


def diagnosticar_archivos(datos):
    """
    Verifica la disponibilidad de las imagenes
    conservadas.
    """

    fotos = filtrar_fotografias(datos)

    encontrados = 0
    faltantes = []

    for _, registro in fotos.iterrows():

        ruta = obtener_ruta_imagen(registro)

        if ruta is None:
            faltantes.append(
                str(registro["archivo"])
            )
        else:
            encontrados += 1

    return {
        "esperados": len(fotos),
        "encontrados": encontrados,
        "faltantes": len(faltantes),
        "archivos_faltantes": faltantes
    }


# ============================================================
# 13. PRUEBAS AUTOMATICAS BASICAS
# ============================================================

def ejecutar_pruebas():
    """Comprueba las funciones principales."""

    print("=" * 55)
    print("PROYECTO dIAra - PRUEBAS DEL BACKEND")
    print("=" * 55)

    datos = cargar_datos()

    print("\n1. ESTADISTICAS")
    estadisticas = obtener_estadisticas(datos)

    for clave, valor in estadisticas.items():
        print(f"{clave}: {valor}")

    print("\n2. FECHAS")
    fechas = obtener_fechas(datos)
    print(f"Fechas disponibles: {len(fechas)}")

    if fechas:
        print(f"Primera: {fechas[0]}")
        print(f"Ultima: {fechas[-1]}")

    print("\n3. CRONOLOGIA")
    cronologia = obtener_cronologia(datos)
    print(f"Dias del periodo: {len(cronologia)}")

    sin_evidencia = obtener_dias_sin_evidencia(datos)
    print(f"Dias sin evidencia: {len(sin_evidencia)}")

    print("\n4. GALERIA")
    galeria = preparar_galeria(datos)
    print(f"Imagenes disponibles: {len(galeria)}")

    print("\n5. COMPARACION")

    if len(fechas) >= 2:
        comparacion = comparar_fechas(
            datos, fechas[0], fechas[-1]
        )

        print(
            f"Primera fecha: "
            f"{comparacion['cantidad_1']} imagenes"
        )

        print(
            f"Ultima fecha: "
            f"{comparacion['cantidad_2']} imagenes"
        )

        print(
            "Comparacion disponible:",
            comparacion["comparacion_disponible"]
        )

    print("\n6. DIAGNOSTICO DE ARCHIVOS")
    diagnostico = diagnosticar_archivos(datos)

    print(
        f"Encontrados: {diagnostico['encontrados']}"
    )
    print(
        f"Faltantes: {diagnostico['faltantes']}"
    )

    print("\n7. ACTIVIDAD DETECTADA")
    actividad = cargar_actividad_detectada()

    if actividad.empty:
        print(
            "Sin archivo de detecciones reales. "
            "No se inventan resultados."
        )
    else:
        print(
            f"Registros de actividad: {len(actividad)}"
        )

    print("\n8. COMPROBACIONES")

    assert len(datos) == sum([
        estadisticas["conservadas"],
        estadisticas["descartadas"]
    ]), (
        "Existen decisiones distintas de "
        "CONSERVADA o DESCARTADA."
    )

    assert len(galeria) == diagnostico["encontrados"]

    assert len(cronologia) == (
        len(cronologia.loc[
            cronologia["tiene_evidencia"]
        ]) + len(sin_evidencia)
    )

    print("Comprobaciones basicas superadas.")
    print("\nBackend ejecutado correctamente.")


if __name__ == "__main__":
    ejecutar_pruebas()
