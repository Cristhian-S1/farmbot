import type { ReactNode } from 'react'

interface Props {
  titulo?: ReactNode
  /** Contenido a la derecha del título: leyenda, insignia o acción. */
  extra?: ReactNode
  pie?: ReactNode
  className?: string
  children: ReactNode
}

export default function Tarjeta({ titulo, extra, pie, className = '', children }: Props) {
  return (
    <section className={`sb-card ${className}`}>
      {(titulo || extra) && (
        <div className="sb-card-head">
          {titulo && <h2 className="sb-card-title">{titulo}</h2>}
          {extra}
        </div>
      )}
      {children}
      {pie && <p className="sb-card-foot">{pie}</p>}
    </section>
  )
}
