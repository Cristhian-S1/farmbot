"""Mide la ficha y el historial de zona del modelo de datos de la API (SQLite, ui/api/almacenamiento.py).

Carga datos sintéticos (200 zonas, 50 recorridos, 20 capturas con una detección por zona y recorrido) en una
base temporal y repite cada consulta sobre 100 zonas. La cifra describe este equipo y estos datos; no sustituye
la medición de RFN4 en el equipo y con los datos del piloto.

    python3 scripts/medir_modelo_datos.py
"""
import os
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "api"))
from almacenamiento import Almacenamiento  # noqa: E402

RECORRIDOS, CAPTURAS_POR_ZONA = 50, 20


def cargar(datos_dir):
    alm = Almacenamiento(datos_dir, {"sector": "A", "predio": "P", "hileras": 8, "zonas_por_hilera": 25})
    with alm._conectar() as db:
        zonas = [r[0] for r in db.execute("SELECT id FROM zonas")]
        for r in range(RECORRIDOS):
            fecha = "2026-%02d-%02dT10:00:00" % (r % 12 + 1, r // 12 + 1)
            db.execute("INSERT INTO recorridos (id, sector_id, estado, inicio) VALUES (?, 1, 'completado', ?)", ("R%d" % r, fecha))
            for z in zonas:
                for e in range(CAPTURAS_POR_ZONA):
                    cid = "R%d-%d-%d" % (r, z, e)
                    db.execute("INSERT INTO capturas VALUES (?, ?, ?, ?, NULL, 'listo')", (cid, "R%d" % r, z, fecha))
                    db.execute("INSERT INTO detecciones (captura_id, clase, confianza, caja) "
                               "VALUES (?, 'tomate_verde', 0.9, '[1,2,3,4]')", (cid,))
    return alm, zonas


def medir(funcion, zonas):
    ms = []
    for z in zonas[:100]:
        t0 = time.perf_counter()
        funcion(z)
        ms.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ms), sorted(ms)[94], max(ms)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        alm, zonas = cargar(tmp)
        with alm._conectar() as db:
            capturas = db.execute("SELECT COUNT(*) FROM capturas").fetchone()[0]
        print("zonas: %d, capturas: %d" % (len(zonas), capturas))
        for nombre, funcion in (("ficha", alm.ficha), ("historial", alm.historial)):
            mediana, p95, maximo = medir(funcion, zonas)
            print("%-9s mediana %.2f ms, p95 %.2f ms, máximo %.2f ms" % (nombre, mediana, p95, maximo))


if __name__ == "__main__":
    main()
