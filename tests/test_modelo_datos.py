"""Comprueba el modelo de datos: el de la API (SQLite, almacenamiento.py) con datos sintéticos, y que
ui/api/modelo_datos.sql (MySQL, el del informe) declare las mismas tablas, columnas y clases.

La medición de la ficha corre en el equipo de desarrollo y no sustituye la verificación de RFN4
en el equipo y con los datos reales del piloto.
"""
import os
import re
import sqlite3
import time

import pytest

from almacenamiento import CLASES, ESQUEMA, Almacenamiento

RUTA_MYSQL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "api", "modelo_datos.sql")
HILERAS, ZONAS_POR_HILERA, RECORRIDOS, CAPTURAS_POR_ZONA = 8, 25, 6, 3  # 200 zonas, como exige RFN4
# Tabla de SQLite (plural) -> tabla de MySQL (singular).
TABLAS = {"sectores": "sector", "hileras": "hilera", "zonas": "zona", "clases": "clase", "modelos": "modelo",
          "recorridos": "recorrido", "capturas": "captura", "detecciones": "deteccion", "incidencias": "incidencia"}


def captura(id_, recorrido, hilera, zona, clases=("tomate_verde",), fecha="2026-10-01T10:00:00"):
    return {"id": id_, "recorrido": recorrido, "fecha": fecha, "hilera": hilera, "zona": zona,
            "detecciones": [{"clase": c, "confianza": 0.9, "caja": [1, 2, 30, 40]} for c in clases]}


@pytest.fixture()
def alm(tmp_path):
    a = Almacenamiento(str(tmp_path), {"sector": "Invernadero A", "predio": "Pampa Concordia",
                                       "hileras": HILERAS, "zonas_por_hilera": ZONAS_POR_HILERA})
    with a._conectar() as db:  # carga directa: guardar_captura una por una sería lento
        zonas = [r[0] for r in db.execute("SELECT id FROM zonas")]
        for r in range(RECORRIDOS):
            fecha = "2026-10-%02dT10:00:00" % (r + 1)
            db.execute("INSERT INTO recorridos (id, sector_id, estado, inicio) VALUES (?, 1, 'completado', ?)", ("R%d" % r, fecha))
            for z in zonas:
                for e in range(CAPTURAS_POR_ZONA):
                    cid = "R%d-%d-%d" % (r, z, e)
                    db.execute("INSERT INTO capturas VALUES (?, ?, ?, ?, NULL, 'listo')", (cid, "R%d" % r, z, fecha))
                    db.execute("INSERT INTO detecciones (captura_id, clase, confianza, caja) VALUES (?, ?, 0.9, '[1,2,3,4]')",
                               (cid, "tomate_verde" if e % 2 else "tomate_maduro"))
    return a


def test_hay_200_zonas_y_las_capturas_esperadas(alm):
    with alm._conectar() as db:
        assert db.execute("SELECT COUNT(*) FROM zonas").fetchone()[0] == 200
        assert db.execute("SELECT COUNT(*) FROM capturas").fetchone()[0] == 200 * RECORRIDOS * CAPTURAS_POR_ZONA


def test_las_restricciones_rechazan_datos_incoherentes(alm):
    with alm._conectar() as db:
        for malo in (("x1", "R0", 99999),  # zona inexistente
                     ("x2", "NO_EXISTE", 1)):  # recorrido inexistente
            with pytest.raises(sqlite3.IntegrityError):
                db.execute("INSERT INTO capturas VALUES (?, ?, ?, '2026-10-01', NULL, 'listo')", malo)
        with pytest.raises(sqlite3.IntegrityError):  # deteccion de una captura inexistente
            db.execute("INSERT INTO detecciones (captura_id, clase, confianza, caja) VALUES ('no', 'maleza', 0.5, '[]')")


def test_captura_sin_zona_es_valida_y_el_reenvio_no_duplica(alm):
    for _ in range(2):  # el robot reenvía desde su cola local
        alm.guardar_captura(captura("sinzona", "R0", None, None))
    with alm._conectar() as db:
        assert [tuple(f) for f in db.execute("SELECT zona_id FROM capturas WHERE id = 'sinzona'")] == [(None,)]
        assert db.execute("SELECT COUNT(*) FROM detecciones WHERE captura_id = 'sinzona'").fetchone()[0] == 1


def test_la_ficha_de_zona_usa_el_indice_y_responde_rapido(alm):
    zona = 100
    with alm._conectar() as db:
        plan = " ".join(str(tuple(r)) for r in db.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM capturas WHERE zona_id = ? AND recorrido_id = ?", (zona, "R5")))
    assert "capturas_recorrido_zona" in plan
    t0 = time.perf_counter()
    ficha = alm.ficha(zona)
    assert time.perf_counter() - t0 < 2.0  # RFN4: menos de 2 s (aquí sobre datos sintéticos)
    assert ficha["recorrido"]["id"] == "R%d" % (RECORRIDOS - 1)  # sin recorrido pedido, el último
    assert ficha["resumen"]["capturas"] == CAPTURAS_POR_ZONA


def test_el_historial_lista_un_recorrido_por_fecha(alm):
    assert [h["recorrido"] for h in alm.historial(7)] == ["R%d" % r for r in reversed(range(RECORRIDOS))]


def columnas_mysql():
    texto = open(RUTA_MYSQL, encoding="utf-8").read()
    tablas = {}
    for nombre, cuerpo in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\) ENGINE", texto, re.S):
        tablas[nombre] = {m.group(1) for m in re.finditer(r"^\s{4}(\w+) [A-Z]", cuerpo, re.M)
                          if m.group(1) not in ("UNIQUE", "INDEX", "FOREIGN", "CHECK", "REFERENCES", "ON")}
    return tablas, texto


def test_el_sql_de_mysql_coincide_con_el_esquema_de_la_api():
    db = sqlite3.connect(":memory:")
    db.executescript(ESQUEMA)
    sqlite = {TABLAS[t]: {c[1] for c in db.execute("PRAGMA table_info(%s)" % t)}
              for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    mysql, texto = columnas_mysql()
    assert mysql == sqlite
    assert set(re.findall(r"\('(\w+)', '[^']+', '(\w+)'\)", texto)) == {(c, g) for c, _, g in CLASES}
