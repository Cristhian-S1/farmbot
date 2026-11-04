// Íconos de trazo de 24 px, con el mismo estilo que los de Centinela.
const TRAZOS = {
  inicio: (
    <>
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5.5 10v9.5h13V10" />
      <path d="M10 19.5v-5h4v5" />
    </>
  ),
  zonas: (
    <>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
    </>
  ),
  recorrido: (
    <>
      <circle cx="6" cy="18" r="2.5" />
      <circle cx="18" cy="6" r="2.5" />
      <path d="M8.5 18H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h6.5" />
    </>
  ),
  historial: (
    <>
      <path d="M4 20h16" />
      <path d="M7 20v-6" />
      <path d="M12 20V6" />
      <path d="M17 20v-9" />
    </>
  ),
  calendario: (
    <>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
      <path d="M3.5 10h17" />
      <path d="M8 3v4" />
      <path d="M16 3v4" />
    </>
  ),
  imagen: (
    <>
      <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
      <circle cx="8.5" cy="9.5" r="1.5" />
      <path d="m4 17 5-5 4 4 3-3 4.5 4.5" />
    </>
  ),
  fruto: (
    <>
      <circle cx="12" cy="13.5" r="7" />
      <path d="M12 6.5V4" />
      <path d="M9 6.8c1-1.5 5-1.5 6 0" />
    </>
  ),
  ok: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8 12.2 2.8 2.8 5.2-5.6" />
    </>
  ),
  warn: (
    <>
      <path d="M12 4 21 19.5H3z" />
      <path d="M12 10v4.5" />
      <path d="M12 17v.01" />
    </>
  ),
  danger: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V13" />
      <path d="M12 16v.01" />
    </>
  ),
  reloj: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  vacio: (
    <>
      <circle cx="12" cy="12" r="8.5" strokeDasharray="3 3" />
      <path d="M8.5 12h7" />
    </>
  ),
  iniciar: <path d="M8 5.5v13l10.5-6.5z" />,
  detener: <rect x="6.5" y="6.5" width="11" height="11" rx="1.5" />,
  camara: (
    <>
      <rect x="3" y="7" width="13" height="11" rx="2" />
      <path d="m16 11 5-3v9l-5-3" />
    </>
  ),
  volver: <path d="M15 5.5 8.5 12l6.5 6.5" />,
}

export type NombreIcono = keyof typeof TRAZOS

export default function Icono({ nombre, className = '' }: { nombre: NombreIcono; className?: string }) {
  return (
    <svg className={`sb-icon ${className}`} viewBox="0 0 24 24" aria-hidden="true">
      {TRAZOS[nombre]}
    </svg>
  )
}
