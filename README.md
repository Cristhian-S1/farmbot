# Sabueso

Sistema de monitoreo preventivo del cultivo de tomate para el predio Pampa Concordia (Arica). Proyecto IV, 2026.

## Contenido

| Ruta | Contenido |
| --- | --- |
| `documentacion/` | Contexto del proyecto: requisitos, informes, rúbrica, diagramas y planificación; guías operativas en `guias/` |
| `src/` | Software del robot Unitree Go2 EDU y del procesamiento de datos |
| `ui/` | Interfaz de usuario (plataforma web de consulta) |
| `scripts/red/` | Red VM/PC ↔ robot: IP fija, NAT, salida a internet del dock y verificación |

## Red y VM

La [guía de VirtualBox](documentacion/guias/guia_virtualbox_robot.md) explica cómo preparar la VM Ubuntu, fijar la IP `192.168.123.222/24`, compartir internet con el dock y verificar la conexión. También incluye cómo exportar la VM como OVA para otro operador.

## Seguridad

Todo movimiento de un robot debe pasar por un único módulo de seguridad, y las pruebas con movimiento requieren a un operador presente con el control remoto físico. No suba contraseñas ni llaves al repositorio.

## Seguimiento

Las tareas del plan están en Beads (`bd ready`, `bd list`), con el prefijo `sabueso`.
