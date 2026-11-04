import { api } from '../../api/cliente'
import { Vacio } from '../../componentes/Aviso'
import Encabezado from '../../componentes/Encabezado'
import ListaCapturas from '../../componentes/ListaCapturas'
import Tarjeta from '../../componentes/Tarjeta'
import { useConsulta } from '../../hooks/useConsulta'
import { subtitulo, type PropsPagina } from '../contexto'
import ControlRecorrido from './ControlRecorrido'
import EnVivo from './EnVivo'

const INTERVALO_CONTROL_MS = 2000
const INTERVALO_CAPTURAS_MS = 3000

export default function Recorrido({ estructura, elegirRecorrido, recargarRecorridos }: PropsPagina) {
  const control = useConsulta(api.control, [], INTERVALO_CONTROL_MS)
  const actual = control.datos?.recorrido ?? null
  const capturas = useConsulta(() => (actual ? api.capturas(actual, { limite: 8 }) : Promise.resolve([])), [actual], INTERVALO_CAPTURAS_MS)

  return (
    <main className="sb-main">
      <Encabezado titulo="Recorrido" sub={subtitulo(estructura)} />
      <div className="sb-row">
        <div className="sb-col">
          <EnVivo />
        </div>
        <div className="sb-col sb-aside">
          <ControlRecorrido
            estructura={estructura}
            control={control}
            onCambio={() => {
              elegirRecorrido(null)
              recargarRecorridos()
            }}
          />
          <Tarjeta titulo="Capturas del recorrido" pie={actual ? `Recorrido ${actual}` : undefined}>
            {capturas.datos?.length ? (
              <ListaCapturas capturas={capturas.datos} />
            ) : (
              <Vacio icono="imagen" titulo="Sin capturas todavía">
                {control.datos?.corriendo && 'Aparecerán aquí a medida que el robot las envíe.'}
              </Vacio>
            )}
          </Tarjeta>
        </div>
      </div>
    </main>
  )
}
