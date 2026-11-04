import { api } from '../../api/cliente'
import { Aviso, Vacio } from '../../componentes/Aviso'
import Encabezado from '../../componentes/Encabezado'
import LeyendaEstados from '../../componentes/LeyendaEstados'
import SelectorRecorrido from '../../componentes/SelectorRecorrido'
import Tarjeta from '../../componentes/Tarjeta'
import { useConsulta } from '../../hooks/useConsulta'
import { enlace } from '../../hooks/useRuta'
import { plural, sinZona } from '../../utilidades/formato'
import { subtitulo, type PropsPagina } from '../contexto'
import MapaZonas from './MapaZonas'
import PanelZona from './PanelZona'

const INTERVALO_MS = 5000

export default function Zonas({ estructura, recorridos, recorrido, elegirRecorrido, zona }: PropsPagina & { zona: number | null }) {
  const mapa = useConsulta(() => api.mapa(recorrido), [recorrido], INTERVALO_MS)
  const zonas = mapa.datos?.zonas ?? []
  const hileras = new Set(zonas.map((z) => z.hilera)).size
  const elegir = (id: number) => {
    window.location.hash = enlace('zonas', id)
  }

  return (
    <main className="sb-main">
      <Encabezado titulo="Zonas e hileras" sub={subtitulo(estructura)}>
        <SelectorRecorrido recorridos={recorridos} valor={recorrido} onCambiar={elegirRecorrido} />
      </Encabezado>

      {mapa.error && <Aviso>No se pudo consultar la API: {mapa.error}</Aviso>}

      <div className="sb-row">
        <Tarjeta
          className="sb-col"
          titulo={`${estructura?.sector.nombre ?? 'Sector'} · ${plural(hileras, 'hilera')}, ${plural(zonas.length, 'zona')}`}
          extra={<LeyendaEstados />}
          pie={
            mapa.datos?.capturas_sin_zona
              ? `${sinZona(mapa.datos.capturas_sin_zona)}. Toca una zona para ver su ficha.`
              : 'Toca una zona para ver su ficha. El borde azul marca la zona seleccionada.'
          }
        >
          {zonas.length ? <MapaZonas zonas={zonas} seleccionada={zona} onElegir={elegir} /> : <p className="sb-muted">Cargando…</p>}
        </Tarjeta>

        <aside className="sb-card sb-aside" aria-live="polite">
          {zona ? (
            <PanelZona key={zona} zona={zona} recorrido={recorrido} onElegirRecorrido={elegirRecorrido} />
          ) : (
            <Vacio icono="zonas" titulo="Elige una zona">
              Su ficha muestra la foto con las detecciones, los conteos y el historial.
            </Vacio>
          )}
        </aside>
      </div>
    </main>
  )
}
