# Fase 1 - Refactor a Core Compartido (Evidencia)

- Fecha: 2026-04-29 13:14:22
- Objetivo: mover logica LLM a `app/core_llm` y dejar `llm_bom_service.py` como facade, sin cambiar salida.

## Archivos creados
- `E:\SISTEMA DE COSTOS\app\core_llm\__init__.py`
- `E:\SISTEMA DE COSTOS\app\core_llm\models.py`
- `E:\SISTEMA DE COSTOS\app\core_llm\normalization.py`
- `E:\SISTEMA DE COSTOS\app\core_llm\costing.py`
- `E:\SISTEMA DE COSTOS\app\core_llm\mapping.py`
- `E:\SISTEMA DE COSTOS\app\core_llm\exporter.py`
- `E:\SISTEMA DE COSTOS\app\core_llm\engine.py`

## Archivos modificados
- `E:\SISTEMA DE COSTOS\app\services\llm_bom_service.py` (ahora facade)

## Backups de rollback
- `E:\SISTEMA DE COSTOS\app\services\llm_bom_service.py.bak_fase1`
- `E:\SISTEMA DE COSTOS\app\ui\windows\config_window.py.bak_fase1`

## Validacion tecnica
1. Compilacion OK
```powershell
python -m py_compile "E:\SISTEMA DE COSTOS\app\services\llm_bom_service.py"
Get-ChildItem "E:\SISTEMA DE COSTOS\app\core_llm" -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```
2. Paridad de salida contra baseline F0
- Baseline: `E:\SISTEMA DE COSTOS\tmp_f0_baseline_output.xlsx`
- Refactor: `E:\SISTEMA DE COSTOS\tmp_f1_refactor_output.xlsx`
- Resultado: mismas filas, mismas columnas, sin diferencias en celdas comparadas.

## Resultado
- Fase 1 completada sin regresion observable en el archivo de prueba.