from __future__ import annotations

import re
import unicodedata

from .costing import build_stk_description
from .models import LlmBomRow
from .normalization import to_float

COST_ALLOWED_MANUFACTURERS = {"INNOVAX", "ZP"}
COST_ALLOWED_MANUFACTURERS_NORMALIZED = {re.sub(r"[^A-Za-z0-9]+", "", x).upper() for x in COST_ALLOWED_MANUFACTURERS}
HI_MANUFACTURERS = {"VEKTEK", "KOSMEK"}
HI_MANUFACTURERS_NORMALIZED = {re.sub(r"[^A-Za-z0-9]+", "", x).upper() for x in HI_MANUFACTURERS}


def resolve_fabricante(mapped: dict[str, str], fabricante_default: str) -> str:
    fabricante = mapped.get("fabricante", "") or mapped.get("fabricado_por", "") or fabricante_default
    return (fabricante or "").strip()


def is_cost_allowed_manufacturer(fabricante: str) -> bool:
    return normalize_token(fabricante) in COST_ALLOWED_MANUFACTURERS_NORMALIZED


def is_hi_manufacturer(fabricante: str) -> bool:
    return normalize_token(fabricante) in HI_MANUFACTURERS_NORMALIZED


def infer_source_value(*, mapped_source: str, part_no: str, fabricante: str, level: int) -> str:
    raw = (mapped_source or "").strip().upper()
    if raw:
        return raw
    if level <= 0:
        return "F"
    if (part_no or "").strip().upper().endswith("-STK"):
        return "J"
    if is_cost_allowed_manufacturer(fabricante):
        return "F"
    return "J"


def infer_productline_value(
    *,
    mapped_productline: str,
    part_no: str,
    fabricante: str,
    source_val: str,
    level: int,
) -> str:
    raw = (mapped_productline or "").strip().upper()
    if raw:
        return raw
    if level <= 0:
        return "PT"
    if (part_no or "").strip().upper().endswith("-STK"):
        return "AC"
    if is_hi_manufacturer(fabricante):
        return "HI"
    if is_cost_allowed_manufacturer(fabricante):
        return "MP"
    src = (source_val or "").strip().upper()
    if src == "P":
        return "AC"
    if src == "M":
        return "PT"
    if src == "F":
        return "MP"
    return "SU"


def build_erp_row(
    *,
    mapped: dict[str, str],
    part_no: str,
    description: str,
    qty: float,
    unit_cost: float,
    level: int,
    material_label: str,
    computed_weight_kg: float,
    input_weight: float | None,
    length_mm: float | None,
    width_mm: float | None,
    thickness_mm: float | None,
    parent_fallback: str,
    sequence: int,
    fabricante: str,
    erp_headers: list[str],
) -> list[object]:
    memo2 = mapped.get("memo2", "").strip()
    source_val = infer_source_value(
        mapped_source=mapped.get("source", ""),
        part_no=part_no,
        fabricante=fabricante,
        level=level,
    )
    productline = infer_productline_value(
        mapped_productline=mapped.get("productline", ""),
        part_no=part_no,
        fabricante=fabricante,
        source_val=source_val,
        level=level,
    )
    sequence_value = to_float(mapped.get("sequence"))
    if sequence_value is None:
        sequence_value = max(0, sequence - 1)

    row_map: dict[str, object] = {
        "PartNo": part_no or f"SIN-PN-{sequence:04d}",
        "Revision": mapped.get("revision", ""),
        "Description": description,
        "AltDescription1": mapped.get("alt_description_1", ""),
        "AltDescription2": mapped.get("alt_description_2", ""),
        "DescExtra": mapped.get("desc_extra", ""),
        "Quantity": qty,
        "IssueUM": mapped.get("issue_um", "") or "PZ",
        "ConsumptionConv": to_float(mapped.get("consumption_conv")) or 0,
        "UM": mapped.get("um", "") or "PZ",
        "Cost": round(unit_cost, 6),
        "Source": source_val,
        "Drawing": mapped.get("drawing", ""),
        "Leadtime": mapped.get("leadtime", ""),
        "Level": level,
        "Location": mapped.get("location", ""),
        "Memo1": mapped.get("memo1", ""),
        "Memo2": memo2,
        "Parent": mapped.get("parent", "") or parent_fallback,
        "Productline": productline,
        "Sequence": int(sequence_value),
        "ShotCode": mapped.get("shotcode", ""),
        "Tag": mapped.get("tag", ""),
        "Category": mapped.get("category", "") or "Blank",
        "fabricante": fabricante,
        "filepat": mapped.get("path", ""),
        "Material": material_label,
        "Peso": input_weight if input_weight is not None else (round(computed_weight_kg, 6) if computed_weight_kg > 0 else None),
        "largo": length_mm if length_mm is not None else None,
        "ancho": width_mm if width_mm is not None else None,
        "espesor": thickness_mm if thickness_mm is not None else None,
        "tratamiento": mapped.get("thermal_treatment", ""),
    }
    return [row_map.get(h, "") for h in erp_headers]


def build_stk_row_from_base(
    *,
    base: LlmBomRow,
    mapped: dict[str, str],
    source_row: int,
    sequence: int,
    erp_headers: list[str],
    overmaterial_mm: float = 10.0,
    unit_weight_kg: float = 0.0,
    total_weight_kg: float = 0.0,
    price_kg_mxn: float = 0.0,
    unit_cost_mxn: float = 0.0,
    total_cost_mxn: float = 0.0,
    length_mm: float | None = None,
    status: str = "OK",
) -> LlmBomRow | None:
    fabricante = resolve_fabricante(mapped, "")
    if not is_cost_allowed_manufacturer(fabricante):
        return None
    if not base.part_no or base.part_no.upper().endswith("-STK"):
        return None
    if base.shape not in {"REDONDO", "CUADRADO", "RECTANGULAR", "TUBO"}:
        return None
    if not (mapped.get("stock_size", "") or mapped.get("length", "") or mapped.get("diameter", "") or mapped.get("thickness", "") or mapped.get("width", "")):
        return None
    level = int(to_float(mapped.get("level")) or 0)
    if level <= 0:
        return None

    stk_part_no = f"{base.part_no}-STK"
    stk_desc = build_stk_description(
        base.material,
        mapped,
        base.shape,
        to_float,
        overmaterial_mm=overmaterial_mm,
    )
    memo2 = (mapped.get("memo2") or "").strip()
    sequence_value = int(max(0, sequence - 1))
    row_map: dict[str, object] = {
        "PartNo": stk_part_no,
        "Revision": mapped.get("revision", ""),
        "Description": stk_desc,
        "AltDescription1": "",
        "AltDescription2": "",
        "DescExtra": "",
        "Quantity": 1,
        "IssueUM": mapped.get("issue_um", "") or "PZ",
        "ConsumptionConv": to_float(mapped.get("consumption_conv")) or 0,
        "UM": mapped.get("um", "") or "PZ",
        "Cost": round(float(unit_cost_mxn or 0.0), 6),
        "Source": "J",
        "Drawing": "",
        "Leadtime": mapped.get("leadtime", ""),
        "Level": level + 1,
        "Location": mapped.get("location", ""),
        "Memo1": "",
        "Memo2": memo2,
        "Parent": base.part_no,
        "Productline": "AC",
        "Sequence": sequence_value,
        "ShotCode": mapped.get("shotcode", ""),
        "Tag": mapped.get("tag", ""),
        "Category": mapped.get("category", "") or "Blank",
        "fabricante": fabricante,
        "filepat": "",
        "Material": None,
        "Peso": None,
        "largo": None,
        "ancho": None,
        "espesor": None,
        "tratamiento": "",
    }
    erp_row = [row_map.get(h, "") for h in erp_headers]
    return LlmBomRow(
        item=f"{base.item}-STK",
        part_no=stk_part_no,
        description=stk_desc,
        material=base.material,
        shape=base.shape,
        qty=1.0,
        stock_size_raw=base.stock_size_raw,
        length_mm=float(length_mm) if length_mm is not None else base.length_mm,
        unit_weight_kg=float(unit_weight_kg or 0.0),
        total_weight_kg=float(total_weight_kg or 0.0),
        price_kg_mxn=float(price_kg_mxn or 0.0),
        unit_cost_mxn=float(unit_cost_mxn or 0.0),
        total_cost_mxn=float(total_cost_mxn or 0.0),
        source_row=source_row,
        status=status,
        erp_row=erp_row,
        is_stk=True,
    )


def normalize_token(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value or "")
    ascii_only = "".join(ch for ch in folded if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", ascii_only).upper()
    return cleaned
