#!/usr/bin/env bash
# Instala el entorno de Sabueso EN el dock del Go2 (Ubuntu 20.04, usuario unitree).
#
# Deja ~/sabueso/.venv con unitree_sdk2py y el paquete sabueso_robot, CycloneDDS
# compilado en ~/cyclonedds/install y las dependencias PyYAML y pytest. Es
# idempotente: conserva lo que ya existe y omite la compilación de CycloneDDS si
# ~/cyclonedds/install está presente.
#
# ADVERTENCIA: ejecútelo en una terminal SIN ROS 2 cargado (sin source /opt/ros/...).
# El CycloneDDS de ROS 2 (Foxy) entra en conflicto con el 0.10.2 que exige
# unitree_sdk2py. Consulte docs/entorno.md.
#
# Uso: ./instalar_dock.sh [--solo-verificar] [--con-apt]
#   --solo-verificar  no instala nada; solo comprueba las importaciones
#   --con-apt         instala antes los paquetes del sistema con sudo apt
#   -h, --help        muestra esta ayuda
set -euo pipefail

REPO="${HOME}/sabueso"
VENV="${REPO}/.venv"
PYTHON="${VENV}/bin/python"
PIP="${VENV}/bin/pip"
CYCLONEDDS="${HOME}/cyclonedds"
CYCLONEDDS_HOME="${CYCLONEDDS}/install"
SDK="${HOME}/unitree_sdk2_python"

# unitree_sdk2py compila su enlace de Python contra esta instalación de CycloneDDS.
export CYCLONEDDS_HOME

SOLO_VERIFICAR=0
CON_APT=0

uso() {
  cat <<'EOF'
Uso: instalar_dock.sh [opciones]

Instala en el dock del Go2 el entorno de Sabueso (Ubuntu 20.04, usuario unitree):
venv, CycloneDDS 0.10.2, unitree_sdk2_python, PyYAML, pytest y el paquete del
repositorio. Debe ejecutarse EN el dock, con el repositorio ya copiado en
~/sabueso (scripts/robot/desplegar.sh se ejecuta desde la PC/VM).

Opciones:
  --solo-verificar  no instala nada; solo comprueba "import unitree_sdk2py, sabueso_robot"
  --con-apt         instala antes cmake, build-essential, git, python3-venv y
                    python3-yaml con sudo apt (sin esta opción no se usa sudo)
  -h, --help        muestra esta ayuda

Advertencia: use una terminal limpia, sin ROS 2 cargado (sin source /opt/ros/...).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --solo-verificar) SOLO_VERIFICAR=1; shift ;;
    --con-apt) CON_APT=1; shift ;;
    -h|--help) uso; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; uso >&2; exit 2 ;;
  esac
done

comprobar_ros2() {
  if [[ -n "${ROS_DISTRO:-}" || -n "${AMENT_PREFIX_PATH:-}" ]]; then
    cat >&2 <<'EOF'
ERROR: esta terminal tiene ROS 2 cargado (ROS_DISTRO o AMENT_PREFIX_PATH definidos).
Cierre esa terminal y abra una limpia sin "source /opt/ros/...": el CycloneDDS de
ROS 2 entra en conflicto con unitree_sdk2py 0.10.2. Consulte docs/entorno.md.
EOF
    exit 1
  fi
}

comprobar_herramientas() {
  local orden
  local faltan=()
  for orden in git cmake make gcc python3; do
    command -v "$orden" >/dev/null 2>&1 || faltan+=("$orden")
  done
  if (( ${#faltan[@]} > 0 )); then
    echo "ERROR: faltan herramientas: ${faltan[*]}. Use --con-apt o instálelas." >&2
    exit 1
  fi
}

instalar_apt() {
  echo "Instalando paquetes del sistema con apt (requiere sudo)..."
  sudo apt-get update
  sudo apt-get install -y cmake build-essential git python3-venv python3-yaml
}

crear_venv() {
  if [[ -x "$PYTHON" ]]; then
    echo "Ya existe el entorno virtual ${VENV}; se reutiliza."
  else
    echo "Creando el entorno virtual ${VENV} (--system-site-packages)..."
    python3 -m venv --system-site-packages "$VENV"
  fi
}

compilar_cyclonedds() {
  if [[ -d "$CYCLONEDDS_HOME" ]]; then
    echo "CycloneDDS ya está en ${CYCLONEDDS_HOME}; se omite la compilación."
    return 0
  fi
  if [[ -e "$CYCLONEDDS" && ! -d "$CYCLONEDDS/.git" ]]; then
    echo "ERROR: ${CYCLONEDDS} existe y no es un repositorio git." >&2
    echo "       Muévalo o elimínelo y vuelva a ejecutar este script." >&2
    exit 1
  fi
  if [[ ! -d "$CYCLONEDDS/.git" ]]; then
    echo "Clonando CycloneDDS (rama releases/0.10.x)..."
    git clone https://github.com/eclipse-cyclonedds/cyclonedds \
      -b releases/0.10.x "$CYCLONEDDS"
  else
    local rama
    rama="$(git -C "$CYCLONEDDS" rev-parse --abbrev-ref HEAD)"
    if [[ "$rama" != "releases/0.10.x" ]]; then
      echo "Cambiando ${CYCLONEDDS} a la rama releases/0.10.x..."
      git -C "$CYCLONEDDS" checkout releases/0.10.x
    fi
  fi
  echo "Compilando CycloneDDS 0.10.2 en ${CYCLONEDDS}..."
  mkdir -p "${CYCLONEDDS}/build"
  (
    cd "${CYCLONEDDS}/build"
    cmake .. -DCMAKE_INSTALL_PREFIX=../install -DBUILD_EXAMPLES=OFF
    cmake --build . --target install
  )
}

instalar_sdk() {
  if [[ -d "$SDK/.git" ]]; then
    echo "Actualizando unitree_sdk2_python en ${SDK}..."
    if ! git -C "$SDK" pull --ff-only; then
      echo "ADVERTENCIA: no se pudo actualizar ${SDK}; se usa la copia existente." >&2
    fi
  else
    echo "Clonando unitree_sdk2_python en ${SDK}..."
    git clone https://github.com/unitreerobotics/unitree_sdk2_python.git "$SDK"
  fi
  echo "Instalando unitree_sdk2_python en el entorno virtual..."
  "$PIP" install -e "$SDK"
}

verificar() {
  echo "Verificando las importaciones con ${PYTHON}..."
  if "$PYTHON" -c 'import unitree_sdk2py, sabueso_robot'; then
    echo "PASA   unitree_sdk2py y sabueso_robot importables."
    return 0
  fi
  echo "FALLA  no se pudieron importar unitree_sdk2py y sabueso_robot." >&2
  return 1
}

comprobar_ros2

if (( SOLO_VERIFICAR )); then
  if [[ ! -x "$PYTHON" ]]; then
    echo "FALLA  no existe el entorno virtual ${VENV}; ejecute el script sin --solo-verificar." >&2
    exit 1
  fi
  verificar
  exit $?
fi

if (( CON_APT )); then
  instalar_apt
fi

comprobar_herramientas

if [[ ! -f "${REPO}/pyproject.toml" ]]; then
  echo "ERROR: no se encontró ${REPO}/pyproject.toml." >&2
  echo "       Copie primero el repositorio con scripts/robot/desplegar.sh desde la PC/VM." >&2
  exit 1
fi

crear_venv

echo "Actualizando pip, setuptools y wheel en el entorno virtual..."
"$PIP" install --upgrade "pip>=21.3" "setuptools>=61" wheel

compilar_cyclonedds
instalar_sdk

echo "Instalando PyYAML y pytest en el entorno virtual..."
"$PIP" install PyYAML pytest

echo "Instalando el paquete Sabueso desde ${REPO}..."
"$PIP" install -e "$REPO"

mkdir -p "${HOME}/sabueso_datos"
echo "Directorio de datos: ${HOME}/sabueso_datos"

verificar
echo "Instalación terminada. Active el entorno con: source ${VENV}/bin/activate"
