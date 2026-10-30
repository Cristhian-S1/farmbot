"""Almacenamiento de registros: SQLite para los datos y una carpeta para las fotos."""
import base64
import os
import sqlite3

ESQUEMA = """
CREATE TABLE IF NOT EXISTS registros (
    id         TEXT PRIMARY KEY,
    recorrido  TEXT NOT NULL,
    fecha      TEXT NOT NULL,
    clase      TEXT NOT NULL,
    confianza  REAL NOT NULL,
    caja       TEXT NOT NULL,
    hilera     TEXT,
    zona       TEXT,
    foto       TEXT
)
"""

CAMPOS = ("id", "recorrido", "fecha", "clase", "confianza", "caja")


class Almacenamiento:
    def __init__(self, datos_dir):
        self.fotos_dir = os.path.join(datos_dir, "fotos")
        os.makedirs(self.fotos_dir, exist_ok=True)
        self.ruta_db = os.path.join(datos_dir, "sabueso.db")
        with self._conectar() as db:
            db.execute(ESQUEMA)

    def _conectar(self):
        db = sqlite3.connect(self.ruta_db)
        db.row_factory = sqlite3.Row
        return db

    def guardar(self, registro):
        """Guarda un registro del robot. Si el id ya existe (reenvío desde la cola), no lo duplica."""
        faltan = [c for c in CAMPOS if c not in registro]
        if faltan:
            raise ValueError("faltan campos: %s" % ", ".join(faltan))
        foto = None
        if registro.get("foto_jpeg"):
            foto = "%s.jpg" % registro["id"]
            with open(os.path.join(self.fotos_dir, foto), "wb") as f:
                f.write(base64.b64decode(registro["foto_jpeg"]))
        with self._conectar() as db:
            db.execute(
                "INSERT OR IGNORE INTO registros VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (registro["id"], registro["recorrido"], registro["fecha"], registro["clase"],
                 float(registro["confianza"]), ",".join(str(v) for v in registro["caja"]),
                 registro.get("hilera"), registro.get("zona"), foto),
            )

    def listar(self, limite=200):
        with self._conectar() as db:
            filas = db.execute("SELECT * FROM registros ORDER BY fecha DESC LIMIT ?", (limite,)).fetchall()
        return [dict(f) for f in filas]
