import { useEffect, useState } from 'react'
import { CAMARA_URL } from './config'

const INTERVALO_MS = 1000

interface EstadoCamara {
  fps: number
  video: boolean
}

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
    <section className="en-vivo">
      <h2>En vivo</h2>
      {estado?.video ? (
        <>
          <img src={`${CAMARA_URL}/video?c=${conexion}`} alt="Video en vivo de la cámara frontal del robot" />
          <p className="nota">{estado.fps} FPS</p>
        </>
      ) : (
        <p className="sin-senal">
          {estado ? 'La transmisión está activa, pero la cámara no envía video.' : 'Sin transmisión del robot.'}
          {' '}En el robot: <code>cd ~/Workspace/farmbot/src && python3 -m transmision</code>
        </p>
      )}
    </section>
  )
}
