# Sabueso

Sistema de monitoreo terrestre preventivo del cultivo de tomate con el robot Unitree Go2 EDU, para el predio Pampa Concordia (Arica). Proyecto IV, 2026.

## Contenido

| Ruta | Contenido |
| --- | --- |
| `fases/` | Requisitos, informes de etapa, rúbrica y el [plan de conectividad y entorno](fases/plan_conectividad_y_entorno.md) |
| `fases/diagramas/` | Diagramas HTML y SVG de los informes |
| `planeacion/` | Documento inicial y planificación del curso |
| `docs/` | Guías operativas: [conexión desde Ubuntu en VirtualBox](docs/guia_virtualbox_robot.md) |
| `scripts/red/` | Red PC/VM ↔ robot: IP fija, NAT, salida a internet del dock y verificación |
| `scripts/robot/` | Inventario de solo lectura del dock |
| `config/` | Plantillas de red, CycloneDDS y límites de seguridad (sin secretos) |
| `robot/sabueso_robot/` | Software del dock; hoy contiene el módulo `seguridad` (limitador, watchdog, paro) |
| `tests/` | Pruebas sin hardware (`pytest`) |

## Inicio rápido (computador del operador)

Siga [docs/guia_virtualbox_robot.md](docs/guia_virtualbox_robot.md). Pruebas locales:

```bash
python3 -m pip install pytest
python3 -m pytest
shellcheck scripts/red/*.sh scripts/robot/*.sh
```

## Seguridad

Ningún script de este repositorio mueve el robot. Todo movimiento debe pasar por `robot/sabueso_robot/seguridad`, y las pruebas con movimiento (fase F4) requieren a un operador presente con el control remoto físico. No suba contraseñas ni llaves al repositorio.

## Seguimiento

Las tareas del plan están en Beads (`bd ready`, `bd list`), con el prefijo `sabueso`.
