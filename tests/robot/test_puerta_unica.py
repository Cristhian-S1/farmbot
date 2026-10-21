"""F3.5: ninguna llamada de movimiento fuera del módulo de seguridad."""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2] / "robot"
PERMITIDO = RAIZ / "sabueso_robot" / "seguridad"
PATRON = re.compile(r"\.(Move|MoveToAbsolutePosition|MoveToIncrementPosition)\s*\(")


def test_move_solo_en_seguridad():
    infractores = [
        f"{archivo.relative_to(RAIZ)}:{numero}"
        for archivo in RAIZ.rglob("*.py")
        if PERMITIDO not in archivo.parents
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1)
        if PATRON.search(linea)
    ]
    assert not infractores, f"Llamadas de movimiento fuera de seguridad: {infractores}"
