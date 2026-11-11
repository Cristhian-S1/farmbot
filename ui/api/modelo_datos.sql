-- Modelo de datos de Sabueso en MySQL/InnoDB (informe de la Parte 2, sección 6.10).
-- La API que corre hoy usa SQLite con el mismo modelo (ESQUEMA en almacenamiento.py),
-- con los nombres de tabla en plural. tests/test_modelo_datos.py comprueba que ambos
-- tengan las mismas tablas, columnas y clases.

CREATE DATABASE sabueso;
USE sabueso;

-- 1. SECTOR: el invernadero o área del predio que recorre el robot.
CREATE TABLE sector (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    predio VARCHAR(100) NOT NULL
) ENGINE=InnoDB;


-- 2. HILERA: cada sector tiene hileras numeradas.
CREATE TABLE hilera (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sector_id INT NOT NULL,
    numero INT NOT NULL,

    UNIQUE (sector_id, numero),
    FOREIGN KEY (sector_id)
        REFERENCES sector(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB;


-- 3. ZONA: tramo de una hilera; es la unidad que se colorea en el mapa.
CREATE TABLE zona (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hilera_id INT NOT NULL,
    numero INT NOT NULL,

    UNIQUE (hilera_id, numero),
    FOREIGN KEY (hilera_id)
        REFERENCES hilera(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB;


-- 4. CLASE: catálogo cerrado de lo que el modelo detecta.
--    El grupo decide el estado de la zona en el mapa.
CREATE TABLE clase (
    codigo VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    grupo VARCHAR(20) NOT NULL,

    CHECK (grupo IN ('fruto', 'maleza', 'follaje', 'otro'))
) ENGINE=InnoDB;

INSERT INTO clase (codigo, nombre, grupo) VALUES
    ('tomate_verde', 'Fruto verde', 'fruto'),
    ('tomate_maduro', 'Fruto maduro', 'fruto'),
    ('maleza', 'Maleza', 'maleza'),
    ('follaje_mancha', 'Manchas en hojas', 'follaje'),
    ('follaje_decoloracion', 'Decoloración', 'follaje'),
    ('follaje_marchitez', 'Marchitez', 'follaje');


-- 5. MODELO: versión del detector con que se analizó un recorrido.
CREATE TABLE modelo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    fecha DATE,

    UNIQUE (nombre, version)
) ENGINE=InnoDB;


-- 6. RECORRIDO: una pasada del robot por un sector.
--    El id lo genera el robot (fecha y hora de inicio, p. ej. 20261104-101500).
CREATE TABLE recorrido (
    id VARCHAR(40) PRIMARY KEY,
    sector_id INT NOT NULL,
    modelo_id INT NULL,
    estado VARCHAR(20) NOT NULL,
    inicio DATETIME NOT NULL,
    fin DATETIME,
    iniciado_por VARCHAR(100),

    CHECK (estado IN ('en_curso', 'completado', 'incompleto', 'cancelado')),
    FOREIGN KEY (sector_id)
        REFERENCES sector(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (modelo_id)
        REFERENCES modelo(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB;


-- 7. CAPTURA: una foto tomada en una zona durante un recorrido.
--    zona_id nulo = «sin zona»: no se inventa una zona desconocida.
--    El id lo genera el robot, así un reenvío desde su cola no se duplica.
CREATE TABLE captura (
    id VARCHAR(64) PRIMARY KEY,
    recorrido_id VARCHAR(40) NOT NULL,
    zona_id INT NULL,
    fecha DATETIME NOT NULL,
    foto VARCHAR(255),
    analisis VARCHAR(20) NOT NULL DEFAULT 'listo',

    CHECK (analisis IN ('listo', 'pendiente')),
    INDEX captura_recorrido_zona (recorrido_id, zona_id),
    FOREIGN KEY (recorrido_id)
        REFERENCES recorrido(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (zona_id)
        REFERENCES zona(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB;


-- 8. DETECCION: cada hallazgo del modelo dentro de una captura.
--    caja = [x1, y1, x2, y2] en píxeles de la foto.
CREATE TABLE deteccion (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    captura_id VARCHAR(64) NOT NULL,
    clase VARCHAR(50) NOT NULL,
    confianza DECIMAL(4,3) NOT NULL,
    caja JSON NOT NULL,

    CHECK (confianza BETWEEN 0 AND 1),
    INDEX deteccion_captura (captura_id),
    FOREIGN KEY (captura_id)
        REFERENCES captura(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (clase)
        REFERENCES clase(codigo)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB;


-- 9. INCIDENCIA: evento del recorrido (obstáculo, pérdida de red, detención).
CREATE TABLE incidencia (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    recorrido_id VARCHAR(40) NOT NULL,
    zona_id INT NULL,
    tipo VARCHAR(100) NOT NULL,
    fecha DATETIME NOT NULL,
    detalle TEXT,

    FOREIGN KEY (recorrido_id)
        REFERENCES recorrido(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (zona_id)
        REFERENCES zona(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB;
