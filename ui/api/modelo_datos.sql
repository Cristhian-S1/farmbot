-- Modelo de datos propuesto para Sabueso (informe de la Parte 2, sección 6.10).
-- No está activo: hoy la API guarda todo en la tabla `registros` de almacenamiento.py.
-- Requiere PRAGMA foreign_keys = ON en cada conexión (SQLite no lo activa por defecto).

CREATE TABLE hilera (
    id      INTEGER PRIMARY KEY,
    codigo  TEXT NOT NULL UNIQUE
);

CREATE TABLE zona (
    id         INTEGER PRIMARY KEY,
    hilera_id  INTEGER NOT NULL REFERENCES hilera (id),
    codigo     TEXT NOT NULL,
    UNIQUE (hilera_id, codigo)
);

CREATE TABLE modelo (
    version         TEXT PRIMARY KEY,
    clases          TEXT NOT NULL,
    entrenado_en    TEXT,
    conjunto_datos  TEXT
);

CREATE TABLE recorrido (
    id      TEXT PRIMARY KEY,
    inicio  TEXT NOT NULL,
    fin     TEXT,
    estado  TEXT NOT NULL CHECK (estado IN ('en_curso', 'completado', 'incompleto', 'cancelado'))
);

-- Un evento es una detección. zona_id nulo significa «sin zona»: no se inventa una zona desconocida.
CREATE TABLE evento (
    id              TEXT PRIMARY KEY,
    recorrido_id    TEXT NOT NULL REFERENCES recorrido (id),
    zona_id         INTEGER REFERENCES zona (id),
    modelo_version  TEXT REFERENCES modelo (version),
    fecha           TEXT NOT NULL,
    clase           TEXT NOT NULL,
    confianza       REAL NOT NULL CHECK (confianza BETWEEN 0 AND 1),
    x1 INTEGER NOT NULL, y1 INTEGER NOT NULL, x2 INTEGER NOT NULL, y2 INTEGER NOT NULL,
    foto            TEXT
);

CREATE INDEX evento_zona_fecha ON evento (zona_id, fecha);
CREATE INDEX evento_recorrido ON evento (recorrido_id);

CREATE TABLE incidencia (
    id            INTEGER PRIMARY KEY,
    recorrido_id  TEXT NOT NULL REFERENCES recorrido (id),
    fecha         TEXT NOT NULL,
    tipo          TEXT NOT NULL,
    detalle       TEXT
);
