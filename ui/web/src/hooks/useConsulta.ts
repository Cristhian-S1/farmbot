import { useCallback, useEffect, useRef, useState } from 'react'

export interface Consulta<T> {
  datos: T | null
  error: string | null
  cargando: boolean
  recargar: () => void
}

/**
 * Consulta la API al montar, cuando cambian `claves` y, si se indica, cada `intervaloMs`.
 * Conserva los últimos datos si una consulta falla, para no vaciar la pantalla por un corte.
 */
export function useConsulta<T>(
  consultar: () => Promise<T>,
  claves: unknown[],
  intervaloMs?: number,
): Consulta<T> {
  const [datos, setDatos] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cargando, setCargando] = useState(true)
  const [vuelta, setVuelta] = useState(0)
  const consultarRef = useRef(consultar)
  consultarRef.current = consultar

  const clave = JSON.stringify(claves)
  useEffect(() => {
    setDatos(null)
    setCargando(true)
  }, [clave])

  useEffect(() => {
    let activo = true
    const cargar = () =>
      consultarRef
        .current()
        .then((d) => {
          if (!activo) return
          setDatos(d)
          setError(null)
        })
        .catch((e: Error) => activo && setError(e.message))
        .finally(() => activo && setCargando(false))

    cargar()
    const id = intervaloMs ? setInterval(cargar, intervaloMs) : undefined
    return () => {
      activo = false
      clearInterval(id)
    }
  }, [clave, intervaloMs, vuelta])

  const recargar = useCallback(() => setVuelta((n) => n + 1), [])
  return { datos, error, cargando, recargar }
}
