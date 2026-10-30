// Transmisión en vivo del robot (src/transmision). Por defecto, el mismo equipo
// que sirve la web en el puerto 8080; definir VITE_CAMARA_URL si el robot está en otro.
export const CAMARA_URL: string =
  import.meta.env.VITE_CAMARA_URL ?? `${window.location.protocol}//${window.location.hostname}:8080`
