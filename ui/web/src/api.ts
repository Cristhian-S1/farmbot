import type { Registro } from './tipos'

export async function obtenerRegistros(): Promise<Registro[]> {
  const respuesta = await fetch('/api/registros')
  if (!respuesta.ok) {
    throw new Error(`La API respondió ${respuesta.status}`)
  }
  return respuesta.json()
}

export function urlFoto(nombre: string): string {
  return `/fotos/${encodeURIComponent(nombre)}`
}
