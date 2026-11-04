import type { ReactNode } from 'react'
import Icono, { type NombreIcono } from './Icono'

export function Aviso({ tipo = 'error', children }: { tipo?: 'error' | 'info'; children: ReactNode }) {
  return (
    <div className={`sb-aviso sb-aviso--${tipo}`} role={tipo === 'error' ? 'alert' : 'status'}>
      <Icono nombre={tipo === 'error' ? 'danger' : 'reloj'} />
      <div>{children}</div>
    </div>
  )
}

export function Vacio({ icono = 'vacio', titulo, children }: { icono?: NombreIcono; titulo: string; children?: ReactNode }) {
  return (
    <div className="sb-vacio">
      <Icono nombre={icono} />
      <strong>{titulo}</strong>
      {children && <p>{children}</p>}
    </div>
  )
}
