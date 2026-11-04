import type { KeyboardEvent } from 'react'
import type { ZonaMapa } from '../../api/tipos'
import { ESTADOS_ZONA } from '../../utilidades/estados'
import './MapaZonas.css'

const ANCHO = 760
const ETIQUETA = 92
const MARGEN = 8
const ESPACIO = 10
const ALTO_FILA = 76
const CABECERA = 30
const ANCHO_MIN_TEXTO = 118

interface Props {
  zonas: ZonaMapa[]
  seleccionada: number | null
  onElegir: (zona: number) => void
}

/** Esquema del invernadero: una fila por hilera, dividida en zonas. El texto acompaña siempre al color. */
export default function MapaZonas({ zonas, seleccionada, onElegir }: Props) {
  const hileras = [...new Set(zonas.map((z) => z.hilera))].sort((a, b) => a - b)
  const columnas = Math.max(1, ...zonas.map((z) => z.numero))
  const anchoCelda = (ANCHO - ETIQUETA - MARGEN - ESPACIO * (columnas - 1)) / columnas
  const alto = CABECERA + hileras.length * (ALTO_FILA + ESPACIO) + MARGEN
  const x = (numero: number) => ETIQUETA + (numero - 1) * (anchoCelda + ESPACIO)
  const y = (hilera: number) => CABECERA + hileras.indexOf(hilera) * (ALTO_FILA + ESPACIO)

  const teclado = (e: KeyboardEvent, zona: number) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onElegir(zona)
    }
  }

  return (
    <svg className="sb-map" viewBox={`0 0 ${ANCHO} ${alto}`} role="group" aria-label="Mapa de hileras y zonas">
      <defs>
        <pattern id="sb-hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect className="hatch" width="2.5" height="7" />
        </pattern>
      </defs>
      {Array.from({ length: columnas }, (_, i) => (
        <text key={i} className="map-sub" x={x(i + 1) + anchoCelda / 2} y={18} textAnchor="middle">
          Zona {i + 1}
        </text>
      ))}
      {hileras.map((h) => (
        <g key={h}>
          <text className="row-label" x={0} y={y(h) + ALTO_FILA / 2 + 5}>
            Hilera {h}
          </text>
          <line className="row-line" x1={ETIQUETA - 6} x2={ANCHO - MARGEN + 2} y1={y(h) + ALTO_FILA / 2} y2={y(h) + ALTO_FILA / 2} />
        </g>
      ))}
      {zonas.map((z) => {
        const estado = ESTADOS_ZONA[z.estado]
        const elegida = z.id === seleccionada
        const cx = x(z.numero)
        const cy = y(z.hilera)
        return (
          <g
            key={z.id}
            className={`zone zone--${estado.nivel}`}
            role="button"
            tabIndex={0}
            aria-pressed={elegida}
            aria-label={`Hilera ${z.hilera}, zona ${z.numero}: ${estado.texto}`}
            onClick={() => onElegir(z.id)}
            onKeyDown={(e) => teclado(e, z.id)}
          >
            <rect className="cell" x={cx} y={cy} width={anchoCelda} height={ALTO_FILA} rx={6} />
            {estado.nivel === 'danger' && <rect className="cell-hatch" x={cx} y={cy} width={anchoCelda} height={ALTO_FILA} rx={6} />}
            {elegida && <rect className="sel" x={cx - 4} y={cy - 4} width={anchoCelda + 8} height={ALTO_FILA + 8} rx={9} />}
            <text className="cell-title" x={cx + 12} y={cy + 26}>
              H{z.hilera}–Z{z.numero}
            </text>
            {anchoCelda >= ANCHO_MIN_TEXTO && (
              <text className="cell-state" x={cx + 12} y={cy + 50}>
                {estado.texto}
              </text>
            )}
            {(z.estado === 'revisar_maleza' || z.estado === 'revisar_follaje') && (
              <text className="cell-count" x={cx + anchoCelda - 12} y={cy + 26} textAnchor="end">
                {z.estado === 'revisar_maleza' ? z.maleza : z.follaje}
              </text>
            )}
            <title>{`H${z.hilera}–Z${z.numero} · ${estado.texto}`}</title>
          </g>
        )
      })}
    </svg>
  )
}
