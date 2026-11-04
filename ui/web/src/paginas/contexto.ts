import type { Estructura, Recorrido } from '../api/tipos'

/** Lo que App entrega a cada página: estructura del invernadero y recorrido elegido. */
export interface PropsPagina {
  estructura: Estructura | null
  recorridos: Recorrido[]
  /** null = el último recorrido. */
  recorrido: string | null
  elegirRecorrido: (recorrido: string | null) => void
  recargarRecorridos: () => void
}

export function subtitulo(estructura: Estructura | null): string | undefined {
  return estructura ? `${estructura.sector.nombre} · ${estructura.sector.predio}` : undefined
}
