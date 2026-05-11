from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.models.catalogo_item import CatalogoItem
from app.models.precio_a36_placa import PrecioA36Placa
from app.models.regla_costo import ReglaCosto


@dataclass(slots=True)
class ImportPreviewRow:
    row_number: int
    status: str  # new | conflict | invalid
    message: str
    values: dict[str, str]


@dataclass(slots=True)
class ImportPreview:
    rows: list[ImportPreviewRow]
    valid_rows: list[dict[str, str]]

    @property
    def nuevas(self) -> int:
        return sum(1 for r in self.rows if r.status == "new")

    @property
    def conflictos(self) -> int:
        return sum(1 for r in self.rows if r.status == "conflict")

    @property
    def invalidas(self) -> int:
        return sum(1 for r in self.rows if r.status == "invalid")


def _write_csv(path: str, headers: list[str], rows: list[list[str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def _write_xlsx(path: str, sheet_name: str, headers: list[str], rows: list[list[str]]) -> None:
    from openpyxl import Workbook  # import lazy para evitar conflicto shiboken/Python 3.14
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)


def exportar_tarifas_a36_csv(path: str, filas: list[PrecioA36Placa]) -> None:
    headers = ["rango", "espesor_minimo", "espesor_maximo", "precio_kg"]
    rows = [
        [
            f.rango_label,
            f"{f.espesor_min_pulgadas}",
            f"{f.espesor_max_pulgadas}",
            f"{f.precio_kg}",
        ]
        for f in filas
    ]
    _write_csv(path, headers, rows)


def exportar_tarifas_a36_xlsx(path: str, filas: list[PrecioA36Placa]) -> None:
    headers = ["rango", "espesor_minimo", "espesor_maximo", "precio_kg"]
    rows = [
        [
            f.rango_label,
            float(f.espesor_min_pulgadas),
            float(f.espesor_max_pulgadas),
            float(f.precio_kg),
        ]
        for f in filas
    ]
    _write_xlsx(path, "TarifasA36", headers, rows)


def importar_tarifas_a36_csv(path: str, existentes: list[PrecioA36Placa]) -> ImportPreview:
    existing_ranges = {(e.espesor_min_pulgadas, e.espesor_max_pulgadas): e for e in existentes}
    rows: list[ImportPreviewRow] = []
    valid_rows: list[dict[str, str]] = []

    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, raw in enumerate(reader, start=2):
            try:
                esp_min = float((raw.get("espesor_minimo") or "").strip())
                esp_max = float((raw.get("espesor_maximo") or "").strip())
                precio = float((raw.get("precio_kg") or "").strip())
                rango = (raw.get("rango") or "").strip()
                if not rango:
                    rango = f"{esp_min} a {esp_max}"

                if esp_min <= 0 or esp_max <= 0 or esp_min > esp_max or precio <= 0:
                    raise ValueError("Valores fuera de rango")

                key = (esp_min, esp_max)
                existing = existing_ranges.get(key)
                if existing is not None:
                    if abs(existing.precio_kg - precio) <= 1e-9 and existing.rango_label == rango:
                        status, message = "conflict", "Duplicado exacto"
                    else:
                        status, message = "conflict", "Rango existente con datos distintos"
                else:
                    status, message = "new", "Listo para importar"
                    valid_rows.append(
                        {
                            "rango": rango,
                            "espesor_minimo": str(esp_min),
                            "espesor_maximo": str(esp_max),
                            "precio_kg": str(precio),
                        }
                    )

                rows.append(ImportPreviewRow(i, status, message, {k: str(v or "") for k, v in raw.items()}))
            except Exception as exc:
                rows.append(
                    ImportPreviewRow(i, "invalid", f"Fila inválida: {exc}", {k: str(v or "") for k, v in raw.items()})
                )

    return ImportPreview(rows=rows, valid_rows=valid_rows)


def exportar_reglas_costo_csv(path: str, filas: list[ReglaCosto]) -> None:
    headers = ["material", "forma", "precio_kg"]
    rows = [[r.material_nombre, r.forma_nombre, f"{r.precio_kg}"] for r in filas]
    _write_csv(path, headers, rows)


def exportar_reglas_costo_xlsx(path: str, filas: list[ReglaCosto]) -> None:
    headers = ["material", "forma", "precio_kg"]
    rows = [[r.material_nombre, r.forma_nombre, float(r.precio_kg)] for r in filas]
    _write_xlsx(path, "ReglasCosto", headers, rows)


def importar_reglas_costo_csv(path: str, existentes: list[ReglaCosto]) -> ImportPreview:
    existing = {(r.material_nombre.strip().upper(), r.forma_nombre.strip().upper()): r for r in existentes}
    rows: list[ImportPreviewRow] = []
    valid_rows: list[dict[str, str]] = []

    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, raw in enumerate(reader, start=2):
            try:
                material = (raw.get("material") or "").strip()
                forma = (raw.get("forma") or "").strip()
                precio = float((raw.get("precio_kg") or "").strip())
                if not material or precio <= 0:
                    raise ValueError("Material y precio son obligatorios")

                key = (material.upper(), forma.upper())
                existing_row = existing.get(key)
                if existing_row is not None:
                    if abs(existing_row.precio_kg - precio) <= 1e-9:
                        status, message = "conflict", "Duplicado exacto"
                    else:
                        status, message = "conflict", "Regla existente con precio distinto"
                else:
                    status, message = "new", "Listo para importar"
                    valid_rows.append({"material": material, "forma": forma, "precio_kg": str(precio)})

                rows.append(ImportPreviewRow(i, status, message, {k: str(v or "") for k, v in raw.items()}))
            except Exception as exc:
                rows.append(
                    ImportPreviewRow(i, "invalid", f"Fila inválida: {exc}", {k: str(v or "") for k, v in raw.items()})
                )

    return ImportPreview(rows=rows, valid_rows=valid_rows)


def exportar_catalogo_items_csv(path: str, filas: list[CatalogoItem]) -> None:
    headers = ["nombre", "prefijo_codigo", "tipo_base", "densidad_kg_m3"]
    rows = [
        [
            c.nombre,
            c.prefijo_codigo,
            (c.tipo_base or "").strip().upper(),
            "" if c.densidad_kg_m3 is None else f"{c.densidad_kg_m3}",
        ]
        for c in filas
    ]
    _write_csv(path, headers, rows)


def exportar_catalogo_items_xlsx(path: str, filas: list[CatalogoItem]) -> None:
    headers = ["nombre", "prefijo_codigo", "tipo_base", "densidad_kg_m3"]
    rows = [
        [
            c.nombre,
            c.prefijo_codigo,
            (c.tipo_base or "").strip().upper(),
            None if c.densidad_kg_m3 is None else float(c.densidad_kg_m3),
        ]
        for c in filas
    ]
    _write_xlsx(path, "Catalogo", headers, rows)


def importar_catalogo_items_csv(path: str, existentes: list[CatalogoItem]) -> ImportPreview:
    existing = {c.nombre.strip().upper(): c for c in existentes}
    rows: list[ImportPreviewRow] = []
    valid_rows: list[dict[str, str]] = []

    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, raw in enumerate(reader, start=2):
            try:
                nombre = (raw.get("nombre") or "").strip()
                prefijo = (raw.get("prefijo_codigo") or "").strip().upper()
                tipo_base = (raw.get("tipo_base") or "").strip().upper()
                densidad_txt = (raw.get("densidad_kg_m3") or "").strip()
                if not nombre or not prefijo:
                    raise ValueError("Nombre y prefijo son obligatorios")

                densidad: float | None = None
                if densidad_txt:
                    densidad = float(densidad_txt.replace(",", ""))
                    if densidad <= 0:
                        raise ValueError("La densidad debe ser mayor a 0")

                existing_row = existing.get(nombre.upper())
                if existing_row is not None:
                    dens_exist = existing_row.densidad_kg_m3
                    tipo_exist = (existing_row.tipo_base or "").strip().upper()
                    same_dens = (
                        (dens_exist is None and densidad is None)
                        or (dens_exist is not None and densidad is not None and abs(float(dens_exist) - float(densidad)) <= 1e-9)
                    )
                    if existing_row.prefijo_codigo.upper() == prefijo and same_dens and tipo_exist == tipo_base:
                        status, message = "conflict", "Duplicado exacto"
                    else:
                        status, message = "conflict", "Ítem existente con datos distintos"
                else:
                    status, message = "new", "Listo para importar"
                    valid_rows.append(
                        {
                            "nombre": nombre,
                            "prefijo_codigo": prefijo,
                            "tipo_base": tipo_base,
                            "densidad_kg_m3": "" if densidad is None else str(densidad),
                        }
                    )

                rows.append(ImportPreviewRow(i, status, message, {k: str(v or "") for k, v in raw.items()}))
            except Exception as exc:
                rows.append(
                    ImportPreviewRow(i, "invalid", f"Fila inválida: {exc}", {k: str(v or "") for k, v in raw.items()})
                )

    return ImportPreview(rows=rows, valid_rows=valid_rows)
