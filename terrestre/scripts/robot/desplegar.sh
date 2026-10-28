#!/usr/bin/env bash
# Copia el repositorio de Sabueso desde la PC/VM al dock del Go2.
#
# Solo copia archivos con rsync: no ejecuta nada en el dock (ni instalación, ni
# pruebas, ni comandos de movimiento). No copia .git, .beads, .venv,
# __pycache__, cachés locales de herramientas ni docs/inventario_robot.md.
#
# Uso: ./desplegar.sh [--destino unitree@192.168.123.18:~/sabueso] [--dry-run]
#   --destino RUTA  destino rsync (por defecto unitree@192.168.123.18:~/sabueso)
#   --dry-run       simula la copia y muestra qué archivos cambiarían
#   -h, --help      muestra esta ayuda
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESTINO="unitree@192.168.123.18:~/sabueso"
SECO=0

uso() {
  cat <<'EOF'
Uso: desplegar.sh [--destino RUTA] [--dry-run]

Copia el repositorio completo (salvo .git, .beads, .venv, __pycache__, cachés
locales y docs/inventario_robot.md) al dock del Go2 con rsync. Se ejecuta en la
PC/VM, nunca en el dock, y no ejecuta comandos remotos: solo transfiere archivos.

Opciones:
  --destino RUTA  destino rsync (por defecto unitree@192.168.123.18:~/sabueso)
  --dry-run       simula la copia y muestra los cambios sin escribir
  -h, --help      muestra esta ayuda

Después de copiar, instale o actualice el entorno EN el dock con:
  ssh unitree@192.168.123.18 ~/sabueso/scripts/robot/instalar_dock.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --destino)
      if [[ $# -lt 2 || -z "$2" ]]; then
        echo "ERROR: --destino requiere una ruta." >&2
        exit 2
      fi
      DESTINO="$2"; shift 2 ;;
    --dry-run) SECO=1; shift ;;
    -h|--help) uso; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; uso >&2; exit 2 ;;
  esac
done

if [[ -z "$DESTINO" ]]; then
  echo "ERROR: --destino requiere una ruta (por ejemplo unitree@192.168.123.18:~/sabueso)." >&2
  exit 2
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "ERROR: rsync no está instalado. En Ubuntu: sudo apt install rsync" >&2
  exit 1
fi

if [[ ! -f "${RAIZ}/pyproject.toml" ]]; then
  echo "ERROR: no se encontró ${RAIZ}/pyproject.toml; ejecute el script desde el repositorio." >&2
  exit 1
fi

OPCIONES=(-a --human-readable --itemize-changes)
if (( SECO )); then
  OPCIONES+=(--dry-run)
fi

echo "Origen:  ${RAIZ}/"
echo "Destino: ${DESTINO}"
if (( SECO )); then
  echo "Modo simulación (--dry-run): no se escribe nada."
fi

rsync "${OPCIONES[@]}" \
  --exclude '.git/' \
  --exclude '.beads/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.codegraph/' \
  --exclude '.serena/' \
  --exclude 'opencode.json' \
  --exclude 'docs/inventario_robot.md' \
  "${RAIZ}/" "$DESTINO/"

if (( SECO )); then
  echo "Simulación terminada; no se copió nada."
else
  echo "Copia terminada. Recuerde ejecutar instalar_dock.sh EN el dock."
fi
