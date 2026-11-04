import { enlace, type Seccion } from '../hooks/useRuta'
import Icono, { type NombreIcono } from './Icono'
import './BarraLateral.css'

const SECCIONES: { seccion: Seccion; texto: string; icono: NombreIcono }[] = [
  { seccion: 'inicio', texto: 'Inicio', icono: 'inicio' },
  { seccion: 'zonas', texto: 'Zonas', icono: 'zonas' },
  { seccion: 'recorrido', texto: 'Recorrido', icono: 'recorrido' },
  { seccion: 'historial', texto: 'Historial', icono: 'historial' },
]

function Marca() {
  return (
    <svg className="sb-mark" viewBox="0 0 40 40" aria-hidden="true">
      <rect className="mark-bg" width="40" height="40" rx="9" />
      <circle className="mark-fg" cx="20" cy="22.5" r="10" />
      <path className="mark-bg" d="M20 12.5c-2.5-3.5-6-4-8-3 1.5 2.5 4.5 3.8 8 3zM20 12.5c2.5-3.5 6-4 8-3-1.5 2.5-4.5 3.8-8 3z" />
      <circle className="mark-bg" cx="20" cy="22.5" r="3.4" />
    </svg>
  )
}

export default function BarraLateral({ actual }: { actual: Seccion }) {
  return (
    <aside className="sb-sidebar">
      <div className="sb-brand">
        <Marca />
        <span className="sb-wordmark">SABUESO</span>
      </div>
      <nav className="sb-nav" aria-label="Principal">
        {SECCIONES.map(({ seccion, texto, icono }) => (
          <a
            key={seccion}
            className="sb-nav-item"
            href={enlace(seccion)}
            aria-current={seccion === actual ? 'page' : undefined}
          >
            <Icono nombre={icono} />
            <span>{texto}</span>
          </a>
        ))}
      </nav>
    </aside>
  )
}
