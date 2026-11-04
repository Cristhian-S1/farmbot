import { api } from '../../api/cliente'
import { Aviso, Vacio } from '../../componentes/Aviso'
import Insignia from '../../componentes/Insignia'
import { useConsulta } from '../../hooks/useConsulta'
import { ESTADOS_ZONA } from '../../utilidades/estados'
import { formatoFechaHora, plural } from '../../utilidades/formato'

interface Props {
  zona: number
  recorrido: string | null
  onElegirRecorrido: (recorrido: string) => void
}

/** Un renglón por recorrido; los que no pasaron por la zona quedan como "Sin datos". */
export default function HistorialZona({ zona, recorrido, onElegirRecorrido }: Props) {
  const historial = useConsulta(() => api.historial(zona), [zona])

  if (historial.error) return <Aviso>No se pudo cargar el historial: {historial.error}</Aviso>
  if (!historial.datos) return <p className="sb-muted">Cargando…</p>
  if (!historial.datos.length) return <Vacio titulo="Sin registros anteriores" />

  return (
    <ul className="sb-list">
      {historial.datos.map((h, i) => {
        const estado = ESTADOS_ZONA[h.estado]
        const actual = recorrido ? h.recorrido === recorrido : i === 0
        return (
          <li key={h.recorrido} className="sb-list-item">
            <div>
              <p className="sb-list-title">
                {formatoFechaHora(h.inicio)}
                {actual && <span className="sb-caption"> · viendo</span>}
              </p>
              <p className="sb-list-sub">
                {h.capturas
                  ? `${plural(h.capturas, 'captura')} · ${h.maleza} maleza · ${h.follaje} follaje · ${h.verdes + h.maduros} frutos`
                  : 'El recorrido no registró esta zona'}
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <Insignia nivel={estado.nivel} texto={estado.texto} />
              {!actual && (
                <button type="button" className="sb-link" onClick={() => onElegirRecorrido(h.recorrido)}>
                  Ver
                </button>
              )}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
