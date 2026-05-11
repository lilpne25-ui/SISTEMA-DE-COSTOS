from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core_llm.runtime_service import LlmGlobalShopRuntime  # noqa: E402
from app.data.pervasive_repository import PervasiveRepository  # noqa: E402


PV_SERVER_DEFAULT = "192.168.1.168"
PV_DBQ_DEFAULT = r"C:\USERS\TI\DESKTOP"
PV_USER_DEFAULT = "Master"
PV_PASSWORD_DEFAULT = "COSTPP"
TEMPLATE_DEFAULT = r"C:\Users\TI\Documents\PRUEBAS LLSMSS\LDM507-473 GLOBAL SHOP.xlsx"


def build_repository() -> PervasiveRepository:
    server = os.getenv("SISTEMA_COSTOS_PERVASIVE_SERVER", PV_SERVER_DEFAULT).strip()
    dbq = os.getenv("SISTEMA_COSTOS_PERVASIVE_DBQ", PV_DBQ_DEFAULT).strip()
    user = os.getenv("SISTEMA_COSTOS_PERVASIVE_USER", PV_USER_DEFAULT).strip()
    pwd = os.getenv("SISTEMA_COSTOS_PERVASIVE_PASSWORD", PV_PASSWORD_DEFAULT).strip()
    repo = PervasiveRepository(server=server, dbq=dbq, user=user, password=pwd)
    repo.precargar_catalogo_materiales()
    return repo


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    raw = str(value).strip().lower()
    return raw in {"1", "true", "yes", "si", "on"}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class LlmApiHandler(BaseHTTPRequestHandler):
    runtime: LlmGlobalShopRuntime | None = None
    template_default: str | None = None
    precio_default_kg: float = 0.0
    fabricante_default: str = "INNOVAX"

    def log_message(self, fmt: str, *args: Any) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        message = fmt % args
        print(f"[{ts}] {self.client_address[0]} {message}")

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        raw_len = self.headers.get("Content-Length")
        if not raw_len:
            raise ValueError("Content-Length requerido")
        length = int(raw_len)
        if length <= 0:
            raise ValueError("Body vacio")
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON invalido: se esperaba objeto")
        return data

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "llm-solid-globalshop-api",
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
            return
        self._send_json(404, {"ok": False, "error": "Ruta no encontrada"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/api/v1/convert", "/convert"}:
            self._send_json(404, {"ok": False, "error": "Ruta no encontrada"})
            return
        if self.runtime is None:
            self._send_json(500, {"ok": False, "error": "Runtime no inicializado"})
            return

        try:
            payload = self._read_json()
            source_path = str(payload.get("source_path") or "").strip()
            output_path = str(payload.get("output_path") or "").strip()
            template_path = str(payload.get("template_path") or "").strip()
            include_rows = _to_bool(payload.get("include_rows"), default=False)
            rows_limit = int(payload.get("rows_limit") or 200)
            precio_default_kg = _to_float(payload.get("precio_default_kg"), default=self.precio_default_kg)
            fabricante_default = str(payload.get("fabricante_default") or self.fabricante_default).strip() or "INNOVAX"

            if not source_path:
                raise ValueError("source_path es obligatorio")
            source = Path(source_path)
            if not source.exists():
                raise FileNotFoundError(f"No existe source_path: {source}")
            if source.suffix.lower() not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
                raise ValueError("source_path debe ser Excel")

            if not output_path:
                output_path = str(source.with_name(f"{source.stem}_GLOBAL_SHOP.xlsx"))
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)

            template_final = template_path or self.template_default or ""
            if template_final and not Path(template_final).exists():
                raise FileNotFoundError(f"No existe template_path: {template_final}")

            result = self.runtime.convert(
                source_path=str(source),
                output_path=str(output),
                template_path=template_final or None,
                precio_default_kg=precio_default_kg,
                fabricante_default=fabricante_default,
            )
            response: dict[str, Any] = {
                "ok": True,
                "request": {
                    "source_path": str(source),
                    "output_path": str(output),
                    "template_path": template_final or None,
                    "precio_default_kg": precio_default_kg,
                    "fabricante_default": fabricante_default,
                },
                "result": self.runtime.summarize(result),
            }
            if include_rows:
                safe_limit = max(1, min(rows_limit, 5000))
                response["rows"] = [
                    self.runtime.row_to_payload(row)
                    for row in result.rows[:safe_limit]
                ]
                response["rows_truncated"] = len(result.rows) > safe_limit
            self._send_json(200, response)
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                500,
                {
                    "ok": False,
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=8),
                },
            )


def run_server(
    *,
    host: str,
    port: int,
    template_default: str | None,
    precio_default_kg: float,
    fabricante_default: str,
) -> None:
    repo = build_repository()
    runtime = LlmGlobalShopRuntime(repo)
    LlmApiHandler.runtime = runtime
    LlmApiHandler.template_default = template_default
    LlmApiHandler.precio_default_kg = precio_default_kg
    LlmApiHandler.fabricante_default = fabricante_default
    httpd = ThreadingHTTPServer((host, port), LlmApiHandler)
    print(f"[LLM API] escuchando en http://{host}:{port}")
    print("[LLM API] health: GET /health")
    print("[LLM API] convert: POST /api/v1/convert")
    httpd.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="API local para conversion LLM SOLID -> GLOBAL SHOP (PDM ready)."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--template-default", default=TEMPLATE_DEFAULT)
    parser.add_argument("--precio-default-kg", type=float, default=0.0)
    parser.add_argument("--fabricante-default", default="INNOVAX")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    template = args.template_default.strip()
    if template and not Path(template).exists():
        print(f"[LLM API] aviso: plantilla default no encontrada: {template}")
        template = ""
    run_server(
        host=args.host,
        port=args.port,
        template_default=template or None,
        precio_default_kg=args.precio_default_kg,
        fabricante_default=args.fabricante_default,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
