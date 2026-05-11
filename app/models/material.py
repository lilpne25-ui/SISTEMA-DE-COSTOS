from dataclasses import dataclass
from typing import Optional


@dataclass
class Material:
    """
    Registro principal de un material manejado por logistica.
    Conserva campos legacy para compatibilidad, pero el flujo actual
    prioriza material, forma y costos.
    """

    id: Optional[int]
    codigo: str
    nombre: str          # grado/aleación: A36, S7, 1045, AL 6061
    tipo: str            # categoría base: ACERO, ALUMINIO
    forma: str = ""
    espesor_pulgadas: Optional[float] = None
    descripcion: str = ""
    norma: str = ""
    unidad_medida: str = "kg"
    densidad: Optional[float] = None
    dureza: str = ""
    resistencia_tensil: Optional[float] = None
    proveedor: str = ""
    observaciones: str = ""
    ficha_tecnica_pdf: str = ""
    precio_actual: Optional[float] = None  # espejo de historial_costos más reciente
