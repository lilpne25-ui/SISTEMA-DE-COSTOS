from dataclasses import dataclass
from typing import Optional


@dataclass
class ReglaCosto:
    id: Optional[int]
    material_nombre: str
    forma_nombre: str
    precio_kg: float
