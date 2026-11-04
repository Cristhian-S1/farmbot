// Fechas en el formato del cliente (es-CL). La API entrega ISO local, sin zona horaria.

const fecha = new Intl.DateTimeFormat('es-CL', { day: '2-digit', month: 'short', year: 'numeric' })
const fechaHora = new Intl.DateTimeFormat('es-CL', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})
const hora = new Intl.DateTimeFormat('es-CL', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

export const formatoFecha = (iso: string) => fecha.format(new Date(iso))
export const formatoFechaHora = (iso: string) => fechaHora.format(new Date(iso))
export const formatoHora = (iso: string) => hora.format(new Date(iso))

export function nombreZona(hilera: number | null, zona: number | null): string {
  if (hilera == null || zona == null) return 'Sin zona'
  return `Hilera ${hilera} · Zona ${zona}`
}

export function plural(n: number, singular: string, varios = `${singular}s`): string {
  return `${n} ${n === 1 ? singular : varios}`
}

export function porcentaje(valor: number): string {
  return `${Math.round(valor * 100)} %`
}

export function sinZona(n: number): string {
  return `${plural(n, 'captura')} sin zona ${n === 1 ? 'queda' : 'quedan'} para revisión`
}
