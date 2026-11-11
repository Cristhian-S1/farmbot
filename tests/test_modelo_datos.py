"""Comprueba el modelo de datos propuesto (ui/api/modelo_datos.sql) con datos sintéticos.

Es una prueba de factibilidad: la medición de la consulta de ficha corre en el equipo de desarrollo
y no sustituye la verificación de RFN4 en el equipo y con los datos reales del piloto.
"""
import os
import sqlite3
import time

import pytest

RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "api", "modelo_datos.sql")
HILERAS, ZONAS_POR_HILERA, RECORRIDOS, EVENTOS_POR_ZONA = 8, 25, 6, 3  # 200 zonas, como exige RFN4


@pytest.fixture()
def db():
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON")
    with open(RUTA, encoding="utf-8") as f:
        con.executescript(f.read())
    con.execute("INSERT INTO modelo VALUES ('m1', 'tomate_verde,tomate_maduro', '2026-11-08', 'AerialYield-T2M')")
    for h in range(HILERAS):
        con.execute("INSERT INTO hilera (id, codigo) VALUES (?, ?)", (h + 1, "H%d" % (h + 1)))
        for z in range(ZONAS_POR_HILERA):
            con.execute("INSERT INTO zona (hilera_id, codigo) VALUES (?, ?)", (h + 1, "Z%d" % (z + 1)))
    zonas = [r[0] for r in con.execute("SELECT id FROM zona")]
    for r in range(RECORRIDOS):
        con.execute("INSERT INTO recorrido VALUES (?, ?, ?, 'completado')", ("R%d" % r, "2026-10-%02d" % (r + 1), "2026-10-%02d" % (r + 1)))
        for z in zonas:
            for e in range(EVENTOS_POR_ZONA):
                con.execute("INSERT INTO evento VALUES (?, ?, ?, 'm1', ?, ?, 0.9, 1, 2, 30, 40, NULL)",
                            ("R%d-%d-%d" % (r, z, e), "R%d" % r, z, "2026-10-%02dT10:00:%02d" % (r + 1, e), "tomate_verde" if e % 2 else "tomate_maduro"))
    con.commit()
    return con


def test_hay_200_zonas_y_los_eventos_esperados(db):
    assert db.execute("SELECT COUNT(*) FROM zona").fetchone()[0] == 200
    assert db.execute("SELECT COUNT(*) FROM evento").fetchone()[0] == 200 * RECORRIDOS * EVENTOS_POR_ZONA


def test_las_restricciones_rechazan_datos_incoherentes(db):
    fila = ("x", "R0", 1, "m1", "2026-10-01T10:00:00", "tomate_verde", 0.5, 1, 2, 3, 4, None)
    db.execute("INSERT INTO evento VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", fila)
    for malo in (("y", "R0", 99999) + fila[3:],  # zona inexistente
                 ("y", "NO_EXISTE", 1) + fila[3:],  # recorrido inexistente
                 ("y", "R0", 1, "m1", "2026-10-01T10:00:00", "tomate_verde", 1.5, 1, 2, 3, 4, None)):  # confianza fuera de rango
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO evento VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", malo)


def test_evento_sin_zona_es_valido_y_el_reenvio_no_duplica(db):
    fila = ("sinzona", "R0", None, "m1", "2026-10-01T10:00:00", "tomate_verde", 0.5, 1, 2, 3, 4, None)
    for _ in range(2):  # el robot reenvía desde su cola local
        db.execute("INSERT OR IGNORE INTO evento VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", fila)
    assert db.execute("SELECT COUNT(*) FROM evento WHERE id = 'sinzona'").fetchone()[0] == 1


def test_la_ficha_de_zona_usa_el_indice_y_responde_rapido(db):
    zona = 100
    ficha = ("SELECT clase, COUNT(*) FROM evento WHERE zona_id = ? AND recorrido_id = "
             "(SELECT recorrido_id FROM evento WHERE zona_id = ? ORDER BY fecha DESC LIMIT 1) GROUP BY clase")
    plan = " ".join(str(r) for r in db.execute("EXPLAIN QUERY PLAN " + ficha, (zona, zona)))
    assert "evento_zona_fecha" in plan
    t0 = time.perf_counter()
    filas = db.execute(ficha, (zona, zona)).fetchall()
    assert time.perf_counter() - t0 < 2.0  # RFN4: menos de 2 s (aquí sobre datos sintéticos)
    assert sum(n for _, n in filas) == EVENTOS_POR_ZONA


def test_el_historial_lista_un_recorrido_por_fecha(db):
    filas = db.execute("SELECT recorrido_id, MIN(fecha) FROM evento WHERE zona_id = 7 GROUP BY recorrido_id ORDER BY MIN(fecha) DESC").fetchall()
    assert [f[0] for f in filas] == ["R%d" % r for r in reversed(range(RECORRIDOS))]
