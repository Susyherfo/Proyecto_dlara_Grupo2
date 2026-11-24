
import argparse
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import shutil
import threading
from urllib.parse import urlsplit

import pandas as pd

import backend


FRONTEND_DIR = backend.BASE_DIR / "Frontend"
PROJECT_FILE = FRONTEND_DIR / "data" / "obra.json"
_registry_lock = threading.Lock()
_registry_cache = None


def load_registry():
    global _registry_cache

    modified = backend.ARCHIVO_CSV.stat().st_mtime_ns
    with _registry_lock:
        if _registry_cache is None or _registry_cache[0] != modified:
            _registry_cache = (modified, backend.cargar_datos())
        return _registry_cache[1]


def load_project():
    with PROJECT_FILE.open(encoding="utf-8") as source:
        project = json.load(source)
    if not isinstance(project, dict):
        raise ValueError(f"La ficha del proyecto debe ser un objeto JSON: {PROJECT_FILE}")
    return project


def _text(value):
    return "" if pd.isna(value) else str(value)


def _date(value):
    return None if pd.isna(value) else pd.Timestamp(value).date().isoformat()


def build_dashboard():
    records = load_registry()
    project = load_project()
    info = backend.obtener_informacion_proyecto(records)
    photos = []

    for photo_id in range(len(records)):
        row = records.iloc[photo_id]
        kept = row["decision"] == "CONSERVADA"
        image_path = backend.obtener_ruta_imagen(row) if kept else None
        brightness = row["brillo"]
        photos.append({
            "id": photo_id,
            "n": _text(row["archivo"]),
            "f": _date(row["fecha"]),
            "h": _text(row["hora"]),
            "b": None if pd.isna(brightness) else float(brightness),
            "d": row["decision"],
            "m": _text(row["motivo"]),
            "rev": bool(row["pendiente_revision"]),
            "p": f"/api/photos/{photo_id}/image" if image_path is not None else None,
        })

    for key in (
        "ubicacion", "institucion_ejecutora", "monto_colones",
        "avance_previsto_pct", "avance_observado_pct", "hitos",
    ):
        project.setdefault(key, None if key != "hitos" else [])
    project.setdefault("nombre", info["nombre"])

    generated = datetime.fromtimestamp(
        backend.ARCHIVO_CSV.stat().st_mtime
    ).astimezone().isoformat(timespec="minutes")
    return {
        "fuente": backend.ARCHIVO_CSV.name,
        "generado": generated,
        "estadisticas": info["estadisticas"],
        "fotos": photos,
        "obra": project,
    }


class ProjectRequestHandler(SimpleHTTPRequestHandler):
    server_version = "dIAra"
    sys_version = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == "/api/health":
                data = load_registry()
                self._send_json(200, {
                    "estado": "ok",
                    "registros": len(data),
                    "fuente": backend.ARCHIVO_CSV.name,
                })
                return

            if path == "/api/dashboard":
                self._send_json(200, build_dashboard())
                return

            match = re.fullmatch(r"/api/photos/(\d+)/image", path)
            if match:
                photo_id = int(match.group(1))
                data = load_registry()
                if photo_id >= len(data):
                    self._send_json(404, {"error": "No existe esa fotografía."})
                    return

                image_path = backend.obtener_ruta_imagen(data.iloc[photo_id])
                if image_path is None:
                    self._send_json(404, {"error": "La fotografía no está disponible."})
                    return

                with image_path.open("rb") as image:
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(image_path.stat().st_size))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    shutil.copyfileobj(image, self.wfile)
                return

            if path.startswith("/api/"):
                self._send_json(404, {"error": "No existe esa ruta de API."})
                return

        except (OSError, ValueError, pd.errors.ParserError) as error:
            self._send_json(503, {"error": str(error)})
            return

        super().do_GET()


class ProjectHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description="Sirve dIAra y su API local.")
    parser.add_argument("--host", default="127.0.0.1", help="Dirección de escucha.")
    parser.add_argument("--port", type=int, default=8765, help="Puerto HTTP.")
    args = parser.parse_args()

    load_registry()
    with ProjectHTTPServer((args.host, args.port), ProjectRequestHandler) as server:
        print(f"dIAra disponible en http://{args.host}:{args.port}/")
        print("API: /api/health y /api/dashboard")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")


if __name__ == "__main__":
    main()
