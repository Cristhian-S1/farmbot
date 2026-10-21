#!/usr/bin/env bash
# Comparte la conexión a internet de la PC (o VM Ubuntu) con la red del robot mediante NAT.
# Es idempotente: ejecutarlo varias veces no duplica reglas. --quitar deshace los cambios.
#
# Uso: sudo ./pc_compartir_internet.sh --lan enp0s8 --wan enp0s3 [--red 192.168.123.0/24] [--persistir]
#      sudo ./pc_compartir_internet.sh --lan enp0s8 --wan enp0s3 --quitar
#   --lan  interfaz conectada al robot (en VirtualBox, el adaptador puente)
#   --wan  interfaz con internet (en VirtualBox, el adaptador NAT)
set -euo pipefail

LAN=""
WAN=""
RED="192.168.123.0/24"
QUITAR=0
PERSISTIR=0
ETIQUETA="sabueso"
SYSCTL_ARCHIVO="/etc/sysctl.d/90-sabueso-forward.conf"

uso() {
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lan) LAN="$2"; shift 2 ;;
    --wan) WAN="$2"; shift 2 ;;
    --red) RED="$2"; shift 2 ;;
    --quitar) QUITAR=1; shift ;;
    --persistir) PERSISTIR=1; shift ;;
    -h|--help) uso 0 ;;
    *) echo "Opción desconocida: $1" >&2; uso 1 ;;
  esac
done

[[ -n "$LAN" && -n "$WAN" ]] || { echo "Faltan --lan y --wan." >&2; uso 1; }
[[ "$LAN" != "$WAN" ]] || { echo "--lan y --wan deben ser distintas." >&2; exit 1; }
[[ $EUID -eq 0 ]] || { echo "Ejecutar con sudo." >&2; exit 1; }
command -v iptables >/dev/null || { echo "Se requiere iptables." >&2; exit 1; }
for interfaz in "$LAN" "$WAN"; do
  ip link show "$interfaz" >/dev/null 2>&1 || { echo "No existe la interfaz $interfaz." >&2; exit 1; }
done

# Cada regla se describe una vez y se aplica con -C (comprobar), -A (agregar) o -D (borrar).
REGLAS=(
  "-t nat POSTROUTING -s $RED -o $WAN -j MASQUERADE"
  "-t filter FORWARD -i $LAN -o $WAN -s $RED -j ACCEPT"
  "-t filter FORWARD -i $WAN -o $LAN -d $RED -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT"
)

aplicar_regla() {
  local accion="$1" tabla cadena resto
  read -r _ tabla cadena resto <<<"$2"
  # shellcheck disable=SC2086  # $resto contiene varios argumentos de iptables a propósito
  if iptables -t "$tabla" -C "$cadena" $resto -m comment --comment "$ETIQUETA" 2>/dev/null; then
    if [[ "$accion" == "quitar" ]]; then
      # shellcheck disable=SC2086
      iptables -t "$tabla" -D "$cadena" $resto -m comment --comment "$ETIQUETA"
      echo "  - quitada: $tabla $cadena $resto"
    else
      echo "  = ya existe: $tabla $cadena $resto"
    fi
  elif [[ "$accion" == "poner" ]]; then
    # shellcheck disable=SC2086
    iptables -t "$tabla" -A "$cadena" $resto -m comment --comment "$ETIQUETA"
    echo "  + agregada: $tabla $cadena $resto"
  fi
}

if [[ $QUITAR -eq 1 ]]; then
  echo "Quitando NAT $RED → $WAN"
  for regla in "${REGLAS[@]}"; do aplicar_regla quitar "$regla"; done
  rm -f "$SYSCTL_ARCHIVO"
  echo "Reenvío IP: se deja en su valor actual ($(sysctl -n net.ipv4.ip_forward)); el archivo persistente fue eliminado."
  exit 0
fi

echo "Activando reenvío IP"
sysctl -q -w net.ipv4.ip_forward=1

echo "Aplicando NAT $RED → $WAN"
for regla in "${REGLAS[@]}"; do aplicar_regla poner "$regla"; done

if [[ $PERSISTIR -eq 1 ]]; then
  echo "net.ipv4.ip_forward=1" >"$SYSCTL_ARCHIVO"
  if command -v netfilter-persistent >/dev/null; then
    netfilter-persistent save
    echo "Reglas guardadas con netfilter-persistent."
  else
    echo "Aviso: instale 'iptables-persistent' para conservar las reglas tras reiniciar." >&2
  fi
fi

echo "Listo. En el dock, use como puerta de enlace la IP de $LAN:"
ip -4 -br addr show "$LAN"
