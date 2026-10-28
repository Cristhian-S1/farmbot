# Sabueso — equipo terrestre

Software del robot terrestre Unitree Go2 EDU. El contexto del proyecto
(requisitos, informes, diagramas y planificación) está en
[`../documentacion/`](../documentacion/).

## Contenido

| Ruta | Contenido |
| --- | --- |
| `robot/sabueso_robot/` | Software del dock; `seguridad/` es la única puerta al movimiento |
| `scripts/red/` | Red VM/PC ↔ robot: IP fija, NAT, salida a internet y verificación |
| `scripts/robot/` | Inventario de solo lectura, instalación y despliegue en el dock |
| `config/` | Plantillas de red, CycloneDDS y límites de seguridad (sin secretos) |
| `docs/` | Guías de VirtualBox, instalación, entornos y revisión de seguridad |
| `tests/` | Pruebas sin hardware (`pytest`) |
| `deploy/` | Unidades systemd de usuario |

## Inicio rápido

Los comandos de este equipo se ejecutan desde `terrestre/`:

```bash
cd terrestre
python3 -m pytest
shellcheck scripts/red/*.sh scripts/robot/*.sh
```

Guía de conexión con el robot:
[`docs/guia_virtualbox_robot.md`](docs/guia_virtualbox_robot.md).
