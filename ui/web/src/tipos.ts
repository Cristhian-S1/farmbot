// Registro tal como lo devuelve GET /api/registros (ver ui/api/almacenamiento.py).
export interface Registro {
  id: string
  recorrido: string
  fecha: string
  clase: string
  confianza: number
  caja: string
  hilera: string | null
  zona: string | null
  foto: string | null
}
