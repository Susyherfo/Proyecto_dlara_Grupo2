# Limpieza y preparación de fotografías – dIAra

## 1. Descripción

Esta etapa del proyecto dIAra consiste en desarrollar un proceso automatizado para la limpieza y preparación de fotografías de seguimiento de obras públicas, con el propósito de disponer de un conjunto de imágenes adecuado para su posterior análisis y visualización.

El proceso busca identificar fotografías dañadas, duplicadas, nocturnas o con condiciones de iluminación insuficientes. También permite identificar imágenes cuyo encuadre presenta diferencias importantes respecto a otras fotografías tomadas en fechas cercanas, para someterlas a revisión manual.

El objetivo es mejorar la calidad y organización de las evidencias fotográficas, manteniendo un registro de las decisiones tomadas durante la limpieza.

## 2. Conjunto de datos utilizado

Para esta etapa se utilizará exclusivamente como conjunto de datos de ejemplo el siguiente directorio:

`diara_liceo_ticaban`

Este conjunto contiene **409 fotografías** correspondientes al seguimiento de la obra del Liceo de Ticabán.

Por el momento, no se incorporarán fotografías de otras instituciones educativas, proyectos de infraestructura u obras públicas.

La selección de este conjunto permite realizar pruebas iniciales del proceso de limpieza y evaluar su funcionamiento antes de considerar su aplicación a otros conjuntos de fotografías.

## 3. Herramientas y tecnologías

El procesamiento se realizó localmente en una computadora, utilizando Visual Studio Code y Python, mediante un entorno virtual independiente.

Las herramientas utilizadas son:

- **Python:** lenguaje de programación utilizado para desarrollar el proceso.
- **Visual Studio Code:** entorno de desarrollo.
- **venv:** entorno virtual para aislar las dependencias.
- **OpenCV:** procesamiento y análisis de imágenes.
- **Pillow:** lectura y validación de archivos de imagen.
- **NumPy:** operaciones numéricas y análisis de matrices.
- **Pandas:** organización de los resultados y generación del registro CSV.
- **tqdm:** visualización del progreso de procesamiento.

## 4. Proceso de limpieza implementado

El proceso se desarrolla en cuatro etapas principales:

### 4.1. Inventario y análisis de fotografías

Se recorren las fotografías JPG y JPEG contenidas en el directorio de origen y sus subcarpetas.

Para cada imagen se recopila información como:

- Nombre del archivo.
- Ruta relativa.
- Fecha y hora, cuando se pueden identificar a partir del nombre.
- Nivel promedio de brillo.
- Porcentaje de píxeles oscuros.
- Identificador MD5 para detectar duplicados exactos.
- Estado del archivo.

También se verifica que las imágenes puedan abrirse y procesarse correctamente.

### 4.2. Aplicación de reglas de descarte

Se aplican las siguientes reglas:

- Archivos dañados o ilegibles.
- Archivos cuyo nombre no contiene una fecha y hora válidas según el formato esperado.
- Fotografías pertenecientes a rangos de fechas definidos para exclusión.
- Fotografías nocturnas o con iluminación insuficiente.
- Fotografías duplicadas exactas.

Los umbrales iniciales configurados son:

| Parámetro | Valor |
|---|---:|
| Brillo mínimo | 30 |
| Porcentaje máximo de píxeles oscuros | 80 % |
| Umbral de similitud de encuadre | 0.80 |
| Ventana temporal para comparar fotografías | 4 días |

Los rangos de exclusión de fechas se encuentran configurables en el código y no se aplican mientras permanezcan comentados.

### 4.3. Identificación de fotografías para revisión manual

Las fotografías que superan las reglas de descarte se comparan con otras imágenes tomadas dentro de una ventana temporal de cuatro días.

Se utiliza una representación normalizada de las imágenes en escala de grises para identificar diferencias importantes de encuadre.

Cuando la similitud calculada no alcanza el umbral configurado, la fotografía se marca con:

`REVISAR: encuadre distinto a las fotos vecinas`

Estas imágenes no se descartan automáticamente. Se mantienen dentro del conjunto de fotografías conservadas y quedan identificadas para una revisión posterior.

### 4.4. Generación del conjunto limpio y registro

Las fotografías que superan las reglas de descarte se copian a un nuevo directorio, manteniendo su estructura de subcarpetas.

Además, se genera un archivo CSV denominado:

`registro_limpieza.csv`

Este archivo contiene información para documentar las decisiones tomadas durante el procesamiento, incluyendo:

- Archivo.
- Ruta relativa.
- Fecha.
- Hora.
- Brillo.
- Decisión (CONSERVADA o DESCARTADA).
- Motivo.
- Indicador de revisión manual.

## 5. Estructura de resultados

La ejecución genera una nueva carpeta denominada:

`diara_liceo_ticaban_imagenes_web`

Su estructura contiene:

- Fotografías que superaron las reglas de descarte.
- Subcarpetas originales, cuando corresponde.
- Archivo `registro_limpieza.csv` con el resultado del procesamiento.

**Importante:** las fotografías originales no se modifican ni se eliminan. El programa trabaja sobre ellas y copia las imágenes seleccionadas a un directorio independiente.

## 6. Entorno de ejecución

El proyecto se ejecuta desde Visual Studio Code mediante un entorno virtual de Python.

Creación del entorno:

```powershell
py -m venv .venv
```

Activación:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalación de dependencias:

```powershell
python -m pip install opencv-python-headless pillow tqdm numpy pandas
```

Ejecución del programa:

```powershell
python limpiar_imagenes_web.py
```

## 7. Alcance y limitaciones

Esta implementación corresponde a una primera prueba de procesamiento automatizado utilizando únicamente las 409 fotografías del Liceo de Ticabán.

Se deben considerar las siguientes limitaciones:

- La identificación de fecha y hora depende del formato del nombre de los archivos.
- La detección de fotografías nocturnas se basa en umbrales de brillo, por lo que algunas imágenes podrían requerir validación humana.
- La detección de duplicados identifica coincidencias exactas mediante MD5; no identifica necesariamente fotografías visualmente similares.
- Las diferencias de encuadre no representan por sí solas evidencia de una irregularidad en la obra.
- Las fotografías marcadas para revisión requieren interpretación y validación manual.
- Los parámetros utilizados son iniciales y podrían necesitar ajustes según las características de otros conjuntos de imágenes.

La limpieza no determina el avance físico de la obra ni verifica por sí misma el cumplimiento de cronogramas o informes oficiales.

## 8. Consideraciones para el perfil auditor de dIAra

El registro generado permite conservar trazabilidad sobre las fotografías procesadas y las decisiones de clasificación.

Esta información podrá servir como insumo para etapas posteriores de análisis, donde se podrán comparar evidencias fotográficas entre fechas y contrastarlas con información documental de la obra.

La clasificación automatizada debe entenderse como una herramienta de apoyo y no como una decisión definitiva sobre la validez de una evidencia.

---

**Estado de esta etapa:** implementación inicial y ejecución local del proceso de limpieza utilizando exclusivamente el conjunto de fotografías de ejemplo del Liceo de Ticabán.