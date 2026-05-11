from __future__ import annotations


def infer_shape(
    shape_hint: str,
    stock_raw: str,
    stock_nums: list[float],
    diameter: float | None,
    width: float | None,
    thickness: float | None,
) -> str:
    text = f"{shape_hint} {stock_raw}".upper()
    if any(k in text for k in ("TUBO", "HUECO", "PIPE", "TUBE")):
        return "TUBO"
    if any(k in text for k in ("REDON", "ROUND", "BARA REDONDA", "BARRA REDONDA")):
        return "REDONDO"
    if any(k in text for k in ("CUAD", "SQUARE", "BARA CUADRADA", "BARRA CUADRADA")):
        return "CUADRADO"
    if any(k in text for k in ("RECT", "PLACA", "PLATINA", "FLAT", "SOLERA")):
        return "RECTANGULAR"
    if any(k in text for k in ("DIA", "DIAM")):
        return "REDONDO"
    if diameter and diameter > 0 and (width is None or width <= 0) and (thickness is None or thickness <= 0):
        return "REDONDO"
    if thickness and thickness > 0:
        return "RECTANGULAR"
    if len(stock_nums) >= 2 and abs(stock_nums[0] - stock_nums[1]) <= 0.001 and (width is None or width > 0):
        return "CUADRADO"
    return "RECTANGULAR"


def apply_tolerance(value: float, tolerance_mm: float) -> float:
    if value <= 0:
        return 0.0
    return value + tolerance_mm


def infer_square_dims(stock_nums: list[float]) -> tuple[float, float]:
    if not stock_nums:
        return 0.0, 0.0
    if len(stock_nums) == 1:
        return stock_nums[0], 0.0
    if len(stock_nums) == 2:
        return stock_nums[0], stock_nums[1]
    side = min(stock_nums[0], stock_nums[1])
    length = max(stock_nums)
    return side, length


def infer_rect_dims(stock_nums: list[float]) -> tuple[float, float, float]:
    if not stock_nums:
        return 0.0, 0.0, 0.0
    if len(stock_nums) == 1:
        return stock_nums[0], 0.0, 0.0
    if len(stock_nums) == 2:
        return stock_nums[0], stock_nums[1], 0.0
    ordered = sorted(stock_nums[:3])
    espesor = ordered[0]
    largo = ordered[2]
    ancho = ordered[1]
    return ancho, espesor, largo


def infer_tube_dims(
    stock_nums: list[float],
    length_value: float | None,
    diameter_value: float | None,
    thickness_value: float | None,
) -> tuple[float, float, float]:
    od = 0.0
    id_ = 0.0
    length = 0.0

    if len(stock_nums) >= 3:
        od = max(stock_nums[0], stock_nums[1])
        id_ = min(stock_nums[0], stock_nums[1])
        length = stock_nums[2]
    elif len(stock_nums) == 2:
        od = stock_nums[0]
        id_ = stock_nums[1]
    elif len(stock_nums) == 1:
        od = stock_nums[0]

    if diameter_value and diameter_value > 0:
        od = diameter_value
    if thickness_value and thickness_value > 0 and od > 0:
        maybe_id = od - (2.0 * thickness_value)
        if maybe_id > 0:
            id_ = maybe_id
    if length_value and length_value > 0:
        length = length_value
    return od, id_, length


def build_stk_description(
    material_text: str,
    mapped: dict[str, str],
    shape: str,
    to_float_fn,
    *,
    overmaterial_mm: float = 0.0,
) -> str:
    material = (material_text or "").strip()
    length = to_float_fn(mapped.get("length")) or 0.0
    width = to_float_fn(mapped.get("width")) or 0.0
    thickness = to_float_fn(mapped.get("thickness")) or 0.0
    if thickness <= 0:
        thickness = to_float_fn(mapped.get("thickness_or_diameter")) or 0.0
    diameter = to_float_fn(mapped.get("diameter")) or thickness
    if overmaterial_mm > 0:
        if length > 0:
            length = apply_tolerance(length, overmaterial_mm)
        if width > 0:
            width = apply_tolerance(width, overmaterial_mm)
        if thickness > 0:
            thickness = apply_tolerance(thickness, overmaterial_mm)
        if diameter > 0:
            diameter = apply_tolerance(diameter, overmaterial_mm)
    shape_u = (shape or "").strip().upper()
    if shape_u in {"REDONDO", "TUBO"} and diameter > 0 and length > 0:
        return f"{material} DIA.{fmt_num(diameter)} x {fmt_num(length)}".strip()
    if shape_u == "CUADRADO" and width > 0 and length > 0:
        return f"{material} {fmt_num(width)} x {fmt_num(width)} x {fmt_num(length)}".strip()
    if thickness > 0 and width > 0 and length > 0:
        return f"{material} {fmt_num(thickness)} x {fmt_num(width)} x {fmt_num(length)}".strip()
    stock = (mapped.get("stock_size") or "").strip()
    return f"{material} {stock}".strip()


def fmt_num(value: float) -> str:
    return f"{float(value):.4f}".rstrip("0").rstrip(".")
