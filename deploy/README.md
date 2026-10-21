# Despliegue de Sabueso en el dock

Esta carpeta contiene las unidades de **usuario** de systemd y las instrucciones
para dejar corriendo en el dock del Go2 la telemetría y la sincronización de
capturas. **Ninguna unidad mueve el robot**: solo ejecutan los subcomandos de
solo lectura `telemetria` y `sincronizar` de `python -m sabueso_robot`.

## Archivos

| Archivo | Qué hace |
| --- | --- |
| `systemd/sabueso-telemetria.service` | Ejecuta `python -m sabueso_robot telemetria --registrar` y guarda la telemetría en SQLite. |
| `systemd/sabueso-sincronizacion.service` | Ejecuta `python -m sabueso_robot sincronizar --continuo` para enviar las capturas pendientes. |

Ambas unidades usan `WorkingDirectory=%h/sabueso`, el intérprete
`%h/sabueso/.venv/bin/python`, `CYCLONEDDS_HOME=%h/cyclonedds/install` y
`SABUESO_CONFIG=%h/sabueso/config/robot.yaml`. `%h` es el directorio del usuario
que las ejecuta (`/home/unitree` en el dock).

## Requisitos previos

1. Copiar el repositorio desde la PC/VM:

   ```bash
   scripts/robot/desplegar.sh
   ```

2. Instalar el entorno **en el dock**, en una terminal sin ROS 2 cargado:

   ```bash
   ssh unitree@192.168.123.18
   ~/sabueso/scripts/robot/instalar_dock.sh --con-apt
   ```

3. Comprobar la configuración (`interfaz_dds`, `directorio_datos`) en
   `~/sabueso/config/robot.yaml`.

## Instalación de las unidades

En el dock, como usuario `unitree`:

```bash
mkdir -p ~/.config/systemd/user
cp ~/sabueso/deploy/systemd/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
loginctl enable-linger unitree
systemctl --user enable --now sabueso-telemetria.service
systemctl --user enable --now sabueso-sincronizacion.service
```

Las unidades de usuario se detienen al cerrar la sesión salvo que se habilite
*linger* para el usuario, por eso se habilita antes de arrancarlas. Si el
comando pide autenticación, use `sudo loginctl enable-linger unitree`.
Con *linger* activo, systemd mantiene las unidades aunque no haya sesión SSH
abierta, y también arrancan al iniciar el dock.

## Verificación

```bash
systemctl --user status sabueso-telemetria.service
systemctl --user status sabueso-sincronizacion.service
journalctl --user -u sabueso-telemetria -f
journalctl --user -u sabueso-sincronizacion -f
```

La telemetría registra en `~/sabueso_datos/telemetria.sqlite` (según
`directorio_datos`). La sincronización necesita `url_servidor` en
`config/robot.yaml` o la opción `--url`; mientras la decisión D1 siga abierta,
deje `sabueso-sincronizacion` deshabilitada para no repetir el error cada 5 s:

```bash
systemctl --user disable --now sabueso-sincronizacion.service
```

## Actualizar el despliegue

Desde la PC/VM:

```bash
scripts/robot/desplegar.sh
```

En el dock, si cambiaron las unidades o el código:

```bash
~/sabueso/scripts/robot/instalar_dock.sh
cp ~/sabueso/deploy/systemd/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user restart sabueso-telemetria.service
```

## Desinstalar

```bash
systemctl --user disable --now sabueso-telemetria.service sabueso-sincronizacion.service
rm ~/.config/systemd/user/sabueso-telemetria.service ~/.config/systemd/user/sabueso-sincronizacion.service
systemctl --user daemon-reload
```

## Notas de seguridad

- Las unidades no incluyen `postura` ni ningún otro comando que desplace al
  robot; esa orden exige una terminal interactiva, confirmación explícita y un
  operador con el control remoto (sección 4.4 del plan).
- No guarde tokens ni contraseñas en `config/robot.yaml` ni en las unidades.
