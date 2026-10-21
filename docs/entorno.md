# Entornos de trabajo: SDK2 y ROS 2 por separado

**Sistema de monitoreo terrestre preventivo del cultivo de tomate Sabueso.** Documento de la tarea F2.4 de [`fases/plan_conectividad_y_entorno.md`](../fases/plan_conectividad_y_entorno.md). Complementa la [guía de VirtualBox](guia_virtualbox_robot.md) y el [manual de instalación](manual_instalacion.md).

**Convención:** los datos marcados como **por verificar** no se han confirmado en el robot del proyecto ni en la VM del operador. Ningún comando de este documento se ejecutó contra el robot. Las referencias entre corchetes ([U2], [P1], [R1], [C4]) remiten a la sección 8 del plan; la sección 6 de este documento lista lo que falta comprobar.

---

## 1. Regla principal

**El software de Sabueso corre en una terminal con el entorno del SDK2 y sin ROS 2 cargado.** ROS 2 se usa solo en otra terminal, y solo para diagnóstico (`ros2 topic list`, RViz).

Motivos:

1. El SDK2 de Unitree y sus rutinas usan su propio CycloneDDS (versión 0.10.2) y, según Unitree, entran en conflicto con un entorno ROS 2 ya cargado en la misma terminal [U2]. La página de [U2] se genera con JavaScript y no se pudo extraer su texto de forma automática; la redacción exacta está **por verificar** en un navegador (sección 6).
2. `unitree_sdk2_python` exige `cyclonedds == 0.10.2` [P1], y la versión de CycloneDDS del robot es la 0.10.2 [R1].
3. El README de `unitree_ros2` pide compilar CycloneDDS con el entorno ROS 2 **sin** cargar, porque de lo contrario la compilación puede fallar [R1]. Es el mismo tipo de interferencia entre ambos mundos.
4. ROS 2 Humble ya trae su propio `rmw_cyclonedds_cpp`, por lo que en Humble no hace falta compilar CycloneDDS [R1]. En Foxy sí hay que compilarlo [R1].

`robot/sabueso_robot/conexion.py` repite esta advertencia en el docstring de `iniciar_dds`.

---

## 2. Los dos entornos

| | Entorno SDK2 (Sabueso) | Entorno ROS 2 (diagnóstico) |
| --- | --- | --- |
| Para qué sirve | `python -m sabueso_robot`, pruebas con el robot, scripts de `unitree_sdk2py` | `ros2 topic list`, `ros2 topic echo`, RViz, `ros2 doctor` |
| Dónde se usa | VM del operador y dock | VM del operador. En el dock, ROS 2 Foxy figura preinstalado [C4] (**por verificar**, V5) y no se usa |
| Base | `venv` de Python con `unitree_sdk2_python` y `cyclonedds` 0.10.2 [P1] | ROS 2 Humble en la VM (Ubuntu 22.04) [R1]; Foxy en el dock [C4] |
| Se carga con | `source ~/venvs/sabueso-sdk2/bin/activate` | `source /opt/ros/humble/setup.bash` |
| ROS 2 cargado | **No** | Sí |
| `RMW_IMPLEMENTATION` | No se define | `rmw_cyclonedds_cpp` [R1] |
| `CYCLONEDDS_HOME` | Solo al instalar el SDK desde fuentes (sección 3) | No se define |
| `CYCLONEDDS_URI` | Opcional (ver nota de la sección 3) | `file://…/config/cyclonedds.xml` en la VM |

El nombre `~/venvs/sabueso-sdk2` es una convención de este documento, no un requisito del SDK.

---

## 3. Variables de entorno

| Variable | Qué hace | Cuándo se define | Fuente |
| --- | --- | --- | --- |
| `CYCLONEDDS_HOME` | Ruta de instalación de CycloneDDS compilado desde fuentes (`~/cyclonedds/install`). Solo la necesita `pip install -e .` del SDK cuando no encuentra CycloneDDS (`Could not locate cyclonedds. Try to set CYCLONEDDS_HOME or CMAKE_PREFIX_PATH`) | Una vez, al instalar el SDK. No se deja exportada de forma permanente | [P1] |
| `CYCLONEDDS_URI` | Configuración de CycloneDDS: ruta `file://…` a un XML o el XML en línea. Unitree la usa para fijar la interfaz de red del robot (`NetworkInterface name="…"`) | Cada vez que se abre una terminal de ROS 2 que hable con el robot | [R1] |
| `RMW_IMPLEMENTATION` | Elige el middleware de ROS 2. Para hablar con el robot debe ser `rmw_cyclonedds_cpp` | Solo en la terminal de ROS 2 | [R1] |

**Nota sobre `CYCLONEDDS_URI` en el entorno SDK2.** `conexion.iniciar_dds(interfaz, dominio)` siempre llama a `ChannelFactoryInitialize(dominio, interfaz)` con el nombre de la interfaz. Los ejemplos del SDK hacen lo mismo [P1]. Al recibir la interfaz, el SDK probablemente construye su propia configuración y no lee `CYCLONEDDS_URI` (**por verificar** leyendo `unitree_sdk2py/core/channel.py` en F2.3). Mientras no se compruebe, la interfaz del SDK se define en `config/robot.yaml` (`interfaz_dds`), no en `CYCLONEDDS_URI`.

---

## 4. Interfaz de red: VM y dock

| Equipo | Interfaz | Dónde se configura | Estado |
| --- | --- | --- | --- |
| VM del operador | `enp0s8` (adaptador puente, 192.168.123.222/24) | `config/cyclonedds.xml` para ROS 2; `interfaz_dds` para el SDK | Habitual en VirtualBox; **por verificar** con `ip -br link` (V21) |
| Dock | `eth0` (192.168.123.18/24) | `config/robot.yaml` (`interfaz_dds: eth0`) | **Por verificar** con `ip -br addr` (V1) |

### 4.1. VM: `config/cyclonedds.xml`

La plantilla fija la interfaz `enp0s8`:

```xml
<NetworkInterface name="enp0s8" priority="default" multicast="default" />
```

Pasos:

1. Confirme el nombre real de la interfaz del puente: `ip -br link`. Si no se llama `enp0s8`, edite la línea `NetworkInterface name` en una copia del archivo.
2. En la terminal de **ROS 2**, desde la raíz del repositorio:

   ```bash
   source /opt/ros/humble/setup.bash
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   export CYCLONEDDS_URI=file://$PWD/config/cyclonedds.xml
   ros2 topic list        # deben aparecer /sportmodestate y /lowstate
   ```

3. En la terminal del **SDK2** no se carga nada de lo anterior. Si la VM usa otra interfaz que `eth0`, copie `config/robot.yaml`, cambie `interfaz_dds` y apunte `SABUESO_CONFIG` a la copia (variable que lee `robot/sabueso_robot/config.py`):

   ```bash
   cp config/robot.yaml ~/robot_vm.yaml        # editar interfaz_dds: enp0s8
   export SABUESO_CONFIG=~/robot_vm.yaml
   ```

Los temas `/sportmodestate` y `/lowstate` provienen de `unitree_ros2` [R1]. En el SDK2 los nombres equivalentes son `rt/sportmodestate` y `rt/lowstate` (`config/robot.yaml`; `rt/sportmodestate` está **por verificar** en el robot, porque algunos ejemplos usan `rt/sportstate`).

### 4.2. Dock: no sobrescribir su configuración

- El dock trae su propio `cyclonedds.xml` ligado a la interfaz con 192.168.123.18 (`/home/unitree/cyclonedds_ws/cyclonedds.xml` según [U2] y el plan; contenido **por verificar**, V6).
- **No copie `config/cyclonedds.xml` al dock.** La plantilla es para la PC o la VM.
- El software de Sabueso en el dock usa `interfaz_dds: eth0` de `config/robot.yaml`. Compruebe el nombre con `ip -br addr` antes de confiar en él (V1).
- Revise que el dock no cargue ROS 2 al abrir cada sesión: `grep -nE 'ros|cyclone' ~/.bashrc ~/.profile`. Si aparece un `source /opt/ros/…`, esa terminal ya no es un entorno SDK2 limpio (**por verificar**; es una práctica frecuente en imágenes con ROS 2, pero no se confirmó en este dock).

---

## 5. Terminales separadas

Abra una terminal por entorno y rotúlela. No use `source` de ROS 2 y `activate` del venv en la misma terminal.

**Terminal A: SDK2 (software de Sabueso).** Para partir de un entorno limpio aunque la sesión haya heredado variables de ROS:

```bash
env -i HOME="$HOME" TERM="$TERM" PATH=/usr/local/bin:/usr/bin:/bin \
  bash --noprofile --norc
source ~/venvs/sabueso-sdk2/bin/activate
export SABUESO_CONFIG=~/robot_vm.yaml        # solo en la VM; en el dock se usa config/robot.yaml
```

**Terminal B: ROS 2 (diagnóstico).**

```bash
source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$HOME/sabueso/config/cyclonedds.xml    # ajuste la ruta del repositorio
```

Reglas:

1. No agregue `source /opt/ros/…` a `~/.bashrc` ni a `~/.profile`, en la VM ni en el dock.
2. No instale `unitree_sdk2_python` en el Python del sistema: use el `venv` (sección 2).
3. Si abrió por error una terminal con ROS 2 cargado, ciérrela y abra otra. No intente limpiar variables a mano.

---

## 6. Comprobaciones

### 6.1. Terminal A (SDK2): debe estar limpia

| Comprobación | Resultado esperado |
| --- | --- |
| `env \| grep -E 'ROS\|AMENT\|COLCON\|RMW'` | Sin salida |
| `echo "$LD_LIBRARY_PATH"` | Sin rutas de `/opt/ros/` (**por verificar**: el `setup.bash` de ROS 2 suele agregarlas) |
| `pip show cyclonedds \| grep -i '^version'` | `Version: 0.10.2` [P1] |
| `python -c "import unitree_sdk2py"` | Sin error (tarea F2.1/F2.2) |
| `python -m sabueso_robot diagnostico` | Informe sin fallas (subcomando previsto; opciones **por verificar** con `--help`) |

### 6.2. Terminal B (ROS 2)

| Comprobación | Resultado esperado |
| --- | --- |
| `printenv RMW_IMPLEMENTATION` | `rmw_cyclonedds_cpp` |
| `printenv CYCLONEDDS_URI` | `file://…/config/cyclonedds.xml` con la ruta correcta |
| `ip -br addr show enp0s8` | `192.168.123.222/24` |
| `ros2 topic list` | Aparecen `/sportmodestate` y `/lowstate` ([R1]; descubrimiento a través del puente **por verificar**, V22) |

### 6.3. Si la IP responde pero no hay mensajes DDS

Siga el orden de la sección 7 de la [guía de VirtualBox](guia_virtualbox_robot.md): `RMW_IMPLEMENTATION`, nombre de la interfaz en `CYCLONEDDS_URI`, ausencia de ROS 2 en la terminal del SDK2 y adaptador 2 en modo puente sobre la NIC correcta.

| Síntoma | Causa probable | Qué hacer |
| --- | --- | --- |
| `Could not locate cyclonedds` al instalar el SDK | Falta `CYCLONEDDS_HOME` [P1] | Compilar CycloneDDS `releases/0.10.x`, exportar `CYCLONEDDS_HOME` solo para ese `pip install` |
| `ImportError` o fallo del enlazador al importar `cyclonedds` | Terminal con ROS 2 cargado o versión de CycloneDDS distinta de 0.10.2 | Abrir una terminal limpia (sección 5) y revisar `pip show cyclonedds` |
| `ros2 topic list` vacío con ping correcto | Interfaz equivocada en `CYCLONEDDS_URI` o RMW distinto | Corregir `NetworkInterface name` y `RMW_IMPLEMENTATION` |
| `iniciar_dds` lanza `RuntimeError: DDS ya iniciado …` | Se pidió otra interfaz o dominio en el mismo proceso | Usar una sola interfaz por proceso |

---

## 7. Pendientes por verificar

| # | Dato | Cómo verificarlo | Tarea |
| --- | --- | --- | --- |
| E1 | Texto exacto de la advertencia de Unitree sobre SDK2 y ROS 2 | Abrir [U2] en un navegador | F2.4 (revisión OR) |
| E2 | Si `ChannelFactoryInitialize(dominio, interfaz)` ignora `CYCLONEDDS_URI` | Leer `unitree_sdk2py/core/channel.py` del SDK instalado | F2.3 |
| E3 | Si el dock carga ROS 2 en `~/.bashrc` o `~/.profile` | `grep -nE 'ros\|cyclone' ~/.bashrc ~/.profile` en el dock | F0.1 |
| E4 | Nombres de interfaz del dock y de la VM | `ip -br addr` (dock, V1) e `ip -br link` (VM, V21) | F0.1, F1.0 |
| E5 | Contenido del `cyclonedds.xml` del dock | Lectura del archivo (V6) | F0.1 |
| E6 | Descubrimiento DDS a través del puente de VirtualBox | `ros2 topic list` o suscripción del SDK desde la VM (V22) | F2.3 |

---

## 8. Fuentes

- [U2] Unitree. *SLAM and Navigation Services Interface*. https://support.unitree.com/home/en/developer/SLAM%20and%20Navigation_service (consultada el 21/10/2026; el contenido es dinámico y no se recuperó en texto).
- [P1] unitreerobotics/unitree_sdk2_python, README (dependencias `cyclonedds == 0.10.2`, `CYCLONEDDS_HOME`, uso con nombre de interfaz). https://github.com/unitreerobotics/unitree_sdk2_python
- [R1] unitreerobotics/unitree_ros2, README (`setup.sh` con `RMW_IMPLEMENTATION` y `CYCLONEDDS_URI`, compilación sin ROS 2 cargado, Humble sin compilar CycloneDDS). https://github.com/unitreerobotics/unitree_ros2
- [C4] Robolegion. *Unitree Go2 EDU: JetPack 6.2.1 Update*. https://robolegion.com/unitree-go2-edu-jetpack-6-2-1-update/ (ROS 2 Foxy en la imagen de fábrica).
- Plan del proyecto: [`fases/plan_conectividad_y_entorno.md`](../fases/plan_conectividad_y_entorno.md), secciones 2.1, 3 y 7 (datos V1, V5, V6, V21, V22).
- Guía del proyecto: [`docs/guia_virtualbox_robot.md`](guia_virtualbox_robot.md), sección 7.
