"""Línea de comandos de Sabueso en el dock: python -m sabueso_robot <subcomando>.

Subcomandos de solo lectura: diagnostico, telemetria, captura-prueba, sincronizar.
El único que actúa sobre el robot es `postura`, y exige confirmar que hay un operador
presente con el control remoto (tarea F4.1). Ningún subcomando desplaza el robot.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from .config import cargar_config, cargar_limites
from .conexion import iniciar_dds

registro = logging.getLogger("sabueso")


def _fuente(config):
    from .telemetria import FuenteTelemetria

    iniciar_dds(config.interfaz_dds, config.dominio_dds)
    fuente = FuenteTelemetria(config)
    fuente.iniciar()
    return fuente


def cmd_diagnostico(args, config) -> int:
    from .sdk import sdk_disponible

    print(f"Configuración: interfaz {config.interfaz_dds}, dominio {config.dominio_dds}")
    print(f"Límites: {cargar_limites()}")
    if not sdk_disponible():
        print("FALLA  unitree_sdk2py no está instalado (ver docs/manual_instalacion.md)")
        return 1
    print("PASA   unitree_sdk2py importable")
    fuente = _fuente(config)
    recibidos = []
    fuente.al_actualizar(recibidos.append)
    time.sleep(args.segundos)
    fuente.detener()
    if not recibidos:
        print(f"FALLA  sin telemetría en {args.segundos} s (revise interfaz y tópicos)")
        return 1
    ultimo = recibidos[-1]
    print(f"PASA   {len(recibidos)} mensajes ({len(recibidos) / args.segundos:.1f} Hz)")
    print(f"       batería {ultimo.bateria_pct} %, voltaje {ultimo.voltaje_v} V, "
          f"obstáculo mínimo {ultimo.distancia_minima_m()} m, error {ultimo.codigo_error}")
    return 0


def cmd_telemetria(args, config) -> int:
    from .telemetria import RegistroTelemetria

    fuente = _fuente(config)
    registro_sql = None
    if args.registrar:
        ruta = Path(config.directorio_datos) / "telemetria.sqlite"
        registro_sql = RegistroTelemetria(str(ruta), periodo_min_s=args.periodo)
        fuente.al_actualizar(registro_sql.guardar)
    fin = time.monotonic() + args.duracion if args.duracion else None
    try:
        while fin is None or time.monotonic() < fin:
            time.sleep(args.periodo)
            estado = fuente.ultimo()
            if estado is not None and not args.registrar:
                print(f"{estado.marca_tiempo:.2f} batería={estado.bateria_pct} "
                      f"vel={estado.velocidad} obst={estado.distancia_minima_m()}")
    except KeyboardInterrupt:
        pass
    finally:
        fuente.detener()
        if registro_sql is not None:
            registro_sql.cerrar()
    return 0


def cmd_captura_prueba(args, config) -> int:
    from .captura import CamaraFrontal, ColaCapturas, ErrorCaptura

    iniciar_dds(config.interfaz_dds, config.dominio_dds)
    camara = CamaraFrontal(timeout_s=config.timeout_rpc_s)
    cola = ColaCapturas(config.directorio_datos)
    fallas = 0
    try:
        for _ in range(args.cantidad):
            inicio = time.monotonic()
            try:
                captura = cola.registrar(camara.obtener_jpeg(), args.recorrido, args.hilera, args.zona)
                print(f"{captura.id} {captura.estado_zona} {time.monotonic() - inicio:.2f} s "
                      f"{cola.ruta_absoluta(captura)}")
            except ErrorCaptura as error:
                fallas += 1
                print(f"FALLA  {error}")
            time.sleep(args.intervalo)
    finally:
        cola.cerrar()
    return 1 if fallas else 0


def cmd_sincronizar(args, config) -> int:
    from .captura import ColaCapturas
    from .sincronizacion import Sincronizador

    url = args.url or config.url_servidor
    if not url:
        print("Falta url_servidor en la configuración (decisión D1 pendiente) o --url.")
        return 1
    cola = ColaCapturas(config.directorio_datos)
    sincronizador = Sincronizador(cola, url, token=args.token)
    try:
        while True:
            resumen = sincronizador.sincronizar_una_vez()
            print(f"enviadas={resumen.enviadas} fallidas={resumen.fallidas} "
                  f"pendientes={resumen.pendientes}")
            if not args.continuo:
                return 1 if resumen.fallidas else 0
            espera = sincronizador.proxima_espera_s() if resumen.fallidas else args.periodo
            time.sleep(espera)
    except KeyboardInterrupt:
        return 0
    finally:
        cola.cerrar()


def cmd_postura(args, config) -> int:
    from .seguridad import ClienteSportGo2

    if not args.confirmo_operador_presente:
        print("Rechazado: agregue --confirmo-operador-presente.")
        return 2
    if not sys.stdin.isatty():
        print("Rechazado: la postura solo se ordena desde una terminal interactiva.")
        return 2
    respuesta = input(
        f"Orden '{args.postura}'. ¿Zona despejada a 2 m y control remoto en mano? Escriba SI: "
    )
    if respuesta.strip() != "SI":
        print("Cancelado.")
        return 2
    iniciar_dds(config.interfaz_dds, config.dominio_dds)
    cliente = ClienteSportGo2(timeout_s=config.timeout_rpc_s)
    acciones = {"de-pie": cliente.ponerse_de_pie, "echado": cliente.echarse}
    codigo = acciones[args.postura]()
    print(f"Código de respuesta: {codigo}")
    return 0 if codigo == 0 else 1


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m sabueso_robot", description=__doc__.split("\n")[0])
    parser.add_argument("--config", help="ruta a robot.yaml (por defecto config/robot.yaml)")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("diagnostico", help="SDK, DDS y recepción de telemetría (F2.3)")
    p.add_argument("--segundos", type=float, default=5.0)
    p.set_defaults(funcion=cmd_diagnostico)

    p = sub.add_parser("telemetria", help="muestra o registra la telemetría (F3.2)")
    p.add_argument("--registrar", action="store_true", help="guarda en SQLite en vez de imprimir")
    p.add_argument("--duracion", type=float, default=0, help="segundos; 0 = hasta Ctrl+C")
    p.add_argument("--periodo", type=float, default=1.0)
    p.set_defaults(funcion=cmd_telemetria)

    p = sub.add_parser("captura-prueba", help="capturas de la cámara frontal (F2.5)")
    p.add_argument("--cantidad", type=int, default=10)
    p.add_argument("--intervalo", type=float, default=1.0)
    p.add_argument("--recorrido", default="prueba")
    p.add_argument("--hilera")
    p.add_argument("--zona")
    p.set_defaults(funcion=cmd_captura_prueba)

    p = sub.add_parser("sincronizar", help="envía capturas pendientes al servidor (F3.4)")
    p.add_argument("--url")
    p.add_argument("--token", help="mejor por variable de entorno en la unidad systemd")
    p.add_argument("--continuo", action="store_true")
    p.add_argument("--periodo", type=float, default=30.0)
    p.set_defaults(funcion=cmd_sincronizar)

    p = sub.add_parser("postura", help="de pie o echado, sin desplazamiento (F4.1)")
    p.add_argument("postura", choices=["de-pie", "echado"])
    p.add_argument("--confirmo-operador-presente", action="store_true")
    p.set_defaults(funcion=cmd_postura)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return args.funcion(args, cargar_config(args.config))


if __name__ == "__main__":
    sys.exit(main())
