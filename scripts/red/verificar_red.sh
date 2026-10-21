#!/usr/bin/env bash
# Verifica la red entre la PC (o VM) y el Go2. Imprime PASA/FALLA por prueba y termina con
# el número de fallas como código de salida.
#
# Uso: ./verificar_red.sh --lan enp0s8 [--dock 192.168.123.18] [--control 192.168.123.161] [--ssh unitree@192.168.123.18]
#   --ssh  además comprueba, dentro del dock, la ruta por defecto y el DNS (requiere llave SSH)
# shellcheck disable=SC2329  # las funciones de prueba se invocan de forma indirecta mediante prueba()
set -uo pipefail

LAN=""
DOCK="192.168.123.18"
CONTROL="192.168.123.161"
SSH_DESTINO=""
FALLAS=0

uso() {
  sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lan) LAN="$2"; shift 2 ;;
    --dock) DOCK="$2"; shift 2 ;;
    --control) CONTROL="$2"; shift 2 ;;
    --ssh) SSH_DESTINO="$2"; shift 2 ;;
    -h|--help) uso 0 ;;
    *) echo "Opción desconocida: $1" >&2; uso 1 ;;
  esac
done

[[ -n "$LAN" ]] || { echo "Falta --lan <interfaz>." >&2; uso 1; }

prueba() {
  local nombre="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf 'PASA   %s\n' "$nombre"
  else
    printf 'FALLA  %s\n' "$nombre"
    FALLAS=$((FALLAS + 1))
  fi
}

ruta_por_lan() { ip route get "$1" | grep -q "dev $LAN"; }
ruta_por_defecto_fuera_de_lan() { ! ip route show default | grep -q "dev $LAN"; }
masquerade_presente() { sudo -n iptables -t nat -S POSTROUTING | grep -q MASQUERADE; }

prueba "$LAN tiene IP en 192.168.123.0/24" bash -c "ip -4 -br addr show '$LAN' | grep -q '192\.168\.123\.'"
prueba "La ruta hacia $DOCK usa $LAN" ruta_por_lan "$DOCK"
prueba "La ruta por defecto no usa $LAN" ruta_por_defecto_fuera_de_lan
prueba "ping $DOCK (dock)" ping -c 3 -W 1 "$DOCK"
prueba "ping $CONTROL (control de movimiento)" ping -c 3 -W 1 "$CONTROL"
prueba "DNS de la PC (github.com)" getent hosts github.com
prueba "HTTPS desde la PC" curl -fsS -o /dev/null -m 10 https://github.com
prueba "Reenvío IP activo" bash -c "[[ \$(sysctl -n net.ipv4.ip_forward) == 1 ]]"
if sudo -n true 2>/dev/null; then
  prueba "Regla MASQUERADE presente" masquerade_presente
else
  echo "OMITE  Regla MASQUERADE (ejecute con sudo para comprobarla)"
fi

if [[ -n "$SSH_DESTINO" ]]; then
  SSH_OPC=(-o BatchMode=yes -o ConnectTimeout=5)
  prueba "SSH con llave a $SSH_DESTINO" ssh "${SSH_OPC[@]}" "$SSH_DESTINO" true
  prueba "Dock: ruta por defecto" ssh "${SSH_OPC[@]}" "$SSH_DESTINO" "ip route show default | grep -q default"
  prueba "Dock: DNS (github.com)" ssh "${SSH_OPC[@]}" "$SSH_DESTINO" "getent hosts github.com"
  # En VirtualBox el ICMP hacia internet puede fallar por el NAT; se prueba con HTTPS.
  prueba "Dock: HTTPS a internet" ssh "${SSH_OPC[@]}" "$SSH_DESTINO" "curl -fsS -o /dev/null -m 10 https://github.com"
fi

echo "Fallas: $FALLAS"
exit "$FALLAS"
