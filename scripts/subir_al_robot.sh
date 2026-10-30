#!/usr/bin/env bash
# Copia el software desde la PC al dock del Go2, en ~/Workspace/farmbot:
#   src/                       recorrido del robot
#   ui/api/ y ui/web/dist/     web del cliente (la web React se compila antes en la PC)
# No copia credenciales de GitHub: el repositorio se clona y actualiza en la PC.
# No toca ~/Workspace/farmbot/.venv ni los datos (ui/datos y datos/) del dock.
#
# Uso: scripts/subir_al_robot.sh [usuario@ip]
set -euo pipefail

DESTINO="${1:-unitree@192.168.123.18}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

if command -v npm >/dev/null 2>&1; then
  echo "compilando ui/web"
  (cd "$RAIZ/ui/web" && { [ -d node_modules ] || npm ci; } && npm run build >/dev/null)
elif [ ! -f "$RAIZ/ui/web/dist/index.html" ]; then
  echo "error: falta npm para compilar ui/web y no existe ui/web/dist" >&2
  exit 1
else
  echo "aviso: sin npm, se sube ui/web/dist tal como está" >&2
fi

tar -C "$RAIZ" --exclude='__pycache__' --exclude='*.pyc' -czf - src ui/api ui/web/dist \
  | ssh "$DESTINO" 'mkdir -p ~/Workspace/farmbot && cd ~/Workspace/farmbot && rm -rf src ui/api ui/web && tar -mxzf -'
echo "src/ y ui/ copiados a $DESTINO:~/Workspace/farmbot"
echo "si la web ya estaba corriendo, reiniciarla para usar la versión nueva"
