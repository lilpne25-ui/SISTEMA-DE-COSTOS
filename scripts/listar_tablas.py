import os, sys
try:
    import pyodbc
except ImportError:
    sys.exit(1)

CONN_STR = (
    "DRIVER={Pervasive ODBC Unicode Interface};"
    f"ServerName={os.getenv('SISTEMA_COSTOS_PERVASIVE_SERVER', '192.168.1.168')};"
    f"DBQ={os.getenv('SISTEMA_COSTOS_PERVASIVE_DBQ', r'C:\USERS\TI\DESKTOP')};"
    f"UID={os.getenv('SISTEMA_COSTOS_PERVASIVE_USER', 'Master')};"
    f"PWD={os.getenv('SISTEMA_COSTOS_PERVASIVE_PASSWORD', 'COSTPP')};"
)

con = pyodbc.connect(CONN_STR, autocommit=True, timeout=10)
cur = con.cursor()
tablas = [row.table_name for row in cur.tables(tableType='TABLE')]
for t in sorted(tablas):
    print(t)
cur.close()
con.close()
