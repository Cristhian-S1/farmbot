#!/usr/bin/env bash
# Inventario de SOLO LECTURA del dock del Go2 (tarea F0.1). No modifica nada.
# Imprime Markdown para pegar en docs/inventario_robot.md.
#
# Uso (desde la PC/VM):
#   ssh unitree@192.168.123.18 'bash -s' < scripts/robot/inventario_robot.sh > docs/inventario_robot.md
set -uo pipefail

seccion() {
  local titulo="$1"; shift
  printf '\n## %s\n\n```text\n' "$titulo"
  "$@" 2>&1 || echo "(comando no disponible)"
  printf '```\n'
}

printf '# Inventario del dock del Go2\n\nGenerado: %s\n' "$(date -Is)"

seccion "Equipo" bash -c 'hostname; cat /proc/device-tree/model 2>/dev/null; echo; uname -a'
seccion "Sistema operativo" bash -c 'lsb_release -a 2>/dev/null || cat /etc/os-release'
seccion "JetPack / L4T" cat /etc/nv_tegra_release
seccion "Interfaces" ip -br addr
seccion "Enlaces" ip -br link
seccion "Rutas" ip route
seccion "NetworkManager" nmcli device status
seccion "Conexiones NetworkManager" nmcli -f NAME,TYPE,DEVICE,AUTOCONNECT connection show
seccion "DNS" bash -c 'resolvectl status 2>/dev/null | head -40 || cat /etc/resolv.conf'
seccion "Distribuciones ROS 2" ls /opt/ros
seccion "cyclonedds.xml del dock" cat /home/unitree/cyclonedds_ws/cyclonedds.xml
seccion "Dispositivos USB" lsusb
seccion "Cámaras de video" bash -c 'ls -l /dev/video* 2>/dev/null || echo "sin /dev/video*"'
seccion "Python y CycloneDDS" bash -c 'python3 --version; python3 -m pip show cyclonedds unitree_sdk2py 2>/dev/null | grep -E "^(Name|Version|Location)"'
seccion "Disco" df -h /
seccion "Memoria" free -h
seccion "Hora" timedatectl
# shellcheck disable=SC2016  # el script interno se expande en el dock, no aquí
seccion "Conectividad con el robot" bash -c 'for ip in 192.168.123.161 192.168.123.20; do ping -c 2 -W 1 "$ip" >/dev/null && echo "$ip responde" || echo "$ip no responde"; done'
seccion "Servicios activos" bash -c 'systemctl list-units --type=service --state=running --no-pager | head -60'
