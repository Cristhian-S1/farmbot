import { useEffect, useState } from 'react'

export type Seccion = 'inicio' | 'zonas' | 'recorrido' | 'historial'

export interface Ruta {
  seccion: Seccion
  /** Id numérico que sigue a la sección, por ejemplo la zona en #/zonas/7. */
  id: number | null
}

const SECCIONES: Seccion[] = ['inicio', 'zonas', 'recorrido', 'historial']

function leer(): Ruta {
  const [, seccion, id] = window.location.hash.split('/')
  return {
    seccion: SECCIONES.includes(seccion as Seccion) ? (seccion as Seccion) : 'inicio',
    id: id && /^\d+$/.test(id) ? Number(id) : null,
  }
}

export function enlace(seccion: Seccion, id?: number | null): string {
  return id == null ? `#/${seccion}` : `#/${seccion}/${id}`
}

/** Ruta según el hash de la URL (#/zonas/7), para no depender de un servidor que reescriba rutas. */
export function useRuta(): Ruta {
  const [ruta, setRuta] = useState(leer)
  useEffect(() => {
    const cambiar = () => setRuta(leer())
    window.addEventListener('hashchange', cambiar)
    return () => window.removeEventListener('hashchange', cambiar)
  }, [])
  return ruta
}
