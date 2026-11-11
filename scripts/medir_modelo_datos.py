"""Mide las consultas de ficha e historial del modelo de datos propuesto (ui/api/modelo_datos.sql).

Carga datos sintéticos (200 zonas, 50 recorridos, 20 eventos por zona y recorrido) en una base SQLite en memoria
y repite cada consulta sobre 100 zonas. La cifra describe este equipo y estos datos; no sustituye la medición
de RFN4 en el equipo y con los datos del piloto.

    python3 scripts/medir_modelo_datos.py
"""
import os
import sqlite3
import statistics
import time

RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "api", "modelo_datos.sql")
RECORRIDOS, EVENTOS_POR_ZONA = 50, 20

FICHA = ("SELECT clase, COUNT(*) FROM evento WHERE zona_id = ? AND recorrido_id = "
         "(SELECT recorrido_id FROM evento WHERE zona_id = ? ORDER BY fecha DESC LIMIT 1) GROUP BY clase")
HISTORIAL = "SELECT recorrido_id, MIN(fecha), COUNT(*) FROM evento WHERE zona_id = ? GROUP BY recorrido_id ORDER BY MIN(fecha) DESC"


def cargar():
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON")
    with open(RUTA, encoding="utf-8") as f:
        con.executescript(f.read())
    con.execute("INSERT INTO modelo VALUES ('m1', 'tomate_verde,tomate_maduro', '2026-11-08', 'AerialYield-T2M')")
    for h in range(8):
        con.execute("INSERT INTO hilera (id, codigo) VALUES (?, ?)", (h + 1, "H%d" % (h + 1)))
        for z in range(25):
            con.execute("INSERT INTO zona (hilera_id, codigo) VALUES (?, ?)", (h + 1, "Z%d" % (z + 1)))
    zonas = [r[0] for r in con.execute("SELECT id FROM zona")]
    for r in range(RECORRIDOS):
        con.execute("INSERT INTO recorrido VALUES (?, '2026-10-01', '2026-10-01', 'completado')", ("R%d" % r,))
        for z in zonas:
            for e in range(EVENTOS_POR_ZONA):
                con.execute("INSERT INTO evento VALUES (?, ?, ?, 'm1', ?, 'tomate_verde', 0.9, 1, 2, 3, 4, NULL)",
                            ("R%d-%d-%d" % (r, z, e), "R%d" % r, z, "2026-%02d-01T10:00:%02d" % (r % 12 + 1, e)))
    con.commit()
    return con, zonas


def medir(con, consulta, zonas, dos_parametros):
    ms = []
    for z in zonas[:100]:
        t0 = time.perf_counter()
        con.execute(consulta, (z, z) if dos_parametros else (z,)).fetchall()
        ms.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ms), sorted(ms)[94], max(ms)


def main():
    con, zonas = cargar()
    print("zonas: %d, eventos: %d" % (len(zonas), con.execute("SELECT COUNT(*) FROM evento").fetchone()[0]))
    for nombre, consulta, dos in (("ficha", FICHA, True), ("historial", HISTORIAL, False)):
        mediana, p95, maximo = medir(con, consulta, zonas, dos)
        print("%-9s mediana %.2f ms, p95 %.2f ms, máximo %.2f ms" % (nombre, mediana, p95, maximo))


if __name__ == "__main__":
    main()
