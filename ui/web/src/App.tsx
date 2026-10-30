import { useEffect, useState } from 'react'
import { obtenerRegistros, urlFoto } from './api'
import type { Registro } from './tipos'

const INTERVALO_MS = 5000

export default function App() {
  const [registros, setRegistros] = useState<Registro[]>([])
  const [error, setError] = useState<string | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    let activo = true
    const cargar = () =>
      obtenerRegistros()
        .then((datos) => {
          if (activo) {
            setRegistros(datos)
            setError(null)
          }
        })
        .catch((e: Error) => activo && setError(e.message))
        .finally(() => activo && setCargando(false))

    cargar()
    const id = setInterval(cargar, INTERVALO_MS)
    return () => {
      activo = false
      clearInterval(id)
    }
  }, [])

  return (
    <main>
      <h1>Sabueso - registros del recorrido</h1>
      {error && <p className="error">No se pudo consultar la API: {error}</p>}
      {cargando ? (
        <p>Cargando…</p>
      ) : registros.length === 0 ? (
        <p>Sin registros todavía.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Recorrido</th>
              <th>Hallazgo</th>
              <th>Confianza</th>
              <th>Hilera</th>
              <th>Zona</th>
              <th>Foto</th>
            </tr>
          </thead>
          <tbody>
            {registros.map((r) => (
              <tr key={r.id}>
                <td>{r.fecha}</td>
                <td>{r.recorrido}</td>
                <td>{r.clase}</td>
                <td>{Math.round(r.confianza * 100)} %</td>
                <td>{r.hilera ?? 'sin hilera'}</td>
                <td>{r.zona ?? 'sin zona'}</td>
                <td>
                  {r.foto ? (
                    <a href={urlFoto(r.foto)} target="_blank" rel="noreferrer">
                      <img src={urlFoto(r.foto)} alt={`Foto del hallazgo ${r.clase}`} />
                    </a>
                  ) : (
                    'sin foto'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  )
}
