import type { Captura } from '../api/tipos'
import { formatoHora, nombreZona, plural } from '../utilidades/formato'
import Insignia from './Insignia'

/** Lista breve de capturas: zona, hora y cuántos hallazgos trae cada una. */
export default function ListaCapturas({ capturas }: { capturas: Captura[] }) {
  return (
    <ul className="sb-list">
      {capturas.map((c) => {
        const alertas = c.detecciones.filter((d) => d.grupo === 'maleza' || d.grupo === 'follaje').length
        const frutos = c.detecciones.filter((d) => d.grupo === 'fruto').length
        return (
          <li key={c.id} className="sb-list-item">
            <div>
              <p className="sb-list-title">{nombreZona(c.hilera, c.zona)}</p>
              <p className="sb-list-sub">
                {formatoHora(c.fecha)}
                {frutos > 0 && ` · ${plural(frutos, 'fruto')}`}
              </p>
            </div>
            {c.analisis === 'pendiente' ? (
              <Insignia nivel="neutral" texto="Pendiente" />
            ) : alertas > 0 ? (
              <Insignia nivel="warn" texto={plural(alertas, 'hallazgo')} />
            ) : (
              <Insignia nivel="ok" texto="Sin alertas" />
            )}
          </li>
        )
      })}
    </ul>
  )
}
