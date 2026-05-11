-- ============================================================================
-- Sistema de Costos - DDL para Pervasive PSQL v13 / Actian Zen
-- Esquema actual: v4 (4 tablas core)
--
-- TABLAS CORE (ya existen en produccion — NO recrear):
--   sistema_meta     — metadatos y version de esquema
--   materiales       — materiales; mapeo de columnas importante:
--                        columna DB 'tipo'     = grado/aleacion (A36, S7, 1045)
--                        columna DB 'material' = categoria      (ACERO, ALUMINIO)
--                      Las tarifas A36 son filas donde tipo='A36' y espesor IS NOT NULL.
--   historial_costos — historial de precios por material (FK a materiales.id)
--   config           — clave-valor: tipos usados = cat_material, cat_forma, secuencia
--
-- COMPATIBILIDAD PERVASIVE APLICADA:
--   * IDENTITY como tipo de dato (no modificador de INTEGER).
--   * Sin DEFAULT CURRENT_TIMESTAMP — la app provee created_at/updated_at.
--   * Sin CHECK constraints (no soportadas en PSQL v13).
--   * Maximo 1 columna LONGVARCHAR o LONGVARBINARY por tabla (debe ir al final).
--   * LONGVARCHAR / LONGVARBINARY no soportan NOT NULL ni DEFAULT.
--   * INSERTs de seeds individuales (multi-row VALUES no soportado).
--
-- REGLA: antes de agregar una tabla nueva, documentarla aqui Y en el encabezado
-- de app/data/pervasive_repository.py para mantener ambos archivos sincronizados.
-- ============================================================================


-- =========================
-- TABLAS CORE (referencia — ya existen, no ejecutar)
-- =========================
-- CREATE TABLE sistema_meta (
--     clave      VARCHAR(80)  NOT NULL,
--     valor      VARCHAR(500) DEFAULT '',
--     updated_at TIMESTAMP,
--     CONSTRAINT pk_sistema_meta PRIMARY KEY (clave)
-- );
--
-- CREATE TABLE materiales (
--     id               INTEGER NOT NULL, -- usar IDENTITY en Pervasive
--     codigo           VARCHAR(40)   NOT NULL,
--     forma            VARCHAR(80)   DEFAULT '',
--     tipo             VARCHAR(80)   DEFAULT '',   -- grado: A36, S7, 1045...
--     material         VARCHAR(80)   DEFAULT '',   -- categoria: ACERO, ALUMINIO...
--     precio_kg        DECIMAL(18,4) DEFAULT 0,
--     densidad         DECIMAL(18,6),
--     espesor          DECIMAL(18,4),
--     ficha_pdf_nombre VARCHAR(260)  DEFAULT '',
--     created_at       TIMESTAMP,
--     updated_at       TIMESTAMP,
--     ficha_pdf_blob   LONGVARBINARY,              -- LONG siempre al final
--     CONSTRAINT pk_materiales PRIMARY KEY (id),
--     CONSTRAINT uq_materiales_codigo UNIQUE (codigo)
-- );
--
-- CREATE TABLE historial_costos (
--     id          IDENTITY NOT NULL,
--     material_id INTEGER        NOT NULL,
--     fecha       VARCHAR(10)    NOT NULL,
--     precio_kg   DECIMAL(18,4)  NOT NULL,
--     proveedor   VARCHAR(200)   DEFAULT '',
--     nota        VARCHAR(500)   DEFAULT '',
--     created_at  TIMESTAMP,
--     CONSTRAINT pk_historial_costos PRIMARY KEY (id),
--     CONSTRAINT fk_hc_material FOREIGN KEY (material_id) REFERENCES materiales (id)
-- );
--
-- CREATE TABLE config (
--     tipo   VARCHAR(40)  NOT NULL,
--     clave  VARCHAR(120) NOT NULL,
--     valor  VARCHAR(500) DEFAULT '',
--     CONSTRAINT pk_config PRIMARY KEY (tipo, clave)
-- );

-- =========================
-- 2) TABLA REQUERIDA: precios_a36_placa
--    Ejecutar una sola vez en la BD Pervasive antes de usar Tarifas A36.
--    Reemplaza el uso de la tabla 'materiales' para almacenar tarifas.
-- =========================
CREATE TABLE precios_a36_placa (
    id          INTEGER NOT NULL, -- usar IDENTITY en Pervasive
    espesor_min DECIMAL(18,4) NOT NULL,
    espesor_max DECIMAL(18,4) NOT NULL,
    precio_kg   DECIMAL(18,4) NOT NULL,
    rango_label VARCHAR(80)   DEFAULT '',
    created_at  TIMESTAMP,
    updated_at  TIMESTAMP,
    CONSTRAINT pk_precios_a36 PRIMARY KEY (id)
);

-- =========================
-- 3) TABLAS OPCIONALES (nombres abreviados)
-- =========================
CREATE TABLE cat_materiales (
    id             INTEGER NOT NULL, -- usar IDENTITY en Pervasive
    nombre         VARCHAR(120) NOT NULL,
    prefijo_codigo VARCHAR(16)  NOT NULL,
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP,
    created_by     VARCHAR(120) DEFAULT 'system',
    updated_by     VARCHAR(120) DEFAULT 'system',
    CONSTRAINT pk_cat_materiales PRIMARY KEY (id)
);

-- =========================
-- 3) TABLAS PENDIENTES (dependen de otras, nombres abreviados)
-- =========================
CREATE TABLE reglas_costo (
    id                   INTEGER NOT NULL, -- usar IDENTITY en Pervasive
    mat_cat_id           INTEGER        NOT NULL,
    forma_cat_id         INTEGER,
    mat_nombre           VARCHAR(120)   DEFAULT '',
    forma_nombre         VARCHAR(120)   DEFAULT '',
    precio_kg            DECIMAL(18,4)  NOT NULL,
    created_at           TIMESTAMP,
    updated_at           TIMESTAMP,
    created_by           VARCHAR(120)   DEFAULT 'system',
    updated_by           VARCHAR(120)   DEFAULT 'system',
    CONSTRAINT pk_reglas_costo PRIMARY KEY (id),
    CONSTRAINT fk_regcosto_matcat FOREIGN KEY (mat_cat_id) REFERENCES cat_materiales (id),
    CONSTRAINT fk_regcosto_formacat FOREIGN KEY (forma_cat_id) REFERENCES catalogo_formas (id)
);

CREATE TABLE mat_archivos (
    id             INTEGER NOT NULL, -- usar IDENTITY en Pervasive
    material_id    INTEGER         NOT NULL,
    tipo           VARCHAR(40)     NOT NULL,
    nombre_archivo VARCHAR(260)    NOT NULL,
    mime_type      VARCHAR(80)     DEFAULT 'application/pdf',
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP,
    created_by     VARCHAR(120)    DEFAULT 'system',
    updated_by     VARCHAR(120)    DEFAULT 'system',
    contenido_blob LONGVARBINARY,
    CONSTRAINT pk_mat_archivos PRIMARY KEY (id),
    CONSTRAINT fk_matarch_mat FOREIGN KEY (material_id) REFERENCES materiales (id) ON DELETE CASCADE,
    CONSTRAINT uq_matarch_tipo UNIQUE (material_id, tipo)
);

-- =========================
-- 4) ÍNDICES PENDIENTES (nombres abreviados, sin duplicados)
-- =========================
-- CREATE UNIQUE INDEX uq_regcosto_mat_forma_id ON reglas_costo (mat_cat_id, forma_cat_id); -- Eliminado por error de Pervasive
-- CREATE INDEX ix_regcosto_mat_forma ON reglas_costo (mat_cat_id, forma_cat_id); -- Eliminado: ya existe índice implícito por UNIQUE/PK
CREATE INDEX ix_matarch_mat_tipo ON mat_archivos (material_id, tipo);
