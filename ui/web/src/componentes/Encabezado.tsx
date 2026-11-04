import type { ReactNode } from 'react'

export default function Encabezado({ titulo, sub, children }: { titulo: string; sub?: string; children?: ReactNode }) {
  return (
    <header className="sb-topbar">
      <div>
        <h1 className="sb-page-title">{titulo}</h1>
        {sub && <p className="sb-page-sub">{sub}</p>}
      </div>
      {children}
    </header>
  )
}
