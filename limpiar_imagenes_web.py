# -*- coding: utf-8 -*-
"""
Limpieza de fotografías de cámara de obra para publicación web.

- NO modifica ni borra la carpeta original: copia las aptas a una carpeta nueva.
- Descarta: archivos dañados, duplicados exactos, fotos nocturnas / sin luz,
  rangos de fecha-hora que usted indique (pruebas de instalación, cámara retirada).
- Marca para REVISIÓN MANUAL (sin descartar) las diurnas cuyo encuadre difiere
  mucho de las fotos vecinas (objeto tapando el lente, cámara movida, etc.).
- Genera un CSV con una fila por foto y el motivo: sirve como evidencia para el auditor.

Uso local en Windows: ajustar las rutas de la sección CONFIGURACIÓN y ejecutar
desde Visual Studio Code con el entorno de Python donde instaló las dependencias.
"""
import re, shutil, hashlib, sys, subprocess, importlib.util
from pathlib import Path

for pkg, mod in [
    ('opencv-python-headless', 'cv2'),
    ('pillow', 'PIL'),
    ('tqdm', 'tqdm'),
    ('numpy', 'numpy'),
    ('pandas', 'pandas')
]:
    if importlib.util.find_spec(mod) is None:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])
import cv2, numpy as np, pandas as pd
from PIL import Image
from tqdm.auto import tqdm

# ======================= CONFIGURACIÓN =======================
# Carpeta original con las fotografías.
ORIGEN = Path(r"C:\Users\susyh\OneDrive\Pictures\Desktop\proyecto_dlara\diara_liceo_ticaban")

# Carpeta nueva donde se copiarán las fotos aptas y el CSV.
# Se crea al ejecutar; la carpeta original no se modifica.
DESTINO = ORIGEN.parent / f"{ORIGEN.name}_imagenes_web"

if not ORIGEN.exists():
    raise FileNotFoundError(
        f"No se encontró la carpeta de imágenes: {ORIGEN}\\n"
        "Verifique que la ruta esté escrita correctamente."
    )
if not ORIGEN.is_dir():
    raise NotADirectoryError(f"La ruta de origen no es una carpeta: {ORIGEN}")

IGNORAR_CARPETAS = {'imagenes_tratadas'}   # nombres de subcarpetas a no procesar ([] si no aplica)
MIN_BRILLO       = 30     # brillo medio (0-255) por debajo = noche / sin luz
MAX_OSCURO_PCT   = 80     # % de píxeles muy oscuros por encima = noche
UMBRAL_ENCUADRE  = 0.80   # correlación mínima con fotos vecinas; menos = "REVISAR"

# Rangos a descartar (pruebas de instalación, cámara retirada, etc.). Formato:
# ('2025-08-05 00:00:00', '2025-08-05 12:12:59', 'Prueba de instalación de la cámara')
EXCLUIR_RANGOS = [
    # ('2025-08-05 00:00:00', '2025-08-05 12:12:59', 'Prueba de instalación de la cámara'),
    # ('2025-09-17 00:00:00', '2025-09-17 23:59:59', 'Cámara movida o retirada'),
]
# =============================================================

PATRON = re.compile(r'(?<!\d)(20\d{2})(\d{2})(\d{2})[-_](\d{2})(\d{2})(\d{2})(?!\d)')
EXT = {'.jpg', '.jpeg'}

def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

# ---- 1. Inventario y métricas -------------------------------------------
filas = []
archivos = [p for p in ORIGEN.rglob('*')
            if p.is_file() and p.suffix.lower() in EXT
            and not any(part.casefold() in {c.casefold() for c in IGNORAR_CARPETAS}
                        for part in p.relative_to(ORIGEN).parts[:-1])]
for p in tqdm(archivos, desc='Analizando'):
    r = {'ruta': str(p), 'archivo': p.name, 'relativa': str(p.relative_to(ORIGEN)),
         'ts': pd.NaT, 'brillo': np.nan, 'oscuro_pct': np.nan, 'md5': None, 'motivo': ''}
    m = PATRON.search(p.stem)
    if m:
        try: r['ts'] = pd.to_datetime(''.join(m.groups()), format='%Y%m%d%H%M%S')
        except ValueError: pass
    try:
        with Image.open(p) as im: im.load()          # detecta archivos truncados
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None: raise ValueError('no legible')
        g = cv2.resize(img, (640, 480), interpolation=cv2.INTER_AREA)
        r['brillo'], r['oscuro_pct'] = float(g.mean()), float((g < 20).mean() * 100)
        r['md5'] = md5(p)
    except Exception:
        r['motivo'] = 'Archivo dañado'
    filas.append(r)
df = pd.DataFrame(filas)

# ---- 2. Reglas de descarte (en orden de prioridad) -----------------------
df.loc[(df.motivo == '') & df.ts.isna(), 'motivo'] = 'Nombre sin fecha-hora válida'
for ini, fin, texto in EXCLUIR_RANGOS:
    m = (df.motivo == '') & df.ts.between(pd.Timestamp(ini), pd.Timestamp(fin))
    df.loc[m, 'motivo'] = texto
m = (df.motivo == '') & ((df.brillo < MIN_BRILLO) | (df.oscuro_pct > MAX_OSCURO_PCT))
df.loc[m, 'motivo'] = 'Nocturna / sin luz suficiente'
dup = (df.motivo == '') & df.md5.notna() & df.duplicated('md5', keep='first')
df.loc[dup, 'motivo'] = 'Duplicado exacto'

# ---- 3. Marcar para revisión manual (no descarta) -------------------------
def firma(p):
    g = cv2.resize(cv2.imread(p, cv2.IMREAD_GRAYSCALE), (64, 48)).astype(np.float32)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    return ((g - g.mean()) / (g.std() + 1e-6)).ravel()

ok = df[df.motivo == ''].sort_values('ts').copy()
df['revisar'] = ''
if len(ok) > 5:
    F = np.stack([firma(p) for p in tqdm(ok.ruta, desc='Comparando encuadre')])
    t = ok.ts.values
    for i in range(len(ok)):
        vec = np.flatnonzero((np.abs(t - t[i]) < np.timedelta64(4, 'D')) & (np.arange(len(ok)) != i))
        if len(vec) and max(F[i] @ F[j] for j in vec) / F.shape[1] < UMBRAL_ENCUADRE:
            df.loc[ok.index[i], 'revisar'] = 'REVISAR: encuadre distinto a las fotos vecinas'

# ---- 4. Copiar las aptas y escribir el registro ----------------------------
DESTINO.mkdir(parents=True, exist_ok=True)
aptas = df[df.motivo == '']
for _, r in tqdm(aptas.iterrows(), total=len(aptas), desc='Copiando aptas'):
    dst = DESTINO / r.relativa
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(r.ruta, dst)

reg = df.assign(decision=np.where(df.motivo == '', 'CONSERVADA', 'DESCARTADA'),
                fecha=df.ts.dt.date, hora=df.ts.dt.strftime('%H:%M:%S'),
                brillo=df.brillo.round(1))[
    ['archivo', 'relativa', 'fecha', 'hora', 'brillo', 'decision', 'motivo', 'revisar']
].sort_values(['fecha', 'hora'])
reg.to_csv(DESTINO / 'registro_limpieza.csv', index=False, encoding='utf-8-sig')

print(f'\nTotal analizadas: {len(df):,}')
print(reg.decision.value_counts().to_string())
print(reg[reg.decision == 'DESCARTADA'].motivo.value_counts().to_string())
print(f'Marcadas para revisión manual: {(df.revisar != "").sum()}')
print('Carpeta limpia:', DESTINO)
