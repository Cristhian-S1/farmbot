# Manual de instalación: de cero a «telemetría recibida»

**Sistema de monitoreo terrestre preventivo del cultivo de tomate Sabueso.** Documento de la tarea F2.6 de [`fases/plan_conectividad_y_entorno.md`](../fases/plan_conectividad_y_entorno.md). Es la base de la verificación de RFN7: «un tercero replica el despliegue con repositorio y manuales en menos de 4 horas» (Tabla 6 de [`fases/fase1_informe_etapa_1.md`](../fases/fase1_informe_etapa_1.md)).

**Estado:** borrador. Los scripts `scripts/robot/instalar_dock.sh` y `scripts/robot/desplegar.sh` y el comando `python -m sabueso_robot` están en desarrollo; los nombres de subcomandos y opciones de esta guía siguen el contrato previsto y están **por verificar** con `--help` cuando existan. Ningún paso se ejecutó todavía sobre el robot del proyecto.

**Convención:** los datos marcados como **por verificar** no se han confirmado. Los tiempos son **estimaciones** de planificación, no mediciones: la sección 3 tiene la tabla donde se registran los tiempos reales.

---

## 1. Alcance

**Meta:** que el computador del operador (VM con Ubuntu 22.04) reciba por DDS el estado del Go2 (`rt/sportmodestate` y `rt/lowstate`) a través del dock, con el software de Sabueso instalado en ambos equipos.

**Fuera de alcance:**

- Todo lo que mueva el robot. El subcomando `postura` (previsto) cambia la postura del robot y exige un operador presente con el control remoto físico en la mano, según la sección 4.4 del plan. **No forma parte de la prueba de RFN7.**
- Servidor de análisis visual y base de datos (decisión D1 abierta).
- Cambios de firmware o de JetPack (decisión D7).

**Qué necesita antes de empezar:**

| Elemento | Detalle |
| --- | --- |
| Robot | Go2 EDU encendido, con el dock conectado por cable RJ45 al computador. Las [reglas de arranque seguro](../fases/plan_conectividad_y_entorno.md) (sección 4.2 del plan) aplican aunque no se mueva el robot |
| Computador | Con VirtualBox y su Extension Pack opcional; Ethernet libre para el robot y otra conexión a internet. Anfitrión **por verificar** (V20) |
| Imagen | ISO de Ubuntu 22.04 LTS |
| Acceso | URL del repositorio (privado) y credenciales de SSH del robot. **No las escriba en el repositorio ni en este manual** |
| Tiempo | Unas 3 h 25 min estimadas, sin contar descargas lentas ni imprevistos (sección 3) |

---

## 2. Pasos

### Paso 1. Preparar la VM de VirtualBox (estimado: 45 min)

Siga la sección 1 de la [guía de VirtualBox](guia_virtualbox_robot.md):

1. Instale Ubuntu 22.04 en la VM y las Guest Additions.
2. Adaptador 1 en **NAT** y adaptador 2 en **puente** sobre la tarjeta Ethernet del cable del robot, con modo promiscuo «Permitir todo».

**Comprobación:** `ip -br link` muestra dos interfaces además de `lo` (habitualmente `enp0s3` y `enp0s8`; **por verificar**, V21). `getent hosts github.com` resuelve.

### Paso 2. Obtener el repositorio y probarlo sin robot (estimado: 10 min)

```bash
sudo apt update && sudo apt install -y git python3-pip python3-venv shellcheck
git clone <URL del repositorio> sabueso && cd sabueso
python3 -m pip install pytest PyYAML
python3 -m pytest
```

**Comprobación:** `pytest` termina sin fallas. Estas pruebas no usan el robot ni el SDK.

### Paso 3. Red entre la VM y el robot (estimado: 15 min)

Sección 2 de la [guía de VirtualBox](guia_virtualbox_robot.md):

```bash
ip -br link
sudo scripts/red/pc_configurar_interfaz_robot.sh --lan enp0s8
ping -c 5 192.168.123.18      # dock
ping -c 5 192.168.123.161     # control de movimiento
```

**Comprobación:** ambos `ping` sin pérdida. Si el nombre de la interfaz no es `enp0s8`, use el que muestre `ip -br link`.

### Paso 4. Acceso SSH por llave (estimado: 10 min)

Sección 3 de la [guía de VirtualBox](guia_virtualbox_robot.md): `ssh-keygen`, `ssh-copy-id unitree@192.168.123.18` (pedirá las credenciales de SSH del robot) y cambio de la contraseña por defecto. Guarde la contraseña nueva en un gestor de contraseñas.

**Comprobación:** `ssh unitree@192.168.123.18 hostname` entra sin pedir contraseña.

### Paso 5. Internet para el dock (estimado: 20 min)

Sección 4 de la [guía de VirtualBox](guia_virtualbox_robot.md):

```bash
sudo apt install -y iptables-persistent
sudo scripts/red/pc_compartir_internet.sh --lan enp0s8 --wan enp0s3 --persistir
scp scripts/red/dock_salida_internet.sh unitree@192.168.123.18:~/
ssh -t unitree@192.168.123.18 'sudo ~/dock_salida_internet.sh --gw 192.168.123.222'
```

**Comprobación:** desde el dock, `getent hosts github.com` resuelve y `sudo apt update` termina sin errores. En el NAT de VirtualBox, `ping 8.8.8.8` puede fallar aunque `apt` funcione.

### Paso 6. Verificar la red (estimado: 10 min)

```bash
sudo scripts/red/verificar_red.sh --lan enp0s8 --ssh unitree@192.168.123.18
```

**Comprobación:** todas las pruebas dicen `PASA`.

### Paso 7. Inventario del dock, solo lectura (estimado: 10 min; opcional para RFN7)

```bash
ssh unitree@192.168.123.18 'bash -s' < scripts/robot/inventario_robot.sh > docs/inventario_robot.md
```

Revise el archivo antes de subirlo: no debe contener contraseñas ni tokens. Resuelve varios datos **por verificar**, entre ellos la interfaz del dock (V1) y la versión de Python y de Ubuntu del dock (el contrato de módulos supone Ubuntu 20.04 con Python 3.8).

### Paso 8. Entorno SDK2 en la VM (estimado: 30 min)

Siga [`docs/entorno.md`](entorno.md): el entorno SDK2 no debe tener ROS 2 cargado.

```bash
python3 -m venv ~/venvs/sabueso-sdk2 && source ~/venvs/sabueso-sdk2/bin/activate
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git ~/unitree_sdk2_python
pip install -e ~/unitree_sdk2_python
pip install -e .[dev]          # desde la raíz del repositorio de Sabueso
```

Si `pip` falla con `Could not locate cyclonedds`, compile CycloneDDS `releases/0.10.x` y exporte `CYCLONEDDS_HOME` solo para esa instalación, como indica el README del SDK [P1] (plan, sección 8).

**Comprobación:** `python -c "import unitree_sdk2py"` sin error y `pip show cyclonedds` indica `0.10.2`.

### Paso 9. Desplegar el código en el dock (estimado: 10 min)

Desde la VM, en la raíz del repositorio. Solo copia archivos con `rsync`; no ejecuta nada en el dock:

```bash
scripts/robot/desplegar.sh --dry-run     # revise qué se copiará
scripts/robot/desplegar.sh               # destino por defecto unitree@192.168.123.18:~/sabueso
```

No copia `.git`, `.beads`, entornos virtuales ni `docs/inventario_robot.md`. No se copian contraseñas ni llaves.

**Comprobación:** `ssh unitree@192.168.123.18 ls ~/sabueso/robot/sabueso_robot`.

### Paso 10. Instalar el software en el dock (estimado: 30 min, la mayor parte es compilar CycloneDDS)

En el dock, en una terminal **sin ROS 2 cargado** (el script se niega a continuar si detecta `ROS_DISTRO` o `AMENT_PREFIX_PATH`):

```bash
ssh -t unitree@192.168.123.18
cd ~/sabueso
scripts/robot/instalar_dock.sh --con-apt   # la primera vez; después basta sin --con-apt
scripts/robot/instalar_dock.sh --solo-verificar
```

El script crea `~/sabueso/.venv`, compila CycloneDDS 0.10.2 en `~/cyclonedds/install` solo si no existe, instala `unitree_sdk2_python`, PyYAML, pytest y el paquete `sabueso_robot`. No modifica `cyclonedds.xml` ni la IP 192.168.123.18. El dock usa Python 3.8 según el contrato de módulos (**por verificar** con el inventario del paso 7).

**Comprobación:** `--solo-verificar` termina con `import unitree_sdk2py, sabueso_robot` correcto, y `~/sabueso/.venv/bin/python -m sabueso_robot --help` lista los subcomandos.

### Paso 11. Telemetría recibida (estimado: 15 min)

Con el robot encendido y de pie, en la terminal del entorno SDK2 (sin ROS 2):

```bash
export CYCLONEDDS_HOME=~/cyclonedds/install
~/sabueso/.venv/bin/python -m sabueso_robot diagnostico --segundos 60   # SDK, DDS, frecuencia y batería
~/sabueso/.venv/bin/python -m sabueso_robot telemetria --duracion 30    # estado cada segundo
```

Hágalo primero en el dock y después en la VM (con `SABUESO_CONFIG` apuntando a una copia de `config/robot.yaml` con `interfaz_dds: enp0s8`; ver [`docs/entorno.md`](entorno.md)).

**Criterio de «telemetría recibida»** (tarea F2.3): mensajes de `rt/sportmodestate` y `rt/lowstate` durante 60 s sin interrupciones, frecuencia medida y registrada, y porcentaje de batería legible. Si `rt/sportmodestate` no responde, pruebe `rt/sportstate` (algunos ejemplos usan ese nombre; **por verificar**).

### Pasos opcionales (fuera de la meta de RFN7)

- `python -m sabueso_robot captura-prueba`: captura de una imagen de la cámara frontal (tarea F2.5).
- `python -m sabueso_robot sincronizar`: envío de capturas al servidor. Sin servidor (D1 abierta), se espera que no haya a dónde enviar.
- `python -m sabueso_robot postura`: **mueve la postura del robot**. Solo con un operador presente y el control remoto físico en mano (plan, secciones 4.2 y 4.4).

---

## 3. Registro de tiempos

La columna «Estimado» es una **estimación**; no se ha medido. El responsable de la prueba anota las demás columnas con un cronómetro.

| Paso | Descripción | Estimado (min) | Real (min) | Dificultades o desvíos | Corrección propuesta al manual |
| --- | --- | ---: | ---: | --- | --- |
| 1 | Preparar la VM | 45 | | | |
| 2 | Repositorio y pruebas sin robot | 10 | | | |
| 3 | Red VM ↔ robot | 15 | | | |
| 4 | SSH por llave | 10 | | | |
| 5 | Internet para el dock | 20 | | | |
| 6 | Verificar la red | 10 | | | |
| 7 | Inventario del dock | 10 | | | |
| 8 | Entorno SDK2 en la VM | 30 | | | |
| 9 | Instalar el dock | 30 | | | |
| 10 | Desplegar el código | 10 | | | |
| 11 | Telemetría recibida | 15 | | | |
| | **Total** | **205 (3 h 25 min)** | | | |

**Datos de la prueba** (rellenar al ejecutarla):

| Campo | Valor |
| --- | --- |
| Fecha | |
| Persona que instala (no debe haber participado en el desarrollo) | |
| Versión del repositorio (`git rev-parse --short HEAD`) | |
| Anfitrión y versión de VirtualBox (V20) | |
| Hora de inicio y de fin | |
| Tiempo total real | |
| Resultado frente a la meta de RFN7 (< 240 min) | |

**Protocolo propuesto** (por confirmar con el coordinador): el cronómetro arranca al abrir este manual con el ISO de Ubuntu ya descargado y la URL del repositorio en mano; se detiene al cumplirse el criterio del paso 11. Las esperas por descargas se anotan aparte, y quien prueba no recibe ayuda más allá del manual. RFN7 no define estos límites en la Tabla 6, por lo que deben fijarse antes de la prueba.

---

## 4. Problemas frecuentes

| Síntoma | Qué revisar |
| --- | --- |
| `ping` al dock falla | Adaptador 2 en puente sobre la NIC correcta, cable conectado, IP de `enp0s8` (paso 3) |
| El dock no resuelve nombres | Que `pc_compartir_internet.sh` siga activo y que el dock tenga la ruta por defecto hacia 192.168.123.222 (paso 5) |
| `ImportError` de `cyclonedds` | Terminal con ROS 2 cargado o versión distinta de 0.10.2 ([`docs/entorno.md`](entorno.md)) |
| Hay IP pero no llegan mensajes DDS | Sección 7 de la [guía de VirtualBox](guia_virtualbox_robot.md) |
| El tiempo total supera 4 h | Anote qué paso se desvió en la sección 3 y proponga la corrección |

---

## 5. Fuentes

- [`fases/fase1_informe_etapa_1.md`](../fases/fase1_informe_etapa_1.md), Tabla 6 (RFN7).
- [`fases/plan_conectividad_y_entorno.md`](../fases/plan_conectividad_y_entorno.md): secciones 4.2, 4.4, 4.5 (meta de RFN7: < 4 h) y 7 (datos por verificar).
- [`docs/guia_virtualbox_robot.md`](guia_virtualbox_robot.md) y [`docs/entorno.md`](entorno.md).
- [`docs/contratos_modulos.md`](contratos_modulos.md): interfaces de los módulos y versión de Python (≥ 3.8).
- unitreerobotics/unitree_sdk2_python, README (instalación y `CYCLONEDDS_HOME`) [P1]. https://github.com/unitreerobotics/unitree_sdk2_python
