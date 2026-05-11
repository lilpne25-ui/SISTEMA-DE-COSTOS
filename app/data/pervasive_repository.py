"""
Repositorio Pervasive PSQL v13 — esquema v4 (4 tablas).

Tablas reales en la BD Pervasive (NO modificar sin actualizar este archivo):
  sistema_meta     — metadatos del sistema (versión de esquema, etc.) — solo lectura desde la app
  materiales       — registros de materiales; columnas clave:
                       id (IDENTITY), codigo, forma, tipo, material,
                       precio_kg, densidad, espesor, ficha_pdf_nombre,
                       ficha_pdf_blob, created_at, updated_at
                     NOTA DE MAPEO: model.nombre → columna DB 'tipo' (grado: A36, S7, 1045)
                                    model.tipo   → columna DB 'material' (categoría: ACERO, ALUMINIO)
  historial_costos — historial de precios por material; columnas clave:
                       id (IDENTITY), material_id (FK→materiales), fecha,
                       precio_kg, proveedor, nota, created_at
  config           — configuración clave-valor; tipos usados:
                       'cat_material' → catálogo de nombres de material
                       'tipo_base_material' → tipo/categoría base por material (ACERO, ALUMINIO...)
                       'densidad_material' → densidad por material (kg/m³)
                       'cat_forma'    → catálogo de formas
                       'secuencia'    → contadores para generación de códigos

REGLAS PARA EXTENDER ESTE REPOSITORIO:
  1. Toda consulta SQL que filtre por grado (A36, S7...) debe usar la columna 'tipo'.
  2. Toda consulta que filtre por categoría (ACERO, ALUMINIO) debe usar la columna 'material'.
  3. Las tarifas A36 son filas en 'materiales' donde tipo='A36' y espesor IS NOT NULL
     (espesor = espesor_min). espesor_max y rango_label viven en 'config':
       tipo='a36_max' clave=str(material_id) valor=str(espesor_max)
       tipo='a36_lbl' clave=str(material_id) valor=rango_label
  4. Las columnas de texto en Pervasive son CHAR (longitud fija) — los valores se
     almacenan con padding de espacios. SIEMPRE usar LTRIM(RTRIM(col)) al comparar
     strings en WHERE. Ej: UPPER(LTRIM(RTRIM(tipo))) = 'A36', nunca UPPER(tipo) = 'A36'.
     BUG CONOCIDO DEL DRIVER ODBC: al bindear Python float a columnas DECIMAL, el driver
     trunca a entero (0.125 → 0, 7.85 → 7). SIEMPRE usar _dec() para convertir floats
     a Decimal antes de pasarlos como parámetros en INSERT/UPDATE.
  5. NO asumir columnas extra sin verificar en la BD real. Si se agrega una tabla,
     documentarla aquí antes de escribir código que la use.
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime
from typing import Any, List, Optional

try:
    import pyodbc  # type: ignore
except Exception:
    pyodbc = None  # type: ignore

from app.data.repository import Repository
from app.models.catalogo_item import CatalogoItem
from app.models.costo import Costo
from app.models.llm_bom_run import LlmBomRun
from app.models.material import Material
from app.models.precio_a36_placa import PrecioA36Placa
from app.models.regla_costo import ReglaCosto


class PervasiveRepository(Repository):
    _CATALOGO_MATERIALES_PRELOAD: tuple[tuple[str, str, str, float], ...] = (
        ("A36", "A36", "ACERO", 7850.0),
        ("4140", "4140", "ACERO", 7850.0),
        ("8620", "8620", "ACERO", 7850.0),
        ("S7", "S7", "ACERO", 7850.0),
        ("BRONCE 841", "BR841", "BRONCE", 8800.0),
        ("ALUMINIO 6061", "AL6061", "ALUMINIO", 2700.0),
    )

    def __init__(
        self,
        dsn: str = "",
        user: str = "",
        password: str = "",
        *,
        server: str = "",
        dbq: str = "",
        actor: str = "system",
        timeout_seconds: int = 8,
        max_retries: int = 2,
    ):
        if pyodbc is None:
            raise RuntimeError(
                "pyodbc no está instalado para este entorno. "
                "Instálalo en un Python compatible y configura el DSN de Pervasive."
            )

        self._actor = (actor or "system").strip() or "system"
        self._timeout_seconds = max(2, int(timeout_seconds))
        self._max_retries = max(1, int(max_retries))

        if server and dbq:
            conn_str = f"DRIVER={{Pervasive ODBC Unicode Interface}};ServerName={server};DBQ={dbq};"
        elif dsn:
            conn_str = f"DSN={dsn};"
        else:
            raise ValueError("Se requiere DSN o (server + dbq) para conectar a Pervasive.")
        if user:
            conn_str += f"UID={user};PWD={password};"
        self._conn_str = conn_str

    # ------------------------------------------------------------------ #
    # Utilidades internas                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _dec(value) -> Optional[Decimal]:
        """Convierte float→Decimal para que pyodbc use SQL_NUMERIC al bindear a columnas DECIMAL
        de Pervasive. Sin esto el driver ODBC trunca valores <1 (ej. 0.125 → 0)."""
        if value is None:
            return None
        return Decimal(str(round(float(value), 6)))

    @staticmethod
    def _ahora() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _normalizar_prefijo(prefijo: str, fallback: str = "GEN") -> str:
        limpio = re.sub(r"[^A-Z0-9]+", "", (prefijo or "").upper())
        return (limpio or fallback)[:8]

    def _friendly_error(self, exc: Exception) -> Exception:
        msg = str(exc)
        if "IM002" in msg:
            return RuntimeError(
                "No se encontró el driver ODBC de Pervasive.\n"
                "Instala el cliente Pervasive PSQL v13 y vuelve a intentarlo."
            )
        if "28000" in msg or "Login failed" in msg:
            return RuntimeError("Credenciales inválidas para Pervasive.")
        return RuntimeError(f"Error de base de datos: {msg}")

    def _connect_once(self):
        assert pyodbc is not None
        # autocommit=True: Pervasive PSQL con tablas Btrieve no soporta transacciones
        # SQL completas — con autocommit=False los datos no se persisten entre sesiones.
        return pyodbc.connect(self._conn_str, autocommit=True, timeout=self._timeout_seconds)

    def _connect(self):
        last_exc: Exception | None = None
        for _ in range(self._max_retries):
            try:
                return self._connect_once()
            except Exception as exc:
                last_exc = exc
        raise self._friendly_error(last_exc or RuntimeError("Conexión fallida"))

    @staticmethod
    def _row_dict(cursor, row) -> dict[str, Any]:
        cols = [c[0] for c in cursor.description]
        return {cols[i]: row[i] for i in range(len(cols))}

    @contextmanager
    def _tx(self):
        con = self._connect()
        try:
            yield con
        finally:
            con.close()

    def _scalar(self, con, sql: str, params: tuple = ()):
        cur = con.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None

    # ------------------------------------------------------------------ #
    # Mapeo filas → modelos                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_material(row: dict[str, Any]) -> Material:
        return Material(
            id=row["id"],
            codigo=row["codigo"],
            nombre=row.get("tipo") or "",           # grado: A36, S7...
            tipo=row.get("material") or "",          # categoría: ACERO, ALUMINIO
            forma=row.get("forma") or "",
            espesor_pulgadas=float(row["espesor"]) if row.get("espesor") is not None else None,
            densidad=float(row["densidad"]) if row.get("densidad") is not None else None,
            ficha_tecnica_pdf=row.get("ficha_pdf_nombre") or "",
            precio_actual=float(row["precio_kg"]) if row.get("precio_kg") else None,
        )

    @staticmethod
    def _row_to_costo(row: dict[str, Any]) -> Costo:
        fecha_raw = row["fecha"]
        if hasattr(fecha_raw, "strftime"):
            fecha = fecha_raw
        else:
            fecha = datetime.strptime(str(fecha_raw)[:10], "%Y-%m-%d").date()
        return Costo(
            id=row["id"],
            material_id=row["material_id"],
            fecha=fecha,
            precio_unitario=float(row["precio_kg"]),
            moneda="MXN",
            unidad="kg",
            proveedor=row.get("proveedor") or "",
            nota=row.get("nota") or "",
        )

    @staticmethod
    def _row_to_catalogo_item(
        nombre: str,
        valor: str,
        item_id: int = 0,
        tipo_base: str = "",
        densidad_kg_m3: Optional[float] = None,
    ) -> CatalogoItem:
        return CatalogoItem(
            id=item_id,
            nombre=nombre,
            prefijo_codigo=valor,
            tipo_base=(tipo_base or "").strip(),
            densidad_kg_m3=densidad_kg_m3,
        )

    @staticmethod
    def _row_to_llm_bom_run(row: dict[str, Any]) -> LlmBomRun:
        return LlmBomRun(
            id=int(row.get("id") or 0),
            created_at=(str(row.get("created_at") or "").strip()),
            project_name=(str(row.get("project_name") or "").strip()),
            actor=(str(row.get("actor") or "").strip()),
            status=(str(row.get("status") or "").strip()),
            source_path=(str(row.get("source_path") or "").strip()),
            output_path=(str(row.get("output_path") or "").strip()),
            source_hash=(str(row.get("source_hash") or "").strip()),
            output_hash=(str(row.get("output_hash") or "").strip()),
            total_rows=int(row.get("total_rows") or 0),
            ok_rows=int(row.get("ok_rows") or 0),
            warn_rows=int(row.get("warn_rows") or 0),
            total_cost_mxn=float(row.get("total_cost") or 0.0),
            notes=(str(row.get("notes") or "").strip()),
        )

    @staticmethod
    def _norm_key(value: str) -> str:
        return (value or "").strip().upper()

    def _insert_config_if_missing(self, con, tipo: str, clave: str, valor: str) -> None:
        key = (clave or "").strip()
        if not key:
            return
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM config WHERE tipo=? AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
            (tipo, key),
        )
        exists = int(cur.fetchone()[0] or 0)
        if not exists:
            cur.execute(
                "INSERT INTO config (tipo, clave, valor) VALUES (?, ?, ?)",
                (tipo, key, str(valor)),
            )
        cur.close()

    def precargar_catalogo_materiales(self) -> None:
        with self._tx() as con:
            for nombre, prefijo, tipo_base, densidad in self._CATALOGO_MATERIALES_PRELOAD:
                mat = (nombre or "").strip()
                if not mat:
                    continue
                pref = self._normalizar_prefijo(prefijo, fallback=mat)
                self._insert_config_if_missing(con, "cat_material", mat, pref)
                self._insert_config_if_missing(con, "tipo_base_material", mat, (tipo_base or "").strip().upper())
                self._insert_config_if_missing(con, "densidad_material", mat, str(round(float(densidad), 3)))

    def _upsert_densidad_material(self, con, material_nombre: str, densidad_kg_m3: Optional[float]) -> None:
        clave = (material_nombre or "").strip()
        if not clave:
            return
        cur = con.cursor()
        if densidad_kg_m3 is None or float(densidad_kg_m3) <= 0:
            cur.execute("DELETE FROM config WHERE tipo='densidad_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)", (clave,))
        else:
            densidad_txt = str(round(float(densidad_kg_m3), 3))
            cur.execute(
                "SELECT COUNT(*) FROM config WHERE tipo='densidad_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                (clave,),
            )
            exists = int(cur.fetchone()[0] or 0)
            if exists:
                cur.execute(
                    "UPDATE config SET valor=? WHERE tipo='densidad_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                    (densidad_txt, clave),
                )
            else:
                cur.execute(
                    "INSERT INTO config (tipo, clave, valor) VALUES ('densidad_material', ?, ?)",
                    (clave, densidad_txt),
                )
        cur.close()

    def _upsert_tipo_base_material(self, con, material_nombre: str, tipo_base: str) -> None:
        clave = (material_nombre or "").strip()
        if not clave:
            return
        valor = (tipo_base or "").strip().upper()
        cur = con.cursor()
        if not valor:
            cur.execute(
                "DELETE FROM config WHERE tipo='tipo_base_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                (clave,),
            )
        else:
            cur.execute(
                "SELECT COUNT(*) FROM config WHERE tipo='tipo_base_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                (clave,),
            )
            exists = int(cur.fetchone()[0] or 0)
            if exists:
                cur.execute(
                    "UPDATE config SET valor=? WHERE tipo='tipo_base_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                    (valor, clave),
                )
            else:
                cur.execute(
                    "INSERT INTO config (tipo, clave, valor) VALUES ('tipo_base_material', ?, ?)",
                    (clave, valor),
                )
        cur.close()

    # ------------------------------------------------------------------ #
    # Generación de código (usa tabla config tipo='secuencia')            #
    # ------------------------------------------------------------------ #

    def _next_codigo(self, con, material_nombre: str, forma_nombre: str) -> str:
        mat_pref = self._normalizar_prefijo(material_nombre, "MAT")
        for_pref = self._normalizar_prefijo(forma_nombre, "FOR")
        clave = f"{mat_pref}-{for_pref}"

        cur = con.cursor()
        cur.execute("SELECT valor FROM config WHERE tipo='secuencia' AND clave=?", (clave,))
        row = cur.fetchone()
        if row:
            siguiente = int(row[0]) + 1
            cur.execute(
                "UPDATE config SET valor=? WHERE tipo='secuencia' AND clave=?",
                (str(siguiente), clave),
            )
        else:
            siguiente = 1
            cur.execute(
                "INSERT INTO config (tipo, clave, valor) VALUES ('secuencia', ?, ?)",
                (clave, str(siguiente)),
            )
        cur.close()
        return f"{mat_pref}-{for_pref}-{siguiente:04d}"

    # ------------------------------------------------------------------ #
    # Materiales                                                           #
    # ------------------------------------------------------------------ #

    def listar_materiales(self, filtro_tipo=None, busqueda=None) -> List[Material]:
        sql = "SELECT id, codigo, forma, tipo, material, precio_kg, densidad, espesor, ficha_pdf_nombre FROM materiales WHERE 1=1"
        params: list[Any] = []

        if filtro_tipo and filtro_tipo != "Todos":
            sql += " AND (UPPER(LTRIM(RTRIM(tipo)))=UPPER(?) OR UPPER(LTRIM(RTRIM(material)))=UPPER(?))"
            params.extend([filtro_tipo, filtro_tipo])
        if busqueda:
            like = f"%{busqueda}%"
            sql += " AND (codigo LIKE ? OR LTRIM(RTRIM(tipo)) LIKE ? OR LTRIM(RTRIM(forma)) LIKE ? OR LTRIM(RTRIM(material)) LIKE ?)"
            params.extend([like, like, like, like])
        sql += " ORDER BY tipo, forma, espesor, material"

        with self._tx() as con:
            cur = con.cursor()
            cur.execute(sql, tuple(params))
            rows = [self._row_to_material(self._row_dict(cur, r)) for r in cur.fetchall()]
            cur.close()
            return rows

    def obtener_material(self, material_id: int) -> Optional[Material]:
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT id, codigo, forma, tipo, material, precio_kg, densidad, espesor, ficha_pdf_nombre FROM materiales WHERE id=?",
                (material_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.close()
                return None
            result = self._row_to_material(self._row_dict(cur, row))
            cur.close()
            return result

    def crear_material(self, material: Material) -> int:
        with self._tx() as con:
            if not material.codigo.strip():
                material.codigo = self._next_codigo(con, material.nombre, material.forma)
            ahora = self._ahora()
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO materiales
                    (codigo, forma, tipo, material, precio_kg, densidad, espesor,
                     ficha_pdf_nombre, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    material.codigo,
                    material.forma or "",
                    material.nombre,
                    material.tipo or "",
                    self._dec(material.precio_actual or 0.0),
                    self._dec(material.densidad),
                    self._dec(material.espesor_pulgadas),
                    material.ficha_tecnica_pdf or "",
                    ahora, ahora,
                ),
            )
            new_id = int(self._scalar(con, "SELECT @@IDENTITY"))
            cur.close()
            return new_id

    def crear_material_con_costo_inicial(self, material: Material, costo: Costo) -> int:
        with self._tx() as con:
            if not material.codigo.strip():
                material.codigo = self._next_codigo(con, material.nombre, material.forma)
            ahora = self._ahora()
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO materiales
                    (codigo, forma, tipo, material, precio_kg, densidad, espesor,
                     ficha_pdf_nombre, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    material.codigo,
                    material.forma or "",
                    material.nombre,
                    material.tipo or "",
                    self._dec(costo.precio_unitario),
                    self._dec(material.densidad),
                    self._dec(material.espesor_pulgadas),
                    material.ficha_tecnica_pdf or "",
                    ahora, ahora,
                ),
            )
            material_id = int(self._scalar(con, "SELECT @@IDENTITY"))

            cur.execute(
                """
                INSERT INTO historial_costos
                    (material_id, fecha, precio_kg, proveedor, nota, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    material_id,
                    costo.fecha.strftime("%Y-%m-%d"),
                    self._dec(costo.precio_unitario),
                    costo.proveedor or "",
                    costo.nota or "",
                    ahora,
                ),
            )
            cur.close()
            return material_id

    def actualizar_material(self, material: Material) -> None:
        with self._tx() as con:
            ahora = self._ahora()

            tipo_db = material.nombre
            categoria_db = material.tipo or ""
            forma_db = material.forma or ""
            espesor_db = self._dec(material.espesor_pulgadas)

            if material.id is not None and self._es_tarifa_a36_id(con, material.id):
                cur_keep = con.cursor()
                cur_keep.execute(
                    "SELECT tipo, material, forma, espesor FROM materiales WHERE id=?",
                    (material.id,),
                )
                row_keep = cur_keep.fetchone()
                cur_keep.close()
                if row_keep:
                    tipo_db = row_keep[0]
                    categoria_db = row_keep[1]
                    forma_db = row_keep[2]
                    espesor_db = self._dec(float(row_keep[3])) if row_keep[3] is not None else None

            cur = con.cursor()
            cur.execute(
                """
                UPDATE materiales
                SET codigo=?, forma=?, tipo=?, material=?, densidad=?, espesor=?,
                    ficha_pdf_nombre=?, updated_at=?
                WHERE id=?
                """,
                (
                    material.codigo,
                    forma_db,
                    tipo_db,
                    categoria_db,
                    self._dec(material.densidad),
                    espesor_db,
                    material.ficha_tecnica_pdf or "",
                    ahora,
                    material.id,
                ),
            )
            cur.close()

    def eliminar_material(self, material_id: int) -> None:
        with self._tx() as con:
            self._a36_delete_meta(con, material_id)
            cur = con.cursor()
            cur.execute("DELETE FROM historial_costos WHERE material_id=?", (material_id,))
            cur.execute("DELETE FROM materiales WHERE id=?", (material_id,))
            cur.close()

    def tipos_material(self) -> List[str]:
        with self._tx() as con:
            cur = con.cursor()
            cur.execute("SELECT DISTINCT tipo FROM materiales WHERE LTRIM(RTRIM(tipo)) <> '' ORDER BY tipo")
            tipos = [str(r[0]).strip() for r in cur.fetchall() if str(r[0]).strip()]
            cur.close()
            return tipos

    def actualizar_ficha_tecnica_pdf(self, material_id: int, nombre_archivo: str, contenido_pdf: bytes) -> None:
        nombre = (nombre_archivo or "").strip()
        if not nombre:
            raise ValueError("El nombre del archivo PDF es obligatorio.")
        if not contenido_pdf:
            raise ValueError("El contenido del PDF está vacío.")
        with self._tx() as con:
            ahora = self._ahora()
            cur = con.cursor()
            cur.execute(
                """
                UPDATE materiales
                SET ficha_pdf_nombre=?, ficha_pdf_blob=?, updated_at=?
                WHERE id=?
                """,
                (nombre, pyodbc.Binary(contenido_pdf), ahora, material_id),
            )
            cur.close()

    def obtener_ficha_tecnica_pdf(self, material_id: int) -> Optional[tuple[str, bytes]]:
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT ficha_pdf_nombre, ficha_pdf_blob FROM materiales WHERE id=?",
                (material_id,),
            )
            row = cur.fetchone()
            cur.close()
            if not row or not row[1]:
                return None
            return row[0], bytes(row[1])

    def eliminar_ficha_tecnica_pdf(self, material_id: int) -> None:
        with self._tx() as con:
            ahora = self._ahora()
            cur = con.cursor()
            cur.execute(
                "UPDATE materiales SET ficha_pdf_nombre='', ficha_pdf_blob=NULL, updated_at=? WHERE id=?",
                (ahora, material_id),
            )
            cur.close()

    # ------------------------------------------------------------------ #
    # Catálogos (tabla config)                                            #
    # ------------------------------------------------------------------ #

    def listar_catalogo_materiales(self) -> List[CatalogoItem]:
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT LTRIM(RTRIM(clave)), LTRIM(RTRIM(valor)) "
                "FROM config WHERE tipo='cat_material' ORDER BY clave"
            )
            rows_cat = cur.fetchall()
            cur.close()

            cur_den = con.cursor()
            cur_den.execute(
                "SELECT LTRIM(RTRIM(clave)), LTRIM(RTRIM(valor)) "
                "FROM config WHERE tipo='densidad_material'"
            )
            dens_cfg: dict[str, float] = {}
            for clave, valor in cur_den.fetchall():
                try:
                    dens_cfg[self._norm_key(str(clave))] = float(valor)
                except Exception:
                    pass
            cur_den.close()

            cur_tipo = con.cursor()
            cur_tipo.execute(
                "SELECT LTRIM(RTRIM(clave)), LTRIM(RTRIM(valor)) "
                "FROM config WHERE tipo='tipo_base_material'"
            )
            tipo_cfg: dict[str, str] = {}
            for clave, valor in cur_tipo.fetchall():
                key = self._norm_key(str(clave))
                if key:
                    tipo_cfg[key] = str(valor or "").strip().upper()
            cur_tipo.close()

            cur_fb = con.cursor()
            cur_fb.execute(
                "SELECT LTRIM(RTRIM(tipo)), LTRIM(RTRIM(material)), densidad FROM materiales "
                "WHERE LTRIM(RTRIM(tipo)) <> '' ORDER BY id DESC"
            )
            dens_fb: dict[str, float] = {}
            tipo_fb: dict[str, str] = {}
            for tipo, categoria, densidad in cur_fb.fetchall():
                key = self._norm_key(str(tipo))
                if not key:
                    continue
                if key not in dens_fb and densidad is not None:
                    dens_fb[key] = float(densidad)
                if key not in tipo_fb:
                    tipo_fb[key] = str(categoria or "").strip().upper()
            cur_fb.close()

            items: list[CatalogoItem] = []
            for nombre, prefijo in rows_cat:
                key = self._norm_key(str(nombre))
                tipo_base = tipo_cfg.get(key)
                if not tipo_base:
                    tipo_base = tipo_fb.get(key, "")
                densidad = dens_cfg.get(key)
                if densidad is None:
                    densidad = dens_fb.get(key)
                items.append(
                    self._row_to_catalogo_item(
                        str(nombre).strip(),
                        str(prefijo).strip(),
                        item_id=str(nombre).strip(),
                        tipo_base=tipo_base,
                        densidad_kg_m3=densidad,
                    )
                )
            return items

    def crear_catalogo_material(self, item: CatalogoItem) -> int:
        nombre = (item.nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio.")
        pref = self._normalizar_prefijo(item.prefijo_codigo, fallback=nombre)
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO config (tipo, clave, valor) VALUES ('cat_material', ?, ?)",
                (nombre, pref),
            )
            cur.close()
            self._upsert_tipo_base_material(con, nombre, item.tipo_base)
            self._upsert_densidad_material(con, nombre, item.densidad_kg_m3)
        return 0

    def actualizar_catalogo_material(self, item: CatalogoItem) -> None:
        nombre = (item.nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio.")
        pref = self._normalizar_prefijo(item.prefijo_codigo, fallback=nombre)
        original = str(item.id or "").strip() or nombre
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE config SET clave=?, valor=? WHERE tipo='cat_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                (nombre, pref, original),
            )
            cur.close()
            if self._norm_key(original) != self._norm_key(nombre):
                cur_ren = con.cursor()
                cur_ren.execute(
                    "UPDATE config SET clave=? WHERE tipo='densidad_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                    (nombre, original),
                )
                cur_ren.execute(
                    "UPDATE config SET clave=? WHERE tipo='tipo_base_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                    (nombre, original),
                )
                cur_ren.close()
            self._upsert_tipo_base_material(con, nombre, item.tipo_base)
            self._upsert_densidad_material(con, nombre, item.densidad_kg_m3)

    def eliminar_catalogo_material(self, item_id: int | str) -> None:
        clave = str(item_id or "").strip()
        if not clave:
            raise ValueError("El nombre del catálogo es obligatorio para eliminar.")
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "DELETE FROM config WHERE tipo='cat_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                (clave,),
            )
            cur.execute(
                "DELETE FROM config WHERE tipo='densidad_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                (clave,),
            )
            cur.execute(
                "DELETE FROM config WHERE tipo='tipo_base_material' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                (clave,),
            )
            cur.close()

    def listar_catalogo_formas(self) -> List[CatalogoItem]:
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT LTRIM(RTRIM(clave)), LTRIM(RTRIM(valor)) "
                "FROM config WHERE tipo='cat_forma' ORDER BY clave"
            )
            items = [self._row_to_catalogo_item(r[0], r[1], item_id=str(r[0]).strip()) for r in cur.fetchall()]
            cur.close()
            return items

    def crear_catalogo_forma(self, item: CatalogoItem) -> int:
        nombre = (item.nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio.")
        pref = self._normalizar_prefijo(item.prefijo_codigo, fallback=nombre)
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO config (tipo, clave, valor) VALUES ('cat_forma', ?, ?)",
                (nombre, pref),
            )
            cur.close()
        return 0

    def actualizar_catalogo_forma(self, item: CatalogoItem) -> None:
        nombre = (item.nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio.")
        pref = self._normalizar_prefijo(item.prefijo_codigo, fallback=nombre)
        original = str(item.id or "").strip() or nombre
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE config SET clave=?, valor=? WHERE tipo='cat_forma' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                (nombre, pref, original),
            )
            cur.close()

    def eliminar_catalogo_forma(self, item_id: int | str) -> None:
        clave = str(item_id or "").strip()
        if not clave:
            raise ValueError("El nombre del catálogo es obligatorio para eliminar.")
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                "DELETE FROM config WHERE tipo='cat_forma' AND UPPER(LTRIM(RTRIM(clave)))=UPPER(?)",
                (clave,),
            )
            cur.close()

    def generar_codigo_material(self, material_nombre: str, forma_nombre: str) -> str:
        with self._tx() as con:
            return self._next_codigo(con, material_nombre.strip(), forma_nombre.strip())

    # ------------------------------------------------------------------ #
    # Tarifas A36 — filas en 'materiales' + metadatos en 'config'         #
    # materiales.espesor  = espesor_min                                   #
    # config tipo='a36_max' clave=str(id) valor=str(espesor_max)          #
    # config tipo='a36_lbl' clave=str(id) valor=rango_label               #
    # ------------------------------------------------------------------ #

    def _a36_meta(self, con, mat_id: int) -> tuple[float, str]:
        """Devuelve (espesor_max, rango_label) desde config para un material A36."""
        cur = con.cursor()
        cur.execute(
            "SELECT tipo, valor FROM config WHERE tipo IN ('a36_max','a36_lbl') AND clave=?",
            (str(mat_id),),
        )
        rows = {r[0]: r[1] for r in cur.fetchall()}
        cur.close()
        return float(rows.get("a36_max") or 0), str(rows.get("a36_lbl") or "")

    def _a36_upsert_meta(self, con, mat_id: int, espesor_max: float, rango_label: str) -> None:
        clave = str(mat_id)
        cur = con.cursor()
        for tipo, valor in (("a36_max", str(espesor_max)), ("a36_lbl", rango_label)):
            cur.execute("SELECT COUNT(*) FROM config WHERE tipo=? AND clave=?", (tipo, clave))
            exists = cur.fetchone()[0]
            if exists:
                cur.execute("UPDATE config SET valor=? WHERE tipo=? AND clave=?", (valor, tipo, clave))
            else:
                cur.execute("INSERT INTO config (tipo, clave, valor) VALUES (?, ?, ?)", (tipo, clave, valor))
        cur.close()

    def _a36_delete_meta(self, con, mat_id: int) -> None:
        clave = str(mat_id)
        cur = con.cursor()
        cur.execute("DELETE FROM config WHERE tipo='a36_max' AND clave=?", (clave,))
        cur.execute("DELETE FROM config WHERE tipo='a36_lbl' AND clave=?", (clave,))
        cur.close()

    def _es_tarifa_a36_id(self, con, material_id: int) -> bool:
        total = self._scalar(
            con,
            "SELECT COUNT(*) FROM config WHERE tipo='a36_max' AND clave=?",
            (str(material_id),),
        )
        return int(total or 0) > 0

    def _listar_precios_a36_placa_tx(self, con) -> List[PrecioA36Placa]:
        cur_meta = con.cursor()
        cur_meta.execute("SELECT tipo, clave, valor FROM config WHERE tipo IN ('a36_max','a36_lbl')")
        meta_max: dict[str, float] = {}
        meta_lbl: dict[str, str] = {}
        for tipo, clave, valor in cur_meta.fetchall():
            key = str(clave or "").strip()
            if not key:
                continue
            if tipo == "a36_max":
                meta_max[key] = float(valor or 0)
            else:
                meta_lbl[key] = str(valor or "").strip()
        cur_meta.close()

        ids = [int(k) for k in meta_max.keys() if k.isdigit()]
        if not ids:
            return []

        cur = con.cursor()
        cur.execute(
            "SELECT id, espesor, precio_kg FROM materiales "
            "WHERE id IN ({}) "
            "AND UPPER(LTRIM(RTRIM(tipo))) = 'A36' "
            "AND UPPER(LTRIM(RTRIM(forma))) = 'PLACA' "
            "AND espesor IS NOT NULL AND espesor > 0 "
            "ORDER BY espesor".format(",".join("?" * len(ids))),
            tuple(ids),
        )
        rows = cur.fetchall()
        cur.close()

        items: list[PrecioA36Placa] = []
        for row in rows:
            mid = int(row[0])
            key = str(mid)
            esp_min = float(row[1])
            esp_max = float(meta_max.get(key, esp_min) or esp_min)
            if esp_max < esp_min:
                esp_max = esp_min
            lbl = meta_lbl.get(key) or (f'{esp_min}"' if abs(esp_max - esp_min) <= 0.0001 else f'{esp_min}" a {esp_max}"')
            items.append(
                PrecioA36Placa(
                    id=mid,
                    espesor_min_pulgadas=esp_min,
                    espesor_max_pulgadas=esp_max,
                    precio_kg=float(row[2]),
                    rango_label=lbl,
                )
            )
        return items

    def _buscar_tarifa_a36_tx(self, con, espesor_pulgadas: float) -> Optional[PrecioA36Placa]:
        for tarifa in self._listar_precios_a36_placa_tx(con):
            if tarifa.espesor_min_pulgadas <= espesor_pulgadas <= tarifa.espesor_max_pulgadas:
                return tarifa
        return None

    def _ids_materiales_a36_en_rango(self, con, espesor_min: float, espesor_max: float) -> list[int]:
        cur = con.cursor()
        cur.execute(
            """
            SELECT id
            FROM materiales
            WHERE UPPER(LTRIM(RTRIM(tipo)))='A36'
              AND UPPER(LTRIM(RTRIM(forma)))='PLACA'
              AND espesor IS NOT NULL
              AND espesor >= ?
              AND espesor <= ?
            """,
            (self._dec(espesor_min), self._dec(espesor_max)),
        )
        ids = [int(r[0]) for r in cur.fetchall()]
        cur.close()
        return ids

    def _registrar_costos_y_precio_materiales(
        self,
        con,
        material_ids: list[int],
        fecha_iso: str,
        precio_kg: float,
        proveedor: str,
        nota: str,
        objetivo_id: Optional[int] = None,
    ) -> int:
        if not material_ids:
            return 0

        ahora = self._ahora()
        precio_dec = self._dec(precio_kg)
        nuevo_id_objetivo = 0
        vistos: set[int] = set()
        cur = con.cursor()
        for material_id in material_ids:
            if material_id in vistos:
                continue
            vistos.add(material_id)

            cur.execute(
                """
                INSERT INTO historial_costos
                    (material_id, fecha, precio_kg, proveedor, nota, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    material_id,
                    fecha_iso,
                    precio_dec,
                    proveedor,
                    nota,
                    ahora,
                ),
            )
            cur.execute("SELECT @@IDENTITY")
            inserted = int(cur.fetchone()[0])
            if objetivo_id is not None and material_id == objetivo_id:
                nuevo_id_objetivo = inserted

            cur.execute(
                "UPDATE materiales SET precio_kg=?, updated_at=? WHERE id=?",
                (precio_dec, ahora, material_id),
            )

        cur.close()
        return nuevo_id_objetivo

    def _sincronizar_tarifa_a36(
        self,
        con,
        tarifa: PrecioA36Placa,
        *,
        fecha_iso: Optional[str] = None,
        proveedor: str = "",
        nota: str = "",
        objetivo_id: Optional[int] = None,
    ) -> int:
        ids = self._ids_materiales_a36_en_rango(con, tarifa.espesor_min_pulgadas, tarifa.espesor_max_pulgadas)
        fecha_val = fecha_iso or datetime.now().strftime("%Y-%m-%d")
        return self._registrar_costos_y_precio_materiales(
            con,
            ids,
            fecha_val,
            tarifa.precio_kg,
            proveedor,
            nota,
            objetivo_id=objetivo_id,
        )

    def listar_precios_a36_placa(self) -> List[PrecioA36Placa]:
        with self._tx() as con:
            return self._listar_precios_a36_placa_tx(con)

    def buscar_precio_a36_placa(self, espesor_pulgadas: float) -> Optional[PrecioA36Placa]:
        with self._tx() as con:
            return self._buscar_tarifa_a36_tx(con, espesor_pulgadas)

    def crear_precio_a36_placa(self, precio: PrecioA36Placa) -> int:
        mat = Material(
            id=None, codigo="", nombre="A36", tipo="ACERO", forma="PLACA",
            espesor_pulgadas=precio.espesor_min_pulgadas,
            densidad=7.85, precio_actual=precio.precio_kg,
        )
        new_id = self.crear_material(mat)
        with self._tx() as con:
            self._a36_upsert_meta(con, new_id, precio.espesor_max_pulgadas, precio.rango_label or "")
            self._sincronizar_tarifa_a36(
                con,
                PrecioA36Placa(
                    id=new_id,
                    espesor_min_pulgadas=precio.espesor_min_pulgadas,
                    espesor_max_pulgadas=precio.espesor_max_pulgadas,
                    precio_kg=precio.precio_kg,
                    rango_label=precio.rango_label,
                ),
                nota=(precio.rango_label or "Tarifa A36 actualizada desde configuración"),
            )
        return new_id

    def actualizar_precio_a36_placa(self, precio: PrecioA36Placa) -> None:
        with self._tx() as con:
            ahora = self._ahora()
            cur = con.cursor()
            cur.execute(
                "UPDATE materiales SET precio_kg=?, espesor=?, updated_at=? WHERE id=?",
                (self._dec(precio.precio_kg), self._dec(precio.espesor_min_pulgadas), ahora, precio.id),
            )
            cur.close()
            self._a36_upsert_meta(con, precio.id, precio.espesor_max_pulgadas, precio.rango_label or "")
            self._sincronizar_tarifa_a36(
                con,
                precio,
                nota=(precio.rango_label or "Tarifa A36 actualizada desde configuración"),
            )

    def eliminar_precio_a36_placa(self, precio_id: int) -> None:
        with self._tx() as con:
            self._a36_delete_meta(con, precio_id)
        self.eliminar_material(precio_id)

    # ------------------------------------------------------------------ #
    # Reglas de costo — derivadas de materiales (sin tabla propia)        #
    # ------------------------------------------------------------------ #

    def _listar_reglas_config_tx(self, con) -> List[ReglaCosto]:
        cur = con.cursor()
        cur.execute("SELECT clave, valor FROM config WHERE tipo='regla_costo' ORDER BY clave")
        rows = cur.fetchall()
        cur.close()

        reglas: list[ReglaCosto] = []
        for clave, valor in rows:
            try:
                regla_id = int(str(clave).strip())
                payload = json.loads(str(valor or "{}"))
                mat = str(payload.get("material") or "").strip()
                forma = str(payload.get("forma") or "").strip()
                precio = float(payload.get("precio_kg") or 0)
                if not mat or precio <= 0:
                    continue
                reglas.append(
                    ReglaCosto(
                        id=regla_id,
                        material_nombre=mat,
                        forma_nombre=forma,
                        precio_kg=precio,
                    )
                )
            except Exception:
                continue
        return reglas

    @staticmethod
    def _regla_payload(regla: ReglaCosto) -> str:
        data = {
            "material": (regla.material_nombre or "").strip(),
            "forma": (regla.forma_nombre or "").strip(),
            "precio_kg": float(regla.precio_kg),
        }
        return json.dumps(data, ensure_ascii=True, separators=(",", ":"))

    def listar_reglas_costo(self) -> List[ReglaCosto]:
        """Lista reglas explícitas guardadas en config; fallback a materiales si no existen."""
        with self._tx() as con:
            reglas_cfg = self._listar_reglas_config_tx(con)
            if reglas_cfg:
                return sorted(
                    reglas_cfg,
                    key=lambda r: ((r.material_nombre or "").upper(), (r.forma_nombre or "").upper()),
                )

            cur = con.cursor()
            cur.execute(
                """
                SELECT m.id, m.tipo, m.forma, m.precio_kg
                FROM materiales m
                INNER JOIN (
                    SELECT
                        UPPER(LTRIM(RTRIM(tipo))) AS tipo_key,
                        UPPER(LTRIM(RTRIM(forma))) AS forma_key,
                        MAX(id) AS max_id
                    FROM materiales
                    WHERE LTRIM(RTRIM(tipo)) <> ''
                    GROUP BY UPPER(LTRIM(RTRIM(tipo))), UPPER(LTRIM(RTRIM(forma)))
                ) g ON g.max_id = m.id
                ORDER BY m.tipo, m.forma
                """
            )
            rows = []
            for row in cur.fetchall():
                d = self._row_dict(cur, row)
                rows.append(ReglaCosto(
                    id=d["id"],
                    material_nombre=d["tipo"],
                    forma_nombre=d.get("forma") or "",
                    precio_kg=float(d["precio_kg"]),
                ))
            cur.close()
            return rows

    def buscar_regla_costo(self, material_nombre: str, forma_nombre: str) -> Optional[ReglaCosto]:
        """Sugiere precio por reglas en config; fallback a datos en materiales."""
        tipo = (material_nombre or "").strip()
        forma = (forma_nombre or "").strip()
        if not tipo:
            return None
        with self._tx() as con:
            reglas_cfg = self._listar_reglas_config_tx(con)
            if reglas_cfg:
                tipo_key = tipo.upper()
                forma_key = forma.upper()
                regla_general: Optional[ReglaCosto] = None
                for regla in reglas_cfg:
                    if (regla.material_nombre or "").strip().upper() != tipo_key:
                        continue
                    regla_forma = (regla.forma_nombre or "").strip().upper()
                    if forma_key and regla_forma == forma_key:
                        return regla
                    if regla_forma == "":
                        regla_general = regla
                if regla_general is not None:
                    return regla_general

            cur = con.cursor()
            if forma:
                cur.execute(
                    """
                    SELECT TOP 1 id, tipo, forma, precio_kg
                    FROM materiales
                    WHERE UPPER(LTRIM(RTRIM(tipo)))=UPPER(?)
                      AND UPPER(LTRIM(RTRIM(forma)))=UPPER(?)
                    ORDER BY id DESC
                    """,
                    (tipo, forma),
                )
            else:
                cur.execute(
                    """
                    SELECT TOP 1 id, tipo, forma, precio_kg
                    FROM materiales
                    WHERE UPPER(LTRIM(RTRIM(tipo)))=UPPER(?)
                    ORDER BY id DESC
                    """,
                    (tipo,),
                )
            row = cur.fetchone()
            if not row:
                cur.close()
                return None
            d = self._row_dict(cur, row)
            cur.close()
            return ReglaCosto(
                id=d["id"],
                material_nombre=d["tipo"],
                forma_nombre=d.get("forma") or "",
                precio_kg=float(d["precio_kg"]),
            )

    def crear_regla_costo(self, regla: ReglaCosto) -> int:
        material = (regla.material_nombre or "").strip()
        forma = (regla.forma_nombre or "").strip()
        if not material:
            raise ValueError("El material es obligatorio.")
        if float(regla.precio_kg) <= 0:
            raise ValueError("El precio debe ser mayor a 0.")

        with self._tx() as con:
            existentes = self._listar_reglas_config_tx(con)
            for r in existentes:
                if (
                    (r.material_nombre or "").strip().upper() == material.upper()
                    and (r.forma_nombre or "").strip().upper() == forma.upper()
                ):
                    raise ValueError("Ya existe una regla para ese material y forma.")

            next_id = (max((int(r.id or 0) for r in existentes), default=0) + 1)
            cur = con.cursor()
            cur.execute(
                "INSERT INTO config (tipo, clave, valor) VALUES ('regla_costo', ?, ?)",
                (str(next_id), self._regla_payload(regla)),
            )
            cur.close()
            return next_id

    def actualizar_regla_costo(self, regla: ReglaCosto) -> None:
        if regla.id is None:
            raise ValueError("La regla no tiene identificador.")
        material = (regla.material_nombre or "").strip()
        forma = (regla.forma_nombre or "").strip()
        if not material:
            raise ValueError("El material es obligatorio.")
        if float(regla.precio_kg) <= 0:
            raise ValueError("El precio debe ser mayor a 0.")

        with self._tx() as con:
            existentes = self._listar_reglas_config_tx(con)
            for r in existentes:
                if r.id == regla.id:
                    continue
                if (
                    (r.material_nombre or "").strip().upper() == material.upper()
                    and (r.forma_nombre or "").strip().upper() == forma.upper()
                ):
                    raise ValueError("Ya existe una regla para ese material y forma.")

            cur = con.cursor()
            cur.execute(
                "UPDATE config SET valor=? WHERE tipo='regla_costo' AND clave=?",
                (self._regla_payload(regla), str(regla.id)),
            )
            cur.close()

    def eliminar_regla_costo(self, regla_id: int) -> None:
        with self._tx() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM config WHERE tipo='regla_costo' AND clave=?", (str(regla_id),))
            cur.close()

    # ------------------------------------------------------------------ #
    # Historial LLM BOM (tabla llm_bom_runs)                              #
    # ------------------------------------------------------------------ #

    def _ensure_llm_bom_runs_table(self, con) -> None:
        cur = con.cursor()
        try:
            cur.execute("SELECT TOP 1 id FROM llm_bom_runs")
            cur.fetchone()
            cur.close()
            return
        except Exception as exc:
            cur.close()
            msg = str(exc).upper()
            missing_markers = ("DOES NOT EXIST", "NOT FOUND", "-1303", "-1305", "NO SUCH TABLE", "UNABLE TO OPEN TABLE")
            if not any(marker in msg for marker in missing_markers):
                raise

        cur_create = con.cursor()
        try:
            cur_create.execute(
                """
                CREATE TABLE llm_bom_runs (
                    id INTEGER,
                    created_at CHAR(19),
                    project_name VARCHAR(120),
                    actor VARCHAR(64),
                    status VARCHAR(24),
                    source_path VARCHAR(512),
                    output_path VARCHAR(512),
                    source_hash VARCHAR(64),
                    output_hash VARCHAR(64),
                    total_rows INTEGER,
                    ok_rows INTEGER,
                    warn_rows INTEGER,
                    total_cost DECIMAL(18,4),
                    notes LONGVARCHAR,
                    PRIMARY KEY (id)
                )
                """
            )
        except Exception as exc:
            msg = str(exc).upper()
            if "-1303" not in msg and "ALREADY EXISTS" not in msg:
                raise
        finally:
            cur_create.close()

    def registrar_llm_bom_run(self, run: LlmBomRun) -> int:
        with self._tx() as con:
            self._ensure_llm_bom_runs_table(con)
            last_id = self._scalar(con, "SELECT MAX(id) FROM llm_bom_runs")
            next_id = int(last_id or 0) + 1
            created_at = (run.created_at or self._ahora()).strip()[:19]
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO llm_bom_runs (
                    id, created_at, project_name, actor, status,
                    source_path, output_path, source_hash, output_hash,
                    total_rows, ok_rows, warn_rows, total_cost, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_id,
                    created_at,
                    (run.project_name or "").strip(),
                    (run.actor or self._actor).strip(),
                    (run.status or "completed").strip(),
                    (run.source_path or "").strip(),
                    (run.output_path or "").strip(),
                    (run.source_hash or "").strip(),
                    (run.output_hash or "").strip(),
                    int(run.total_rows or 0),
                    int(run.ok_rows or 0),
                    int(run.warn_rows or 0),
                    self._dec(float(run.total_cost_mxn or 0.0)),
                    (run.notes or "").strip(),
                ),
            )
            cur.close()
            return next_id

    def actualizar_llm_bom_run(self, run: LlmBomRun) -> None:
        if run.id is None:
            raise ValueError("La corrida LLM no tiene id.")
        with self._tx() as con:
            self._ensure_llm_bom_runs_table(con)
            cur = con.cursor()
            cur.execute(
                """
                UPDATE llm_bom_runs
                SET created_at=?,
                    project_name=?,
                    actor=?,
                    status=?,
                    source_path=?,
                    output_path=?,
                    source_hash=?,
                    output_hash=?,
                    total_rows=?,
                    ok_rows=?,
                    warn_rows=?,
                    total_cost=?,
                    notes=?
                WHERE id=?
                """,
                (
                    (run.created_at or self._ahora()).strip()[:19],
                    (run.project_name or "").strip(),
                    (run.actor or self._actor).strip(),
                    (run.status or "draft").strip(),
                    (run.source_path or "").strip(),
                    (run.output_path or "").strip(),
                    (run.source_hash or "").strip(),
                    (run.output_hash or "").strip(),
                    int(run.total_rows or 0),
                    int(run.ok_rows or 0),
                    int(run.warn_rows or 0),
                    self._dec(float(run.total_cost_mxn or 0.0)),
                    (run.notes or "").strip(),
                    int(run.id),
                ),
            )
            cur.close()

    def listar_llm_bom_runs(self, limite: int = 200) -> List[LlmBomRun]:
        limite_valido = max(1, int(limite))
        with self._tx() as con:
            try:
                self._ensure_llm_bom_runs_table(con)
            except Exception:
                return []
            cur = con.cursor()
            cur.execute(
                f"""
                SELECT TOP {int(limite_valido)}
                    id, created_at, project_name, actor, status,
                    source_path, output_path, source_hash, output_hash,
                    total_rows, ok_rows, warn_rows, total_cost, notes
                FROM llm_bom_runs
                ORDER BY id DESC
                """
            )
            rows = [self._row_to_llm_bom_run(self._row_dict(cur, r)) for r in cur.fetchall()]
            cur.close()
            return rows

    # ------------------------------------------------------------------ #
    # Costos (historial_costos)                                           #
    # ------------------------------------------------------------------ #

    def listar_costos(self, material_id: int) -> List[Costo]:
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT id, material_id, fecha, precio_kg, proveedor, nota
                FROM historial_costos
                WHERE material_id=?
                ORDER BY fecha DESC, id DESC
                """,
                (material_id,),
            )
            rows = [self._row_to_costo(self._row_dict(cur, r)) for r in cur.fetchall()]
            cur.close()
            return rows

    def agregar_costo(self, costo: Costo) -> int:
        if costo.precio_unitario <= 0:
            raise ValueError("El precio debe ser mayor a 0.")
        with self._tx() as con:
            cur = con.cursor()
            cur.execute("SELECT tipo, forma, espesor FROM materiales WHERE id=?", (costo.material_id,))
            material_row = cur.fetchone()
            cur.close()

            tipo = str(material_row[0] or "").strip().upper() if material_row else ""
            forma = str(material_row[1] or "").strip().upper() if material_row else ""
            espesor = float(material_row[2]) if material_row and material_row[2] is not None else None

            if tipo == "A36" and forma == "PLACA" and espesor is not None and espesor > 0:
                tarifa = self._buscar_tarifa_a36_tx(con, espesor)
                if tarifa is not None:
                    ahora = self._ahora()
                    cur_sync = con.cursor()
                    cur_sync.execute(
                        "UPDATE materiales SET precio_kg=?, updated_at=? WHERE id=?",
                        (self._dec(costo.precio_unitario), ahora, tarifa.id),
                    )
                    cur_sync.close()

                    tarifa_actualizada = PrecioA36Placa(
                        id=tarifa.id,
                        espesor_min_pulgadas=tarifa.espesor_min_pulgadas,
                        espesor_max_pulgadas=tarifa.espesor_max_pulgadas,
                        precio_kg=float(costo.precio_unitario),
                        rango_label=tarifa.rango_label,
                    )
                    nota_sync = (costo.nota or "").strip() or f"Tarifa A36 placa {tarifa.rango_label}"
                    nuevo_id = self._sincronizar_tarifa_a36(
                        con,
                        tarifa_actualizada,
                        fecha_iso=costo.fecha.strftime("%Y-%m-%d"),
                        proveedor=costo.proveedor or "",
                        nota=nota_sync,
                        objetivo_id=costo.material_id,
                    )
                    return nuevo_id

            nota = (costo.nota or "").strip()
            return self._registrar_costos_y_precio_materiales(
                con,
                [costo.material_id],
                costo.fecha.strftime("%Y-%m-%d"),
                costo.precio_unitario,
                costo.proveedor or "",
                nota,
                objetivo_id=costo.material_id,
            )

    def costo_actual(self, material_id: int) -> Optional[Costo]:
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT TOP 1 id, material_id, fecha, precio_kg, proveedor, nota
                FROM historial_costos
                WHERE material_id=?
                ORDER BY fecha DESC, id DESC
                """,
                (material_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.close()
                return None
            result = self._row_to_costo(self._row_dict(cur, row))
            cur.close()
            return result

    def listar_proveedores_historicos(self, limite: int = 50) -> List[str]:
        limite_valido = max(1, int(limite))
        with self._tx() as con:
            cur = con.cursor()
            cur.execute(
                f"""
                SELECT TOP {int(limite_valido)} proveedor
                FROM (
                    SELECT proveedor, MAX(fecha) AS ult_fecha, MAX(id) AS ult_id
                    FROM historial_costos
                    WHERE proveedor IS NOT NULL AND LTRIM(RTRIM(proveedor)) <> ''
                    GROUP BY proveedor
                ) sub
                ORDER BY ult_fecha DESC, ult_id DESC
                """
            )
            items = [r[0] for r in cur.fetchall()]
            cur.close()
            return items
