import type { Recorrido } from '../api/tipos'
import { ESTADOS_RECORRIDO } from '../utilidades/estados'
import { formatoFechaHora } from '../utilidades/formato'
import Icono from './Icono'

interface Props {
  recorridos: Recorrido[]
  /** null = el último recorrido. */
  valor: string | null
  onCambiar: (recorrido: string | null) => void
}

export default function SelectorRecorrido({ recorridos, valor, onCambiar }: Props) {
  return (
    <label className="sb-field">
      <span className="sb-label">Recorrido</span>
      <span className="sb-input">
        <Icono nombre="calendario" />
        <select value={valor ?? ''} onChange={(e) => onCambiar(e.target.value || null)}>
          <option value="">Último recorrido</option>
          {recorridos.map((r) => (
            <option key={r.id} value={r.id}>
              {formatoFechaHora(r.inicio)} · {ESTADOS_RECORRIDO[r.estado].texto}
            </option>
          ))}
        </select>
      </span>
    </label>
  )
}
