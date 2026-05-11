from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib import request


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with request.urlopen(req, timeout=1200) as resp:  # noqa: S310
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Cliente CLI para API LLM SOLID -> GLOBAL SHOP (usable desde PDM Task)."
    )
    p.add_argument("--source", required=True, help="Ruta Excel fuente de SOLIDWORKS")
    p.add_argument("--output", default="", help="Ruta Excel salida GLOBAL SHOP (opcional)")
    p.add_argument("--api-url", default="http://127.0.0.1:8787/api/v1/convert")
    p.add_argument("--template", default="")
    p.add_argument("--precio-default-kg", type=float, default=0.0)
    p.add_argument("--fabricante-default", default="INNOVAX")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    if not args.output:
        output = source.with_name(f"{source.stem}_GLOBAL_SHOP.xlsx")
    else:
        output = Path(args.output)
    payload = {
        "source_path": str(source),
        "output_path": str(output),
        "template_path": args.template or "",
        "precio_default_kg": args.precio_default_kg,
        "fabricante_default": args.fabricante_default,
    }
    try:
        response = post_json(args.api_url, payload)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] No se pudo llamar API: {exc}")
        return 2

    if not response.get("ok"):
        print("[ERROR] API devolvio error")
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 1

    result = response.get("result", {})
    print("[OK] GLOBAL SHOP generado")
    print(f"source: {payload['source_path']}")
    print(f"output: {payload['output_path']}")
    print(f"input_rows: {result.get('input_rows')}")
    print(f"output_rows: {result.get('output_rows')}")
    print(f"warnings: {result.get('warning_rows')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
