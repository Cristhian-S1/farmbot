import Icono, { type NombreIcono } from './Icono'
import './Kpi.css'

interface Props {
  icono: NombreIcono
  etiqueta: string
  valor: string | number
  nota: string
  alerta?: boolean
}

export default function Kpi({ icono, etiqueta, valor, nota, alerta = false }: Props) {
  return (
    <div className="sb-card sb-kpi">
      <span className={`sb-kpi-icon${alerta ? ' sb-kpi-icon--danger' : ''}`}>
        <Icono nombre={icono} />
      </span>
      <div>
        <p className="sb-kpi-label">{etiqueta}</p>
        <p className="sb-kpi-value">{valor}</p>
        <p className="sb-kpi-note">{nota}</p>
      </div>
    </div>
  )
}
