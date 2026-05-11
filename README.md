# Sistema de Costos

App de escritorio Windows para que el encargado de logistica gestione materiales de forma simple, registrando forma del material, material y costos historicos.
El sistema maneja precios en pesos mexicanos (MXN) y unidad fija en kg.
Las placas A36 usan una tabla de precios por espesor para sugerir el costo por kg, administrada desde un modulo independiente de tarifas A36.
Con clic izquierdo sobre un material se abre su ficha tecnica PDF en un visualizador interno; si no existe, el sistema permite adjuntarla en ese momento.
La ficha PDF se guarda dentro de la base de datos (BLOB) y su eliminacion requiere contrasena.
El modulo de configuracion tambien permite administrar catalogos de materiales y formas con sus prefijos para la asignacion de codigos.
Ese mismo modulo permite configurar reglas de costo base por material/forma para sugerir costo inicial automaticamente.
Prioridad de costo sugerido al crear material: `A36+Placa por espesor` -> `regla Material+Forma` -> `regla general por Material` -> manual.

## Stack
- Python 3.10+
- PySide6 (Qt) para UI nativa Windows
- Pervasive PSQL v13 (ODBC)
- Patron Repository para desacoplar UI y persistencia

## Estructura
```text
main.py
requirements.txt
app/
|-- models/       # dataclasses (Material, Costo)
|-- data/         # Repository + PervasiveRepository
`-- ui/           # MainWindow, MaterialForm, CostoForm
```

## Como correrlo (Windows)
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Empaquetar como .exe
```bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "SistemaCostos" main.py
```

El ejecutable queda en `dist/SistemaCostos/`.

## Configuracion Pervasive
1. Instalar el driver ODBC de Pervasive PSQL v13 en la PC.
2. Configurar las variables `SISTEMA_COSTOS_PERVASIVE_SERVER`, `SISTEMA_COSTOS_PERVASIVE_DBQ`, `SISTEMA_COSTOS_PERVASIVE_USER` y `SISTEMA_COSTOS_PERVASIVE_PASSWORD`.
3. Ejecutar `python main.py`.

## Proximos pasos sugeridos
- Importar costos masivos desde Excel.
- Control de usuarios y auditoria.
- Grafico historico de precios por material.
