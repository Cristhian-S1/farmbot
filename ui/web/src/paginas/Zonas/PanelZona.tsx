import { useState } from 'react'
import { api } from '../../api/cliente'
import type { Captura } from '../../api/tipos'
import { Aviso, Vacio } from '../../componentes/Aviso'
import FotoDetecciones from '../../componentes/FotoDetecciones'
import Insignia from '../../componentes/Insignia'
import { useConsulta } from '../../hooks/useConsulta'
import { ESTADOS_RECORRIDO, ESTADOS_ZONA } from '../../utilidades/estados'
import { formatoFecha, formatoHora, nombreZona, plural } from '../../utilidades/formato'
import HistorialZona from './HistorialZona'
import './PanelZona.css'

const INTERVALO_MS = 5000
const MINIATURAS = 8

interface Props {
  zona: number
  recorrido: string | null
  onElegirRecorrido: (recorrido: string) => void
}

function leyenda(c: Captura): string {
  const n = c.detecciones.length
  return `${formatoHora(c.fecha)} · ${n ? plural(n, 'detección', 'detecciones') : 'sin hallazgos'}`
}

/** Ficha de una zona: foto con detecciones, conteos y acceso al historial. */
export default function PanelZona({ zona, recorrido, onElegirRecorrido }: Props) {
  const ficha = useConsulta(() => api.ficha(zona, recorrido), [zona, recorrido], INTERVALO_MS)
  const [elegida, setElegida] = useState<string | null>(null)
  const [verHistorial, setVerHistorial] = useState(false)

  if (ficha.error && !ficha.datos) {
    return (
      <Aviso>
        No se pudo cargar la zona: {ficha.error}{' '}
        <button type="button" className="sb-link" onClick={ficha.recargar}>Reintentar</button>
      </Aviso>
    )
  }
  if (!ficha.datos) return <p className="sb-muted">Cargando…</p>

  const f = ficha.datos
  const estado = ESTADOS_ZONA[f.estado]
  // Por defecto, la captura más reciente con hallazgos; si no hay, la más reciente.
  const captura =
    f.capturas.find((c) => c.id === elegida) ?? f.capturas.find((c) => c.detecciones.length) ?? f.capturas[0]
  const r = f.resumen

  return (
    <>
      <p className="sb-caption">Zona seleccionada</p>
      <div className="sb-card-head" style={{ marginBottom: 'var(--space-1)' }}>
        <h2 className="sb-page-title">{nombreZona(f.hilera, f.numero)}</h2>
        <Insignia nivel={estado.nivel} texto={estado.texto} />
      </div>
      <p className="sb-muted" style={{ marginBottom: 'var(--space-4)' }}>
        {f.recorrido
          ? `Recorrido del ${formatoFecha(f.recorrido.inicio)} · ${ESTADOS_RECORRIDO[f.recorrido.estado].texto}`
          : 'Todavía no hay recorridos'}
      </p>

      {verHistorial ? (
        <>
          <HistorialZona
            zona={zona}
            recorrido={recorrido}
            onElegirRecorrido={(id) => {
              onElegirRecorrido(id)
              setVerHistorial(false)
            }}
          />
          <button type="button" className="sb-btn sb-btn--secondary sb-btn--block sb-panel-accion" onClick={() => setVerHistorial(false)}>
            Volver a la evidencia
          </button>
        </>
      ) : (
        <>
          {captura ? (
            <FotoDetecciones captura={captura} leyenda={leyenda(captura)} />
          ) : (
            <Vacio icono="imagen" titulo="Sin datos">
              Este recorrido no registró capturas en la zona. Sin datos no significa sin problemas.
            </Vacio>
          )}

          {f.capturas.length > 1 && (
            <div className="sb-thumbs" role="group" aria-label="Capturas de la zona">
              {f.capturas.slice(0, MINIATURAS).map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className="sb-thumb"
                  aria-pressed={c.id === captura?.id}
                  aria-label={leyenda(c)}
                  onClick={() => setElegida(c.id)}
                >
                  <FotoDetecciones captura={c} etiquetas={false} />
                </button>
              ))}
            </div>
          )}

          <dl style={{ marginTop: 'var(--space-4)' }}>
            <div className="sb-dl-row"><dt>Última captura</dt><dd>{r.ultima_captura ? formatoHora(r.ultima_captura) : '–'}</dd></div>
            <div className="sb-dl-row"><dt>Frutos verdes</dt><dd>{r.verdes}</dd></div>
            <div className="sb-dl-row"><dt>Frutos maduros</dt><dd>{r.maduros}</dd></div>
            <div className="sb-dl-row"><dt>Maleza</dt><dd>{r.maleza}</dd></div>
            <div className="sb-dl-row"><dt>Signos en el follaje</dt><dd>{r.follaje}</dd></div>
            <div className="sb-dl-row"><dt>Capturas</dt><dd>{r.capturas}{r.pendientes ? ` (${r.pendientes} pendientes)` : ''}</dd></div>
            <div className="sb-dl-row">
              <dt>Modelo</dt>
              <dd>{f.recorrido?.modelo ? `${f.recorrido.modelo} ${f.recorrido.modelo_version}` : 'Sin registrar'}</dd>
            </div>
          </dl>
          <p className="sb-caption" style={{ marginTop: 'var(--space-2)' }}>
            Los conteos suman las detecciones de todas las capturas; un mismo fruto puede aparecer en varias.
          </p>
          {r.sin_foto > 0 && (
            <Aviso tipo="info">{plural(r.sin_foto, 'captura')} sin imagen: se conservan sus datos.</Aviso>
          )}

          <button type="button" className="sb-btn sb-btn--secondary sb-btn--block sb-panel-accion" onClick={() => setVerHistorial(true)}>
            Consultar historial
          </button>
        </>
      )}
    </>
  )
}
