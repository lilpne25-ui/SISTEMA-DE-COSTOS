# Rediseño UI/UX Empresarial — Sistema de Costos

Guía de implementación por fases con prompts listos para pegar en una conversación nueva con Claude. Cada fase es un prompt autónomo: lo copias, lo pegas, dejas que Claude lo ejecute, revisas, avanzas a la siguiente.

---

## Cómo usar este documento

1. Abre una conversación nueva de Claude con acceso a tu carpeta `E:\SISTEMA DE COSTOS`.
2. Pega el bloque **Contexto base** al inicio (se pega una sola vez por conversación).
3. Pega el prompt de la **Fase 1**. Deja que Claude la ejecute de principio a fin. Revisa los cambios. Haz commit en git.
4. Cuando valides la Fase 1, pega el prompt de la **Fase 2**. Idem.
5. Finalmente, pega el prompt de la **Fase 3**.

Regla de oro: **no mezcles fases**. Una fase por vez, con commit entre cada una, para poder revertir si algo rompe.

---

## Preparativos antes de empezar (manuales, 5 minutos)

Dos cosas que debes hacer tú, no Claude, antes de la Fase 1:

1. **Crear rama git nueva**:

   ```bash
   cd "E:\SISTEMA DE COSTOS"
   git checkout -b rediseno-uiux
   git add -A
   git commit -m "snapshot antes de rediseño UI/UX"
   ```

2. **Descargar fuentes** (las vas a necesitar en la Fase 1):

   - Inter: https://github.com/rsms/inter/releases (descarga `Inter-4.0.zip`, usa los `.ttf` de la carpeta `Inter Desktop`)
   - JetBrains Mono: https://www.jetbrains.com/lp/mono/ (descarga el zip, usa los `.ttf` de la carpeta `fonts/ttf`)

   Deja los archivos `Inter-Regular.ttf`, `Inter-Medium.ttf`, `Inter-SemiBold.ttf`, `JetBrainsMono-Regular.ttf` y `JetBrainsMono-Medium.ttf` a la mano. Claude te pedirá dónde están.

3. **Descargar iconos Lucide** (los necesitas en la Fase 2):

   - Ve a https://lucide.dev y descarga los SVG de estos nombres: `plus`, `edit-2`, `trash-2`, `search`, `chevron-left`, `chevron-right`, `minus`, `maximize`, `download`, `printer`, `alert-triangle`, `alert-circle`, `check`, `x`, `copy`, `settings`, `sun`, `moon`, `file-text`, `package`.
   - Déjalos en una carpeta temporal; en la Fase 2 se moverán a `app/ui/icons/`.

---

## Contexto base (pegar primero, una sola vez)

```text
Actúa como Principal Product Designer y desarrollador senior de Python con
especialización en aplicaciones de escritorio empresariales construidas en
PySide6 (Qt Widgets). Tienes 15+ años rediseñando herramientas internas de
manufactura, logística y fintech. Tu referencia estética es Linear, Stripe
Dashboard, Figma y JetBrains IDE, aterrizada en Qt nativo, no web.

El proyecto que vamos a rediseñar vive en la carpeta "E:\SISTEMA DE COSTOS".
Es un sistema de costos de logística construido con:

- Python 3 + PySide6 + Pervasive PSQL v13.
- Punto de entrada: main.py. Ventana inicial 1200x720.
- Dominio: materiales (acero A36 placa, otras formas), historial de precios
  por kg en MXN, fichas técnicas PDF embebidas en BD, tarifas A36 por rango
  de espesor en pulgadas.
- Usuarios: personal de logística, compras y planta. Power-users, uso en PC
  de escritorio, varias consultas al día.
- Módulos UI en app/ui/:
  1. main_window.py — MainWindow con toolbar, tabla de materiales, panel
     detalle e historial de costos.
  2. material_form.py — Diálogo crear/editar material.
  3. costo_form.py — Diálogo agregar costo.
  4. a36_price_manager.py — Diálogo con tabs para tarifas A36, reglas de
     costo, catálogo de materiales y formas.
  5. pdf_viewer_dialog.py — Visor de fichas técnicas PDF.
- Estado actual: uso masivo de QTableWidget (no MVC), sin QSS global, sin
  design tokens, sin iconografía, sin tema claro/oscuro, sin atajos de
  teclado, labels sin acentos, validaciones en QMessageBox, y un password
  hardcodeado en main_window.py línea 44 que además es anti-UX.

Reglas no negociables para todas tus respuestas:

1. Prohibido dar consejos genéricos. Cada recomendación nombra archivo,
   clase, método y línea exacta.
2. Prohibido usar emojis.
3. Prohibido proponer soluciones web (Tailwind, shadcn, CSS, React). Esto
   es Qt nativo. Trabaja con QSS, QPalette, QProxyStyle, QFontDatabase,
   QIcon, QStyledItemDelegate y layouts Qt.
4. Imperativo técnico, no sugerencias. "Reemplaza X por Y porque Z", nunca
   "podrías considerar".
5. Toda decisión se justifica en: reducción de tiempo de tarea, reducción
   de errores, densidad informativa, claridad semántica, escalabilidad del
   código UI o percepción de calidad premium.
6. Cuando edites código, edita el archivo real, no solo me muestres el diff.

Estándar visual obligatorio del sistema:

- Tipografía: Inter como primaria, JetBrains Mono para columnas numéricas.
  Escala 11/12/13/14/16/20/24 px. Registrar con QFontDatabase.addApplicationFont.
- Paleta tokenizada en app/ui/theme.py con tokens surface, surface_raised,
  surface_sunken, border, border_strong, text_primary, text_secondary,
  text_muted, accent, accent_hover, accent_soft, danger, danger_soft,
  warning, warning_soft, success, success_soft.
- Tema claro y oscuro conmutable vía QPalette + QSS.
- Bordes 1px, radios 4/6/8, sin sombras.
- Row height 28px en tablas, padding 8/12 en inputs, 6/10 en botones.
- Foco visible con outline accent 2px en todos los widgets interactivos.
- Iconografía: Lucide como SVG en app/ui/icons/.
- Contraste mínimo 4.5:1, setTabOrder coherente, setAccessibleName en
  inputs críticos, atajos con QKeySequence estándar.

Trabajaremos por fases. No avances a la siguiente fase hasta que yo lo diga
explícitamente. Si encuentras decisiones de arquitectura que no están en el
prompt, pregunta antes de asumir.

Confirma que entendiste y queda a la espera del prompt de la Fase 1.
```

---

## Fase 1 — Cimientos (1-2 días de trabajo)

**Objetivo:** poner los cimientos sin cambiar UX visible todavía. Después de esta fase, la app corre igual que antes pero ya tiene tema, tokens, fuentes, widgets base y el password hardcodeado resuelto.

**Qué toca:**

- Crea `app/ui/theme.py`, `app/ui/formatting.py`, `app/ui/icons.py`.
- Crea `app/ui/fonts/` y mete las fuentes.
- Crea `app/ui/widgets/` con los componentes base.
- Saca `_formatear_pulgadas` de `a36_price_manager.py` a `formatting.py`.
- Aplica `apply_theme(app, "light")` en `main.py`.
- Resuelve el password hardcodeado (mínimo a variable de entorno).

**Qué NO toca:** nada del layout actual, ninguna tabla, ningún flujo. Solo fundamentos.

### Prompt de la Fase 1 (copiar y pegar tal cual)

```text
FASE 1 - CIMIENTOS DEL SISTEMA DE DISEÑO

Objetivo: implementar los cimientos del nuevo sistema de diseño sin cambiar
todavía ninguna UX visible. Al terminar esta fase, la app debe correr igual
que antes pero con tema aplicado, tokens disponibles, fuentes registradas y
widgets base listos para usar.

Tareas a ejecutar en este orden:

1. Crea app/ui/theme.py con:
   - Dataclass ColorTokens con todos los tokens de color claros y oscuros
     (LIGHT y DARK) definidos en el estándar visual.
   - Dataclass Typography con family_ui="Inter", family_mono="JetBrains Mono"
     y los tamaños xs=11, sm=12, md=13, lg=14, xl=16, 2xl=20, 3xl=24.
   - Dataclass Spacing con xs=4, sm=6, md=8, lg=12, xl=16, xxl=24.
   - Dataclass Radius con sm=4, md=6, lg=8.
   - Variable global _tokens inicializada en LIGHT.
   - Función tokens() que devuelve _tokens actual.
   - Función _registrar_fuentes() que carga los .ttf desde app/ui/fonts/
     con QFontDatabase.addApplicationFont, tolerante a archivos faltantes.
   - Función _build_qss(t) que devuelve el QSS global con estilos para
     QMainWindow, QDialog, QWidget, QToolBar, QStatusBar, QLineEdit,
     QComboBox, QDoubleSpinBox, QDateEdit, QTextEdit, QPushButton
     (incluyendo variantes role="primary" y role="danger"), QTableView,
     QHeaderView, QSplitter, QTabWidget, QTabBar, QGroupBox, QScrollBar.
   - Función apply_theme(app, mode) que setea _tokens, llama
     _registrar_fuentes(), configura QPalette base, setea la fuente default
     y aplica el QSS global.

2. Crea app/ui/formatting.py y mueve la función _formatear_pulgadas desde
   app/ui/a36_price_manager.py. Expórtala como formatear_pulgadas (sin
   guion bajo). Agrega también:
   - formatear_money(valor, moneda="MXN", unidad="kg") que devuelve
     "MXN 32.50 /kg" con separador de miles correcto.
   - formatear_delta(nuevo, anterior) que devuelve tupla (texto, signo)
     donde signo es "up", "down" o "flat".
   Actualiza todos los imports en a36_price_manager.py para que sigan
   funcionando.

3. Crea app/ui/fonts/ y pídeme que te confirme dónde tengo los .ttf de
   Inter y JetBrains Mono. Cuando te los indique, cópialos a esa carpeta.
   Si aún no los tengo, crea la carpeta vacía y avísame que debo ponerlos
   después para que apply_theme los encuentre.

4. Crea app/ui/icons/ vacía por ahora. En la Fase 2 se llenará con SVGs.

5. Crea app/ui/widgets/__init__.py y los siguientes widgets, cada uno en
   su propio archivo:
   - primary_button.py: PrimaryButton(QPushButton) con setProperty role primary.
   - secondary_button.py: SecondaryButton(QPushButton), es un QPushButton
     plano, sin role.
   - danger_button.py: DangerButton(QPushButton) con setProperty role danger.
   - form_field.py: FormField(QWidget) que envuelve un QLabel de título, un
     widget input (cualquier QWidget que reciba por constructor) y un
     QLabel de error oculto por default. Métodos set_error(msg) y
     clear_error(). El label de error usa property field-error para el QSS.
   - toast.py: Toast(QWidget) flotante. Constructor recibe parent, texto y
     variante ("success" | "error" | "info"). Se auto-posiciona en esquina
     inferior derecha del parent. Auto-dismiss en 4 segundos usando QTimer.
     Método estático Toast.show_toast(parent, texto, variante).
   - card.py: Card(QWidget) contenedor con borde 1px, radius 8, padding 14,
     background surface_raised. Layout interno es QVBoxLayout accesible
     vía self.body.

6. Crea app/ui/icons.py con función icon(name: str) -> QIcon que:
   - Busca el archivo app/ui/icons/{name}.svg.
   - Devuelve un QIcon vacío si no existe (no crashea).
   - Por ahora no hace recoloreado, solo carga el SVG tal cual.

7. Modifica app/main.py para:
   - Importar apply_theme desde app.ui.theme.
   - Llamarlo justo después de crear QApplication con mode="light".
   - Mantener todo lo demás igual.

8. Arregla el password hardcodeado en app/ui/main_window.py línea 44:
   - Elimina la constante PASSWORD_ELIMINAR_FICHA del archivo.
   - Lee la contraseña desde la variable de entorno SISTEMA_COSTOS_PASSWORD
     al inicio del módulo, con un fallback a un hash vacío y mensaje claro
     al usuario si no está definida.
   - No cambies el flujo de pedir contraseña todavía (eso es Fase 2). Solo
     saca la constante del repo.
   - Crea un archivo .env.example en la raíz con la variable documentada.
   - Agrega .env al .gitignore si no está.

9. Corre la app y verifica que:
   - Arranca sin errores.
   - El tema claro se aplica correctamente (bordes, fondos, fuentes).
   - Ninguna funcionalidad previa se rompió.

10. Al final, entrégame un resumen con:
    - Lista de archivos nuevos creados.
    - Lista de archivos modificados.
    - Cualquier decisión que hayas tomado sobre la marcha y por qué.
    - Qué debo verificar manualmente antes de hacer commit y avanzar a la
      Fase 2.

Reglas de esta fase:
- No toques main_window.py más allá del password. No cambies layout, no
  cambies widgets, no migres QTableWidget a QTableView. Eso es Fase 2.
- No toques material_form.py, costo_form.py, a36_price_manager.py ni
  pdf_viewer_dialog.py, salvo el import de _formatear_pulgadas en
  a36_price_manager.py.
- Si alguna decisión no está clara, pregúntame antes de asumir.

Empieza ahora, paso por paso, y repórtame avances al terminar cada bloque
grande (theme, formatting, widgets, main.py, password).
```

**Después de la Fase 1, haz esto manualmente:**

```bash
cd "E:\SISTEMA DE COSTOS"
python main.py          # verifica que arranca
git add -A
git commit -m "fase 1: cimientos del sistema de diseño"
```

---

## Fase 2 — MVC y pantallas principales (3-4 días de trabajo)

**Objetivo:** migrar la tabla principal a MVC, rediseñar la MainWindow con el nuevo layout, y rediseñar los dos formularios más usados (MaterialForm y CostoForm).

**Qué toca:**

- Migra `QTableWidget` a `QTableView` + `QAbstractTableModel` + delegates en `main_window.py`.
- Aplica el nuevo layout de MainWindow (top bar, action bar, splitter 62/38, status bar enriquecida).
- Atajos de teclado globales.
- Reemplaza `QMessageBox` de feedback por `Toast`.
- Rediseña `CostoForm` con contexto, delta, autocomplete de proveedor, chips de fecha.
- Rediseña `MaterialForm` con secciones, rule card, code preview en vivo.
- Mueve los iconos Lucide a `app/ui/icons/`.

**Qué NO toca:** `a36_price_manager.py` ni `pdf_viewer_dialog.py`. Esos son Fase 3.

### Prompt de la Fase 2 (copiar y pegar tal cual)

```text
FASE 2 - MVC Y PANTALLAS PRINCIPALES

Contexto: la Fase 1 ya está aplicada. Ahora vamos a rediseñar MainWindow,
MaterialForm y CostoForm, y a migrar la tabla principal a MVC.

Antes de empezar: los iconos Lucide que descargué están en la carpeta que
yo te indique. Pídemelo al inicio y muévelos a app/ui/icons/.

Tareas en orden:

BLOQUE A - Modelos y delegates

1. Crea app/ui/models/__init__.py y app/ui/models/materiales_model.py con
   MaterialesTableModel(QAbstractTableModel). Columnas: Código, Material,
   Forma, Espesor, Costo vigente, Actualizado. Implementa los roles
   DisplayRole, TextAlignmentRole, FontRole (JetBrains Mono para código,
   espesor y costo), UserRole (id en columna código). Método cargar(filas)
   donde filas es lista de tuplas (Material, Costo|None). Método
   material_en_fila(fila).

2. Crea app/ui/models/costos_model.py con CostosTableModel similar para el
   historial de costos del panel detalle. Columnas: Fecha, Precio, Moneda,
   Unidad, Proveedor.

3. Crea app/ui/delegates/__init__.py y los siguientes delegates:
   - money_delegate.py: MoneyDelegate pinta valor float con separador de
     miles, 2 decimales, alineado derecha, JetBrains Mono 13px, y sufijo
     "MXN/kg" en text_secondary.
   - espesor_delegate.py: EspesorDelegate usa formatear_pulgadas para
     mostrar "3/8\"" en lugar de "0.375".
   - estado_delegate.py: EstadoDelegate pinta un chip pequeño con color
     según antigüedad del costo (verde si es de hoy, ámbar si es de esta
     semana, muted si más viejo).

BLOQUE B - MainWindow rediseñada

4. Rediseña app/ui/main_window.py completo:

   a. Reemplaza QTableWidget de materiales por QTableView. Usa
      MaterialesTableModel y QSortFilterProxyModel para que el filtro de
      búsqueda sea in-memory. Setea setFilterKeyColumn(-1) y
      setFilterCaseSensitivity(Qt.CaseInsensitive). Aplica los delegates
      a las columnas correspondientes. Row height 28px.

   b. Reemplaza QTableWidget del historial de costos por QTableView con
      CostosTableModel.

   c. Separa la barra superior en dos toolbars:
      - topBar (objectName topBar): logo/título a la izquierda, search
        field (usa un QLineEdit con clear button y placeholder "Buscar
        por código, material, forma o espesor"), combo de tipo, y a la
        derecha un botón icon-only de tema (sun/moon) y el nombre del
        usuario en un QLabel.
      - actionBar (objectName actionBar): botones Nuevo (PrimaryButton
        con icono plus), Editar (SecondaryButton con icono edit-2),
        Eliminar (DangerButton con icono trash-2), separador, Configuración
        (SecondaryButton con icono settings), Abrir ficha PDF
        (SecondaryButton con icono file-text).

   d. Reescribe el panel detalle usando Card widgets en lugar de
      QGroupBox. Cuatro cards verticales: Identificación, Costo vigente,
      Ficha técnica, Historial de costos.

      - Identificación: código, material, forma, espesor con FormField
        en modo read-only.
      - Costo vigente: un MoneyLabel grande con el precio, fecha del
        costo debajo en text_muted.
      - Ficha técnica: nombre del archivo PDF si existe, botón "Ver
        ficha" (SecondaryButton con icono file-text), botón "Cambiar"
        (SecondaryButton) y botón "Eliminar" (DangerButton). Si no hay
        ficha, muestra EmptyState con CTA "Adjuntar ficha".
      - Historial de costos: QTableView con CostosTableModel, más
        PrimaryButton "Agregar costo" arriba.

      Los "-" como valor vacío cámbialos por "Sin dato" en text_muted.

   e. Splitter 62/38 con setHandleWidth(1). Guarda proporción del
      splitter, posición de ventana y último filtro de tipo en QSettings
      ("InnovaX", "SistemaCostos"). Restaura al abrir.

   f. Status bar enriquecida: muestra a la izquierda "Conectado a Pervasive",
      en el centro el contador de materiales, a la derecha el usuario y
      un reloj QTimer que actualiza cada minuto.

   g. Reemplaza todos los QMessageBox de feedback (éxito/error no crítico)
      por Toast.show_toast. Los QMessageBox.question para confirmar
      eliminación sí quedan porque son destructivos.

   h. Resuelve el comportamiento de doble-click abre PDF: quita
      _on_click_material de itemClicked y conéctalo a doubleClicked. El
      click simple solo selecciona.

   i. Atajos de teclado globales con QShortcut:
      Ctrl+F foco buscar, Ctrl+N nuevo, Ctrl+E editar, Supr eliminar,
      Ctrl+, configuración, Ctrl+Shift+C agregar costo, Ctrl+P abrir
      ficha PDF, F5 recargar, Ctrl+Shift+T conmutar tema.

   j. setAccessibleName en search field, combo tipo, tabla, botones
     principales del panel detalle.

BLOQUE C - CostoForm rediseñado

5. Reescribe app/ui/costo_form.py:

   a. Cambia el constructor a:
      CostoForm(material, costo_vigente, proveedores_recientes, parent,
                precio_default, nota_default)
      donde material es Material y costo_vigente es Optional[Costo] y
      proveedores_recientes es list[str].

   b. Layout con Card de contexto arriba que muestra:
      - Línea 1: código · nombre · forma · espesor formateado.
      - Línea 2: "Costo vigente: MXN 32.50 /kg (hace 12 días)" o "Primer
        costo registrado" si no hay costo vigente.

   c. Campo fecha con QDateEdit y tres ChipButton al lado: "Hoy", "Ayer",
      "-1 sem". Crea ChipButton en app/ui/widgets/chip_button.py si no
      existe. Atajos Alt+H y Alt+A.

   d. Campo precio con DeltaLabel debajo que muestra diferencia absoluta
      y porcentaje contra costo vigente, actualizado en vivo con la señal
      valueChanged del QDoubleSpinBox. Crea DeltaLabel en
      app/ui/widgets/delta_label.py. Colores: success si baja, warning si
      sube, muted si igual. Usa formatear_delta de formatting.py.

   e. Campo proveedor con QLineEdit + QCompleter (MatchContains, case
      insensitive) alimentado por proveedores_recientes.

   f. Campo nota con QTextEdit altura fija 60px y placeholder
      descriptivo.

   g. Elimina los QLabel de moneda y unidad. Pon "MXN/kg" como sufijo
      inline del spinbox de precio (usa setSuffix o un QLabel adjunto).

   h. Valida con FormField.set_error inline, no con QMessageBox.

   i. Atajos: Ctrl+Enter guarda, Ctrl+S guarda, Esc cancela.

   j. Foco inicial en spn_precio, no en la fecha.

   k. Actualiza app/ui/main_window.py _agregar_costo para llamar a repo
      y conseguir costo_vigente y proveedores_recientes, y pasarlos al
      constructor.

   l. Añade al Repository un método listar_proveedores_historicos() que
      devuelva los 50 proveedores más recientes distintos. Si no puedes
      modificar Repository directamente, avísame y lo hago yo.

BLOQUE D - MaterialForm rediseñado

6. Reescribe app/ui/material_form.py:

   a. Tamaño 720x560. Diálogo con tres secciones separadas por Card:
      Identificación, Especificación, Costo inicial (solo al crear).

   b. Sección Identificación contiene combos Forma y Material (con
      QCompleter contains-match case-insensitive) y debajo un CodePreview
      que muestra el código autogenerado en JetBrains Mono 14px con
      color accent y un botón copy pequeño al lado. Crea CodePreview en
      app/ui/widgets/code_preview.py.

   c. Sección Especificación contiene el espesor (con sufijo " y paso
      0.125) y un RuleCard que muestra el costo base calculado. Crea
      RuleCard en app/ui/widgets/rule_card.py con título y valor grande
      (JetBrains Mono 20px semibold). Si no hay regla, el RuleCard
      muestra alert-circle + texto + CTA "Configurar tarifas" que abre
      A36PriceManagerDialog.

   d. Sección Costo inicial solo aparece cuando _material_original es
      None. Usa FormField con DoubleSpinBox y sufijo MXN/kg.

   e. El campo espesor no hace reflow al cambiar visibilidad: queda
      siempre en su lugar pero deshabilitado con setEnabled(False)
      cuando no aplica, no con setVisible.

   f. Validaciones inline con FormField.set_error. Elimina todos los
      QMessageBox.warning de este archivo.

   g. Fuerza los textos de los botones del QDialogButtonBox a "Guardar"
      y "Cancelar" en español.

   h. Atajos: Ctrl+C cuando CodePreview tiene foco copia el código,
      Enter guarda, Esc cancela.

7. Verifica que la app arranca, la tabla se llena correctamente, los
   delegates pintan bien, los formularios abren, guardan y validan
   inline, los atajos funcionan, y el tema claro se ve consistente.

8. Entrégame un resumen con archivos nuevos, archivos modificados,
   decisiones que tomaste, y checklist de verificación manual.

Reglas de esta fase:
- No toques a36_price_manager.py ni pdf_viewer_dialog.py. Eso es Fase 3.
- Si encuentras que necesitas método nuevo en Repository, créalo con
  nombre claro y pregúntame si es la intención correcta.
- Si algo no está claro, pregunta antes de asumir.

Empieza por el Bloque A y repórtame al terminar cada bloque grande.
```

**Después de la Fase 2, haz esto manualmente:**

```bash
cd "E:\SISTEMA DE COSTOS"
python main.py
# Verifica: búsqueda instantánea, doble-click abre PDF, atajos funcionan,
# agregar costo muestra delta, crear material muestra código en vivo.
git add -A
git commit -m "fase 2: MVC, main window, costo form y material form rediseñados"
```

---

## Fase 3 — Configuración y visor PDF (2-3 días de trabajo)

**Objetivo:** migrar la configuración a una ventana no-modal con navegación lateral, y rediseñar el visor PDF con búsqueda, paginación, guardar e imprimir.

**Qué toca:**

- Convierte `A36PriceManagerDialog` en `ConfigWindow` (no-modal) con `QListWidget` de navegación + `QStackedWidget`.
- Migra las 4 tablas internas a `QTableView` + modelos.
- Agrega import/export CSV y XLSX.
- Rediseña `PdfViewerDialog` con toolbar, búsqueda, navegación por página, guardar e imprimir.
- Tema oscuro completo.
- Conmutación de tema en caliente.

### Prompt de la Fase 3 (copiar y pegar tal cual)

```text
FASE 3 - CONFIGURACIÓN Y VISOR PDF

Contexto: Fases 1 y 2 ya están aplicadas. Esta es la última fase del
rediseño. Al terminar, el sistema tiene los 5 módulos rediseñados y se
puede conmutar entre tema claro y oscuro en caliente.

Tareas en orden:

BLOQUE A - ConfigWindow

1. Crea app/ui/windows/__init__.py y app/ui/windows/config_window.py con
   ConfigWindow(QMainWindow). No modal. Tamaño 1080x640.

2. Layout: QSplitter horizontal con QListWidget nav a la izquierda (ancho
   fijo 220px, objectName configNav) y QStackedWidget a la derecha. La
   nav tiene 4 ítems: "Tarifas A36", "Reglas de costo", "Catálogo de
   materiales", "Catálogo de formas". Cada uno con icono Lucide
   correspondiente.

3. Cada página del stack tiene estructura común:
   - QLabel con role page-title (nombre de la sección).
   - QLabel con role page-subtitle (descripción corta de la sección).
   - Barra de acciones: SearchField, botones Importar, Exportar, Nuevo.
   - QTableView con su modelo correspondiente.
   - Footer con "Última modificación: {fecha} por {usuario}" en
     text_muted.

4. Crea modelos en app/ui/models/:
   - tarifas_a36_model.py: TarifasA36Model con columnas Rango, Espesor
     mínimo, Espesor máximo, Precio /kg. Usa EspesorDelegate y
     MoneyDelegate.
   - reglas_costo_model.py: ReglasCostoModel con columnas Material,
     Forma, Precio /kg.
   - catalogo_items_model.py: CatalogoItemsModel genérico reutilizable
     para Materiales y Formas. Columnas Nombre, Prefijo código, Usado en.

5. Migra los formularios internos (A36PriceForm, ReglaCostoForm,
   CatalogoItemForm) a usar FormField y PrimaryButton/SecondaryButton.
   Validaciones inline, no QMessageBox. Acentos correctos en todos los
   textos.

6. En A36PriceForm, mueve el label Rango a la parte superior del
   formulario en JetBrains Mono 16px, y actualízalo en vivo.

7. Agrega filtro con QSortFilterProxyModel en cada tabla.

8. Implementa import/export CSV y XLSX:
   - Crea app/services/__init__.py si no existe y
     app/services/import_export_service.py.
   - Funciones exportar_tarifas_a36_csv, exportar_tarifas_a36_xlsx,
     importar_tarifas_a36_csv con preview antes de escribir. Usa openpyxl
     para XLSX; si no está instalado, avísame y lo instalo con pip.
   - Idem para reglas y catálogos.
   - El botón Importar abre QFileDialog, lee el archivo, muestra diálogo
     con preview de filas (nuevas, conflictos, inválidas) y pide
     confirmación.

9. En el botón Eliminar de cada sección, antes de ejecutar chequea
   dependencias: si una tarifa A36 o catálogo está referenciado en N
   materiales, muestra confirmación contextual tipo "Esta tarifa aplica
   a N materiales existentes. Al eliminarla, esos materiales perderán
   su costo sugerido automático."

10. Atajos dentro de ConfigWindow: Ctrl+1..4 cambiar sección, Ctrl+F
    foco buscar, Ctrl+N nuevo, Ctrl+E exportar, Ctrl+I importar.

11. En main_window.py, cambia _abrir_modulo_tarifas_a36 para abrir
    ConfigWindow como ventana independiente no-modal (self.config_window
    guardado como atributo, no usar exec()).

12. Elimina o deprecia A36PriceManagerDialog. Mueve lo que se pueda
    reutilizar al nuevo módulo.

BLOQUE B - PdfViewerDialog rediseñado

13. Reescribe app/ui/pdf_viewer_dialog.py:

    a. Hazlo no modal (setModal(False)) y convierte la creación en
       main_window a self.pdf_viewer = PdfViewerDialog(...); self.pdf_viewer.show().

    b. Aplica tema oscuro forzado al diálogo, sin importar el tema global
       del sistema (usa un QSS local vía setStyleSheet que use los tokens
       DARK directamente). El contenido PDF se ve mejor sobre fondo oscuro.

    c. Reemplaza el QHBoxLayout de botones por una QToolBar con
       QToolButton icon-only:
       - chevron-left (página anterior)
       - chevron-right (página siguiente)
       - QLineEdit pequeño de 40px con número de página actual /
         QLabel con total de páginas
       - separador
       - QLineEdit de búsqueda con icono search placeholder "Buscar en
         el documento"
       - separador
       - minus (zoom out)
       - QLabel con porcentaje de zoom
       - plus (zoom in)
       - maximize (ajustar ancho)
       - separador
       - download (guardar como)
       - printer (imprimir)

    d. Implementa búsqueda con QPdfSearchModel. Navegación entre
       resultados con F3 (siguiente) y Shift+F3 (anterior).

    e. Implementa navegación por página conectada a pageNavigator del
       QPdfView.

    f. Implementa guardar como con QFileDialog.getSaveFileName y
       shutil.copy del archivo temporal.

    g. Implementa imprimir con QPrintDialog. Si QPdfView no expone
       método print directamente, renderiza página por página a
       QPrinter usando QPdfDocument.render.

    h. Footer con nombre del archivo, tamaño en KB/MB, total de páginas.

    i. Atajos: Ctrl++ zoom in, Ctrl+- zoom out, Ctrl+0 ajustar, Ctrl+1
       tamaño real, Ctrl+F buscar, PgDown/PgUp navegar páginas, Ctrl+S
       guardar como, Ctrl+P imprimir, Esc cerrar, F3 siguiente
       resultado, Shift+F3 anterior.

    j. Usa tempfile.TemporaryDirectory con context manager en lugar de
       NamedTemporaryFile con delete=False. Elimina el QMessageBox.warning
       de limpieza fallida, loguea a consola en su lugar.

    k. Estado de error de carga: si el PDF no carga, muestra widget
       inline con alert-triangle y mensaje, no QMessageBox ni raise.

BLOQUE C - Conmutación de tema en caliente

14. En app/ui/theme.py, modifica apply_theme para que se pueda llamar
    varias veces y reemplace QSS y palette en la QApplication actual.
    Emite una señal o expón una función toggle_theme que alterna claro y
    oscuro y guarda la preferencia en QSettings.

15. En main_window.py, conecta el botón de tema (sun/moon) y el atajo
    Ctrl+Shift+T a toggle_theme.

16. Verifica que todos los widgets (incluida ConfigWindow si está
    abierta) reflejan el cambio sin relanzar la app.

17. Verifica tema oscuro completo: tablas, formularios, toolbars, status
    bar, cards, empty states, toasts. Corrige cualquier color
    hardcodeado que se haya colado.

BLOQUE D - Limpieza final

18. Busca y elimina todos los QMessageBox que sobraron para feedback no
    crítico, reemplazándolos por Toast.

19. Verifica que no queda ninguna referencia a PASSWORD_ELIMINAR_FICHA
    ni a string hardcodeados de credencial en el repo.

20. Verifica que todos los labels tienen acentos correctos en español
    ("Código", "Contraseña", "Configuración", "Eliminar", etc).

21. Entrégame:
    - Checklist final de verificación manual.
    - Lista de deuda técnica pendiente que detectaste durante el
      rediseño y no era parte del scope.
    - Sugerencias de mejora futura (command palette Ctrl+K, docks en
      lugar de diálogos, auditoría de cambios, roles de usuario).

Reglas de esta fase:
- Si te bloquea la falta de QtPrintSupport o openpyxl, avísame para
  instalarlos antes de continuar.
- Si encuentras deuda técnica fuera del scope, no la arregles, solo
  anótala para el resumen final.

Empieza por el Bloque A y repórtame al terminar cada bloque.
```

**Después de la Fase 3, haz esto manualmente:**

```bash
cd "E:\SISTEMA DE COSTOS"
pip install openpyxl       # si no estaba instalado
python main.py
# Prueba conmutar tema con Ctrl+Shift+T.
# Abre Configuración (Ctrl+,), revisa las 4 secciones.
# Abre una ficha PDF, prueba búsqueda, zoom, guardar como, imprimir.
git add -A
git commit -m "fase 3: config window, visor PDF y tema oscuro completos"
```

---

## Checklist final de validación

Después de terminar las tres fases, verifica esto antes de considerar el rediseño hecho:

- Arranca sin errores en menos de 2 segundos.
- Búsqueda de materiales es instantánea (sin parpadeo, sin recarga de BD por tecla).
- Doble click en fila abre PDF. Click simple solo selecciona.
- Ctrl+F mueve el foco al buscador desde cualquier punto.
- Ctrl+N abre Nuevo material. Ctrl+, abre Configuración. Ctrl+Shift+C agrega costo.
- Ctrl+Shift+T conmuta entre tema claro y oscuro sin relanzar.
- Agregar costo muestra contexto del material y delta contra el costo vigente.
- Crear material muestra código autogenerado en vivo.
- Configuración abre como ventana, no modal. Puedes seguir usando la ventana principal mientras editas tarifas.
- Import CSV de tarifas A36 funciona con preview.
- Visor PDF tiene búsqueda, navegación por página, zoom, guardar como e imprimir.
- Todos los labels tienen acentos en español.
- Ningún `QMessageBox` como feedback de éxito (solo para confirmaciones destructivas).
- Ninguna credencial hardcodeada en el repo.
- Columnas numéricas de las tablas en `JetBrains Mono`, alineadas a la derecha.
- Contraste de texto legible en ambos temas.

---

## Si algo sale mal

Cada fase está en su propia rama/commit. Si algo rompe:

```bash
git log --oneline                    # ver commits
git reset --hard <hash-fase-anterior> # volver a fase anterior
```

Si un prompt falla a la mitad, dile a Claude: *"Para, no avances. Lo que llevas hasta ahora revirtelo. Vamos a rehacer el bloque X."*

---

## Ideas para después del rediseño

Cosas que no están en el scope pero valen la pena considerar una vez termines:

- Migración de `QTableWidget` a `QTableView` en cualquier lugar que quedara pendiente.
- Command palette global con `Ctrl+K` estilo Linear/VS Code.
- Auditoría de cambios: tabla `audit_log` que registre cada modificación de tarifa, regla, catálogo con usuario, timestamp y valor anterior.
- Sistema de roles (admin, consulta, captura) con `AuthService` y `bcrypt` para hashear contraseñas.
- Dashboard de resumen: materiales más consultados, últimos costos capturados, alertas de costos sin actualizar en > 30 días.
- Migración a Pervasive (ya tienes el comentario en `main.py` línea 10).
- Exportación de reportes a PDF con `reportlab`.
- Atajo de impresión directa de ficha técnica desde la tabla de materiales.
