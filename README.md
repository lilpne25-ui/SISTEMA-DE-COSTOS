# Sistema de Costos

Sistema desktop en Python/PySide6 con Pervasive para logistica e ingenieria.
Incluye operacion de costos de materiales y flujo LLM para convertir BOM de SOLIDWORKS al layout de GLOBAL SHOP.

## Que hace hoy
- Gestion de materiales, costos historicos y catalogos (materiales/formas).
- Reglas de costo por material/forma y tabla A36 por espesor.
- Fichas tecnicas PDF por material almacenadas en base de datos (BLOB).
- App de ingenieria `LLM SOLID -> GLOBAL SHOP` sobre la misma base de reglas/costos.
- API local para integracion con PDM Task y cliente CLI para conversion automatizada.

## Integracion LLM SOLID <-> LLM GLOBAL SHOP
La interconexion actual ya esta implementada y usa un core compartido:

- `main_llm_ingenieria.py`: levanta la app de ingenieria y abre el modulo LLM dentro de `ConfigWindow`.
- `app/core_llm/runtime_service.py`: runtime headless (`LlmGlobalShopRuntime`) que reutiliza el repositorio y reglas reales del sistema.
- `app/core_llm/engine.py`: motor de conversion SOLIDWORKS -> GLOBAL SHOP, incluido manejo de filas STK.
- `scripts/llm_globalshop_api.py`: API HTTP local (`/health`, `/api/v1/convert`) para integracion externa (PDM-ready).
- `scripts/llm_globalshop_api_client.py`: cliente CLI que consume la API para generar el archivo de salida GLOBAL SHOP.

Resultado: tanto UI de ingenieria como API/CLI usan el mismo motor y la misma fuente de verdad de costos.

## Reglas de costo en el flujo LLM
Resolucion de precio por kg en conversion:
1. A36 placa (formas rectangular/cuadrado) con tabla por espesor.
2. Regla por material+forma.
3. Regla por material (forma vacia como fallback en repositorio).
4. `precio_default_kg` si no hay regla.

## Stack
- Python 3.10+
- PySide6 (Qt) para UI Windows
- Pervasive PSQL v13 (ODBC)
- Patron Repository para desacoplar UI, reglas de negocio y persistencia

## Estructura
```text
main.py
main_llm_ingenieria.py
requirements.txt
app/
|-- core_llm/     # Motor y runtime SOLID -> GLOBAL SHOP
|-- data/         # Repository + PervasiveRepository
|-- models/       # Entidades y dataclasses
`-- ui/           # Ventanas y componentes PySide6
scripts/
|-- llm_globalshop_api.py
`-- llm_globalshop_api_client.py
```

## Como correr (Windows)
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### App de logistica
```bat
python main.py
```

### App de ingenieria (LLM)
```bat
python main_llm_ingenieria.py
```

### API local LLM SOLID -> GLOBAL SHOP
```bat
python scripts\llm_globalshop_api.py --host 127.0.0.1 --port 8787
```

### Cliente CLI de conversion (PDM/automatizacion)
```bat
python scripts\llm_globalshop_api_client.py ^
  --source "C:\ruta\entrada.xlsx" ^
  --output "C:\ruta\salida_GLOBAL_SHOP.xlsx" ^
  --api-url "http://127.0.0.1:8787/api/v1/convert"
```

## Configuracion Pervasive
1. Instalar driver ODBC de Pervasive PSQL v13.
2. Definir variables:
   - `SISTEMA_COSTOS_PERVASIVE_SERVER`
   - `SISTEMA_COSTOS_PERVASIVE_DBQ`
   - `SISTEMA_COSTOS_PERVASIVE_USER`
   - `SISTEMA_COSTOS_PERVASIVE_PASSWORD`
3. Ejecutar `main.py`, `main_llm_ingenieria.py` o la API.

## Empaquetado .exe
```bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "SistemaCostos" main.py
```
