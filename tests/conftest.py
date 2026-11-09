import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for ruta in ("src", "ui/api", "ml"):
    sys.path.insert(0, os.path.join(RAIZ, ruta))
