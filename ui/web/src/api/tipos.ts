// Respuestas de la API Flask (ver ui/api/app.py y ui/api/almacenamiento.py).

export type EstadoZona = 'sin_datos' | 'pendiente' | 'revisar_maleza' | 'revisar_follaje' | 'sin_alertas'
export type EstadoRecorrido = 'en_curso' | 'completado' | 'incompleto' | 'cancelado'
export type GrupoClase = 'fruto' | 'maleza' | 'follaje' | 'otro'

export interface Clase {
  codigo: string
  nombre: string
  grupo: GrupoClase
}

export interface Estructura {
  sector: {
    id: number
    nombre: string
    predio: string
    hileras: { numero: number; zonas: { id: number; numero: number }[] }[]
  }
  clases: Clase[]
}

export interface Recorrido {
  id: string
  estado: EstadoRecorrido
  inicio: string
  fin: string | null
  iniciado_por: string | null
  modelo: string | null
  modelo_version: string | null
  capturas: number
  zonas: number
  sin_zona: number
  alertas: number
}

export interface ResumenZona {
  capturas: number
  pendientes: number
  sin_foto: number
  verdes: number
  maduros: number
  maleza: number
  follaje: number
  ultima_captura: string | null
}

export interface ZonaMapa extends ResumenZona {
  id: number
  hilera: number
  numero: number
  estado: EstadoZona
}

export interface Mapa {
  recorrido: string | null
  zonas: ZonaMapa[]
  capturas_sin_zona: number
}

export interface Deteccion {
  clase: string
  nombre: string
  grupo: GrupoClase
  confianza: number
  caja: [number, number, number, number]
}

export interface Captura {
  id: string
  recorrido_id: string
  zona_id: number | null
  hilera: number | null
  zona: number | null
  fecha: string
  foto: string | null
  analisis: 'pendiente' | 'listo' | 'error'
  detecciones: Deteccion[]
}

export interface Ficha {
  id: number
  hilera: number
  numero: number
  estado: EstadoZona
  resumen: ResumenZona
  recorrido: (Omit<Recorrido, 'capturas' | 'zonas' | 'sin_zona' | 'alertas'>) | null
  capturas: Captura[]
}

export interface RenglonHistorial extends ResumenZona {
  recorrido: string
  inicio: string
  estado_recorrido: EstadoRecorrido
  estado: EstadoZona
}

export interface EstadoControl {
  corriendo: boolean
  recorrido: string | null
  salida: string[]
}

export interface EstadoCamara {
  fps: number
  video: boolean
}
