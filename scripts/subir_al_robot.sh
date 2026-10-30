#!/usr/bin/env bash
# Copia src/ desde la PC al dock del Go2, en ~/Workspace/farmbot/src.
# No copia credenciales de GitHub: el repositorio se clona y actualiza en la PC.
# El entorno ~/Workspace/farmbot/.venv del dock no se toca.
#
# Uso: scripts/subir_al_robot.sh [usuario@ip]
set -euo pipefail

DESTINO="${1:-unitree@192.168.123.18}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

tar -C "$RAIZ" --exclude='__pycache__' --exclude='*.pyc' -czf - src \
  | ssh "$DESTINO" 'mkdir -p ~/Workspace/farmbot && rm -rf ~/Workspace/farmbot/src && tar -C ~/Workspace/farmbot -mxzf -'
echo "src/ copiado a $DESTINO:~/Workspace/farmbot/src"
