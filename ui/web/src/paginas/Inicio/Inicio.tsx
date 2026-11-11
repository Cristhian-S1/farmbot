import { api } from '../../api/cliente'
import type { EstadoZona } from '../../api/tipos'
import { Aviso, Vacio } from '../../componentes/Aviso'
import Encabezado from '../../componentes/Encabezado'
import Insignia from '../../componentes/Insignia'
import Kpi from '../../componentes/Kpi'
import ListaCapturas from '../../componentes/ListaCapturas'
import SelectorRecorrido from '../../componentes/SelectorRecorrido'
import Tarjeta from '../../componentes/Tarjeta'
import { useConsulta } from '../../hooks/useConsulta'
import { enlace } from '../../hooks/useRuta'
import { ESTADOS_RECORRIDO, ORDEN_ESTADOS, esAlerta } from '../../utilidades/estados'
import { formatoFecha, plural, sinZona } from '../../utilidades/formato'
import { subtitulo, type PropsPagina } from '../contexto'
import BarraEstados from './BarraEstados'
import ZonasPorRevisar from './ZonasPorRevisar'

const INTERVALO_MS = 5000

export default function Inicio({ estructura, recorridos, recorrido, elegirRecorrido }: PropsPagina) {
  const mapa = useConsulta(() => api.mapa(recorrido), [recorrido], INTERVALO_MS)
  // Con "Último recorrido" (recorrido nulo), las capturas siguen al recorrido que muestra el mapa;
  // sin esto, la API devolvería las de todos los recorridos mezcladas.
  const mostrado = recorrido ?? mapa.datos?.recorrido ?? null
  const conHallazgos = useConsulta(
    () => (mostrado ? api.capturas(mostrado, { hallazgos: true, limite: 200 }) : Promise.resolve([])),
    [mostrado],
    INTERVALO_MS,
  )
  const recientes = useConsulta(
    () => (mostrado ? api.capturas(mostrado, { limite: 6 }) : Promise.resolve([])),
    [mostrado],
    INTERVALO_MS,
  )

  const zonas = mapa.datos?.zonas ?? []
  const actual = recorridos.find((r) => r.id === mapa.datos?.recorrido)
  const conteo = Object.fromEntries(ORDEN_ESTADOS.map((e) => [e, zonas.filter((z) => z.estado === e).length])) as Record<EstadoZona, number>
  const porRevisar = zonas.filter((z) => esAlerta(z.estado))
  const observadas = zonas.length - conteo.sin_datos
  const hileras = new Set(zonas.map((z) => z.hilera)).size
  const verdes = zonas.reduce((n, z) => n + z.verdes, 0)
  const maduros = zonas.reduce((n, z) => n + z.maduros, 0)
  const sinRecorridos = mapa.datos && !mapa.datos.recorrido

  return (
    <main className="sb-main">
      <Encabezado titulo="Resumen del recorrido" sub={subtitulo(estructura)}>
        <SelectorRecorrido recorridos={recorridos} valor={recorrido} onCambiar={elegirRecorrido} />
      </Encabezado>

      {mapa.error && <Aviso>No se pudo consultar la API: {mapa.error}</Aviso>}

      {sinRecorridos ? (
        <Tarjeta>
          <Vacio icono="recorrido" titulo="Todavía no hay recorridos">
            Inicia uno desde <a href={enlace('recorrido')}>Recorrido</a>. Los hallazgos aparecerán aquí a medida que
            el robot los registre.
          </Vacio>
        </Tarjeta>
      ) : (
        <>
          <section className="sb-kpis">
            <Kpi
              icono="imagen"
              etiqueta="Capturas"
              valor={actual?.capturas ?? '–'}
              nota={actual ? `Recorrido del ${formatoFecha(actual.inicio)}` : 'Cargando…'}
            />
            <Kpi
              icono="zonas"
              etiqueta="Zonas observadas"
              valor={observadas}
              nota={`de ${zonas.length} zonas · ${plural(hileras, 'hilera')}`}
            />
            <Kpi
              icono="danger"
              etiqueta="Zonas por revisar"
              valor={porRevisar.length}
              nota={`${conteo.revisar_follaje} por follaje · ${conteo.revisar_maleza} por maleza`}
              alerta={porRevisar.length > 0}
            />
            <Kpi icono="fruto" etiqueta="Frutos detectados" valor={verdes + maduros} nota={`${verdes} verdes · ${maduros} maduros`} />
          </section>

          <div className="sb-row">
            <div className="sb-col">
              <Tarjeta
                titulo="Estado del cultivo"
                extra={<p className="sb-muted">{conteo.sin_alertas} de {zonas.length} zonas sin alertas registradas</p>}
              >
                <BarraEstados conteo={conteo} />
              </Tarjeta>

              <Tarjeta
                titulo="Zonas por revisar"
                extra={<p className="sb-muted">De la más urgente a la menos</p>}
                pie={
                  mapa.datos?.capturas_sin_zona
                    ? `${sinZona(mapa.datos.capturas_sin_zona)} y no se cuentan en el mapa.`
                    : 'Sin datos no significa sin problemas: revisa también las zonas no observadas.'
                }
              >
                {porRevisar.length ? (
                  <ZonasPorRevisar zonas={porRevisar} capturas={conHallazgos.datos ?? []} />
                ) : (
                  <Vacio icono="ok" titulo="No hay zonas con alertas registradas">
                    {observadas < zonas.length && `${zonas.length - observadas} zonas no tienen datos en este recorrido.`}
                  </Vacio>
                )}
              </Tarjeta>
            </div>

            <div className="sb-col sb-aside">
              <Tarjeta
                titulo="Recorrido"
                extra={actual && <Insignia {...ESTADOS_RECORRIDO[actual.estado]} />}
              >
                <dl>
                  <div className="sb-dl-row"><dt>Inicio</dt><dd>{actual ? new Date(actual.inicio).toLocaleString('es-CL') : '–'}</dd></div>
                  <div className="sb-dl-row"><dt>Modelo</dt><dd>{actual?.modelo ? `${actual.modelo} ${actual.modelo_version}` : 'Sin registrar'}</dd></div>
                </dl>
                <a className="sb-btn sb-btn--secondary sb-btn--block" style={{ marginTop: 'var(--space-4)' }} href={enlace('recorrido')}>
                  Ir a recorrido
                </a>
              </Tarjeta>
              <Tarjeta titulo="Últimas capturas" pie="Se actualiza cada 5 segundos.">
                {recientes.datos?.length ? <ListaCapturas capturas={recientes.datos} /> : <Vacio titulo="Sin capturas todavía" />}
              </Tarjeta>
            </div>
          </div>
        </>
      )}
    </main>
  )
}
