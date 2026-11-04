import type {
  Captura,
  EstadoControl,
  Estructura,
  Ficha,
  Mapa,
  Recorrido,
  RenglonHistorial,
} from './tipos'

async function pedir<T>(url: string, opciones?: RequestInit): Promise<T> {
  const respuesta = await fetch(url, opciones)
  const datos = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    throw new Error(datos?.error ?? `La API respondió ${respuesta.status}`)
  }
  return datos as T
}

function enviar<T>(url: string, cuerpo: object = {}): Promise<T> {
  return pedir<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  })
}

function conRecorrido(url: string, recorrido: string | null): string {
  return recorrido ? `${url}${url.includes('?') ? '&' : '?'}recorrido=${encodeURIComponent(recorrido)}` : url
}

export const api = {
  estructura: () => pedir<Estructura>('/api/estructura'),
  recorridos: () => pedir<Recorrido[]>('/api/recorridos'),
  mapa: (recorrido: string | null) => pedir<Mapa>(conRecorrido('/api/mapa', recorrido)),
  ficha: (zona: number, recorrido: string | null) => pedir<Ficha>(conRecorrido(`/api/zonas/${zona}`, recorrido)),
  historial: (zona: number) => pedir<RenglonHistorial[]>(`/api/zonas/${zona}/historial`),
  capturas: (recorrido: string | null, { hallazgos = false, limite = 50 } = {}) =>
    pedir<Captura[]>(conRecorrido(`/api/capturas?limite=${limite}${hallazgos ? '&hallazgos=1' : ''}`, recorrido)),
  control: () => pedir<EstadoControl>('/api/recorridos/actual'),
  iniciar: (hilera: number | null, zona: number | null) =>
    enviar<{ recorrido: string }>('/api/recorridos', { hilera, zona }),
  detener: () => enviar<{ recorrido: string | null }>('/api/recorridos/actual/detener'),
}

export function urlFoto(nombre: string): string {
  return `/fotos/${encodeURIComponent(nombre)}`
}
