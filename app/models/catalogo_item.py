from dataclasses import dataclass
from typing import Optional


@dataclass
class CatalogoItem:
    id: Optional[int]
    nombre: str
    prefijo_codigo: str
    tipo_base: str = ""
    densidad_kg_m3: Optional[float] = None
