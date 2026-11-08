#!/usr/bin/env bash
# Se ejecuta EN EL DOCK del Go2. Agrega una ruta por defecto hacia la PC/VM que comparte internet
# y fija DNS explícitos. No cambia la IP 192.168.123.18 ni el cyclonedds.xml.
# Si el dock trae una puerta de enlace de fábrica (p. ej. 192.168.123.1), la retira para que no
# compita con la ruta hacia la PC/VM y la guarda para restaurarla con --quitar.
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
DIR_ESTADO="/var/lib/sabueso"
ARCHIVO_GW="$DIR_ESTADO/dock_salida_internet.gateway"

uso() {
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
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
[[ "$METRICA" =~ ^[0-9]+$ ]] || { echo "La métrica debe ser un número entero." >&2; exit 1; }

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
    if [[ -f "$ARCHIVO_GW" ]]; then
      GW_ANTERIOR="$(cat "$ARCHIVO_GW")"
      nmcli connection modify "$CONEXION" ipv4.gateway "$GW_ANTERIOR"
      rm -f "$ARCHIVO_GW"
      echo "Puerta de enlace restaurada: ${GW_ANTERIOR:-ninguna}."
    else
      echo "Aviso: no hay puerta de enlace guardada; se deja la actual." >&2
    fi
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

  if [[ ! -f "$ARCHIVO_GW" ]]; then
    GW_ANTERIOR="$(nmcli -g ipv4.gateway connection show "$CONEXION" 2>/dev/null || true)"
    if [[ "$GW_ANTERIOR" == "--" ]]; then
      GW_ANTERIOR=""
    fi
    install -d -m 0755 "$DIR_ESTADO"
    printf '%s\n' "$GW_ANTERIOR" >"$ARCHIVO_GW"
    chmod 600 "$ARCHIVO_GW"
    echo "Puerta de enlace de fábrica guardada: ${GW_ANTERIOR:-ninguna}."
  fi

  # La puerta de enlace de fábrica crea una ruta por defecto con mejor métrica que la de la VM.
  # Se retira; --quitar la restaura desde $ARCHIVO_GW.
  nmcli connection modify "$CONEXION" ipv4.gateway ""

  if ! nmcli -g ipv4.routes connection show "$CONEXION" | grep -q "0.0.0.0/0 $GW"; then
    nmcli connection modify "$CONEXION" +ipv4.routes "0.0.0.0/0 $GW $METRICA"
  fi
  nmcli connection modify "$CONEXION" ipv4.dns "$DNS" ipv4.ignore-auto-dns yes
  nmcli device reapply "$IFACE"
else
  echo "Aviso: $IFACE no está gestionada por NetworkManager; se aplica de forma temporal." >&2
  echo "Aviso: si hay otra ruta por defecto con métrica menor, use --metrica con un valor menor." >&2
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
if ! ip route get 1.1.1.1 2>/dev/null | grep -q "via $GW"; then
  echo "FALLA: la ruta a internet no pasa por $GW." >&2
  echo "Revise 'ip route show default'. Si el dock conserva otra ruta por defecto," >&2
  echo "ejecute: sudo nmcli connection up \"$CONEXION\"" >&2
  exit 1
fi
if getent hosts github.com >/dev/null; then
  echo "DNS: PASA (github.com resuelve)."
else
  echo "DNS: FALLA. Revise el NAT en la PC/VM." >&2
  exit 1
fi
