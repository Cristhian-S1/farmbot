"""F3.5 y S10: el robot solo recibe órdenes de movimiento desde seguridad/cliente_sport.py.

Analiza el AST de todo el código Python del repositorio (robot/ y scripts/): ninguna llamada
ni acceso a métodos de SportClient u ObstaclesAvoidClient que desplacen el robot fuera del
adaptador, y el adaptador solo usa la lista blanca aprobada.
"""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ADAPTADOR = RAIZ / "robot" / "sabueso_robot" / "seguridad" / "cliente_sport.py"
PUERTA = RAIZ / "robot" / "sabueso_robot" / "seguridad" / "puerta_movimiento.py"
LISTA_BLANCA = {"Move", "StopMove", "StandUp", "StandDown", "BalanceStand", "SetTimeout", "Init"}
PELIGROSOS = {
    "Move", "MoveToAbsolutePosition", "MoveToIncrementPosition", "Damp", "StandUp",
    "StandDown", "BalanceStand", "RecoveryStand", "FrontFlip", "FrontJump", "FrontPounce",
    "FreeWalk", "StaticWalk", "TrotRun", "Dance1", "Dance2", "Hello", "Stretch", "Sit",
    "RiseSit", "SpeedLevel", "SwitchGait", "HandStand", "LeftFlip", "BackFlip", "_Call",
    "_CallNoReply",
}


def _archivos():
    for carpeta in ("robot", "scripts"):
        yield from (RAIZ / carpeta).rglob("*.py")


def _usos(arbol):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Attribute):
            yield nodo.attr, nodo.lineno
        elif (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id == "getattr"
            and len(nodo.args) >= 2
            and isinstance(nodo.args[1], ast.Constant)
        ):
            yield nodo.args[1].value, nodo.lineno


def test_movimiento_solo_en_el_adaptador_y_la_puerta():
    infractores = []
    for archivo in _archivos():
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nombre, linea in _usos(arbol):
            if nombre not in PELIGROSOS:
                continue
            if archivo == ADAPTADOR:
                continue
            if archivo == PUERTA and nombre == "Move":
                continue
            infractores.append(f"{archivo.relative_to(RAIZ)}:{linea} {nombre}")
    assert not infractores, f"Órdenes de movimiento fuera de seguridad: {infractores}"


def test_adaptador_usa_solo_la_lista_blanca():
    arbol = ast.parse(ADAPTADOR.read_text(encoding="utf-8"))
    llamados = {
        nodo.func.attr
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and isinstance(nodo.func.value, ast.Attribute)
        and nodo.func.value.attr == "_cliente"
    } | {
        nodo.func.attr
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and isinstance(nodo.func.value, ast.Name)
        and nodo.func.value.id == "cliente"
    }
    assert llamados <= LISTA_BLANCA, f"Métodos no aprobados: {sorted(llamados - LISTA_BLANCA)}"
