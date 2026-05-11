from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Costo:
    """
    Registro histórico de costo de un material.
    Guardamos todos los costos cargados para poder hacer trazabilidad
    (cuándo subió, cuál fue el proveedor, etc.).
    """
    id: Optional[int]
    material_id: int
    fecha: date
    precio_unitario: float       # en pesos mexicanos
    moneda: str = "MXN"
    unidad: str = "kg"
    proveedor: str = ""
    nota: str = ""
