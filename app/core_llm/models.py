from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

PriceResolver = Callable[[str, str, str, float], float | None]
DensityResolver = Callable[[str], float | None]


@dataclass(slots=True)
class LlmBomRow:
    item: str
    part_no: str
    description: str
    material: str
    shape: str
    qty: float
    stock_size_raw: str
    length_mm: float
    unit_weight_kg: float
    total_weight_kg: float
    price_kg_mxn: float
    unit_cost_mxn: float
    total_cost_mxn: float
    source_row: int
    status: str
    erp_row: list[object]
    is_stk: bool = False


@dataclass(slots=True)
class LlmBomResult:
    rows: list[LlmBomRow]
    source_sheet: str
    total_rows: int
    converted_rows: int
    warning_rows: int
