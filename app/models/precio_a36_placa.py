from dataclasses import dataclass
from typing import Optional


@dataclass
class PrecioA36Placa:
    id: Optional[int]
    espesor_min_pulgadas: float
    espesor_max_pulgadas: float
    precio_kg: float
    rango_label: str
