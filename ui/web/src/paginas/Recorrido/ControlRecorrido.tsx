import { useState } from 'react'
import { api } from '../../api/cliente'
import type { Estructura } from '../../api/tipos'
import { Aviso } from '../../componentes/Aviso'
import Icono from '../../componentes/Icono'
import Insignia from '../../componentes/Insignia'
import Tarjeta from '../../componentes/Tarjeta'
import type { Consulta } from '../../hooks/useConsulta'
import type { EstadoControl } from '../../api/tipos'

interface Props {
  estructura: Estructura | null
  control: Consulta<EstadoControl>
  onCambio: () => void
}

/** Inicia y detiene el recorrido. Solo enciende cámara, detección y registro: no mueve el robot. */
export default function ControlRecorrido({ estructura, control, onCambio }: Props) {
  const [hilera, setHilera] = useState('')
  const [zona, setZona] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hileras = estructura?.sector.hileras ?? []
  const zonas = hileras.find((h) => String(h.numero) === hilera)?.zonas ?? []
  const corriendo = control.datos?.corriendo ?? false

  const accion = (pedir: () => Promise<unknown>) => {
    setEnviando(true)
    setError(null)
    pedir()
      .then(() => {
        control.recargar()
        onCambio()
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setEnviando(false))
  }

  return (
    <Tarjeta
      titulo="Recorrido"
      extra={control.datos && <Insignia nivel={corriendo ? 'neutral' : 'vacio'} texto={corriendo ? 'En curso' : 'Detenido'} />}
    >
      {corriendo ? (
        <>
          <dl>
            <div className="sb-dl-row"><dt>Id</dt><dd>{control.datos?.recorrido}</dd></div>
          </dl>
          <button
            type="button"
            className="sb-btn sb-btn--danger sb-btn--block"
            style={{ marginTop: 'var(--space-4)' }}
            disabled={enviando}
            onClick={() => accion(api.detener)}
          >
            <Icono nombre="detener" />
            Detener recorrido
          </button>
        </>
      ) : (
        <>
          <div className="sb-fields">
            <label className="sb-field">
              <span className="sb-label">Hilera</span>
              <span className="sb-input">
                <select id="hilera" value={hilera} onChange={(e) => { setHilera(e.target.value); setZona('') }}>
                  <option value="">Sin indicar</option>
                  {hileras.map((h) => <option key={h.numero} value={h.numero}>Hilera {h.numero}</option>)}
                </select>
              </span>
            </label>
            <label className="sb-field">
              <span className="sb-label">Zona</span>
              <span className="sb-input">
                <select id="zona" value={zona} disabled={!hilera} onChange={(e) => setZona(e.target.value)}>
                  <option value="">Sin indicar</option>
                  {zonas.map((z) => <option key={z.id} value={z.numero}>Zona {z.numero}</option>)}
                </select>
              </span>
            </label>
          </div>
          <p className="sb-caption" style={{ marginTop: 'var(--space-2)' }}>
            Sin hilera y zona, las capturas quedan "sin zona" para revisión.
          </p>
          <button
            type="button"
            className="sb-btn sb-btn--block"
            style={{ marginTop: 'var(--space-4)' }}
            disabled={enviando || !control.datos}
            onClick={() => accion(() => api.iniciar(hilera ? Number(hilera) : null, zona ? Number(zona) : null))}
          >
            <Icono nombre="iniciar" />
            Iniciar recorrido
          </button>
        </>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', marginTop: 'var(--space-4)' }}>
        {error && <Aviso>{error}</Aviso>}
        {control.error && <Aviso>No se pudo consultar el estado del recorrido: {control.error}</Aviso>}
        <Aviso tipo="info">
          El robot no se mueve solo: el recorrido enciende cámara, detección y registro. Llévalo por la hilera con el mando.
        </Aviso>
        {!!control.datos?.salida.length && (
          <details>
            <summary className="sb-label" style={{ cursor: 'pointer' }}>Salida del proceso</summary>
            <pre className="sb-log" style={{ marginTop: 'var(--space-2)' }}>{control.datos.salida.join('\n')}</pre>
          </details>
        )}
      </div>
    </Tarjeta>
  )
}
