# Fase 2 + Fase 3 - Evidencia de Integracion y App Ingenieria

- Fecha: 2026-04-29 13:17:48

## F2 - Integracion UI sin romper
- Se mantuvo `ConfigWindow` y flujo actual de Logistica sin cambios de negocio.
- Smoke UI en modo offscreen: instancia de `ConfigWindow`, carga SOLID, recalculo preview.
- Resultado smoke: `result_none=False`, `rows=106`, `table_rows=106`.

Comando ejecutado (resumen):
```powershell
$env:QT_QPA_PLATFORM="offscreen"; python <script_smoke_config_window>
```

## F3 - Cascaron App Ingenieria minima
- Archivo creado: `E:\SISTEMA DE COSTOS\main_llm_ingenieria.py`
- Esta app abre solo el modulo `LLM SOLID -> GLOBAL SHOP` (oculta navegacion y fija stack index 4).
- Reutiliza exactamente el mismo core/servicio del sistema actual.

Comando de arranque app Ingenieria:
```powershell
python "E:\SISTEMA DE COSTOS\main_llm_ingenieria.py"
```

Smoke tecnico app Ingenieria (offscreen):
- `nav_hidden=True`
- `stack_index=4`
- `preview_rows=106`

## Validacion contra baseline F0
- Baseline: `E:\SISTEMA DE COSTOS\tmp_f0_baseline_output.xlsx`
- Validacion F3: `E:\SISTEMA DE COSTOS\tmp_f3_engineering_validation.xlsx`
- Resultado: misma forma (`107x32`) y `total_diff_cells=0`.

## Compilacion
```powershell
python -m py_compile "E:\SISTEMA DE COSTOS\main_llm_ingenieria.py"
python -m py_compile "E:\SISTEMA DE COSTOS\app\services\llm_bom_service.py"
Get-ChildItem "E:\SISTEMA DE COSTOS\app\core_llm" -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

## Estado
- F2: cumplida (integracion y smoke OK).
- F3: cumplida (app minima separada de Ingenieria funcionando sobre el core compartido).