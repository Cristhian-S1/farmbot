import { useEffect, useRef } from 'react'
import type { Recorrido } from '../../api/tipos'
import { ESTADOS_RECORRIDO, ESTADOS_ZONA } from '../../utilidades/estados'
import { formatoDia, formatoFechaHora, formatoHoraCorta, plural } from '../../utilidades/formato'
import './GraficoRecorridos.css'

const MAX_RECORRIDOS = 12
const TOPE_MINIMO = 4

/** Marcas enteras y redondas del eje, desde 0 hasta un tope que contiene al máximo. */
function marcasEje(maximo: number): number[] {
  const paso = maximo <= TOPE_MINIMO ? 1 : maximo <= 10 ? 2 : maximo <= 25 ? 5 : 10
  const tope = Math.max(TOPE_MINIMO, Math.ceil(maximo / paso) * paso)
  return Array.from({ length: tope / paso + 1 }, (_, i) => i * paso)
}

const altoBarra = (zonas: number, tope: number) => ({ height: `calc(var(--sb-chart-alto) * ${zonas / tope})` })

interface Props {
  /** Del más reciente al más antiguo, como los entrega la API. */
  recorridos: Recorrido[]
  totalZonas: number | null
}

/** Columnas apiladas con las zonas por revisar de cada recorrido, del más antiguo al más reciente. */
export default function GraficoRecorridos({ recorridos, totalZonas }: Props) {
  const ultimos = recorridos.slice(0, MAX_RECORRIDOS).reverse()
  const marcas = marcasEje(Math.max(...ultimos.map((r) => r.zonas_maleza + r.zonas_follaje)))
  const tope = marcas[marcas.length - 1]
  const posicion = (marca: number) => ({ bottom: `${(marca / tope) * 100}%` })

  // En pantallas angostas el gráfico se desplaza: partir mostrando lo más reciente.
  const desplazable = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = desplazable.current
    if (el) el.scrollLeft = el.scrollWidth
  }, [ultimos.length])

  return (
    <div className="sb-chart">
      <div className="sb-chart-eje" aria-hidden="true">
        {marcas.map((m) => (
          <span key={m} style={posicion(m)}>{m}</span>
        ))}
      </div>
      <div className="sb-chart-desplazable" ref={desplazable}>
        <div className="sb-chart-columnas" role="group" aria-label="Zonas por revisar en cada recorrido">
          <div className="sb-chart-rejilla" aria-hidden="true">
            {marcas.map((m) => (
              <i key={m} className={m === 0 ? 'base' : undefined} style={posicion(m)} />
            ))}
          </div>
          {ultimos.map((r, i) => {
            const total = r.zonas_maleza + r.zonas_follaje
            const estado = ESTADOS_RECORRIDO[r.estado]
            const observadas = totalZonas == null ? `${r.zonas}` : `${r.zonas} de ${totalZonas}`
            return (
              <div
                key={r.id}
                className="sb-chart-col"
                role="img"
                tabIndex={0}
                aria-label={`Recorrido del ${formatoFechaHora(r.inicio)}, ${estado.texto.toLowerCase()}: ${plural(total, 'zona')} por revisar, ${r.zonas_follaje} por follaje y ${r.zonas_maleza} por maleza. ${observadas} zonas observadas.`}
              >
                <div className="sb-chart-area">
                  <span className="sb-chart-total">{total}</span>
                  {r.zonas_follaje > 0 && <span className="sb-chart-seg sb-chart-seg--danger" style={altoBarra(r.zonas_follaje, tope)} />}
                  {r.zonas_maleza > 0 && <span className="sb-chart-seg sb-chart-seg--warn" style={altoBarra(r.zonas_maleza, tope)} />}
                </div>
                <div className="sb-chart-x">
                  <strong>{formatoDia(r.inicio)}</strong>
                  <span>{formatoHoraCorta(r.inicio)}</span>
                  {r.estado !== 'completado' && <span>{estado.texto}</span>}
                </div>
                <div className={`sb-chart-tip ${i < ultimos.length / 2 ? 'sb-chart-tip--izq' : 'sb-chart-tip--der'}`}>
                  <p className="sb-chart-tip-titulo">{formatoFechaHora(r.inicio)}</p>
                  <p className="sb-caption">{estado.texto}</p>
                  <dl>
                    <div><dt><i className="sb-swatch sb-swatch--barra-danger" />{ESTADOS_ZONA.revisar_follaje.texto}</dt><dd>{r.zonas_follaje}</dd></div>
                    <div><dt><i className="sb-swatch sb-swatch--barra-warn" />{ESTADOS_ZONA.revisar_maleza.texto}</dt><dd>{r.zonas_maleza}</dd></div>
                    <div><dt>Zonas observadas</dt><dd>{observadas}</dd></div>
                  </dl>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/** Leyenda del gráfico, para ponerla en la cabecera de la tarjeta. */
export function LeyendaGrafico() {
  return (
    <div className="sb-legend">
      <span className="sb-legend-item"><i className="sb-swatch sb-swatch--barra-warn" />{ESTADOS_ZONA.revisar_maleza.texto}</span>
      <span className="sb-legend-item"><i className="sb-swatch sb-swatch--barra-danger" />{ESTADOS_ZONA.revisar_follaje.texto}</span>
    </div>
  )
}
