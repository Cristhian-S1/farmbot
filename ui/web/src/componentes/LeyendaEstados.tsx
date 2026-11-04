import type { EstadoZona } from '../api/tipos'
import { ESTADOS_ZONA, ORDEN_ESTADOS } from '../utilidades/estados'

/** Leyenda de estados de zona; con `conteo`, muestra cuántas zonas hay en cada uno. */
export default function LeyendaEstados({ conteo }: { conteo?: Record<EstadoZona, number> }) {
  return (
    <div className="sb-legend" aria-label="Estados de las zonas">
      {ORDEN_ESTADOS.map((estado) => (
        <span key={estado} className="sb-legend-item">
          <i className={`sb-swatch sb-swatch--${ESTADOS_ZONA[estado].nivel}`} />
          {conteo && <strong>{conteo[estado]}</strong>}
          {ESTADOS_ZONA[estado].texto}
        </span>
      ))}
    </div>
  )
}
