"""Pruebas de la API. Desde ui/api: python3 -m unittest"""
import base64
import os
import sys
import tempfile
import time
import unittest

from almacenamiento import Almacenamiento
from app import crear_app
from control import ControlRecorrido

ESTRUCTURA = {"sector": "Invernadero A", "predio": "Pampa Concordia", "hileras": 2, "zonas_por_hilera": 3}
FOTO = base64.b64encode(b"\xff\xd8\xff\xd9").decode()


def captura(id_, hilera=1, zona=1, detecciones=(), recorrido="R1", fecha="2026-11-04T10:00:00"):
    return {"id": id_, "recorrido": recorrido, "fecha": fecha, "hilera": hilera, "zona": zona,
            "foto_jpeg": FOTO, "detecciones": [
                {"clase": c, "confianza": 0.9, "caja": [1, 2, 3, 4]} for c in detecciones]}


class BaseApi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.datos = self.tmp.name
        self.almacenamiento = Almacenamiento(self.datos, ESTRUCTURA)
        self.src = os.path.join(self.datos, "src")
        os.makedirs(os.path.join(self.src, "recorrido"))
        self.control = ControlRecorrido(self.almacenamiento, self.src, sys.executable,
                                        "http://127.0.0.1:1", self.datos)
        self.cliente = crear_app(self.almacenamiento, self.control, web_dir=self.datos).test_client()

    def tearDown(self):
        self.control.detener()
        self.tmp.cleanup()

    def zona(self, mapa, hilera, numero):
        return next(z for z in mapa["zonas"] if z["hilera"] == hilera and z["numero"] == numero)


class PruebasCapturas(BaseApi):
    def test_estructura_crea_hileras_y_zonas(self):
        datos = self.cliente.get("/api/estructura").get_json()
        self.assertEqual(datos["sector"]["nombre"], "Invernadero A")
        self.assertEqual([len(h["zonas"]) for h in datos["sector"]["hileras"]], [3, 3])

    def test_captura_repetida_no_se_duplica(self):
        r = self.cliente.post("/api/capturas", json=captura("a", detecciones=["maleza"]))
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.get_json()["nueva"])
        r = self.cliente.post("/api/capturas", json=captura("a", detecciones=["maleza"]))
        self.assertFalse(r.get_json()["nueva"])
        self.assertEqual(len(self.cliente.get("/api/capturas").get_json()), 1)

    def test_formato_antiguo_de_registros(self):
        registro = {"id": "b", "recorrido": "R1", "fecha": "2026-11-04T10:00:00", "clase": "maleza",
                    "confianza": 0.8, "caja": [1, 2, 3, 4], "hilera": "1", "zona": None}
        self.assertEqual(self.cliente.post("/api/registros", json=registro).status_code, 201)
        capturas = self.cliente.get("/api/capturas").get_json()
        self.assertEqual(capturas[0]["detecciones"][0]["clase"], "maleza")
        self.assertIsNone(capturas[0]["zona_id"])

    def test_captura_incompleta_responde_400(self):
        r = self.cliente.post("/api/capturas", json={"id": "x"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("faltan campos", r.get_json()["error"])


class PruebasMapa(BaseApi):
    def test_estados_de_las_zonas(self):
        self.cliente.post("/api/capturas", json=captura("1", 1, 1))
        self.cliente.post("/api/capturas", json=captura("2", 1, 2, ["maleza", "tomate_verde"]))
        self.cliente.post("/api/capturas", json=captura("3", 1, 3, ["follaje_mancha"]))
        self.cliente.post("/api/capturas", json=captura("4", 2, 1, ["maleza", "follaje_marchitez"]))
        self.cliente.post("/api/capturas", json=captura("5", None, None, ["maleza"]))
        mapa = self.cliente.get("/api/mapa").get_json()
        self.assertEqual(mapa["recorrido"], "R1")
        self.assertEqual(self.zona(mapa, 1, 1)["estado"], "sin_alertas")
        self.assertEqual(self.zona(mapa, 1, 2)["estado"], "revisar_maleza")
        self.assertEqual(self.zona(mapa, 1, 2)["verdes"], 1)
        self.assertEqual(self.zona(mapa, 1, 3)["estado"], "revisar_follaje")
        self.assertEqual(self.zona(mapa, 2, 1)["estado"], "revisar_maleza")
        self.assertEqual(self.zona(mapa, 2, 1)["follaje"], 1)
        self.assertEqual(self.zona(mapa, 2, 2)["estado"], "sin_datos")
        self.assertEqual(mapa["capturas_sin_zona"], 1)

    def test_recorridos_cuentan_zonas_como_el_mapa(self):
        self.cliente.post("/api/capturas", json=captura("1", 1, 1, ["maleza", "follaje_mancha"]))
        self.cliente.post("/api/capturas", json=captura("2", 1, 1, ["maleza"]))
        self.cliente.post("/api/capturas", json=captura("3", 1, 2, ["follaje_mancha"]))
        self.cliente.post("/api/capturas", json=dict(captura("4", 1, 3, ["maleza"]), analisis="pendiente"))
        self.cliente.post("/api/capturas", json=captura("5", None, None, ["maleza"]))
        self.cliente.post("/api/capturas", json=captura("6", 2, 1, ["follaje_mancha"], recorrido="R2"))
        recorridos = {r["id"]: r for r in self.cliente.get("/api/recorridos").get_json()}
        self.assertEqual(recorridos["R1"]["zonas_maleza"], 1)
        self.assertEqual(recorridos["R1"]["zonas_follaje"], 1)
        self.assertEqual(recorridos["R2"]["zonas_maleza"], 0)
        self.assertEqual(recorridos["R2"]["zonas_follaje"], 1)

    def test_ficha_e_historial(self):
        self.cliente.post("/api/capturas", json=captura("1", 1, 1, ["maleza"], recorrido="R1"))
        self.cliente.post("/api/capturas", json=captura("2", 1, 2, [], recorrido="R2", fecha="2026-11-05T10:00:00"))
        zona_id = self.zona(self.cliente.get("/api/mapa?recorrido=R1").get_json(), 1, 1)["id"]

        ficha = self.cliente.get("/api/zonas/%d?recorrido=R1" % zona_id).get_json()
        self.assertEqual(ficha["estado"], "revisar_maleza")
        self.assertEqual(ficha["capturas"][0]["detecciones"][0]["caja"], [1, 2, 3, 4])

        historial = self.cliente.get("/api/zonas/%d/historial" % zona_id).get_json()
        self.assertEqual([(h["recorrido"], h["estado"]) for h in historial],
                         [("R2", "sin_datos"), ("R1", "revisar_maleza")])
        self.assertEqual(self.cliente.get("/api/zonas/999").status_code, 404)

    def test_mapa_sin_recorridos(self):
        mapa = self.cliente.get("/api/mapa").get_json()
        self.assertIsNone(mapa["recorrido"])
        self.assertTrue(all(z["estado"] == "sin_datos" for z in mapa["zonas"]))


class PruebasControl(BaseApi):
    def escribir_recorrido(self, codigo):
        with open(os.path.join(self.src, "recorrido", "__main__.py"), "w") as f:
            f.write(codigo)

    def test_iniciar_y_detener(self):
        self.escribir_recorrido("import time\nprint('listo', flush=True)\ntime.sleep(60)\n")
        r = self.cliente.post("/api/recorridos", json={"hilera": 1, "zona": 2})
        self.assertEqual(r.status_code, 201)
        recorrido_id = r.get_json()["recorrido"]
        self.assertTrue(self.cliente.get("/api/recorridos/actual").get_json()["corriendo"])
        self.assertEqual(self.cliente.post("/api/recorridos", json={}).status_code, 409)

        self.cliente.post("/api/recorridos/actual/detener")
        self.assertFalse(self.cliente.get("/api/recorridos/actual").get_json()["corriendo"])
        self.assertEqual(self.almacenamiento.recorrido(recorrido_id)["estado"], "completado")

    def test_recorrido_que_se_cae_queda_incompleto(self):
        self.escribir_recorrido("raise SystemExit(3)\n")
        recorrido_id = self.cliente.post("/api/recorridos", json={}).get_json()["recorrido"]
        for _ in range(50):
            if not self.cliente.get("/api/recorridos/actual").get_json()["corriendo"]:
                break
            time.sleep(0.1)
        self.assertEqual(self.almacenamiento.recorrido(recorrido_id)["estado"], "incompleto")
        incidencias = self.cliente.get("/api/recorridos/%s/incidencias" % recorrido_id).get_json()
        self.assertEqual(incidencias[0]["tipo"], "proceso")

    def test_robot_avisa_el_fin(self):
        self.cliente.post("/api/capturas", json=captura("1"))
        self.cliente.post("/api/recorridos/R1/fin", json={"estado": "completado"})
        recorridos = self.cliente.get("/api/recorridos").get_json()
        self.assertEqual(recorridos[0]["estado"], "completado")
        self.assertEqual(recorridos[0]["capturas"], 1)


if __name__ == "__main__":
    unittest.main()
