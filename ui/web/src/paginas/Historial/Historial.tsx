import { Aviso, Vacio } from '../../componentes/Aviso'
import Encabezado from '../../componentes/Encabezado'
import Insignia from '../../componentes/Insignia'
import Tarjeta from '../../componentes/Tarjeta'
import { enlace } from '../../hooks/useRuta'
import { ESTADOS_RECORRIDO } from '../../utilidades/estados'
import { formatoFechaHora, formatoHora, plural } from '../../utilidades/formato'
import type { PropsPagina } from '../contexto'

export default function Historial({ recorridos, recorrido, elegirRecorrido }: PropsPagina) {
  const verMapa = (id: string) => {
    elegirRecorrido(id)
    window.location.hash = enlace('zonas')
  }
  const elegido = recorrido ?? recorridos[0]?.id

  return (
    <main className="sb-main">
      <Encabezado titulo="Historial" sub="Recorridos del robot, del más reciente al más antiguo" />
      <Tarjeta
        titulo="Recorridos"
        pie={recorridos.length ? `Mostrando ${plural(recorridos.length, 'recorrido')}. "Hallazgos" cuenta detecciones de maleza y follaje.` : undefined}
      >
        {!recorridos.length ? (
          <Vacio icono="recorrido" titulo="Todavía no hay recorridos" />
        ) : (
          <div className="sb-table-wrap">
            <table className="sb-table">
              <thead>
                <tr>
                  <th>Inicio</th>
                  <th>Fin</th>
                  <th>Estado</th>
                  <th className="num">Capturas</th>
                  <th className="num">Zonas</th>
                  <th className="num">Hallazgos</th>
                  <th className="num">Sin zona</th>
                  <th>Modelo</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {recorridos.map((r) => (
                  <tr key={r.id} aria-current={r.id === elegido ? 'true' : undefined}>
                    <td className="sb-num">{formatoFechaHora(r.inicio)}</td>
                    <td className="sb-num">{r.fin ? formatoHora(r.fin) : '–'}</td>
                    <td><Insignia {...ESTADOS_RECORRIDO[r.estado]} /></td>
                    <td className="num">{r.capturas}</td>
                    <td className="num">{r.zonas}</td>
                    <td className="num">{r.alertas}</td>
                    <td className="num">{r.sin_zona}</td>
                    <td>{r.modelo ? `${r.modelo} ${r.modelo_version}` : 'Sin registrar'}</td>
                    <td>
                      <button type="button" className="sb-link" onClick={() => verMapa(r.id)}>
                        Ver mapa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Tarjeta>
      {recorridos.some((r) => r.estado === 'incompleto') && (
        <Aviso tipo="info">Un recorrido incompleto terminó sin que nadie lo detuviera; sus zonas pueden haber quedado sin datos.</Aviso>
      )}
    </main>
  )
}
