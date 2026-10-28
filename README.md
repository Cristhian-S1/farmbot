# Sabueso

Sistema de monitoreo preventivo del cultivo de tomate para el predio Pampa Concordia (Arica). Proyecto IV, 2026.

## Contenido

| Ruta | Contenido |
| --- | --- |
| `documentacion/` | Contexto del proyecto: requisitos, informes de etapa, rúbrica, diagramas y planificación del curso |
| `terrestre/` | [Robot terrestre Unitree Go2 EDU](terrestre/README.md) (nuestro equipo) |
| `aereo/` | Sistema aéreo (equipo aéreo) |
| `interfaz/` | Interfaz de usuario común a ambos sistemas |

## Desarrollo

El software del equipo terrestre está en [`terrestre/`](terrestre/README.md). Los comandos de ese equipo se ejecutan desde esa carpeta:

```bash
cd terrestre
python3 -m pytest
shellcheck scripts/red/*.sh scripts/robot/*.sh
```

## Seguridad

Todo movimiento de un robot debe pasar por un único módulo de seguridad, y las pruebas con movimiento requieren a un operador presente con el control remoto físico. No suba contraseñas ni llaves al repositorio.

## Seguimiento

Las tareas del plan están en Beads (`bd ready`, `bd list`), con el prefijo `sabueso`.
