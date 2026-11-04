"""Almacenamiento de Sabueso: SQLite para los datos y una carpeta para las fotos.

Sigue el modelo entidad-relación: sector → hileras → zonas; un recorrido genera
capturas (una foto en una zona) y cada captura contiene detecciones. Las
clases son un catálogo cerrado; su grupo decide el estado de la zona en el mapa.
"""
import base64
import json
import os
import re
import sqlite3
from datetime import datetime

ESQUEMA = """
CREATE TABLE IF NOT EXISTS sectores (
    id      INTEGER PRIMARY KEY,
    nombre  TEXT NOT NULL,
    predio  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hileras (
    id         INTEGER PRIMARY KEY,
    sector_id  INTEGER NOT NULL REFERENCES sectores(id),
    numero     INTEGER NOT NULL,
    UNIQUE (sector_id, numero)
);
CREATE TABLE IF NOT EXISTS zonas (
    id         INTEGER PRIMARY KEY,
    hilera_id  INTEGER NOT NULL REFERENCES hileras(id),
    numero     INTEGER NOT NULL,
    UNIQUE (hilera_id, numero)
);
CREATE TABLE IF NOT EXISTS clases (
    codigo  TEXT PRIMARY KEY,
    nombre  TEXT NOT NULL,
    grupo   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS modelos (
    id       INTEGER PRIMARY KEY,
    nombre   TEXT NOT NULL,
    version  TEXT NOT NULL,
    fecha    TEXT,
    UNIQUE (nombre, version)
);
CREATE TABLE IF NOT EXISTS recorridos (
    id            TEXT PRIMARY KEY,
    sector_id     INTEGER NOT NULL REFERENCES sectores(id),
    modelo_id     INTEGER REFERENCES modelos(id),
    estado        TEXT NOT NULL,
    inicio        TEXT NOT NULL,
    fin           TEXT,
    iniciado_por  TEXT
);
CREATE TABLE IF NOT EXISTS capturas (
    id            TEXT PRIMARY KEY,
    recorrido_id  TEXT NOT NULL REFERENCES recorridos(id),
    zona_id       INTEGER REFERENCES zonas(id),
    fecha         TEXT NOT NULL,
    foto          TEXT,
    analisis      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS detecciones (
    id          INTEGER PRIMARY KEY,
    captura_id  TEXT NOT NULL REFERENCES capturas(id),
    clase       TEXT NOT NULL REFERENCES clases(codigo),
    confianza   REAL NOT NULL,
    caja        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS incidencias (
    id            INTEGER PRIMARY KEY,
    recorrido_id  TEXT NOT NULL REFERENCES recorridos(id),
    zona_id       INTEGER REFERENCES zonas(id),
    tipo          TEXT NOT NULL,
    fecha         TEXT NOT NULL,
    detalle       TEXT
);
CREATE INDEX IF NOT EXISTS capturas_recorrido_zona ON capturas (recorrido_id, zona_id);
CREATE INDEX IF NOT EXISTS detecciones_captura ON detecciones (captura_id);
"""

# Catálogo de lo que el modelo puede detectar. El grupo decide el estado en el mapa.
CLASES = (
    ("tomate_verde", "Fruto verde", "fruto"),
    ("tomate_maduro", "Fruto maduro", "fruto"),
    ("maleza", "Maleza", "maleza"),
    ("follaje_mancha", "Manchas en hojas", "follaje"),
    ("follaje_decoloracion", "Decoloración", "follaje"),
    ("follaje_marchitez", "Marchitez", "follaje"),
)

ESTADOS_RECORRIDO = ("en_curso", "completado", "incompleto", "cancelado")

RESUMEN_ZONA = """
    COUNT(DISTINCT c.id) AS capturas,
    COUNT(DISTINCT CASE WHEN c.analisis = 'pendiente' THEN c.id END) AS pendientes,
    COUNT(DISTINCT CASE WHEN c.foto IS NULL THEN c.id END) AS sin_foto,
    COALESCE(SUM(d.clase = 'tomate_verde'), 0) AS verdes,
    COALESCE(SUM(d.clase = 'tomate_maduro'), 0) AS maduros,
    COALESCE(SUM(cl.grupo = 'maleza'), 0) AS maleza,
    COALESCE(SUM(cl.grupo = 'follaje'), 0) AS follaje,
    MAX(c.fecha) AS ultima_captura
"""


def estado_zona(resumen):
    """Estado de una zona en un recorrido; gana la primera regla que se cumple."""
    if not resumen["capturas"]:
        return "sin_datos"
    if resumen["pendientes"]:
        return "pendiente"
    if resumen["maleza"]:
        return "revisar_maleza"
    if resumen["follaje"]:
        return "revisar_follaje"
    return "sin_alertas"


def _numero(valor):
    """'3', 3, 'H3' o 'Z3' → 3. None si no trae un número."""
    if valor is None:
        return None
    encontrado = re.search(r"\d+", str(valor))
    return int(encontrado.group()) if encontrado else None


def _ahora():
    return datetime.now().isoformat(timespec="seconds")


class Almacenamiento:
    def __init__(self, datos_dir, estructura):
        self.fotos_dir = os.path.join(datos_dir, "fotos")
        os.makedirs(self.fotos_dir, exist_ok=True)
        self.ruta_db = os.path.join(datos_dir, "sabueso.db")
        with self._conectar() as db:
            db.executescript(ESQUEMA)
            db.executemany("INSERT OR IGNORE INTO clases VALUES (?, ?, ?)", CLASES)
            self._cargar_estructura(db, estructura)

    def _conectar(self):
        db = sqlite3.connect(self.ruta_db)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def _cargar_estructura(self, db, estructura):
        """Crea el sector, sus hileras y zonas. Agrega las que falten; no borra nada."""
        db.execute(
            "INSERT OR IGNORE INTO sectores (id, nombre, predio) VALUES (1, ?, ?)",
            (estructura["sector"], estructura["predio"]),
        )
        db.execute("UPDATE sectores SET nombre = ?, predio = ? WHERE id = 1",
                   (estructura["sector"], estructura["predio"]))
        for h in range(1, estructura["hileras"] + 1):
            db.execute("INSERT OR IGNORE INTO hileras (sector_id, numero) VALUES (1, ?)", (h,))
            hilera_id = db.execute("SELECT id FROM hileras WHERE sector_id = 1 AND numero = ?", (h,)).fetchone()[0]
            for z in range(1, estructura["zonas_por_hilera"] + 1):
                db.execute("INSERT OR IGNORE INTO zonas (hilera_id, numero) VALUES (?, ?)", (hilera_id, z))

    # Estructura del invernadero

    def estructura(self):
        with self._conectar() as db:
            sector = dict(db.execute("SELECT * FROM sectores WHERE id = 1").fetchone())
            filas = db.execute(
                "SELECT z.id, h.numero AS hilera, z.numero FROM zonas z JOIN hileras h ON h.id = z.hilera_id "
                "WHERE h.sector_id = 1 ORDER BY h.numero, z.numero"
            ).fetchall()
            clases = [dict(f) for f in db.execute("SELECT * FROM clases ORDER BY grupo, codigo")]
        hileras = {}
        for f in filas:
            hileras.setdefault(f["hilera"], []).append({"id": f["id"], "numero": f["numero"]})
        sector["hileras"] = [{"numero": n, "zonas": z} for n, z in hileras.items()]
        return {"sector": sector, "clases": clases}

    def _zona_id(self, db, hilera, zona):
        h, z = _numero(hilera), _numero(zona)
        if h is None or z is None:
            return None
        fila = db.execute(
            "SELECT z.id FROM zonas z JOIN hileras h ON h.id = z.hilera_id "
            "WHERE h.sector_id = 1 AND h.numero = ? AND z.numero = ?", (h, z)
        ).fetchone()
        return fila[0] if fila else None

    # Recorridos

    def iniciar_recorrido(self, recorrido_id, iniciado_por=None, inicio=None):
        with self._conectar() as db:
            db.execute(
                "INSERT OR IGNORE INTO recorridos (id, sector_id, estado, inicio, iniciado_por) "
                "VALUES (?, 1, 'en_curso', ?, ?)",
                (recorrido_id, inicio or _ahora(), iniciado_por),
            )

    def cerrar_recorrido(self, recorrido_id, estado):
        """Cierra un recorrido en curso. Uno ya cerrado no cambia."""
        if estado not in ESTADOS_RECORRIDO or estado == "en_curso":
            raise ValueError("estado de cierre no válido: %s" % estado)
        with self._conectar() as db:
            cursor = db.execute(
                "UPDATE recorridos SET estado = ?, fin = ? WHERE id = ? AND estado = 'en_curso'",
                (estado, _ahora(), recorrido_id),
            )
            return cursor.rowcount == 1

    def listar_recorridos(self, limite=100):
        with self._conectar() as db:
            filas = db.execute(
                "SELECT r.*, m.nombre AS modelo, m.version AS modelo_version, "
                "(SELECT COUNT(*) FROM capturas c WHERE c.recorrido_id = r.id) AS capturas, "
                "(SELECT COUNT(DISTINCT c.zona_id) FROM capturas c WHERE c.recorrido_id = r.id) AS zonas, "
                "(SELECT COUNT(*) FROM capturas c WHERE c.recorrido_id = r.id AND c.zona_id IS NULL) AS sin_zona, "
                "(SELECT COUNT(*) FROM detecciones d JOIN capturas c ON c.id = d.captura_id "
                " JOIN clases cl ON cl.codigo = d.clase "
                " WHERE c.recorrido_id = r.id AND cl.grupo IN ('maleza', 'follaje')) AS alertas "
                "FROM recorridos r LEFT JOIN modelos m ON m.id = r.modelo_id "
                "ORDER BY r.inicio DESC LIMIT ?", (limite,)
            ).fetchall()
        return [dict(f) for f in filas]

    def recorrido(self, recorrido_id):
        with self._conectar() as db:
            fila = db.execute("SELECT * FROM recorridos WHERE id = ?", (recorrido_id,)).fetchone()
        return dict(fila) if fila else None

    def _recorrido_o_ultimo(self, db, recorrido_id):
        if recorrido_id:
            return recorrido_id
        fila = db.execute("SELECT id FROM recorridos ORDER BY inicio DESC LIMIT 1").fetchone()
        return fila[0] if fila else None

    # Capturas

    def guardar_captura(self, captura):
        """Guarda una captura del robot con sus detecciones.

        También acepta el formato antiguo de /api/registros (una detección por
        registro), por si quedan registros en la cola local del robot. Si el id
        ya existe (reenvío desde la cola), no la duplica.
        """
        if "detecciones" not in captura and "clase" in captura:
            captura = dict(captura, detecciones=[
                {k: captura[k] for k in ("clase", "confianza", "caja") if k in captura}
            ])
        faltan = [c for c in ("id", "recorrido", "fecha", "detecciones") if c not in captura]
        if faltan:
            raise ValueError("faltan campos: %s" % ", ".join(faltan))
        detecciones = captura["detecciones"]
        if not isinstance(detecciones, list):
            raise ValueError("detecciones debe ser una lista")
        for d in detecciones:
            if not all(k in d for k in ("clase", "confianza", "caja")) or len(d["caja"]) != 4:
                raise ValueError("cada detección necesita clase, confianza y caja [x1, y1, x2, y2]")

        with self._conectar() as db:
            if db.execute("SELECT 1 FROM capturas WHERE id = ?", (captura["id"],)).fetchone():
                return False
            db.execute(
                "INSERT OR IGNORE INTO recorridos (id, sector_id, estado, inicio) VALUES (?, 1, 'en_curso', ?)",
                (captura["recorrido"], captura["fecha"]),
            )
            modelo = captura.get("modelo")
            if modelo:
                db.execute("INSERT OR IGNORE INTO modelos (nombre, version, fecha) VALUES (?, ?, ?)",
                           (modelo["nombre"], modelo["version"], modelo.get("fecha")))
                db.execute(
                    "UPDATE recorridos SET modelo_id = (SELECT id FROM modelos WHERE nombre = ? AND version = ?) "
                    "WHERE id = ? AND modelo_id IS NULL", (modelo["nombre"], modelo["version"], captura["recorrido"])
                )
            foto = None
            if captura.get("foto_jpeg"):
                foto = "%s.jpg" % re.sub(r"[^A-Za-z0-9_-]", "", str(captura["id"]))
                with open(os.path.join(self.fotos_dir, foto), "wb") as f:
                    f.write(base64.b64decode(captura["foto_jpeg"]))
            db.execute(
                "INSERT INTO capturas VALUES (?, ?, ?, ?, ?, ?)",
                (captura["id"], captura["recorrido"], self._zona_id(db, captura.get("hilera"), captura.get("zona")),
                 captura["fecha"], foto, captura.get("analisis", "listo")),
            )
            for d in detecciones:
                db.execute("INSERT OR IGNORE INTO clases VALUES (?, ?, 'otro')", (d["clase"], d["clase"]))
                db.execute(
                    "INSERT INTO detecciones (captura_id, clase, confianza, caja) VALUES (?, ?, ?, ?)",
                    (captura["id"], d["clase"], float(d["confianza"]), json.dumps([int(v) for v in d["caja"]])),
                )
        return True

    def _con_detecciones(self, db, capturas):
        resultado = []
        for c in capturas:
            c = dict(c)
            c["detecciones"] = [
                dict(d, caja=json.loads(d["caja"])) for d in db.execute(
                    "SELECT d.clase, cl.nombre, cl.grupo, d.confianza, d.caja FROM detecciones d "
                    "JOIN clases cl ON cl.codigo = d.clase WHERE d.captura_id = ? ORDER BY d.confianza DESC",
                    (c["id"],)
                )
            ]
            resultado.append(c)
        return resultado

    def listar_capturas(self, recorrido_id=None, zona_id=None, solo_con_hallazgos=False, limite=50):
        condiciones, parametros = [], []
        if recorrido_id:
            condiciones.append("c.recorrido_id = ?")
            parametros.append(recorrido_id)
        if zona_id:
            condiciones.append("c.zona_id = ?")
            parametros.append(zona_id)
        if solo_con_hallazgos:
            condiciones.append("EXISTS (SELECT 1 FROM detecciones d WHERE d.captura_id = c.id)")
        donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
        with self._conectar() as db:
            filas = db.execute(
                "SELECT c.*, h.numero AS hilera, z.numero AS zona FROM capturas c "
                "LEFT JOIN zonas z ON z.id = c.zona_id LEFT JOIN hileras h ON h.id = z.hilera_id "
                "%s ORDER BY c.fecha DESC LIMIT ?" % donde, parametros + [limite]
            ).fetchall()
            return self._con_detecciones(db, filas)

    # Consultas del mapa, la ficha y el historial

    def mapa(self, recorrido_id=None):
        with self._conectar() as db:
            recorrido_id = self._recorrido_o_ultimo(db, recorrido_id)
            filas = db.execute(
                "SELECT z.id, h.numero AS hilera, z.numero, %s FROM zonas z "
                "JOIN hileras h ON h.id = z.hilera_id "
                "LEFT JOIN capturas c ON c.zona_id = z.id AND c.recorrido_id = ? "
                "LEFT JOIN detecciones d ON d.captura_id = c.id "
                "LEFT JOIN clases cl ON cl.codigo = d.clase "
                "WHERE h.sector_id = 1 GROUP BY z.id ORDER BY h.numero, z.numero" % RESUMEN_ZONA,
                (recorrido_id,)
            ).fetchall()
            sin_zona = db.execute(
                "SELECT COUNT(*) FROM capturas WHERE recorrido_id = ? AND zona_id IS NULL", (recorrido_id,)
            ).fetchone()[0]
        zonas = []
        for f in filas:
            z = dict(f)
            z["estado"] = estado_zona(z)
            zonas.append(z)
        return {"recorrido": recorrido_id, "zonas": zonas, "capturas_sin_zona": sin_zona}

    def ficha(self, zona_id, recorrido_id=None):
        with self._conectar() as db:
            zona = db.execute(
                "SELECT z.id, h.numero AS hilera, z.numero FROM zonas z JOIN hileras h ON h.id = z.hilera_id "
                "WHERE z.id = ?", (zona_id,)
            ).fetchone()
            if not zona:
                return None
            recorrido_id = self._recorrido_o_ultimo(db, recorrido_id)
            resumen = dict(db.execute(
                "SELECT %s FROM capturas c LEFT JOIN detecciones d ON d.captura_id = c.id "
                "LEFT JOIN clases cl ON cl.codigo = d.clase WHERE c.zona_id = ? AND c.recorrido_id = ?"
                % RESUMEN_ZONA, (zona_id, recorrido_id)
            ).fetchone())
            recorrido = db.execute(
                "SELECT r.*, m.nombre AS modelo, m.version AS modelo_version FROM recorridos r "
                "LEFT JOIN modelos m ON m.id = r.modelo_id WHERE r.id = ?", (recorrido_id,)
            ).fetchone()
        ficha = dict(zona)
        ficha["recorrido"] = dict(recorrido) if recorrido else None
        ficha["resumen"] = resumen
        ficha["estado"] = estado_zona(resumen)
        ficha["capturas"] = self.listar_capturas(recorrido_id, zona_id, limite=30) if recorrido_id else []
        return ficha

    def historial(self, zona_id, limite=50):
        """Un renglón por recorrido, incluso los que no pasaron por la zona (quedan como sin datos)."""
        with self._conectar() as db:
            filas = db.execute(
                "SELECT r.id AS recorrido, r.inicio, r.estado AS estado_recorrido, %s FROM recorridos r "
                "LEFT JOIN capturas c ON c.recorrido_id = r.id AND c.zona_id = ? "
                "LEFT JOIN detecciones d ON d.captura_id = c.id "
                "LEFT JOIN clases cl ON cl.codigo = d.clase "
                "GROUP BY r.id ORDER BY r.inicio DESC LIMIT ?" % RESUMEN_ZONA, (zona_id, limite)
            ).fetchall()
        historial = []
        for f in filas:
            h = dict(f)
            h["estado"] = estado_zona(h)
            historial.append(h)
        return historial

    # Incidencias

    def registrar_incidencia(self, recorrido_id, tipo, detalle=None, hilera=None, zona=None):
        with self._conectar() as db:
            db.execute(
                "INSERT INTO incidencias (recorrido_id, zona_id, tipo, fecha, detalle) VALUES (?, ?, ?, ?, ?)",
                (recorrido_id, self._zona_id(db, hilera, zona), tipo, _ahora(), detalle),
            )

    def listar_incidencias(self, recorrido_id):
        with self._conectar() as db:
            filas = db.execute(
                "SELECT i.*, h.numero AS hilera, z.numero AS zona FROM incidencias i "
                "LEFT JOIN zonas z ON z.id = i.zona_id LEFT JOIN hileras h ON h.id = z.hilera_id "
                "WHERE i.recorrido_id = ? ORDER BY i.fecha", (recorrido_id,)
            ).fetchall()
        return [dict(f) for f in filas]
