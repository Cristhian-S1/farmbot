import type { Nivel } from '../utilidades/estados'
import Icono from './Icono'
import './Insignia.css'

const ICONO: Record<Nivel, 'ok' | 'warn' | 'danger' | 'reloj' | 'vacio'> = {
  ok: 'ok',
  warn: 'warn',
  danger: 'danger',
  neutral: 'reloj',
  vacio: 'vacio',
}

/** Insignia de estado: siempre ícono más palabra, nunca solo color. */
export default function Insignia({ nivel, texto }: { nivel: Nivel; texto: string }) {
  return (
    <span className={`sb-badge sb-badge--${nivel}`}>
      <Icono nombre={ICONO[nivel]} />
      {texto}
    </span>
  )
}
