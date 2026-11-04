import type { EstadoZona } from '../../api/tipos'
import LeyendaEstados from '../../componentes/LeyendaEstados'
import { ESTADOS_ZONA, ORDEN_ESTADOS } from '../../utilidades/estados'
import './BarraEstados.css'

/** Barra proporcional con cuántas zonas hay en cada estado. */
export default function BarraEstados({ conteo }: { conteo: Record<EstadoZona, number> }) {
  const descripcion = ORDEN_ESTADOS.map((e) => `${conteo[e]} ${ESTADOS_ZONA[e].texto.toLowerCase()}`).join(', ')
  return (
    <>
      <div className="sb-statusbar" role="img" aria-label={`Zonas: ${descripcion}`}>
        {ORDEN_ESTADOS.filter((e) => conteo[e] > 0).map((e) => (
          <span
            key={e}
            className={`sb-statusbar-seg sb-statusbar-seg--${ESTADOS_ZONA[e].nivel}`}
            style={{ flex: conteo[e] }}
            title={`${ESTADOS_ZONA[e].texto}: ${conteo[e]}`}
          />
        ))}
      </div>
      <div style={{ marginTop: 'var(--space-3)' }}>
        <LeyendaEstados conteo={conteo} />
      </div>
    </>
  )
}
