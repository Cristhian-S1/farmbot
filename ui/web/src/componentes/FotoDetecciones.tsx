import { useState } from 'react'
import { urlFoto } from '../api/cliente'
import type { Captura } from '../api/tipos'
import { NIVEL_GRUPO } from '../utilidades/estados'
import { porcentaje } from '../utilidades/formato'
import Icono from './Icono'
import './FotoDetecciones.css'

interface Props {
  captura: Captura
  etiquetas?: boolean
  leyenda?: string
  className?: string
}

/** Foto de una captura con las cajas de detección dibujadas encima, en coordenadas de la imagen. */
export default function FotoDetecciones({ captura, etiquetas = true, leyenda, className = '' }: Props) {
  const [tamano, setTamano] = useState<{ ancho: number; alto: number } | null>(null)
  const [falla, setFalla] = useState(false)

  if (!captura.foto || falla) {
    return (
      <div className={`sb-photo sb-photo--ausente ${className}`} role="img" aria-label="Imagen no disponible">
        <Icono nombre="imagen" />
        <span>Imagen no disponible</span>
      </div>
    )
  }

  // Trazo y etiquetas proporcionales a la foto, para que se vean igual en miniatura y en grande.
  const trazo = tamano ? Math.max(2, tamano.ancho / 320) : 2
  const escala = tamano ? Math.max(1, tamano.ancho / 420) : 1
  const descripcion = captura.detecciones.length
    ? `Foto con ${captura.detecciones.map((d) => d.nombre.toLowerCase()).join(', ')}`
    : 'Foto sin hallazgos'

  return (
    <figure className={`sb-photo ${className}`}>
      <img
        src={urlFoto(captura.foto)}
        alt={descripcion}
        onLoad={(e) => setTamano({ ancho: e.currentTarget.naturalWidth, alto: e.currentTarget.naturalHeight })}
        onError={() => setFalla(true)}
      />
      {tamano && (
        <svg viewBox={`0 0 ${tamano.ancho} ${tamano.alto}`} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
          {captura.detecciones.map((d, i) => {
            const [x1, y1, x2, y2] = d.caja
            const nivel = NIVEL_GRUPO[d.grupo]
            const texto = `${d.nombre} ${porcentaje(d.confianza)}`
            return (
              <g key={i}>
                <rect className="sb-bbox-halo" x={x1} y={y1} width={x2 - x1} height={y2 - y1} strokeWidth={trazo * 2} />
                <rect className={`sb-bbox sb-bbox--${nivel}`} x={x1} y={y1} width={x2 - x1} height={y2 - y1} strokeWidth={trazo} />
                {etiquetas && (
                  <g className={`sb-tag sb-tag--${nivel}`} transform={`translate(${x1} ${Math.max(0, y1 - 26 * escala)}) scale(${escala})`}>
                    <rect width={texto.length * 7.4 + 16} height="24" rx="3" />
                    <text x="8" y="16.5">{texto}</text>
                  </g>
                )}
              </g>
            )
          })}
        </svg>
      )}
      {leyenda && <figcaption className="sb-photo-cap">{leyenda}</figcaption>}
    </figure>
  )
}
