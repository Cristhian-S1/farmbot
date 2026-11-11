import type { Captura, ZonaMapa } from '../../api/tipos'
import FotoDetecciones from '../../componentes/FotoDetecciones'
import Icono from '../../componentes/Icono'
import Insignia from '../../componentes/Insignia'
import { enlace } from '../../hooks/useRuta'
import { ESTADOS_ZONA } from '../../utilidades/estados'
import { formatoHora, nombreZona, plural } from '../../utilidades/formato'
import './ZonasPorRevisar.css'

function frutos(z: ZonaMapa): string {
  const partes = []
  if (z.verdes) partes.push(plural(z.verdes, 'fruto verde', 'frutos verdes'))
  if (z.maduros) partes.push(plural(z.maduros, 'fruto maduro', 'frutos maduros'))
  return partes.join(' y ')
}

function resumen(z: ZonaMapa): string {
  const partes = []
  if (z.follaje) partes.push(`${plural(z.follaje, 'signo')} en el follaje`)
  if (z.maleza) partes.push(`${plural(z.maleza, 'detección', 'detecciones')} de maleza`)
  if (z.verdes || z.maduros) partes.push(frutos(z))
  return partes.join(' · ')
}

interface Props {
  zonas: ZonaMapa[]
  /** Capturas con hallazgos del recorrido, de la más reciente a la más antigua. */
  capturas: Captura[]
}

/** Zonas con alertas, de la más urgente a la menos: primero follaje, luego por cantidad. */
export default function ZonasPorRevisar({ zonas, capturas }: Props) {
  const ordenadas = [...zonas].sort((a, b) => b.follaje - a.follaje || b.maleza - a.maleza)
  return (
    <ul className="sb-list">
      {ordenadas.map((z) => {
        const foto = capturas.find(
          (c) => c.zona_id === z.id && c.detecciones.some((d) => d.grupo === 'maleza' || d.grupo === 'follaje'),
        )
        const estado = ESTADOS_ZONA[z.estado]
        return (
          <li key={z.id} className="sb-alert-row">
            {foto ? (
              <FotoDetecciones captura={foto} etiquetas={false} className="sb-alert-thumb" />
            ) : (
              <div className="sb-alert-thumb sb-alert-thumb--vacia">
                <Icono nombre="imagen" />
              </div>
            )}
            <div className="sb-alert-body">
              <div className="sb-alert-head">
                <p className="sb-list-title">{nombreZona(z.hilera, z.numero)}</p>
                <Insignia nivel={estado.nivel} texto={estado.texto} />
              </div>
              <p>{resumen(z)}</p>
              <p className="sb-caption">
                {plural(z.capturas, 'captura')}
                {z.ultima_captura && ` · última a las ${formatoHora(z.ultima_captura)}`}
              </p>
            </div>
            <a className="sb-btn sb-btn--secondary sb-btn--small" href={enlace('zonas', z.id)}>
              Ver detalle
            </a>
          </li>
        )
      })}
    </ul>
  )
}
