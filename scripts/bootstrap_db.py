"""
Crea las 3 tablas del esquema v3 en Pervasive si no existen.
Uso: python scripts/bootstrap_db.py
"""
import os, sys
try:
    import pyodbc
except ImportError:
    print("ERROR: pip install pyodbc")
    sys.exit(1)

CONN_STR = (
    "DRIVER={Pervasive ODBC Unicode Interface};"
    f"ServerName={os.getenv('SISTEMA_COSTOS_PERVASIVE_SERVER', '192.168.1.168')};"
    f"DBQ={os.getenv('SISTEMA_COSTOS_PERVASIVE_DBQ', r'C:\USERS\TI\DESKTOP')};"
    f"UID={os.getenv('SISTEMA_COSTOS_PERVASIVE_USER', 'Master')};"
    f"PWD={os.getenv('SISTEMA_COSTOS_PERVASIVE_PASSWORD', 'COSTPP')};"
)

def tabla_existe(cur, nombre):
    try:
        cur.execute(f"SELECT TOP 1 * FROM {nombre}")
        cur.fetchone()
        return True
    except Exception:
        return False

def run():
    con = pyodbc.connect(CONN_STR, autocommit=False, timeout=15)
    cur = con.cursor()
    print("Conectado.")

    if not tabla_existe(cur, "materiales"):
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
        print("  materiales creada.")
    else:
        print("  materiales ya existe.")

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
        print("  historial_costos creada.")
    else:
        print("  historial_costos ya existe.")

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
        print("  config creada.")
    else:
        print("  config ya existe.")

    # Índice en historial_costos
    try:
        cur.execute("CREATE INDEX idx_hc_material ON historial_costos (material_id)")
        con.commit()
    except Exception:
        pass

    cur.close()
    con.close()
    print("Listo. Tablas verificadas.")

if __name__ == "__main__":
    run()
