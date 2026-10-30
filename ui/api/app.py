"""API de la web del cliente: recibe los registros del robot y los entrega a la web React.

Uso, desde ui/api:
    python3 app.py
API en http://<equipo>:5000/api. Si existe ui/web/dist (npm run build), también
sirve la web React en http://<equipo>:5000.
"""
import os

from flask import Flask, abort, jsonify, request, send_from_directory

from almacenamiento import Almacenamiento

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS_DIR = os.environ.get("SABUESO_UI_DATOS", os.path.join(AQUI, "..", "datos"))
WEB_DIR = os.path.join(AQUI, "..", "web", "dist")
HOST = os.environ.get("SABUESO_UI_HOST", "0.0.0.0")
PUERTO = int(os.environ.get("SABUESO_UI_PUERTO", "5000"))


def crear_app(almacenamiento, web_dir=WEB_DIR):
    app = Flask(__name__, static_folder=None)

    @app.route("/api/registros", methods=["POST"])
    def recibir_registro():
        registro = request.get_json(silent=True)
        if not isinstance(registro, dict):
            abort(400, "se esperaba un JSON")
        try:
            almacenamiento.guardar(registro)
        except (ValueError, TypeError) as e:
            abort(400, str(e))
        return jsonify(ok=True, id=registro["id"]), 201

    @app.route("/api/registros")
    def listar_registros():
        return jsonify(almacenamiento.listar())

    @app.route("/fotos/<nombre>")
    def foto(nombre):
        return send_from_directory(almacenamiento.fotos_dir, nombre)

    @app.route("/", defaults={"ruta": ""})
    @app.route("/<path:ruta>")
    def web(ruta):
        if not os.path.isdir(web_dir):
            return "Web no compilada: ejecutar npm run build en ui/web", 404
        if ruta and os.path.isfile(os.path.join(web_dir, ruta)):
            return send_from_directory(web_dir, ruta)
        return send_from_directory(web_dir, "index.html")

    return app


if __name__ == "__main__":
    crear_app(Almacenamiento(DATOS_DIR)).run(host=HOST, port=PUERTO)
