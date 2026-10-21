#!/usr/bin/env bash
# Fija la IP estática de la interfaz conectada al robot (PC nativa o VM de VirtualBox).
# La interfaz del robot nunca se usa como ruta por defecto (ipv4.never-default).
#
# Uso: sudo ./pc_configurar_interfaz_robot.sh --lan enp0s8 [--ip 192.168.123.222/24] [--perfil go2-lan]
set -euo pipefail

LAN=""
IP_CIDR="192.168.123.222/24"
PERFIL="go2-lan"

uso() {
  sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lan) LAN="$2"; shift 2 ;;
    --ip) IP_CIDR="$2"; shift 2 ;;
    --perfil) PERFIL="$2"; shift 2 ;;
    -h|--help) uso 0 ;;
    *) echo "Opción desconocida: $1" >&2; uso 1 ;;
  esac
done

[[ -n "$LAN" ]] || { echo "Falta --lan <interfaz>" >&2; uso 1; }
[[ $EUID -eq 0 ]] || { echo "Ejecutar con sudo." >&2; exit 1; }
command -v nmcli >/dev/null || { echo "Se requiere NetworkManager (nmcli)." >&2; exit 1; }
ip link show "$LAN" >/dev/null 2>&1 || { echo "No existe la interfaz $LAN. Revise 'ip -br link'." >&2; exit 1; }

case "${IP_CIDR%/*}" in
  192.168.123.18|192.168.123.161|192.168.123.20)
    echo "La IP ${IP_CIDR%/*} pertenece al robot. Elija otra (p. ej. 192.168.123.222)." >&2
    exit 1 ;;
  192.168.123.*) ;;
  *) echo "La IP debe estar en 192.168.123.0/24." >&2; exit 1 ;;
esac

if nmcli -t -f NAME connection show | grep -Fxq "$PERFIL"; then
  nmcli connection modify "$PERFIL" connection.interface-name "$LAN"
else
  nmcli connection add type ethernet con-name "$PERFIL" ifname "$LAN"
fi

nmcli connection modify "$PERFIL" \
  ipv4.method manual \
  ipv4.addresses "$IP_CIDR" \
  ipv4.gateway "" \
  ipv4.never-default yes \
  ipv6.method disabled \
  connection.autoconnect yes

nmcli connection up "$PERFIL"

echo "Perfil '$PERFIL' activo en $LAN con $IP_CIDR (sin ruta por defecto)."
ip -br addr show "$LAN"
