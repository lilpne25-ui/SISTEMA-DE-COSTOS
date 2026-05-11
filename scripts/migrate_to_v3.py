"""
Migración esquema v3 — Pervasive PSQL
======================================
Convierte de 9 tablas a 3 tablas:
  - materiales     (forma, tipo, material, precio_kg, densidad, espesor, ficha PDF)
  - historial_costos (ex-costos)
  - config           (catálogos, secuencias, meta)

Uso:
    python scripts/migrate_to_v3.py

Variables de entorno (opcionales):
    SISTEMA_COSTOS_PERVASIVE_SERVER   (default: 192.168.1.168)
    SISTEMA_COSTOS_PERVASIVE_DBQ      (default: C:\\USERS\\TI\\DESKTOP)
    SISTEMA_COSTOS_PERVASIVE_USER     (default: Master)
    SISTEMA_COSTOS_PERVASIVE_PASSWORD (default: COSTPP)
"""

import os
import sys

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc no está instalado. Ejecuta: pip install pyodbc")
    sys.exit(1)

SERVER   = os.getenv("SISTEMA_COSTOS_PERVASIVE_SERVER",   "192.168.1.168")
DBQ      = os.getenv("SISTEMA_COSTOS_PERVASIVE_DBQ",      r"C:\USERS\TI\DESKTOP")
USER     = os.getenv("SISTEMA_COSTOS_PERVASIVE_USER",     "Master")
PASSWORD = os.getenv("SISTEMA_COSTOS_PERVASIVE_PASSWORD", "COSTPP")

CONN_STR = (
    f"DRIVER={{Pervasive ODBC Unicode Interface}};"
    f"ServerName={SERVER};DBQ={DBQ};"
    f"UID={USER};PWD={PASSWORD};"
)


def connect():
    return pyodbc.connect(CONN_STR, autocommit=False, timeout=15)


def tabla_existe(cur, nombre: str) -> bool:
    try:
        cur.execute(f"SELECT TOP 1 * FROM {nombre}")
        cur.fetchone()
        return True
    except Exception:
        return False


def infer_material_cat(tipo: str) -> str:
    """Infiere categoría base (ACERO/ALUMINIO) a partir del grado/tipo."""
    t = (tipo or "").upper()
    if t.startswith("AL") or "ALUM" in t or "6061" in t or "7075" in t:
        return "ALUMINIO"
    return "ACERO"


def run():
    print("Conectando a Pervasive...")
    con = connect()
    cur = con.cursor()
    print(f"  OK — {SERVER} / {DBQ}")

    # ------------------------------------------------------------------ #
    # 1. BACKUP tabla materiales original                                  #
    # ------------------------------------------------------------------ #
    if not tabla_existe(cur, "materiales_bak"):
        print("\n[1/5] Respaldando materiales → materiales_bak ...")
        cur.execute("SELECT * INTO materiales_bak FROM materiales")
        con.commit()
        print("      OK")
    else:
        print("\n[1/5] materiales_bak ya existe, omitiendo backup.")

    # ------------------------------------------------------------------ #
    # 2. CREAR nuevas tablas si no existen                                 #
    # ------------------------------------------------------------------ #
    print("\n[2/5] Creando nuevas tablas...")

    if not tabla_existe(cur, "historial_costos"):
        cur.execute("""
            CREATE TABLE historial_costos (
                id          IDENTITY NOT NULL,
                material_id INTEGER NOT NULL,
                fecha       CHAR(10) NOT NULL,
                precio_kg   DECIMAL(12,4) NOT NULL,
                proveedor   VARCHAR(200) DEFAULT '',
                nota        VARCHAR(500) DEFAULT '',
                created_at  CHAR(19) DEFAULT '2000-01-01 00:00:00',
                PRIMARY KEY (id)
            )
        """)
        con.commit()
        print("      historial_costos creada")
    else:
        print("      historial_costos ya existe")

    if not tabla_existe(cur, "config"):
        cur.execute("""
            CREATE TABLE config (
                tipo  VARCHAR(50)  NOT NULL,
                clave VARCHAR(100) NOT NULL,
                valor VARCHAR(500) NOT NULL DEFAULT '',
                PRIMARY KEY (tipo, clave)
            )
        """)
        con.commit()
        print("      config creada")
    else:
        print("      config ya existe")

    # ------------------------------------------------------------------ #
    # 3. MIGRAR historial de costos                                        #
    # ------------------------------------------------------------------ #
    print("\n[3/5] Migrando costos → historial_costos ...")
    cur.execute("SELECT COUNT(*) FROM historial_costos")
    ya_migrados = cur.fetchone()[0]
    if ya_migrados == 0:
        if tabla_existe(cur, "costos"):
            cur.execute("""
                INSERT INTO historial_costos
                    (material_id, fecha, precio_kg, proveedor, nota, created_at)
                SELECT
                    material_id,
                    fecha,
                    precio_unitario,
                    COALESCE(proveedor, ''),
                    COALESCE(nota, ''),
                    COALESCE(created_at, '2000-01-01 00:00:00')
                FROM costos
            """)
            con.commit()
            cur.execute("SELECT COUNT(*) FROM historial_costos")
            n = cur.fetchone()[0]
            print(f"      {n} registros migrados")
        else:
            print("      tabla costos ya no existe — historial quedará vacío (re-ingresa precios desde la app)")
    else:
        print(f"      Ya hay {ya_migrados} registros, omitiendo.")

    # ------------------------------------------------------------------ #
    # 4. MIGRAR catálogos y secuencias → config                           #
    # ------------------------------------------------------------------ #
    print("\n[4/5] Migrando catálogos → config ...")
    cur.execute("SELECT COUNT(*) FROM config")
    ya_config = cur.fetchone()[0]

    if ya_config == 0:
        # cat_materiales
        if tabla_existe(cur, "cat_materiales"):
            cur.execute("SELECT nombre, prefijo_codigo FROM cat_materiales")
            for row in cur.fetchall():
                cur.execute(
                    "INSERT INTO config (tipo, clave, valor) VALUES ('cat_material', ?, ?)",
                    (row[0], row[1])
                )
        # catalogo_formas
        if tabla_existe(cur, "catalogo_formas"):
            cur.execute("SELECT nombre, prefijo_codigo FROM catalogo_formas")
            for row in cur.fetchall():
                cur.execute(
                    "INSERT INTO config (tipo, clave, valor) VALUES ('cat_forma', ?, ?)",
                    (row[0], row[1])
                )
        # secuencias_codigo
        if tabla_existe(cur, "secuencias_codigo"):
            cur.execute("SELECT material_prefijo, forma_prefijo, ultimo_numero FROM secuencias_codigo")
            for row in cur.fetchall():
                clave = f"{row[0]}-{row[1]}"
                cur.execute(
                    "INSERT INTO config (tipo, clave, valor) VALUES ('secuencia', ?, ?)",
                    (clave, str(row[2]))
                )
        con.commit()
        cur.execute("SELECT COUNT(*) FROM config")
        print(f"      {cur.fetchone()[0]} entradas en config")
    else:
        print(f"      Ya hay {ya_config} entradas, omitiendo.")

    # ------------------------------------------------------------------ #
    # 5. RECONSTRUIR tabla materiales con nuevo esquema                    #
    # ------------------------------------------------------------------ #
    print("\n[5/5] Reconstruyendo materiales con nuevo esquema ...")

    # Verificar si la tabla ya tiene el nuevo esquema con datos
    tiene_nuevo_esquema = False
    try:
        cur.execute("SELECT COUNT(*) FROM materiales WHERE precio_kg IS NOT NULL")
        n_filas = cur.fetchone()[0]
        if n_filas > 0:
            tiene_nuevo_esquema = True
    except Exception:
        pass

    if tiene_nuevo_esquema:
        print("      La tabla materiales ya tiene el nuevo esquema con datos, omitiendo.")
    else:
        # Obtener precio más reciente por material para desnormalizar
        print("      Obteniendo precios vigentes...")
        precios = {}
        if tabla_existe(cur, "historial_costos"):
            cur.execute("SELECT COUNT(*) FROM historial_costos")
            if cur.fetchone()[0] > 0:
                cur.execute("""
                    SELECT material_id, precio_kg
                    FROM historial_costos h1
                    WHERE id = (
                        SELECT TOP 1 id FROM historial_costos h2
                        WHERE h2.material_id = h1.material_id
                        ORDER BY fecha DESC, id DESC
                    )
                """)
                precios = {row[0]: float(row[1]) for row in cur.fetchall()}
        if not precios:
            print("      Sin historial de precios — precio_kg quedará en 0 (actualiza desde la app)")

        # Obtener PDFs desde mat_archivos (si existe)
        pdfs = {}
        if tabla_existe(cur, "mat_archivos"):
            cur.execute("""
                SELECT material_id, nombre_archivo, contenido_blob
                FROM mat_archivos
                WHERE tipo = 'ficha_tecnica_pdf'
            """)
            for row in cur.fetchall():
                pdfs[row[0]] = (row[1], row[2])

        # Leer datos actuales desde el backup
        cur.execute("""
            SELECT id, codigo, nombre, tipo, forma, espesor_pulgadas,
                   densidad, ficha_tecnica_pdf
            FROM materiales_bak
        """)
        filas = cur.fetchall()

        # Guardar historial_costos en memoria para re-insertar con IDs remapeados
        print("      Guardando historial_costos en memoria para re-insertar...")
        cur.execute("SELECT material_id, fecha, precio_kg, proveedor, nota, created_at FROM historial_costos")
        historial_rows = cur.fetchall()

        # Eliminar tablas que referencian materiales (FKs)
        print("      Eliminando tablas dependientes...")
        for dep in ["historial_costos", "costos", "mat_archivos"]:
            try:
                cur.execute(f"DROP TABLE {dep}")
                con.commit()
                print(f"        DROP {dep} OK")
            except Exception:
                pass  # no existía o ya fue eliminada

        print("      Eliminando tabla materiales antigua...")
        cur.execute("DROP TABLE materiales")
        con.commit()

        print("      Creando tabla materiales con nuevo esquema...")
        cur.execute("""
            CREATE TABLE materiales (
                id              IDENTITY NOT NULL,
                codigo          VARCHAR(50)  NOT NULL,
                forma           VARCHAR(50)  NOT NULL DEFAULT '',
                tipo            VARCHAR(50)  NOT NULL DEFAULT '',
                material        VARCHAR(50)  NOT NULL DEFAULT '',
                precio_kg       DECIMAL(12,4) NOT NULL DEFAULT 0,
                densidad        FLOAT,
                espesor         DECIMAL(10,4),
                ficha_pdf_nombre VARCHAR(255) DEFAULT '',
                ficha_pdf_blob  LONGVARBINARY,
                created_at      CHAR(19) DEFAULT '2000-01-01 00:00:00',
                updated_at      CHAR(19) DEFAULT '2000-01-01 00:00:00',
                PRIMARY KEY (id),
                UNIQUE (codigo)
            )
        """)
        con.commit()

        # Los blobs PDF se omiten durante la migración para evitar timeouts ODBC.
        # Re-sube los PDFs desde la app después de verificar la migración.
        con_pdf = sum(1 for old_id in pdfs if old_id in {f[0] for f in filas})
        if con_pdf:
            print(f"      AVISO: {con_pdf} PDFs omitidos (re-súbelos desde la app)")

        print(f"      Insertando {len(filas)} materiales y construyendo mapa old_id→new_id...")
        old_to_new = {}  # old_id → new_id para re-mapear historial_costos
        for fila in filas:
            old_id, codigo, nombre, tipo_old, forma, espesor, densidad, ficha_nombre = fila
            grado = nombre or tipo_old or ""
            material_cat = infer_material_cat(grado)
            precio = precios.get(old_id, 0.0)
            pdf_nombre = ""
            if old_id in pdfs:
                pdf_nombre = pdfs[old_id][0]  # solo el nombre, sin blob
            elif ficha_nombre:
                pdf_nombre = ficha_nombre

            cur.execute("""
                INSERT INTO materiales
                    (codigo, forma, tipo, material, precio_kg, densidad, espesor,
                     ficha_pdf_nombre, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '2000-01-01 00:00:00', '2000-01-01 00:00:00')
            """, (
                codigo, forma or "", grado, material_cat, precio,
                densidad, espesor, pdf_nombre
            ))
            # Obtener el nuevo ID asignado por IDENTITY
            cur.execute("SELECT id FROM materiales WHERE codigo = ?", (codigo,))
            new_row = cur.fetchone()
            if new_row:
                old_to_new[old_id] = new_row[0]

        con.commit()
        cur.execute("SELECT COUNT(*) FROM materiales")
        print(f"      {cur.fetchone()[0]} materiales insertados con nuevo esquema")

        # Recrear historial_costos (sin FK para evitar conflictos futuros)
        print("      Recreando historial_costos...")
        cur.execute("""
            CREATE TABLE historial_costos (
                id          IDENTITY NOT NULL,
                material_id INTEGER NOT NULL,
                fecha       CHAR(10) NOT NULL,
                precio_kg   DECIMAL(12,4) NOT NULL,
                proveedor   VARCHAR(200) DEFAULT '',
                nota        VARCHAR(500) DEFAULT '',
                created_at  CHAR(19) DEFAULT '2000-01-01 00:00:00',
                PRIMARY KEY (id)
            )
        """)
        con.commit()

        print(f"      Re-insertando {len(historial_rows)} registros de historial (con IDs remapeados)...")
        omitidos = 0
        for hrow in historial_rows:
            old_mat_id = hrow[0]
            new_mat_id = old_to_new.get(old_mat_id)
            if new_mat_id is None:
                omitidos += 1
                continue
            cur.execute("""
                INSERT INTO historial_costos (material_id, fecha, precio_kg, proveedor, nota, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_mat_id, hrow[1], hrow[2], hrow[3] or "", hrow[4] or "", hrow[5] or "2000-01-01 00:00:00"))
        con.commit()
        if omitidos:
            print(f"      AVISO: {omitidos} registros omitidos (material_id sin correspondencia)")
        cur.execute("SELECT COUNT(*) FROM historial_costos")
        print(f"      {cur.fetchone()[0]} registros en historial_costos")

    # ------------------------------------------------------------------ #
    # Crear índice en historial_costos                                    #
    # ------------------------------------------------------------------ #
    try:
        cur.execute("CREATE INDEX idx_hc_material ON historial_costos (material_id)")
        con.commit()
    except Exception:
        pass  # ya existe

    cur.close()
    con.close()

    print("\n" + "="*60)
    print("MIGRACIÓN COMPLETADA")
    print("="*60)
    print("Tablas nuevas:  materiales, historial_costos, config")
    print("Tablas backup:  materiales_bak  (puedes eliminarlas cuando verifiques)")
    print("Tablas antiguas que ya no se usan (eliminar manualmente si todo OK):")
    print("  costos, cat_materiales, catalogo_formas, secuencias_codigo,")
    print("  precios_a36_placa, reglas_costo, mat_archivos")
    print()
    print("IMPORTANTE: Revisa la columna 'material' en materiales.")
    print("  Se infirió automáticamente (AL*/ALUM* = ALUMINIO, resto = ACERO).")
    print("  Corrígela manualmente si algún valor es incorrecto.")


if __name__ == "__main__":
    run()
