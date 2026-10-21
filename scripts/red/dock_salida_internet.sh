#!/usr/bin/env bash
# Se ejecuta EN EL DOCK del Go2. Agrega una ruta por defecto hacia la PC/VM que comparte internet
# y fija DNS explícitos. No cambia la IP 192.168.123.18 ni el cyclonedds.xml.
#
# Uso: sudo ./dock_salida_internet.sh --gw 192.168.123.222 [--iface eth0] [--dns "1.1.1.1 8.8.8.8"] [--metrica 700]
#      sudo ./dock_salida_internet.sh --gw 192.168.123.222 --quitar
# Copiar al dock: scp scripts/red/dock_salida_internet.sh unitree@192.168.123.18:~/
set -euo pipefail

GW=""
IFACE="eth0"
DNS="1.1.1.1 8.8.8.8"
METRICA="700"
QUITAR=0
IP_DOCK="192.168.123.18"

uso() {
  sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gw) GW="$2"; shift 2 ;;
    --iface) IFACE="$2"; shift 2 ;;
    --dns) DNS="$2"; shift 2 ;;
    --metrica) METRICA="$2"; shift 2 ;;
    --quitar) QUITAR=1; shift ;;
    -h|--help) uso 0 ;;
    *) echo "Opción desconocida: $1" >&2; uso 1 ;;
  esac
done

[[ -n "$GW" ]] || { echo "Falta --gw <IP de la PC o VM en 192.168.123.0/24>." >&2; uso 1; }
[[ $EUID -eq 0 ]] || { echo "Ejecutar con sudo." >&2; exit 1; }

if ! ip -4 addr show "$IFACE" 2>/dev/null | grep -q "inet $IP_DOCK/"; then
  echo "La interfaz $IFACE no tiene $IP_DOCK. Revise 'ip -br addr' y use --iface." >&2
  exit 1
fi

CONEXION=""
if command -v nmcli >/dev/null; then
  CONEXION="$(nmcli -g GENERAL.CONNECTION device show "$IFACE" 2>/dev/null || true)"
fi

if [[ $QUITAR -eq 1 ]]; then
  if [[ -n "$CONEXION" ]]; then
    nmcli connection modify "$CONEXION" -ipv4.routes "0.0.0.0/0 $GW $METRICA" || true
    nmcli connection modify "$CONEXION" ipv4.dns "" ipv4.ignore-auto-dns no
    nmcli device reapply "$IFACE"
  fi
  ip route del default via "$GW" dev "$IFACE" 2>/dev/null || true
  echo "Ruta por defecto vía $GW quitada."
  exit 0
fi

if ! ping -c 2 -W 1 "$GW" >/dev/null 2>&1; then
  echo "No hay respuesta de $GW. ¿Está la PC/VM conectada y con la IP fija?" >&2
  exit 1
fi

if [[ -n "$CONEXION" ]]; then
  echo "Configurando la conexión NetworkManager '$CONEXION' (persistente)."
  echo "Aviso: la sesión SSH puede pausarse unos segundos al reaplicar."
  if ! nmcli -g ipv4.routes connection show "$CONEXION" | grep -q "0.0.0.0/0 $GW"; then
    nmcli connection modify "$CONEXION" +ipv4.routes "0.0.0.0/0 $GW $METRICA"
  fi
  nmcli connection modify "$CONEXION" ipv4.dns "$DNS" ipv4.ignore-auto-dns yes
  nmcli device reapply "$IFACE"
else
  echo "Aviso: $IFACE no está gestionada por NetworkManager; se aplica de forma temporal." >&2
  ip route replace default via "$GW" dev "$IFACE" metric "$METRICA"
  if command -v resolvectl >/dev/null; then
    # shellcheck disable=SC2086  # $DNS es una lista separada por espacios
    resolvectl dns "$IFACE" $DNS
  else
    echo "Configure DNS manualmente en /etc/resolv.conf." >&2
  fi
fi

echo "Ruta hacia internet:"
ip route get 1.1.1.1
if getent hosts github.com >/dev/null; then
  echo "DNS: PASA (github.com resuelve)."
else
  echo "DNS: FALLA. Revise el NAT en la PC/VM." >&2
  exit 1
fi
