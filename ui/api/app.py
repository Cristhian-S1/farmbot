"""API de la web del cliente: recibe las capturas del robot y las entrega a la web React.

Uso, desde ui/api:
    python3 app.py
API en http://<equipo>:5000/api. Si existe ui/web/dist (npm run build), también
sirve la web React en http://<equipo>:5000.
"""
import json
import os

from flask import Flask, abort, jsonify, request, send_from_directory

from almacenamiento import ESTADOS_RECORRIDO, Almacenamiento
from control import ControlRecorrido, RecorridoEnCurso, python_robot

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS_DIR = os.environ.get("SABUESO_UI_DATOS", os.path.join(AQUI, "..", "datos"))
WEB_DIR = os.path.join(AQUI, "..", "web", "dist")
SRC_DIR = os.environ.get("SABUESO_SRC", os.path.join(AQUI, "..", "..", "src"))
ESTRUCTURA = os.environ.get("SABUESO_ESTRUCTURA", os.path.join(AQUI, "estructura.json"))
HOST = os.environ.get("SABUESO_UI_HOST", "0.0.0.0")
PUERTO = int(os.environ.get("SABUESO_UI_PUERTO", "5000"))


def _json():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        abort(400, "se esperaba un JSON")
    return datos


def crear_app(almacenamiento, control, web_dir=WEB_DIR):
    app = Flask(__name__, static_folder=None)

    @app.route("/api/estructura")
    def estructura():
        return jsonify(almacenamiento.estructura())

    # Robot

    @app.route("/api/capturas", methods=["POST"])
    @app.route("/api/registros", methods=["POST"])
    def recibir_captura():
        captura = _json()
        try:
            nueva = almacenamiento.guardar_captura(captura)
        except (ValueError, TypeError, KeyError) as e:
            abort(400, str(e))
        return jsonify(ok=True, id=captura["id"], nueva=nueva), 201

    @app.route("/api/recorridos/<recorrido_id>/fin", methods=["POST"])
    def fin_recorrido(recorrido_id):
        estado = _json().get("estado", "completado")
        if estado not in ESTADOS_RECORRIDO:
            abort(400, "estado no válido")
        almacenamiento.cerrar_recorrido(recorrido_id, estado)
        return jsonify(ok=True)

    @app.route("/api/recorridos/<recorrido_id>/incidencias", methods=["POST"])
    def nueva_incidencia(recorrido_id):
        datos = _json()
        if not datos.get("tipo"):
            abort(400, "falta el tipo de incidencia")
        almacenamiento.registrar_incidencia(recorrido_id, datos["tipo"], datos.get("detalle"),
                                            datos.get("hilera"), datos.get("zona"))
        return jsonify(ok=True), 201

    # Web: control del recorrido

    @app.route("/api/recorridos")
    def listar_recorridos():
        return jsonify(almacenamiento.listar_recorridos())

    @app.route("/api/recorridos", methods=["POST"])
    def iniciar_recorrido():
        datos = request.get_json(silent=True) or {}
        try:
            recorrido_id = control.iniciar(datos.get("hilera"), datos.get("zona"))
        except RecorridoEnCurso as e:
            abort(409, "ya hay un recorrido en curso: %s" % e)
        except OSError as e:
            abort(500, "no se pudo iniciar el recorrido: %s" % e)
        return jsonify(ok=True, recorrido=recorrido_id), 201

    @app.route("/api/recorridos/actual")
    def recorrido_actual():
        return jsonify(control.estado())

    @app.route("/api/recorridos/actual/detener", methods=["POST"])
    def detener_recorrido():
        return jsonify(ok=True, recorrido=control.detener())

    @app.route("/api/recorridos/<recorrido_id>/incidencias")
    def listar_incidencias(recorrido_id):
        return jsonify(almacenamiento.listar_incidencias(recorrido_id))

    # Web: consulta

    @app.route("/api/mapa")
    def mapa():
        return jsonify(almacenamiento.mapa(request.args.get("recorrido")))

    @app.route("/api/zonas/<int:zona_id>")
    def ficha(zona_id):
        ficha = almacenamiento.ficha(zona_id, request.args.get("recorrido"))
        if ficha is None:
            abort(404, "la zona no existe")
        return jsonify(ficha)

    @app.route("/api/zonas/<int:zona_id>/historial")
    def historial(zona_id):
        return jsonify(almacenamiento.historial(zona_id))

    @app.route("/api/capturas")
    def listar_capturas():
        return jsonify(almacenamiento.listar_capturas(
            request.args.get("recorrido"),
            solo_con_hallazgos=request.args.get("hallazgos") == "1",
            limite=min(int(request.args.get("limite", 50)), 200),
        ))

    @app.route("/fotos/<nombre>")
    def foto(nombre):
        return send_from_directory(almacenamiento.fotos_dir, nombre)

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(500)
    def error_json(e):
        if request.path.startswith("/api/"):
            return jsonify(ok=False, error=e.description), e.code
        return e

    @app.route("/", defaults={"ruta": ""})
    @app.route("/<path:ruta>")
    def web(ruta):
        if not os.path.isdir(web_dir):
            return "Web no compilada: ejecutar npm run build en ui/web", 404
        if ruta and os.path.isfile(os.path.join(web_dir, ruta)):
            return send_from_directory(web_dir, ruta)
        return send_from_directory(web_dir, "index.html")

    return app


def main():
    with open(ESTRUCTURA) as f:
        almacenamiento = Almacenamiento(DATOS_DIR, json.load(f))
    control = ControlRecorrido(almacenamiento, os.path.abspath(SRC_DIR), python_robot(),
                               "http://127.0.0.1:%d" % PUERTO, DATOS_DIR)
    crear_app(almacenamiento, control).run(host=HOST, port=PUERTO, threaded=True)


if __name__ == "__main__":
    main()
