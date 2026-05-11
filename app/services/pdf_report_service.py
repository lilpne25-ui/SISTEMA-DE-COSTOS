"""
Generación de reportes PDF de costos por rango de fechas.

Usa reportlab para producir un PDF con encabezado de empresa, tabla de
costos y resumen estadístico.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import BytesIO
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass
class CostoReporte:
    """Fila plana para el reporte, combina material + costo."""
    codigo: str
    material: str
    forma: str
    fecha: date
    precio_unitario: float
    moneda: str
    unidad: str
    proveedor: str


@dataclass
class EmpresaInfo:
    """Datos del encabezado de empresa."""
    nombre: str = "InnovaX Logística"
    subtitulo: str = "Sistema de Gestión de Costos de Acero"
    direccion: str = ""
    telefono: str = ""


def generar_reporte_costos_pdf(
    filas: List[CostoReporte],
    fecha_inicio: date,
    fecha_fin: date,
    empresa: Optional[EmpresaInfo] = None,
    filtro_material: str = "Todos",
) -> bytes:
    """Genera un PDF con el reporte de costos y retorna los bytes."""
    if empresa is None:
        empresa = EmpresaInfo()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        title=f"Reporte de Costos {fecha_inicio} a {fecha_fin}",
        author=empresa.nombre,
    )

    styles = getSampleStyleSheet()

    style_empresa = ParagraphStyle(
        "Empresa",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#111827"),
        spaceAfter=2 * mm,
    )
    style_subtitulo = ParagraphStyle(
        "Subtitulo",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=4 * mm,
    )
    style_titulo_reporte = ParagraphStyle(
        "TituloReporte",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#111827"),
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
    )
    style_info = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=2 * mm,
    )
    style_resumen_title = ParagraphStyle(
        "ResumenTitle",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=colors.HexColor("#111827"),
        spaceBefore=8 * mm,
        spaceAfter=3 * mm,
    )

    elements: list = []

    # ---- Encabezado empresa -------------------------------------------
    elements.append(Paragraph(empresa.nombre, style_empresa))
    elements.append(Paragraph(empresa.subtitulo, style_subtitulo))

    if empresa.direccion:
        elements.append(Paragraph(empresa.direccion, style_info))
    if empresa.telefono:
        elements.append(Paragraph(f"Tel: {empresa.telefono}", style_info))

    elements.append(Spacer(1, 4 * mm))

    # ---- Título del reporte -------------------------------------------
    elements.append(
        Paragraph(
            f"Reporte de Costos — {fecha_inicio:%d/%m/%Y} al {fecha_fin:%d/%m/%Y}",
            style_titulo_reporte,
        )
    )

    filtro_txt = f"Filtro: {filtro_material}" if filtro_material != "Todos" else "Todos los materiales"
    elements.append(
        Paragraph(
            f"{filtro_txt} · {len(filas)} registro{'s' if len(filas) != 1 else ''} · "
            f"Generado: {date.today():%d/%m/%Y}",
            style_info,
        )
    )
    elements.append(Spacer(1, 4 * mm))

    # ---- Tabla de costos ----------------------------------------------
    header = ["Código", "Material", "Forma", "Fecha", "Precio", "Moneda", "Unidad", "Proveedor"]

    data = [header]
    for f in filas:
        data.append([
            f.codigo,
            f.material,
            f.forma,
            f"{f.fecha:%d/%m/%Y}",
            f"{f.precio_unitario:,.4f}",
            f.moneda,
            f.unidad,
            f.proveedor or "—",
        ])

    col_widths = [
        2.4 * cm,   # Código
        2.8 * cm,   # Material
        2.2 * cm,   # Forma
        2.2 * cm,   # Fecha
        2.6 * cm,   # Precio
        1.4 * cm,   # Moneda
        1.2 * cm,   # Unidad
        3.2 * cm,   # Proveedor
    ]

    table = Table(data, colWidths=col_widths, repeatRows=1)

    accent = colors.HexColor("#2563EB")
    accent_soft = colors.HexColor("#DBEAFE")
    border_color = colors.HexColor("#D9DEE6")
    text_dark = colors.HexColor("#111827")
    text_muted = colors.HexColor("#6B7280")
    bg_alt = colors.HexColor("#F7F8FA")

    table_style = TableStyle([
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),

        # Cuerpo
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), text_dark),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),

        # Bordes
        ("GRID", (0, 0), (-1, -1), 0.5, border_color),
        ("LINEBELOW", (0, 0), (-1, 0), 1, accent),

        # Alineación precio a la derecha
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),

        # Filas alternas
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt]),

        # Valign
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    table.setStyle(table_style)
    elements.append(table)

    # ---- Resumen estadístico ------------------------------------------
    if filas:
        precios = [f.precio_unitario for f in filas]
        precio_min = min(precios)
        precio_max = max(precios)
        precio_prom = sum(precios) / len(precios)
        materiales_unicos = len({f.codigo for f in filas})
        proveedores_unicos = len({f.proveedor for f in filas if f.proveedor})

        elements.append(Paragraph("Resumen", style_resumen_title))

        resumen_data = [
            ["Concepto", "Valor"],
            ["Total de registros", str(len(filas))],
            ["Materiales únicos", str(materiales_unicos)],
            ["Proveedores únicos", str(proveedores_unicos)],
            ["Precio mínimo", f"${precio_min:,.4f}"],
            ["Precio máximo", f"${precio_max:,.4f}"],
            ["Precio promedio", f"${precio_prom:,.4f}"],
        ]

        resumen_table = Table(resumen_data, colWidths=[5 * cm, 4 * cm])
        resumen_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), accent_soft),
            ("TEXTCOLOR", (0, 0), (-1, 0), accent),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("FONTNAME", (1, 1), (1, -1), "Helvetica"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_alt]),
        ]))
        elements.append(resumen_table)

    # ---- Pie de página implícito vía onPage ----------------------------
    def _pie_pagina(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#9CA3AF"))
        canvas.drawString(
            1.8 * cm,
            1 * cm,
            f"{empresa.nombre} — Reporte de costos generado el {date.today():%d/%m/%Y}",
        )
        canvas.drawRightString(
            LETTER[0] - 1.8 * cm,
            1 * cm,
            f"Página {doc_obj.page}",
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    return buffer.getvalue()
