# PDM Task + API para LLM SOLID -> GLOBAL SHOP

## Objetivo
Automatizar la conversion `SOLIDWORKS -> GLOBAL SHOP` desde flujo de PDM, sin usar la UI manual.

## MVP implementado en este repo
1. API local headless: `scripts/llm_globalshop_api.py`
2. Runtime de conversion con reglas/densidades del sistema: `app/core_llm/runtime_service.py`
3. Cliente CLI para invocar la API desde tareas externas (incluyendo PDM): `scripts/llm_globalshop_api_client.py`

## Arquitectura
1. PDM dispara una tarea (transicion de estado o task manual).
2. La tarea ejecuta `llm_globalshop_api_client.py` con `source` y `output`.
3. El cliente llama `POST /api/v1/convert`.
4. La API usa el motor actual `app/core_llm/engine.py` y escribe el `.xlsx` de salida.

## Arranque del servicio API
```powershell
py E:\SISTEMA DE COSTOS\scripts\llm_globalshop_api.py --host 127.0.0.1 --port 8787
```

Healthcheck:
```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8787/health"
```

## Prueba manual de conversion
```powershell
py E:\SISTEMA DE COSTOS\scripts\llm_globalshop_api_client.py `
  --source "C:\RUTA\BOM_SOLID.xlsx" `
  --output "C:\RUTA\BOM_SOLID_GLOBAL_SHOP.xlsx" `
  --api-url "http://127.0.0.1:8787/api/v1/convert"
```

## Payload HTTP directo
```json
{
  "source_path": "C:\\RUTA\\BOM_SOLID.xlsx",
  "output_path": "C:\\RUTA\\BOM_SOLID_GLOBAL_SHOP.xlsx",
  "template_path": "C:\\Users\\TI\\Documents\\PRUEBAS LLSMSS\\LDM507-473 GLOBAL SHOP.xlsx",
  "precio_default_kg": 0.0,
  "fabricante_default": "INNOVAX",
  "include_rows": false
}
```

## Integracion en PDM (MVP operativo)
Configurar la tarea para ejecutar un comando que invoque el cliente:

```powershell
py E:\SISTEMA DE COSTOS\scripts\llm_globalshop_api_client.py --source "<BOM_INPUT.xlsx>" --output "<GLOBAL_SHOP_OUTPUT.xlsx>"
```

O usar wrapper PowerShell (mas limpio para Task scheduler):

```powershell
powershell -ExecutionPolicy Bypass -File E:\SISTEMA DE COSTOS\scripts\pdm_task_convert.ps1 -SourcePath "<BOM_INPUT.xlsx>" -OutputPath "<GLOBAL_SHOP_OUTPUT.xlsx>"
```

Notas:
1. Los placeholders exactos de rutas/variables dependen de como este configurada la Task en tu PDM.
2. La API debe estar levantada en la misma maquina donde corre la tarea.
3. Si quieres evitar dependencia de API levantada, se puede hacer siguiente fase con ejecutable unico para Task Host.

## Fase siguiente (Add-in PDM completo)
1. Crear proyecto C# `IEdmAddIn5` para task server.
2. Registrar Add-in en PDM Admin.
3. Pasar argumentos de vault/file/revision al worker.
4. Llamar API local (o motor embebido) y adjuntar output al vault.
5. Auditoria: guardar log por JobId + archivo.

## Criterios de exito MVP
1. Desde PDM se dispara el comando y termina con exit code `0`.
2. Se genera el archivo `_GLOBAL_SHOP.xlsx` con layout ERP.
3. El response de API devuelve `ok=true` y resumen de filas.
