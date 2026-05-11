# Transicion Fase 3: Motor Compartido (LLM SOLID -> GLOBAL SHOP)

## Objetivo Principal (no negociable)
Separar el modulo **LLM SOLID -> GLOBAL SHOP** como app de Ingenieria, sin perder alimentacion desde Sistema de Costos, y **sin romper nada** del flujo actual de Logistica.

## Alcance de Fase 3
- Extraer la logica de conversion/costeo LLM a un **core compartido**.
- Mantener operativo el flujo actual dentro de Sistema de Costos.
- Crear base para segunda app de Ingenieria reutilizando el mismo core.
- No introducir cambios de negocio no solicitados.

## Restricciones Criticas
- No romper UI, reglas, catalogos, ni calculo actual de costos.
- No cambiar contratos de BD existentes sin justificacion.
- No eliminar codigo funcional sin plan de reemplazo.
- Cambios pequenos, verificables y reversibles.
- Cada paso debe cerrar con evidencia (compilacion/prueba/smoke).

## Arquitectura Objetivo (Fase 3)
- `app/services/llm_bom_service.py` -> se convierte en orquestador ligero.
- Nuevo paquete core compartido (propuesta):
  - `app/core_llm/models.py` (DTOs)
  - `app/core_llm/normalization.py` (headers, alias, parse)
  - `app/core_llm/costing.py` (peso, tolerancias, costo)
  - `app/core_llm/mapping.py` (Source/Productline/STK)
  - `app/core_llm/exporter.py` (armado filas ERP + xlsx)
- UI actual (`config_window.py`) sigue llamando al servicio, pero el servicio delega al core.

## Plan de Ejecucion por Fases

### F0 - Congelamiento y linea base
1. Capturar baseline del flujo actual (archivo SOLID de prueba + salida esperada).
2. Guardar evidencia de:
   - Encabezados ERP actuales.
   - Conteo de filas por Productline.
   - Muestra de filas clave (`MP`, `AC`, `SU`, `HI`, `PT`).
3. Definir checklist de no-regresion.

Criterio de salida F0:
- Baseline documentado y reproducible.

### F1 - Extraccion del Core (sin cambiar comportamiento)
1. Mover funciones puras del servicio al paquete `app/core_llm`.
2. Mantener firmas y resultados iguales.
3. Dejar `llm_bom_service.py` como facade.

Criterio de salida F1:
- Misma salida (estructura y datos) en archivo de prueba.

### F2 - Integracion en Sistema de Costos
1. Conectar `config_window.py` al servicio refactorizado.
2. Validar preview, guardado y reglas de costo.
3. Confirmar reglas automáticas Productline:
   - `-STK` -> `AC`
   - Proveedor (`VEKTEK/KOSMEK`) -> `HI`
   - Proveedor (`INNOVAX/ZP`) -> `MP`
   - Fallback por `Source` (`P->AC`, `M->PT`, `F->MP`, otros->`SU`)

Criterio de salida F2:
- Flujo UI actual intacto.
- Cero regresiones visibles en conversion.

### F3 - Cascaron de App Ingenieria (minimo viable)
1. Crear entrypoint/app ligera para Ingenieria.
2. Reusar core y resolver costo/densidad desde Sistema de Costos.
3. Exportar GLOBAL SHOP igual que hoy.

Criterio de salida F3:
- App de Ingenieria genera mismos resultados que modulo embebido.

## Checklist de No-Regresion
- El sistema abre sin errores.
- Configuracion -> LLM SOLID -> GLOBAL SHOP funciona.
- Se puede cargar SOLID, ver preview y guardar Excel.
- Encabezados ERP iguales al template Global Shop.
- Renglones `-STK` correctos.
- `Memo1` no contaminado con stock.
- Costos solo para `INNOVAX` y `ZP`.
- Productline respeta reglas automaticas actuales.

## Estrategia de Validacion (comandos)
Ejecutar al final de cada fase:

```powershell
python -m py_compile "E:\SISTEMA DE COSTOS\app\services\llm_bom_service.py"
```

Si se tocan modulos nuevos:

```powershell
Get-ChildItem "E:\SISTEMA DE COSTOS\app\core_llm" -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

Smoke de conversion con archivo real:
- `C:\Users\TI\Documents\PRUEBAS LLSMSS\LDM507-473 SOLID .xlsx`
- Template ERP:
  `C:\Users\TI\Documents\PRUEBAS LLSMSS\LDM507-473 GLOBAL SHOP.xlsx`

## Rollback Seguro (sin git)
- Antes de cada fase, crear copia:
  - `app/services/llm_bom_service.py.bak_faseX`
  - `app/ui/windows/config_window.py.bak_faseX`
- Si hay regresion: restaurar `.bak` y repetir fase con menor alcance.

## Prompt Maestro para Claude (usar antes de cualquier cambio)
```text
Actua como ingeniero senior en Python/PySide6.
Objetivo principal: separar el motor de LLM SOLID -> GLOBAL SHOP como core compartido para futura app de Ingenieria, sin romper el Sistema de Costos actual.
Restricciones:
1) No romper funcionalidades existentes.
2) No cambiar reglas de negocio ya definidas.
3) No eliminar codigo funcional sin reemplazo validado.
4) Entregar cambios pequenos, auditables y reversibles.
5) Mostrar siempre: archivos tocados, que cambiaste, como validaste, y riesgos.
Prioridad tecnica:
- Mantener paridad de salida del Excel.
- Mantener reglas actuales de Productline/Source/STK/costos por fabricante.
- Refactor primero, nuevas features despues.
Si detectas riesgo de regresion, detente y propone alternativa de menor riesgo.
```

## Prompts por Fase para Claude

### Prompt F0 - Baseline
```text
Tarea: levantar baseline del flujo LLM SOLID -> GLOBAL SHOP sin modificar logica.
Haz lo siguiente:
1) Ejecuta conversion con archivo SOLID de prueba y template GLOBAL SHOP.
2) Reporta encabezados, conteo total de filas, conteo por Productline y muestra de 20 filas clave.
3) Guarda evidencia en un archivo markdown dentro de docs/.
No edites reglas de negocio en esta fase.
```

### Prompt F1 - Extraer Core
```text
Tarea: refactor a core compartido sin cambiar comportamiento.
Acciones:
1) Crea paquete app/core_llm con modulos: models, normalization, costing, mapping, exporter.
2) Mueve funciones puras desde llm_bom_service.py al core.
3) Deja llm_bom_service.py como facade.
4) Mantiene la misma firma publica de convertir_solid_a_global_shop.
5) Valida paridad contra baseline F0.
Regla: si cambia la salida del Excel, corrige hasta recuperar paridad.
```

### Prompt F2 - Integrar UI sin romper
```text
Tarea: conectar UI actual al servicio refactorizado sin alterar UX.
Acciones:
1) Verifica que Configuracion -> LLM SOLID -> GLOBAL SHOP siga funcionando.
2) Valida preview, guardado y reglas de costeo.
3) Confirma reglas Productline vigentes (STK, proveedor, source).
Entrega:
- Lista de pruebas ejecutadas.
- Evidencia de que no hubo regresion.
```

### Prompt F3 - App Ingenieria minima
```text
Tarea: crear app minima de Ingenieria que use el core compartido.
Objetivo:
- Cargar Excel SOLID.
- Mostrar preview basico.
- Exportar a formato GLOBAL SHOP.
- Consumir reglas/costos desde Sistema de Costos.
Restricciones:
- No duplicar logica del core.
- No romper app principal.
- Mantener compatibilidad de datos y columnas.
Entrega:
- Archivos creados.
- Como se ejecuta la app.
- Validacion contra baseline.
```

### Prompt de Gate Final (obligatorio)
```text
Antes de cerrar, responde en este formato:
1) Objetivo principal: cumplido / no cumplido.
2) Riesgo de regresion: bajo / medio / alto y por que.
3) Evidencia tecnica: comandos corridos y resultado.
4) Archivos tocados con ruta completa.
5) Que NO cambiaste para evitar romper produccion.
Si no puedes demostrar no-regresion, no cierres tarea.
```

## Definicion de Exito
- Existe core compartido reutilizable.
- Sistema de Costos sigue estable en produccion.
- El modulo LLM puede vivir como app de Ingenieria sin duplicar reglas.
- Resultado Excel conserva estructura ERP y reglas actuales.
