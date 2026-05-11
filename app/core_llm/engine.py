from __future__ import annotations

import math

from .costing import (
    apply_tolerance,
    infer_rect_dims,
    infer_shape,
    infer_square_dims,
    infer_tube_dims,
)
from .exporter import ERP_HEADERS, write_output_xlsx
from .mapping import (
    build_erp_row,
    build_stk_row_from_base,
    is_cost_allowed_manufacturer,
    resolve_fabricante,
)
from .models import DensityResolver, LlmBomResult, LlmBomRow, PriceResolver
from .normalization import extract_numbers, infer_parent_base, read_source_rows, to_float

STK_OVERMATERIAL_MM = 10.0
ERP_COST_INDEX = ERP_HEADERS.index("Cost")


def convertir_solid_a_global_shop(
    source_path: str,
    output_path: str | None,
    *,
    price_resolver: PriceResolver | None = None,
    density_resolver: DensityResolver | None = None,
    precio_default_kg: float = 0.0,
    template_path: str | None = None,
    fabricante_default: str = "INNOVAX",
) -> LlmBomResult:
    rows, sheet_name = read_source_rows(source_path)
    parent_fallback = infer_parent_base(rows, source_path)
    converted: list[LlmBomRow] = []
    warnings = 0
    output_sequence = 1

    for row_data in rows:
        mapped = row_data["mapped"]
        source_row = int(row_data["source_row"])
        row = _convert_row(
            mapped,
            source_row,
            sequence=output_sequence,
            parent_fallback=parent_fallback,
            price_resolver=price_resolver,
            density_resolver=density_resolver,
            precio_default_kg=precio_default_kg,
            fabricante_default=fabricante_default,
        )

        stk_metrics = _calculate_stk_metrics(
            mapped=mapped,
            material=row.material,
            material_label=(mapped.get("material", "") or mapped.get("thickness_or_diameter", "")),
            shape=row.shape,
            shape_hint=mapped.get("shape", "") or mapped.get("part_type", ""),
            density_resolver=density_resolver,
            price_resolver=price_resolver,
            precio_default_kg=precio_default_kg,
        )

        stk_row = None
        if stk_metrics is not None:
            stk_row = build_stk_row_from_base(
                base=row,
                mapped=mapped,
                source_row=source_row,
                sequence=output_sequence + 1,
                erp_headers=ERP_HEADERS,
                overmaterial_mm=STK_OVERMATERIAL_MM,
                unit_weight_kg=stk_metrics["unit_weight_kg"],
                total_weight_kg=stk_metrics["total_weight_kg"],
                price_kg_mxn=stk_metrics["price_kg_mxn"],
                unit_cost_mxn=stk_metrics["unit_cost_mxn"],
                total_cost_mxn=stk_metrics["total_cost_mxn"],
                length_mm=stk_metrics["length_mm"],
                status=stk_metrics["status"],
            )
            if stk_row is not None:
                _zero_base_row_cost(row)

        if row.status != "OK":
            warnings += 1
        converted.append(row)
        output_sequence += 1

        if stk_row is not None:
            if stk_row.status != "OK":
                warnings += 1
            converted.append(stk_row)
            output_sequence += 1

    result = LlmBomResult(
        rows=converted,
        source_sheet=sheet_name,
        total_rows=len(rows),
        converted_rows=sum(1 for r in converted if not r.is_stk and r.status == "OK"),
        warning_rows=warnings,
    )

    if output_path:
        write_output_xlsx(output_path, result.rows, template_path=template_path)
    return result


def _convert_row(
    mapped: dict[str, str],
    source_row: int,
    *,
    sequence: int,
    parent_fallback: str,
    price_resolver: PriceResolver | None,
    density_resolver: DensityResolver | None,
    precio_default_kg: float,
    fabricante_default: str,
) -> LlmBomRow:
    item = mapped.get("item") or str(source_row)
    part_no = mapped.get("part_no", "")
    description = mapped.get("description", "")
    material = mapped.get("material", "")
    material_label = mapped.get("material", "") or mapped.get("thickness_or_diameter", "")
    qty = to_float(mapped.get("qty")) or 1.0
    stock_raw = mapped.get("stock_size", "")
    length_value = to_float(mapped.get("length"))
    diameter = to_float(mapped.get("diameter"))
    width = to_float(mapped.get("width"))
    thickness = to_float(mapped.get("thickness"))
    if (thickness is None or thickness <= 0) and to_float(mapped.get("thickness_or_diameter")):
        thickness = to_float(mapped.get("thickness_or_diameter"))
    shape_hint = mapped.get("shape", "") or mapped.get("part_type", "")
    weight_input = to_float(mapped.get("weight"))
    level_value = int(to_float(mapped.get("level")) or 0)
    fabricante = resolve_fabricante(mapped, fabricante_default)
    cost_allowed = is_cost_allowed_manufacturer(fabricante)

    stock_nums = extract_numbers(stock_raw)
    shape = infer_shape(shape_hint, stock_raw, stock_nums, diameter, width, thickness)
    status_messages: list[str] = []
    length_mm = 0.0
    unit_weight = 0.0
    total_weight = 0.0
    price_kg = 0.0
    unit_cost = 0.0
    total_cost = 0.0

    if cost_allowed and level_value > 0:
        densidad = density_resolver(material) if density_resolver is not None else None
        if densidad is None or densidad <= 0:
            densidad = density_resolver(material_label) if density_resolver is not None else None
        if densidad is None or densidad <= 0:
            densidad = 0.0
            status_messages.append("Sin densidad para material")

        if shape == "REDONDO":
            d_nom = diameter or (stock_nums[0] if stock_nums else 0.0)
            l_nom = length_value or (stock_nums[1] if len(stock_nums) >= 2 else 0.0)
            d_eff = apply_tolerance(d_nom, 10.0)
            length_mm = apply_tolerance(l_nom, 20.0)
            if d_eff > 0 and length_mm > 0 and densidad > 0:
                unit_weight = ((math.pi * (d_eff**2) * length_mm * densidad) / 4_000_000_000.0)
            else:
                status_messages.append("Falta diametro o largo")
        elif shape == "CUADRADO":
            side_nom, l_nom = infer_square_dims(stock_nums)
            if width and width > 0:
                side_nom = width
            if length_value and length_value > 0:
                l_nom = length_value
            side_eff = apply_tolerance(side_nom, 10.0)
            length_mm = apply_tolerance(l_nom, 10.0)
            if side_eff > 0 and length_mm > 0 and densidad > 0:
                unit_weight = ((side_eff * side_eff * length_mm * densidad) / 1_000_000_000.0)
            else:
                status_messages.append("Falta lado o largo")
        elif shape == "TUBO":
            od_nom, id_nom, l_nom = infer_tube_dims(stock_nums, length_value, diameter, thickness)
            od_eff = apply_tolerance(od_nom, 10.0)
            id_eff = id_nom
            length_mm = apply_tolerance(l_nom, 20.0)
            if od_eff > 0 and id_eff >= 0 and od_eff > id_eff and length_mm > 0 and densidad > 0:
                unit_weight = ((math.pi * ((od_eff**2) - (id_eff**2)) * length_mm * densidad) / 4_000_000_000.0)
            else:
                status_messages.append("Falta OD/ID/largo para tubo")
        else:
            ancho_nom, espesor_nom, l_nom = infer_rect_dims(stock_nums)
            if width and width > 0:
                ancho_nom = width
            if thickness and thickness > 0:
                espesor_nom = thickness
            if length_value and length_value > 0:
                l_nom = length_value
            ancho_eff = apply_tolerance(ancho_nom, 10.0)
            espesor_eff = apply_tolerance(espesor_nom, 10.0)
            length_mm = apply_tolerance(l_nom, 10.0)
            if ancho_eff > 0 and espesor_eff > 0 and length_mm > 0 and densidad > 0:
                unit_weight = ((ancho_eff * espesor_eff * length_mm * densidad) / 1_000_000_000.0)
            else:
                status_messages.append("Falta ancho, espesor o largo")

        total_weight = unit_weight * qty
        if price_resolver is not None:
            thickness_ref_mm = thickness or (stock_nums[1] if shape in ("RECTANGULAR", "CUADRADO") and len(stock_nums) >= 2 else 0.0)
            price_kg = price_resolver(material, shape, shape_hint, thickness_ref_mm) or 0.0
            if price_kg <= 0 and material_label and material_label != material:
                price_kg = price_resolver(material_label, shape, shape_hint, thickness_ref_mm) or 0.0
        if price_kg <= 0:
            price_kg = max(precio_default_kg, 0.0)
        if price_kg <= 0:
            status_messages.append("Sin precio configurado para material/forma")

        unit_cost = unit_weight * price_kg
        total_cost = unit_cost * qty

    status = "OK" if not status_messages else f"WARN: {'; '.join(status_messages)}"
    erp_row = build_erp_row(
        mapped=mapped,
        part_no=part_no,
        description=description,
        qty=qty,
        unit_cost=unit_cost,
        level=level_value,
        material_label=material_label,
        computed_weight_kg=total_weight,
        input_weight=weight_input,
        length_mm=length_value,
        width_mm=width,
        thickness_mm=thickness,
        parent_fallback=parent_fallback,
        sequence=sequence,
        fabricante=fabricante,
        erp_headers=ERP_HEADERS,
    )

    return LlmBomRow(
        item=str(item),
        part_no=part_no,
        description=description,
        material=material,
        shape=shape,
        qty=qty,
        stock_size_raw=stock_raw,
        length_mm=length_mm,
        unit_weight_kg=unit_weight,
        total_weight_kg=total_weight,
        price_kg_mxn=price_kg,
        unit_cost_mxn=unit_cost,
        total_cost_mxn=total_cost,
        source_row=source_row,
        status=status,
        erp_row=erp_row,
        is_stk=False,
    )


def _zero_base_row_cost(row: LlmBomRow) -> None:
    row.price_kg_mxn = 0.0
    row.unit_cost_mxn = 0.0
    row.total_cost_mxn = 0.0
    if 0 <= ERP_COST_INDEX < len(row.erp_row):
        row.erp_row[ERP_COST_INDEX] = 0.0


def _calculate_stk_metrics(
    *,
    mapped: dict[str, str],
    material: str,
    material_label: str,
    shape: str,
    shape_hint: str,
    density_resolver: DensityResolver | None,
    price_resolver: PriceResolver | None,
    precio_default_kg: float,
) -> dict[str, float | str] | None:
    fabricante = resolve_fabricante(mapped, "")
    if not is_cost_allowed_manufacturer(fabricante):
        return None

    level_value = int(to_float(mapped.get("level")) or 0)
    if level_value <= 0:
        return None

    shape_u = (shape or "").strip().upper()
    if shape_u not in {"REDONDO", "CUADRADO", "RECTANGULAR", "TUBO"}:
        return None

    if not (
        mapped.get("stock_size", "")
        or mapped.get("length", "")
        or mapped.get("diameter", "")
        or mapped.get("thickness", "")
        or mapped.get("width", "")
    ):
        return None

    stock_raw = mapped.get("stock_size", "")
    stock_nums = extract_numbers(stock_raw)
    length_value = to_float(mapped.get("length"))
    diameter = to_float(mapped.get("diameter"))
    width = to_float(mapped.get("width"))
    thickness = to_float(mapped.get("thickness"))
    if (thickness is None or thickness <= 0) and to_float(mapped.get("thickness_or_diameter")):
        thickness = to_float(mapped.get("thickness_or_diameter"))

    status_messages: list[str] = []
    density = _resolve_density(material, material_label, density_resolver)
    if density <= 0:
        status_messages.append("Sin densidad para material")

    unit_weight = 0.0
    length_mm = 0.0
    thickness_ref_mm = thickness or (stock_nums[1] if shape_u in ("RECTANGULAR", "CUADRADO") and len(stock_nums) >= 2 else 0.0)

    if shape_u == "REDONDO":
        d_nom = diameter or (stock_nums[0] if stock_nums else 0.0)
        l_nom = length_value or (stock_nums[1] if len(stock_nums) >= 2 else 0.0)
        d_eff = apply_tolerance(d_nom, STK_OVERMATERIAL_MM)
        length_mm = apply_tolerance(l_nom, STK_OVERMATERIAL_MM)
        if d_eff > 0 and length_mm > 0 and density > 0:
            unit_weight = (math.pi * (d_eff**2) * length_mm * density) / 4_000_000_000.0
        else:
            status_messages.append("Falta diametro o largo")
    elif shape_u == "CUADRADO":
        side_nom, l_nom = infer_square_dims(stock_nums)
        if width and width > 0:
            side_nom = width
        if length_value and length_value > 0:
            l_nom = length_value
        side_eff = apply_tolerance(side_nom, STK_OVERMATERIAL_MM)
        length_mm = apply_tolerance(l_nom, STK_OVERMATERIAL_MM)
        if side_eff > 0 and length_mm > 0 and density > 0:
            unit_weight = (side_eff * side_eff * length_mm * density) / 1_000_000_000.0
        else:
            status_messages.append("Falta lado o largo")
    elif shape_u == "TUBO":
        od_nom, id_nom, l_nom = infer_tube_dims(stock_nums, length_value, diameter, thickness)
        od_eff = apply_tolerance(od_nom, STK_OVERMATERIAL_MM)
        id_eff = apply_tolerance(id_nom, STK_OVERMATERIAL_MM) if id_nom > 0 else 0.0
        length_mm = apply_tolerance(l_nom, STK_OVERMATERIAL_MM)
        if od_eff > 0 and id_eff >= 0 and od_eff > id_eff and length_mm > 0 and density > 0:
            unit_weight = (math.pi * ((od_eff**2) - (id_eff**2)) * length_mm * density) / 4_000_000_000.0
        else:
            status_messages.append("Falta OD/ID/largo para tubo")
    else:
        ancho_nom, espesor_nom, l_nom = infer_rect_dims(stock_nums)
        if width and width > 0:
            ancho_nom = width
        if thickness and thickness > 0:
            espesor_nom = thickness
        if length_value and length_value > 0:
            l_nom = length_value
        ancho_eff = apply_tolerance(ancho_nom, STK_OVERMATERIAL_MM)
        espesor_eff = apply_tolerance(espesor_nom, STK_OVERMATERIAL_MM)
        length_mm = apply_tolerance(l_nom, STK_OVERMATERIAL_MM)
        if ancho_eff > 0 and espesor_eff > 0 and length_mm > 0 and density > 0:
            unit_weight = (ancho_eff * espesor_eff * length_mm * density) / 1_000_000_000.0
        else:
            status_messages.append("Falta ancho, espesor o largo")

    price_kg = _resolve_price(
        material=material,
        material_label=material_label,
        shape=shape_u,
        shape_hint=shape_hint,
        thickness_ref_mm=thickness_ref_mm,
        price_resolver=price_resolver,
        precio_default_kg=precio_default_kg,
    )
    if price_kg <= 0:
        status_messages.append("Sin precio configurado para material/forma")

    total_weight = unit_weight  # Qty fija=1 en renglón STK
    unit_cost = unit_weight * price_kg
    total_cost = unit_cost

    status = "OK" if not status_messages else f"WARN: {'; '.join(status_messages)}"
    return {
        "length_mm": length_mm,
        "unit_weight_kg": unit_weight,
        "total_weight_kg": total_weight,
        "price_kg_mxn": price_kg,
        "unit_cost_mxn": unit_cost,
        "total_cost_mxn": total_cost,
        "status": status,
    }


def _resolve_density(
    material: str,
    material_label: str,
    density_resolver: DensityResolver | None,
) -> float:
    if density_resolver is None:
        return 0.0
    density = density_resolver(material) or 0.0
    if density <= 0 and material_label and material_label != material:
        density = density_resolver(material_label) or 0.0
    return float(density or 0.0)


def _resolve_price(
    *,
    material: str,
    material_label: str,
    shape: str,
    shape_hint: str,
    thickness_ref_mm: float,
    price_resolver: PriceResolver | None,
    precio_default_kg: float,
) -> float:
    price_kg = 0.0
    if price_resolver is not None:
        price_kg = price_resolver(material, shape, shape_hint, thickness_ref_mm) or 0.0
        if price_kg <= 0 and material_label and material_label != material:
            price_kg = price_resolver(material_label, shape, shape_hint, thickness_ref_mm) or 0.0
    if price_kg <= 0:
        price_kg = max(float(precio_default_kg or 0.0), 0.0)
    return float(price_kg)
