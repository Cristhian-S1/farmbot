import { useEffect, useState } from 'react'
import type { EstadoCamara } from '../../api/tipos'
import { Vacio } from '../../componentes/Aviso'
import Insignia from '../../componentes/Insignia'
import Tarjeta from '../../componentes/Tarjeta'
import { CAMARA_URL } from '../../config'
import './EnVivo.css'

const INTERVALO_MS = 1000

/** Video MJPEG de `python3 -m transmision` (puerto 8080 del dock). */
export default function EnVivo() {
  const [estado, setEstado] = useState<EstadoCamara | null>(null)
  // Cambia cuando vuelve el video, para que la imagen reabra la transmisión.
  const [conexion, setConexion] = useState(0)

  useEffect(() => {
    let activo = true
    let habiaVideo = false
    const consultar = () =>
      fetch(`${CAMARA_URL}/estado`)
        .then((r) => r.json() as Promise<EstadoCamara>)
        .then((datos) => {
          if (!activo) return
          if (datos.video && !habiaVideo) setConexion((n) => n + 1)
          habiaVideo = datos.video
          setEstado(datos)
        })
        .catch(() => {
          if (!activo) return
          habiaVideo = false
          setEstado(null)
        })

    consultar()
    const id = setInterval(consultar, INTERVALO_MS)
    return () => {
      activo = false
      clearInterval(id)
    }
  }, [])

  return (
    <Tarjeta
      titulo="En vivo"
      extra={
        estado?.video ? (
          <Insignia nivel="ok" texto={`${estado.fps} FPS`} />
        ) : (
          <Insignia nivel="vacio" texto="Sin señal" />
        )
      }
      pie="Cámara frontal del Go2."
    >
      {estado?.video ? (
        <img className="sb-video" src={`${CAMARA_URL}/video?c=${conexion}`} alt="Video en vivo de la cámara frontal del robot" />
      ) : (
        <Vacio icono="camara" titulo={estado ? 'La cámara no envía video' : 'Sin transmisión del robot'}>
          En el dock: <code>cd ~/Workspace/farmbot/src && python3 -m transmision</code>
        </Vacio>
      )}
    </Tarjeta>
  )
}
