from __future__ import annotations

from math import gcd
from typing import Optional


def formatear_pulgadas(valor: Optional[float]) -> str:
    if valor is None:
        return ""

    pasos = int(round(valor * 8))
    aproximado = pasos / 8
    if abs(aproximado - valor) <= 0.001:
        entero = pasos // 8
        residuo = pasos % 8
        if residuo == 0:
            return f'{entero}"'
        divisor = gcd(residuo, 8)
        numerador = residuo // divisor
        denominador = 8 // divisor
        if entero == 0:
            return f'{numerador}/{denominador}"'
        return f'{entero} {numerador}/{denominador}"'

    texto = f"{valor:.3f}".rstrip("0").rstrip(".")
    return f'{texto}"'


def formatear_money(valor: float, moneda: str = "MXN", unidad: str = "kg") -> str:
    monto = f"{valor:,.2f}"
    return f"{moneda} {monto} /{unidad}"


def formatear_delta(nuevo: float, anterior: Optional[float]) -> tuple[str, str]:
    if anterior is None:
        return "N/A", "flat"

    delta = nuevo - anterior
    if abs(delta) <= 1e-9:
        return "0.00%", "flat"

    if abs(anterior) <= 1e-9:
        texto = f"{delta:+,.2f}"
    else:
        porcentaje = (delta / anterior) * 100
        texto = f"{porcentaje:+.2f}%"

    # "warning" cuando sube (cuesta más), "success" cuando baja (ahorro)
    return texto, "warning" if delta > 0 else "success"
