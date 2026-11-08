#!/usr/bin/env bash
# Se ejecuta EN EL DOCK del Go2. Pone la salida a internet a través de la PC/VM que
# comparte su conexión, sin tocar la IP del dock ni su cyclonedds.xml.
# Guarda el estado anterior (gateway de fábrica, DNS y rutas) para poder restaurarlo
# con --quitar, incluso después de reiniciar. Requiere NetworkManager.
#
# Uso: sudo ./dock_salida_internet.sh --gw 192.168.123.222 [--iface eth0]
#      [--dns "1.1.1.1 8.8.8.8"] [--metrica 700] [--ip-dock 192.168.123.18]
#      sudo ./dock_salida_internet.sh --quitar
#      sudo ./dock_salida_internet.sh --estado
set -euo pipefail

GW=""
IFACE="eth0"
DNS="1.1.1.1 8.8.8.8"
METRICA="700"
QUITAR=0
MOSTRAR_ESTADO=0
IP_DOCK="192.168.123.18"
RED="192.168.123.0/24"
ESTADO_DIR="${SABUESO_ESTADO_DIR:-/var/lib/sabueso/dock_salida_internet}"
ESTADO="$ESTADO_DIR/estado.env"
RUTAS="$ESTADO_DIR/rutas.txt"
DNS_ANT="$ESTADO_DIR/dns.txt"
ROLLBACK=0

msg() { printf '%s\n' "$*"; }
err() { printf '%s\n' "$*" >&2; }

uso() {
  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gw) GW="$2"; shift 2 ;;
    --iface) IFACE="$2"; shift 2 ;;
    --dns) DNS="$2"; shift 2 ;;
    --metrica) METRICA="$2"; shift 2 ;;
    --ip-dock) IP_DOCK="$2"; shift 2 ;;
    --quitar) QUITAR=1; shift ;;
    --estado) MOSTRAR_ESTADO=1; shift ;;
    -h|--help) uso 0 ;;
    *) err "Opción desconocida: $1"; uso 1 ;;
  esac
done

validar_ipv4() {
  local ip="$1" octeto
  [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || return 1
  IFS=. read -r -a octetos <<<"$ip"
  for octeto in "${octetos[@]}"; do
    ((octeto >= 0 && octeto <= 255)) || return 1
  done
}

leer_dns_guardado() {
  local dns
  dns="$(tr '\n' ' ' <"$DNS_ANT" 2>/dev/null || true)"
  dns="${dns#"${dns%%[![:space:]]*}"}"
  dns="${dns%"${dns##*[![:space:]]}"}"
  [[ "$dns" == "--" ]] && dns=""
  printf '%s' "$dns"
}

estado_cargar() {
  [[ -f "$ESTADO" ]] || return 1
  # shellcheck disable=SC1090
  source "$ESTADO" || return 1
  if [[ "${GUARDADO_CONEXION:-}" != "$CONEXION" ]]; then
    err "El estado guardado pertenece a '${GUARDADO_CONEXION:-desconocida}', no a '$CONEXION'."
    return 1
  fi
  return 0
}

guardar_estado() {
  local gw_ant nd_ant iar_ant iad_ant
  install -d -m 0755 "$ESTADO_DIR"
  gw_ant="$(nmcli -g ipv4.gateway connection show "$CONEXION" 2>/dev/null || true)"
  nd_ant="$(nmcli -g ipv4.never-default connection show "$CONEXION" 2>/dev/null || true)"
  iar_ant="$(nmcli -g ipv4.ignore-auto-routes connection show "$CONEXION" 2>/dev/null || true)"
  iad_ant="$(nmcli -g ipv4.ignore-auto-dns connection show "$CONEXION" 2>/dev/null || true)"
  [[ "$gw_ant" == "--" ]] && gw_ant=""
  [[ "$nd_ant" == "--" || -z "$nd_ant" ]] && nd_ant="no"
  [[ "$iar_ant" == "--" || -z "$iar_ant" ]] && iar_ant="no"
  [[ "$iad_ant" == "--" || -z "$iad_ant" ]] && iad_ant="no"

  nmcli -g ipv4.routes connection show "$CONEXION" >"$RUTAS" 2>/dev/null || : >"$RUTAS"
  nmcli -g ipv4.dns connection show "$CONEXION" >"$DNS_ANT" 2>/dev/null || : >"$DNS_ANT"

  {
    printf 'GUARDADO_CONEXION=%q\n' "$CONEXION"
    printf 'GUARDADO_GATEWAY=%q\n' "$gw_ant"
    printf 'GUARDADO_NEVER_DEFAULT=%q\n' "$nd_ant"
    printf 'GUARDADO_IGNORE_AUTO_ROUTES=%q\n' "$iar_ant"
    printf 'GUARDADO_IGNORE_AUTO_DNS=%q\n' "$iad_ant"
    printf 'GUARDADO_GW_APLICADO=%q\n' "$GW"
    printf 'GUARDADO_METRICA_APLICADA=%q\n' "$METRICA"
    printf 'GUARDADO_DNS_APLICADO=%q\n' "$DNS"
  } >"$ESTADO"
  chmod 600 "$ESTADO" "$RUTAS" "$DNS_ANT"
  msg "Estado anterior guardado en $ESTADO_DIR."
}

restaurar_rutas() {
  local ruta
  nmcli connection modify "$CONEXION" ipv4.routes "" || return 1
  while IFS= read -r ruta; do
    [[ -z "$ruta" || "$ruta" == "--" ]] && continue
    nmcli connection modify "$CONEXION" +ipv4.routes "$ruta" || return 1
  done <"$RUTAS"
}

restaurar_estado() {
  estado_cargar || return 1
  msg "Restaurando la conexión '$CONEXION'..."
  nmcli connection modify "$CONEXION" \
    ipv4.gateway "$GUARDADO_GATEWAY" \
    ipv4.never-default "$GUARDADO_NEVER_DEFAULT" \
    ipv4.ignore-auto-routes "$GUARDADO_IGNORE_AUTO_ROUTES" \
    ipv4.ignore-auto-dns "$GUARDADO_IGNORE_AUTO_DNS" \
    ipv4.dns "$(leer_dns_guardado)" || return 1
  restaurar_rutas || return 1
  nmcli device reapply "$IFACE" || nmcli connection up "$CONEXION" || return 1
  rm -rf "$ESTADO_DIR"
  msg "Estado anterior restaurado."
  ip route show default || true
}

al_salir() {
  local codigo=$?
  if [[ $ROLLBACK -eq 1 ]]; then
    err "Error inesperado; se restaura el estado anterior..."
    restaurar_estado || err "No se pudo restaurar; revise $ESTADO_DIR."
  fi
  exit "$codigo"
}
trap al_salir EXIT

via_actual() {
  ip -4 route get 1.1.1.1 2>/dev/null |
    awk '{for (i = 1; i <= NF; i++) if ($i == "via") { print $(i + 1); exit }}'
}

contar_defaults() {
  ip route show default 2>/dev/null | grep -c '^default' || true
}

esperar_ruta() {
  local i
  for ((i = 0; i < 10; i++)); do
    [[ "$(via_actual)" == "$GW" ]] && return 0
    sleep 1
  done
  return 1
}

esperar_dns() {
  local i
  for ((i = 0; i < 10; i++)); do
    getent hosts github.com >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}

# Validaciones comunes.
[[ $EUID -eq 0 ]] || { err "Ejecutar con sudo."; exit 1; }
command -v nmcli >/dev/null || { err "Se requiere NetworkManager (nmcli)."; exit 1; }
command -v ip >/dev/null || { err "Se requiere iproute2."; exit 1; }
ip link show "$IFACE" >/dev/null 2>&1 || { err "No existe la interfaz $IFACE. Use --iface."; exit 1; }
ip -4 -br addr show "$IFACE" | grep -q "${IP_DOCK}/" || {
  err "La interfaz $IFACE no tiene $IP_DOCK. Revise 'ip -br addr' y use --iface/--ip-dock."
  exit 1
}

CONEXION="$(nmcli -g GENERAL.CONNECTION device show "$IFACE" 2>/dev/null || true)"
[[ -n "$CONEXION" && "$CONEXION" != "--" ]] || {
  err "La interfaz $IFACE no está gestionada por NetworkManager."
  exit 1
}

if [[ $MOSTRAR_ESTADO -eq 1 ]]; then
  estado_cargar || { err "No hay estado guardado."; exit 2; }
  msg "Conexión: $CONEXION"
  msg "Gateway de fábrica: ${GUARDADO_GATEWAY:-ninguna}"
  msg "Ruta aplicada: ${GUARDADO_GW_APLICADO:-?} (métrica ${GUARDADO_METRICA_APLICADA:-?})"
  msg "DNS aplicado: ${GUARDADO_DNS_APLICADO:-?}"
  exit 0
fi

if [[ $QUITAR -eq 1 ]]; then
  if ! estado_cargar; then
    if [[ -n "$GW" ]]; then
      err "No hay estado guardado; se quita solo la ruta indicada, sin restaurar la gateway de fábrica."
      nmcli connection modify "$CONEXION" -ipv4.routes "0.0.0.0/0 $GW $METRICA" 2>/dev/null || true
      nmcli device reapply "$IFACE" 2>/dev/null || true
      exit 2
    fi
    err "No hay estado guardado. Use --gw y --metrica para quitar una ruta aplicada a mano."
    exit 2
  fi
  restaurar_estado
  exit 0
fi

[[ -n "$GW" ]] || { err "Falta --gw <IP de la PC o VM en $RED>."; uso 1; }
validar_ipv4 "$GW" || { err "La IP '$GW' no es IPv4 válida."; exit 1; }
[[ "$GW" == 192.168.123.* ]] || { err "La IP debe estar en $RED."; exit 1; }
case "$GW" in
  192.168.123.1 | 192.168.123.18 | 192.168.123.161 | 192.168.123.20)
    err "La IP $GW está reservada (gateway de fábrica, dock o robot). Elija la IP de la VM."
    exit 1
    ;;
esac
if [[ ! "$METRICA" =~ ^[0-9]+$ ]]; then
  err "La métrica debe ser un entero entre 1 y 4294967295."
  exit 1
fi
if ((METRICA < 1 || METRICA > 4294967295)); then
  err "La métrica debe ser un entero entre 1 y 4294967295."
  exit 1
fi
[[ "$DNS" =~ ^[0-9a-zA-Z.:\ -]+$ ]] || { err "El DNS contiene caracteres no válidos."; exit 1; }

if ! ping -c 2 -W 1 "$GW" >/dev/null 2>&1; then
  err "No hay respuesta de $GW. ¿Está la PC/VM conectada y con la IP fija?"
  exit 1
fi

if ! estado_cargar; then
  guardar_estado
else
  msg "Ya hay un estado guardado para '$CONEXION'; se reutiliza."
fi
ROLLBACK=1

msg "Configurando '$CONEXION' (la sesión SSH puede pausarse al reaplicar)..."
# La gateway de fábrica se ignora con never-default y las rutas DHCP con
# ignore-auto-routes; la ruta explícita /0 es la que instala NetworkManager.
nmcli connection modify "$CONEXION" ipv4.routes "" || {
  err "No se pudieron limpiar las rutas del perfil."
  exit 1
}
nmcli connection modify "$CONEXION" \
  ipv4.gateway "" \
  ipv4.never-default yes \
  ipv4.ignore-auto-routes yes \
  ipv4.dns "$DNS" \
  ipv4.ignore-auto-dns yes || {
  err "No se pudo modificar el perfil."
  exit 1
}
nmcli connection modify "$CONEXION" +ipv4.routes "0.0.0.0/0 $GW $METRICA" || {
  err "No se pudo agregar la ruta por defecto."
  exit 1
}
nmcli device reapply "$IFACE" || nmcli connection up "$CONEXION" || {
  err "No se pudo reactivar la conexión."
  exit 1
}
resolvectl flush-caches 2>/dev/null || true

if ! esperar_ruta; then
  err "FALLA: la ruta a internet no pasa por $GW."
  ip route show default >&2 || true
  ROLLBACK=0
  restaurar_estado || err "Tampoco se pudo restaurar; revise $ESTADO_DIR."
  exit 1
fi
if [[ "$(contar_defaults)" -ne 1 ]]; then
  err "FALLA: hay $(contar_defaults) rutas por defecto; debe haber exactamente una vía $GW."
  ip route show default >&2 || true
  ROLLBACK=0
  restaurar_estado || err "Tampoco se pudo restaurar; revise $ESTADO_DIR."
  exit 1
fi
if ! esperar_dns; then
  err "FALLA: el DNS no resuelve github.com. Revise el NAT de la PC/VM."
  ROLLBACK=0
  restaurar_estado || err "Tampoco se pudo restaurar; revise $ESTADO_DIR."
  exit 1
fi

ROLLBACK=0
msg "Listo. Ruta a internet:"
ip route show default
msg "DNS: PASA (github.com resuelve)."
