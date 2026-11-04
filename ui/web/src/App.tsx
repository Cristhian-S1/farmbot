import { useState } from 'react'
import { api } from './api/cliente'
import BarraLateral from './componentes/BarraLateral'
import { useConsulta } from './hooks/useConsulta'
import { useRuta } from './hooks/useRuta'
import type { PropsPagina } from './paginas/contexto'
import Historial from './paginas/Historial/Historial'
import Inicio from './paginas/Inicio/Inicio'
import Recorrido from './paginas/Recorrido/Recorrido'
import Zonas from './paginas/Zonas/Zonas'

const INTERVALO_RECORRIDOS_MS = 5000

export default function App() {
  const ruta = useRuta()
  const [recorrido, elegirRecorrido] = useState<string | null>(null)
  const estructura = useConsulta(api.estructura, [])
  const recorridos = useConsulta(api.recorridos, [], INTERVALO_RECORRIDOS_MS)

  const props: PropsPagina = {
    estructura: estructura.datos,
    recorridos: recorridos.datos ?? [],
    recorrido,
    elegirRecorrido,
    recargarRecorridos: recorridos.recargar,
  }

  return (
    <div className="sb-frame">
      <BarraLateral actual={ruta.seccion} />
      {ruta.seccion === 'inicio' && <Inicio {...props} />}
      {ruta.seccion === 'zonas' && <Zonas {...props} zona={ruta.id} />}
      {ruta.seccion === 'recorrido' && <Recorrido {...props} />}
      {ruta.seccion === 'historial' && <Historial {...props} />}
    </div>
  )
}
