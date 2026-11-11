import type { EstadoRecorrido, EstadoZona, GrupoClase } from '../api/tipos'

/** Nivel visual compartido por insignias, mapa y leyendas. */
export type Nivel = 'ok' | 'warn' | 'danger' | 'neutral' | 'vacio'

/** `corto` es el texto para las celdas del mapa, donde el completo no cabe. */
export const ESTADOS_ZONA: Record<EstadoZona, { nivel: Nivel; texto: string; corto?: string }> = {
  sin_alertas: { nivel: 'ok', texto: 'Sin alertas registradas', corto: 'Sin alertas' },
  revisar_maleza: { nivel: 'warn', texto: 'Revisar maleza' },
  revisar_follaje: { nivel: 'danger', texto: 'Revisar follaje' },
  pendiente: { nivel: 'neutral', texto: 'Análisis pendiente' },
  sin_datos: { nivel: 'vacio', texto: 'Sin datos' },
}

/** Orden de la leyenda y de la barra de estados: de lo normal a lo que falta. */
export const ORDEN_ESTADOS: EstadoZona[] = ['sin_alertas', 'revisar_maleza', 'revisar_follaje', 'pendiente', 'sin_datos']

export const ESTADOS_RECORRIDO: Record<EstadoRecorrido, { nivel: Nivel; texto: string }> = {
  en_curso: { nivel: 'neutral', texto: 'En curso' },
  completado: { nivel: 'ok', texto: 'Completado' },
  incompleto: { nivel: 'warn', texto: 'Incompleto' },
  cancelado: { nivel: 'vacio', texto: 'Cancelado' },
}

/** Color de las cajas de detección según el grupo de la clase. */
export const NIVEL_GRUPO: Record<GrupoClase, 'ok' | 'warn' | 'danger' | 'neutral'> = {
  fruto: 'ok',
  maleza: 'warn',
  follaje: 'danger',
  otro: 'neutral',
}

export function esAlerta(estado: EstadoZona): boolean {
  return estado === 'revisar_maleza' || estado === 'revisar_follaje'
}
