# Plan de conectividad y entorno de desarrollo del Go2 EDU

**Sistema de monitoreo terrestre preventivo del cultivo de tomate Sabueso**

**Autores:** Cristian Huanca y Cristhian Sanchez. **Asignatura:** Proyecto IV. **Fecha:** 21 de octubre de 2026.

**Estado de partida:** el computador del operador (un equipo distinto del usado para redactar este plan) se conecta al dock del robot por cable RJ45 y accede por SSH. En ese computador, Ubuntu se ejecuta como máquina virtual en VirtualBox (sección 2.3); el sistema operativo anfitrión está **por verificar**. Falta dar salida a internet al robot y dejar el entorno de desarrollo operativo. Este documento es un plan: ninguna medición de latencia, consumo o tiempo citada aquí fue ejecutada sobre el hardware del proyecto, salvo que se indique.

**Convención:** los datos marcados como **por verificar** no se han confirmado en el robot del proyecto y no deben tratarse como hechos. Las estimaciones de latencia y consumo son órdenes de magnitud para planificar, no resultados.

---

## 1. Resumen ejecutivo

**Situación.** El Go2 EDU tiene dos computadores en la red interna 192.168.123.0/24: el control de movimiento (192.168.123.161) y el dock de expansión Jetson (192.168.123.18), al que el equipo ya accede por SSH [U1, U2]. De fábrica, el dock no tiene Wi-Fi propio [C1, C2] y su red interna no tiene puerta de enlace hacia internet. Por eso hoy no puede ejecutar `apt`, `pip` ni `git clone`.

**Recomendación para el desarrollo (escenario A).** Se recomienda una PC con **Ubuntu 22.04** conectada por RJ45 que comparta su conexión con NAT (`ip_forward` + `MASQUERADE`) y deje la ruta por defecto y el DNS del dock apuntando a la PC. Linux es la opción preferente por tres razones con evidencia:

1. Unitree recomienda desarrollar en Ubuntu 20.04/22.04 e indica que Windows y Mac no tienen soporte [U1].
2. El ICS de Windows asigna 192.168.137.1/24 a la interfaz compartida [W1, W2]. Ese rango choca con la subred 192.168.123.0/24 obligatoria para hablar con el robot [U1], así que exige editar el registro o usar RRAS.
3. CycloneDDS, el SDK2 y `unitree_ros2` se configuran en Linux con el nombre de la interfaz conectada al robot [U1, R1, P1].

**Ubuntu virtualizado (VirtualBox).** Es viable y es la configuración que adopta el equipo, aunque no resulta igual de sencilla que Ubuntu nativo (sección 2.3). La VM necesita dos adaptadores: uno en **modo puente** sobre la tarjeta Ethernet conectada al robot (192.168.123.222/24, sin puerta de enlace) y otro en **NAT** hacia internet. Dentro de la VM, el NAT hacia el dock se hace igual que en un Ubuntu nativo. Con eso, el anfitrión Windows no necesita ICS. El costo son unos cuatro pasos extra de configuración, un doble NAT y algo más de latencia y variación. Nada de eso afecta al control de alto nivel que usa Sabueso.

**Recomendación para la operación autónoma (escenario B).** Se recomienda montar sobre el robot un **router de viaje con módem 4G/LTE**, conectado al segundo puerto RJ45 del dock (el dock tiene dos puertos Gigabit [U3]) y en una subred distinta de la 192.168.123.0/24. La alternativa de menor costo es un **adaptador USB Wi-Fi en el dock** en modo cliente, conectado a un hotspot de teléfono o a un punto de acceso del invernadero [C1, C2]. En ambos casos, el tráfico DDS de control se queda en la red cableada interna. Hacia fuera solo salen la telemetría resumida y las imágenes, por un protocolo tolerante a cortes. El módulo 4G del cuerpo del Go2 figura solo para las regiones CN/GB [U3], así que no se debe contar con él en Chile (**por verificar**).

**Entorno.** En el dock se mantiene la imagen de fábrica (JetPack 5.1.1, Ubuntu 20.04, ROS 2 Foxy [C3, C4]) y se instala `unitree_sdk2_python` con CycloneDDS 0.10.2 [P1]. En la PC: Ubuntu 22.04, ROS 2 Humble y el mismo SDK. La actualización a JetPack 6 queda como decisión pendiente (D7) porque tiene riesgo de dejar el dock sin arranque [C4].

**Seguridad.** Todo movimiento pasa por un módulo limitador: 0,5 m/s en pruebas y tope absoluto de 1 m/s (RFN5). Hay además un watchdog de comandos y paro de emergencia con el control remoto físico. Ninguna prueba de movimiento se ejecuta sin un operador con el control en la mano. Las decisiones de seguridad no se delegan a subagentes.

**Plan.** Son seis fases (F0–F5) y 35 tareas con identificador, dependencias y responsable. La meta inmediata es la entrega de la Parte 2 del 28 de octubre de 2026 [R0]: herramientas seleccionadas, repositorio en GitHub y alcance del producto. F0–F2 deben estar cerradas antes de esa fecha.

**Pendientes.** Hay diez decisiones abiertas (sección 5), con una recomendación cada una. Las más urgentes son D1 (arquitectura de comunicación), D2 (dónde se procesan las imágenes) y D3 (salida a internet en el invernadero).

---

## 2. Investigación de conectividad

### 2.1. Red del robot según la documentación oficial

| Elemento | Dato | Estado | Fuente |
| --- | --- | --- | --- |
| Computador de control de movimiento | 192.168.123.161 | Documentado; **por verificar** con `ping` | [U1, U2] |
| Dock de expansión (Jetson) | 192.168.123.18, usuario `unitree` | Documentado; confirmado por SSH por el equipo | [U2, U3] |
| LiDAR para SLAM del dock | 192.168.123.20 (MID-360/XT16) | Documentado; **por verificar** si el robot tiene ese LiDAR | [U2] |
| IP de la PC | Cualquier 192.168.123.x libre; Unitree sugiere .222; no usar .161 ni .18 | Documentado | [U1, C5] |
| Contraseña SSH | Credenciales de SSH del robot (contraseña por defecto publicada por Unitree) | Confirmado por el equipo; **debe cambiarse** | [U3] |
| Configuración DDS del dock | `/home/unitree/cyclonedds_ws/cyclonedds.xml`, ligada a la interfaz con .18 | Documentado; **por verificar** su contenido | [U2] |
| Interfaz cableada del dock | `eth0` según guías de terceros | **Por verificar** con `ip -br addr` | [C2, C6] |
| Wi-Fi del dock | Sin Wi-Fi de serie; requiere adaptador USB | Documentado por terceros; **por verificar** | [C1, C2] |
| Wi-Fi del cuerpo | Wi-Fi 6 doble banda, modos AP (192.168.12.1) y STA, configurable con la app | Documentado | [U3, U4, C7] |
| 4G del cuerpo | Módulo 4G con GPS solo en versiones CN/GB | Documentado; **por verificar** en este robot | [U3] |
| Imagen del dock | JetPack 5.1.1, Ubuntu 20.04, ROS 2 Foxy | Documentado; **por verificar** con `cat /etc/nv_tegra_release` | [U3, C3, C4] |

Hay dos matices entre fuentes. La guía rápida de Unitree dice que "no se soporta el desarrollo en el computador interno del Go2" [U1]. Ese computador es el de control de movimiento (.161), no el dock: la propia Unitree documenta servicios SLAM desplegados en el dock [U2]. Además, Unitree advierte que el SDK2 y sus rutinas usan su propio CycloneDDS y entran en conflicto con un entorno ROS 2 ya cargado en la misma terminal [U2]. Esto obliga a separar terminales o entornos (tarea F2.4).

### 2.2. Escenario A: PC conectada al robot por RJ45

Topología: internet → PC (Wi-Fi o segunda tarjeta) → cable RJ45 → dock (.18) ↔ control de movimiento (.161).

| Criterio | A1. Linux con NAT (iptables/nftables) | A2. Linux con NetworkManager "Compartida" | A3. Windows con ICS | A4. Túnel SOCKS por SSH (`ssh -R`) |
| --- | --- | --- | --- | --- |
| Requisitos | Ubuntu 22.04; IP fija 192.168.123.x en la NIC del robot; una segunda conexión con internet | Igual que A1 | Windows 10/11; dos adaptadores | Cualquier SO con cliente OpenSSH |
| Configuración | `sysctl net.ipv4.ip_forward=1`; `MASQUERADE` por la interfaz con internet; reglas `FORWARD`; en el dock, `ip route replace default via <IP PC>` y DNS explícito [C6, C8] | `ipv4.method shared` en el perfil cableado | Activar ICS en la conexión a internet | `ssh -R 1080 unitree@192.168.123.18`; `apt` y `pip` con proxy `socks5h://127.0.0.1:1080` [C1] |
| Compatibilidad con 192.168.123.0/24 | Total: la PC conserva su IP .123.x | Mala: NetworkManager asigna por defecto 10.42.0.1/24 y levanta un DHCP. Se puede fijar 192.168.123.x en `ipv4.addresses`, pero el DHCP en la red del robot es un riesgo (**por verificar**) | Mala: fuerza 192.168.137.1/24 [W1, W2]; cambiarlo exige editar el registro (`ScopeAddress`) o usar RRAS [W2] | Total: no cambia rutas |
| DNS | Configurar en el dock (`nmcli ... ipv4.dns`, `ignore-auto-dns yes`); con IP manual NetworkManager no lo rellena [C6] | Lo entrega el DHCP de NetworkManager | Lo entrega ICS | Resuelve el lado de la PC (`socks5h`) |
| Riesgos | Reglas no persistentes tras reinicio; equivocarse de interfaz; la ruta por defecto del dock queda "muerta" sin la PC | DHCP en la subred del robot; cambios de IP inesperados | Pérdida de comunicación con .161/.18 al cambiar la subred; sin soporte oficial de Unitree para desarrollar en Windows [U1] | Solo sirve a programas que aceptan proxy; Docker y `git` requieren configuración adicional |
| Latencia esperada | Enlace PC–dock < 1 ms; a internet, la del enlace de la PC + ~1 ms (estimación) | Igual que A1 | Igual que A1 | + sobrecarga de SSH (baja) |
| Consumo de datos | Lo que se instale: del orden de 1–5 GB para paquetes, SDK e imágenes Docker (estimación) | Igual | Igual | Igual |
| Campo (invernadero) | Sí, mientras la PC acompañe al robot con cable: sirve para instalar, no para patrullar | Igual | Igual | Igual |
| Verificado en documentación | Procedimiento descrito por terceros con el mismo .18 [C6, C8]; la subred obligatoria es oficial [U1] | Comportamiento de NetworkManager, no documentado por Unitree | Rango 192.168.137.0/24 oficial de Microsoft [W1] | Descrito por terceros [C1] |
| Probar en hardware | Nombres de interfaz, persistencia y DNS | Que el DHCP no interfiera con .161 | No se recomienda probar | Que `apt` y `pip` funcionen con el proxy |

**Por qué Linux es la mejor opción:**

1. Es la única plataforma de desarrollo soportada por Unitree para el SDK2 [U1].
2. El NAT de Linux permite conservar la IP 192.168.123.x de la PC, mientras que el ICS de Windows impone 192.168.137.1 [W1, W2].
3. CycloneDDS y `unitree_ros2` se ligan a la interfaz por nombre (`enp3s0`, `enxf8e4...`) en `CYCLONEDDS_URI` o en `ChannelFactoryInitialize(0, "<interfaz>")` [R1, P1]; en Windows esos nombres no existen.
4. Las herramientas de verificación (`ip`, `tcpdump`, `ros2 topic`, `nmcli`) son las mismas en la PC y en el dock.

**Recomendación A:** A1, con scripts idempotentes versionados en el repositorio (tareas F1.3–F1.5). A4 queda como respaldo cuando no se puedan cambiar las rutas del dock. Cuando Ubuntu corre en VirtualBox, A1 se ejecuta dentro de la VM con la topología de la sección 2.3.

### 2.3. Escenario A con Ubuntu virtualizado en VirtualBox

Topología: internet → anfitrión (Windows u otro SO, **por verificar**) → adaptador NAT de VirtualBox → VM Ubuntu 22.04 (NAT con `iptables`) → adaptador puente sobre la tarjeta Ethernet del anfitrión → cable RJ45 → dock (.18).

```text
Internet ─► Anfitrión ─► [Adaptador 1: NAT de VirtualBox] ─► enp0s3 (DHCP 10.0.2.15)
                                                               │  VM Ubuntu 22.04
                                                               │  ip_forward + MASQUERADE
Robot ◄── cable RJ45 ◄── [Adaptador 2: puente sobre la NIC Ethernet] ◄── enp0s8 (192.168.123.222/24)
```

**Configuración de la VM:**

| Elemento | Valor | Motivo |
| --- | --- | --- |
| Adaptador 1 | NAT (DHCP; puerta de enlace 10.0.2.2 de VirtualBox) | Única ruta por defecto de la VM, hacia internet |
| Adaptador 2 | Adaptador puente sobre la tarjeta **Ethernet** conectada al robot (no sobre el Wi-Fi) | Pone la VM en la misma red de capa 2 que el dock y el control de movimiento; el multicast DDS llega sin enrutamiento |
| Modo promiscuo del adaptador 2 | "Permitir todo" (`VBoxManage modifyvm "<VM>" --nic-promisc2 allow-all`) | No es indispensable para el tráfico dirigido a la VM, pero evita filtrados en el puente; la política existe en el modo puente [VB1] |
| Tipo de NIC | Intel PRO/1000 MT Desktop o `virtio-net` | Drivers incluidos en Ubuntu |
| IP en la VM | `enp0s8`: 192.168.123.222/24 manual, `ipv4.never-default yes`; `enp0s3`: DHCP | La red del robot nunca se convierte en ruta por defecto [C10] |
| Hora | Guest Additions + `chrony` | Las marcas de tiempo de captura dependen del reloj de la VM |
| Anfitrión Windows | ICS desactivado; el adaptador Ethernet conserva habilitado el "VirtualBox NDIS6 Bridged Networking Driver"; suspensión desactivada mientras se trabaja con el robot | Evita la subred 192.168.137.0/24 [W1] y los cortes del puente |

Los nombres `enp0s3` y `enp0s8` son los habituales de VirtualBox para los adaptadores 1 y 2, pero están **por verificar** en la VM del equipo (`ip -br link`).

**Comparación con Ubuntu nativo:**

| Criterio | Ubuntu nativo | Ubuntu en VirtualBox (puente + NAT) | Ubuntu en VirtualBox con USB-Ethernet pasado a la VM |
| --- | --- | --- | --- |
| Pasos de red | 1 perfil de IP fija + script NAT | Además: crear dos adaptadores, elegir la NIC correcta del puente, política promiscua y verificar nombres de interfaz | Instalar el Extension Pack (licencia PUEL, uso personal o educativo [VB2]), filtro USB y luego igual que nativo |
| Acceso a .18/.161 por SSH | Directo | Directo (misma red de capa 2) | Directo |
| Descubrimiento DDS (multicast) | Funciona [R1] | Funciona en guías de Go2 con VM de dos NIC (VMware) [C10]; en VirtualBox está **por verificar** con `ros2 topic list` | Equivalente a nativo |
| Internet para el dock | NAT de un salto | Doble NAT (VM y VirtualBox): funciona para TCP/UDP salientes; `ping` (ICMP) a internet puede fallar en el NAT de VirtualBox aunque `apt` funcione, así que se verifica con `getent` y `curl` | Doble NAT, igual |
| Latencia PC–robot | < 1 ms | + 0,1–1 ms y más variación con el anfitrión cargado (estimación, **por medir** con `ping -c 100`) | Cercana a nativo |
| Aptitud para el control de alto nivel (`SportClient`, 10–50 Hz) | Sí | Sí | Sí |
| Aptitud para el control de bajo nivel (500 Hz) | Sí, con cuidado | No se recomienda (variación del reloj y la planificación de la VM) | No se recomienda |
| Gráficos (RViz) | Aceleración nativa | Lento sin aceleración 3D; usar RViz en lo mínimo o Foxglove | Igual que la VM |
| Riesgos propios | — | Puente sobre la NIC equivocada; con Hyper-V, WSL2 o "Integridad de memoria" activos, VirtualBox funciona en modo lento (**por verificar** en el anfitrión); suspensión del anfitrión | Desconexión del USB; dependencia del Extension Pack |

**Veredicto.** Conectarse al robot desde Ubuntu en VirtualBox es **viable**, pero **no igual de sencillo** que desde Ubuntu nativo. Exige configurar dos adaptadores con roles fijos y verificar el descubrimiento DDS a través del puente. Una vez hecho, el procedimiento hacia el robot es idéntico (mismos scripts, misma IP, mismo `CYCLONEDDS_URI` con la interfaz puente). Sus limitaciones (doble NAT, algo más de latencia, gráficos lentos) no afectan al alcance de Sabueso, que usa control de alto nivel. Si el puente da problemas con DDS, la alternativa más cercana a nativo es pasar a la VM un adaptador USB-Ethernet dedicado.

**Procedimiento resumido (tareas F1.0–F1.5):**

1. Con la VM apagada, configurar el adaptador 1 en NAT y el adaptador 2 en puente sobre la NIC Ethernet conectada al robot, con política promiscua "Permitir todo".
2. Arrancar la VM y fijar la IP de la interfaz puente: `sudo scripts/red/pc_configurar_interfaz_robot.sh --lan enp0s8`.
3. Activar el NAT dentro de la VM: `sudo scripts/red/pc_compartir_internet.sh --lan enp0s8 --wan enp0s3`.
4. En el dock, por SSH: `sudo ./dock_salida_internet.sh --gw 192.168.123.222` (ruta por defecto y DNS).
5. Verificar desde la VM: `scripts/red/verificar_red.sh --lan enp0s8`.

### 2.4. Escenario B: robot autónomo, sin PC conectada por cable

En este escenario hay que separar dos redes:

- **Red de control** (DDS/SDK2 entre el dock y .161): cableada, interna, con multicast. No debe salir a internet.
- **Red de datos** (telemetría, imágenes y acceso remoto): sale por el enlace inalámbrico.

DDS usa descubrimiento multicast. Llevarlo por Wi-Fi o 4G degrada el descubrimiento o lo bloquea (operadores móviles y muchos puntos de acceso filtran multicast). Por eso no se recomienda: la red de datos usará HTTP/MQTT o un puente (decisión D1).

| Criterio | B1. Wi-Fi del cuerpo en STA (app Unitree) | B2. Wi-Fi del cuerpo en AP (192.168.12.1) | B3. Adaptador USB Wi-Fi en el dock (cliente) + AP del invernadero o hotspot de teléfono | B4. Router de viaje 4G/LTE sobre el robot, por RJ45 al dock | B5. Módulo 4G del cuerpo |
| --- | --- | --- | --- | --- | --- |
| Requisitos | App Unitree Go; red Wi-Fi con internet | App Unitree Go | Adaptador con driver para Jetson (p. ej. RTL88x2BU [C2], TP-Link T2UB [C1]); red disponible | Router 4G compacto alimentado por USB o batería; SIM con datos; soporte mecánico | Versión CN/GB del robot y SIM compatible |
| Configuración | Emparejar por Bluetooth y elegir Wi-Fi [U4] | Elegir modo AP y contraseña [U4] | Compilar el driver; `nmcli dev wifi connect`; ruta por defecto por `wlan0` [C1, C2] | Router en otra subred (p. ej. 192.168.50.0/24) en el 2.º RJ45 del dock; dock con DHCP en esa interfaz y ruta por defecto hacia el router; eth0 queda en .123 | Desde la app [U4] |
| ¿Da internet al dock? | No directamente: conecta el control de movimiento (OTA, WebRTC) [U5]. Que el dock salga por ahí está **por verificar** y no se recomienda depender de ello | No | Sí | Sí | No directamente (igual que B1) |
| Restricciones de red | Expone el cuerpo a la red del predio; WebRTC hacia la nube de Unitree [U5] | Red aislada; útil solo para la app o WebRTC local | Con DHCP del AP, la IP de `wlan0` cambia; NAT del teléfono impide conexiones entrantes | NAT del operador (CGNAT) impide conexiones entrantes: acceso remoto con VPN saliente (p. ej. WireGuard o Tailscale); el router no debe dar DHCP en 192.168.123.0/24 | Igual que B4 |
| Riesgos | Interferencia co-canal: el manual pide no operar con Wi-Fi interferente [U4] | Solo alcance local | Driver fuera del árbol del kernel; se rompe al actualizar JetPack [C2]; sombra de radio en hileras densas | Peso, fijación y calor sobre el robot; el manual prohíbe rodar de costado con accesorios [U4]; cobertura celular variable | Probablemente no disponible en Chile |
| Latencia esperada | 2–20 ms en LAN (estimación) | 2–10 ms (estimación) | 2–20 ms LAN; 30–100 ms a internet vía teléfono 4G (estimación) | 30–100 ms típica en LTE; picos > 300 ms (estimación) | Igual que B4 |
| Consumo de datos | Bajo si solo se usa la app | Nulo hacia internet | Telemetría: < 10 MB/h. Imágenes: con 1 MB por JPEG, 200 zonas × 3 fotos ≈ 0,6 GB por recorrido sin comprimir (estimación); mitigación en D2 y D5 | Igual que B3 | Igual |
| Campo (invernadero de Pampa Concordia) | Solo si existe Wi-Fi en el predio (**por verificar**) | Sí, a corta distancia | Sí, si hay AP o un teléfono cerca; el teléfono puede acompañar al operador | Sí, si hay cobertura LTE dentro del invernadero (**por verificar**; la estructura atenúa la señal) | **Por verificar** |
| Verificado en documentación | Modos AP/STA oficiales [U4] | Oficial [U4]; IP .12.1 por terceros [C7] | Procedimiento de terceros sobre el mismo dock [C1, C2] | Puertos del dock oficiales [U3]; topología propuesta por el equipo | Restricción CN/GB oficial [U3] |
| Probar en hardware | Ruta desde el dock | — | Driver, alcance entre hileras y reconexión | Cobertura, consumo eléctrico y fijación | Si existe el módulo |

**Recomendación B:**

- **Piloto:** B3 (USB Wi-Fi en el dock) conectado a un AP o a un teléfono que acompaña al operador. Es barato y reversible.
- **Despliegue:** B4 (router 4G sobre el robot), si la prueba de cobertura F1.9 confirma señal en las hileras.
- **Siempre:** el robot guarda las capturas en local y sincroniza al recuperar conexión. Así se cumple CU1: "si falla la comunicación, se preserva la evidencia adquirida" (informe de la Parte 1, sección 2.6.1).

**Supervisión local.** B2 (AP del cuerpo) sirve para que el operador vea el robot con la app. No sustituye al control remoto físico como paro de emergencia.

---

## 3. Herramientas necesarias

Las versiones se verificaron en Context7 o en la documentación oficial al 21 de octubre de 2026. Cuando una versión depende del hardware, figura como **por verificar**.

### 3.1. Software en el robot (dock Jetson)

| Herramienta | Versión recomendada | Propósito en Sabueso | Obligatoria |
| --- | --- | --- | --- |
| JetPack / Ubuntu del dock | JetPack 5.1.1 con Ubuntu 20.04 (de fábrica) [U3, C4] | Sistema base; se mantiene hasta resolver D7 | Sí |
| `unitree_sdk2_python` | Rama `master` del repositorio oficial (último commit 21/09/2026); Python ≥ 3.8 [P1] | Movimiento de alto nivel (`SportClient`), evasión (`ObstaclesAvoidClient`), cámara frontal (`VideoClient`) y estados | Sí |
| CycloneDDS | 0.10.2 (exigido por el SDK y por `unitree_ros2` en Foxy) [P1, R1] | Middleware DDS del robot | Sí |
| `unitree_sdk2` (C++) | v2.0.2 (07/07/2025, última release en GitHub) | Solo si un módulo requiere C++ o control de bajo nivel | Opcional |
| ROS 2 Foxy + `unitree_ros2` | Foxy (preinstalado) [C4]; `unitree_ros2` rama `master` [R1] | Visualización y herramientas ROS; no obligatorio si se elige SDK2 directo (D1) | Opcional |
| Servicios Unitree del dock (SLAM, odometría) | Paquete de actualización vía `http://192.168.123.18` [U3] | RF1 (navegación LiDAR), solo con LiDAR MID-360/XT16 [U2] (**por verificar**) | Opcional; depende de D8 |
| Driver de cámara de profundidad (`librealsense`/`realsense-ros`) | Compatible con JetPack 5.1.1 (**por verificar**); hay reportes de fallos del nodo ROS 2 en Foxy [C9] | Captura RGB-D a altura del fruto (RF2) | Opcional; depende de D4 |
| OpenCV, NumPy | Las que instala el SDK (`opencv-python`, `numpy`) [P1] | Decodificar y guardar imágenes | Sí |
| SQLite 3 | La del sistema | Cola local de capturas y metadatos sin conexión | Sí |
| OpenSSH server, `chrony` | Del sistema | Acceso por llaves y hora sincronizada (las marcas de tiempo de captura dependen de ella) | Sí |
| Driver de adaptador USB Wi-Fi | Según adaptador (p. ej. RTL88x2BU) [C2] | Escenario B3 | Opcional |
| WireGuard o Tailscale | Del sistema / cliente oficial | Acceso remoto saliente detrás de CGNAT (B4) | Opcional |

### 3.2. Software en la PC

| Herramienta | Versión recomendada | Propósito | Obligatoria |
| --- | --- | --- | --- |
| Ubuntu | 22.04 LTS [U1, R1] | SO de desarrollo soportado | Sí |
| ROS 2 | Humble (recomendado por `unitree_ros2`; con Humble no hace falta compilar CycloneDDS) [R1] | Herramientas `ros2 topic`, RViz y pruebas de interoperabilidad | Sí si D1 = ROS 2; si no, recomendada |
| `ros-humble-rmw-cyclonedds-cpp` | Paquete de Humble [R1] | RMW compatible con el robot | Igual que ROS 2 |
| `unitree_sdk2_python` + CycloneDDS 0.10.2 | Igual que en el dock [P1] | Desarrollar y probar en la PC | Sí |
| Python | 3.10 (de Ubuntu 22.04) con `venv` | Entorno aislado | Sí |
| Herramientas de red | `iproute2`, `iptables`/`nftables`, `iptables-persistent`, `tcpdump`, `nmap`, `iperf3`, `mtr` | NAT, diagnóstico y medición de latencia y ancho de banda | Sí |
| Visualización | RViz2 (con ROS 2), `foxglove` (opcional) | Ver LiDAR, odometría y cámaras | Opcional |
| Docker | Estable de Docker Inc. | Reproducibilidad para RFN7 | Recomendado |
| VirtualBox | 7.2.x (rama vigente del manual [VB1]) + Guest Additions | Ejecutar Ubuntu 22.04 en el computador del operador (sección 2.3) | Sí, en el computador del equipo |
| VirtualBox Extension Pack | Misma versión que VirtualBox (licencia PUEL [VB2]) | Solo si se pasa un adaptador USB-Ethernet a la VM | Opcional |

### 3.3. Hardware complementario

| Elemento | Recomendación | Propósito | Obligatorio |
| --- | --- | --- | --- |
| Cable Ethernet Cat6 y adaptador USB-Ethernet para la PC | Gigabit | Escenario A; la guía oficial usa USB-Ethernet [U1] | Sí |
| Control remoto físico del Go2 | El incluido en EDU [U3] | Paro de emergencia y toma manual | Sí |
| Batería de larga duración | 15 000 mAh (2–4 h) [U3]; una segunda unidad si las misiones superan 1,5 h | Autonomía de patrullaje | Sí (una); segunda opcional |
| Cargador rápido | 33,6 V 9 A [U3] | Recarga entre recorridos | Recomendado |
| Adaptador USB Wi-Fi | Con driver Linux conocido para ARM64 (RTL88x2BU) [C2] | B3 | Opcional |
| Router de viaje 4G/LTE + SIM | Con alimentación USB, puertos LAN/WAN y bandas LTE de operadores chilenos (**por verificar**) | B4 | Opcional; depende de D3 |
| Antena externa LTE/Wi-Fi | Ganancia moderada, montaje en el soporte del dock | Mejorar la cobertura en el invernadero | Opcional |
| Adaptador USB-C a HDMI | Unitree recomienda UGREEN CM475 [U3] | Recuperar el dock si se pierde la red | Recomendado |
| Cámara de profundidad | Intel RealSense D435i (accesorio oficial) [U3] | Captura a altura del fruto (RF2), si la cámara frontal no basta (D4) | Opcional |
| Sensores de suelo | No aplica | La medición de suelo está fuera del alcance de la Parte 1 (sección 2.2.1) | No |
| Cómputo embebido adicional | No | El dock Orin (Nano 40 TOPS u NX 100 TOPS, **por verificar** cuál) basta para captura e inferencia ligera [U3] | No |

### 3.4. Desarrollo y control de versiones

| Herramienta | Uso | Obligatoria |
| --- | --- | --- |
| Git + GitHub | Exigido en la Parte 2 [R0]; repositorio con ramas por tarea y PR revisado | Sí |
| Beads (`bd`) | Seguimiento de tareas del plan (AGENTS.md) | Sí |
| `pytest` | Pruebas unitarias del limitador, del watchdog y de los metadatos | Sí |
| `ruff` | Estilo y errores comunes de Python | Recomendada |
| `shellcheck` | Revisar los scripts de red | Recomendada |
| Orca ADE | Orquestación de subagentes (sección 6) | Sí, según el método acordado |

---

## 4. Plan de implementación por fases

**Seguimiento:** cada tarea y decisión está registrada en Beads como hija de la épica `sabueso-cjx`, con el identificador del plan al inicio del título (por ejemplo, `F1.3: …`). Use `bd ready` para ver las tareas desbloqueadas.

**Responsables sugeridos:** CH = Cristian Huanca; CS = Cristhian Sanchez. Agentes: OR = orquestador Opus 5.5; SO = Sonnet 5.5; CX = Codex GPT 6.1 Sol; OC = OpenCode DeepSeek v4.1 flash. Cuando una tarea toca el robot físico, el responsable humano ejecuta y el agente prepara.

### Fase F0. Inventario y línea base (antes del 23/10/2026)

| ID | Tarea | Depende de | Responsable | Criterio de aceptación |
| --- | --- | --- | --- | --- |
| F0.1 | Inventariar el robot por SSH, solo lectura: `ip -br addr`, `ip route`, `cat /etc/nv_tegra_release`, `lsb_release -a`, `nvidia-smi`/`tegrastats`, `lsusb`, contenido de `cyclonedds.xml`, versión de firmware del cuerpo en la app | — | CS (agente: CX) | Archivo `docs/inventario_robot.md` sin secretos, con cada dato **por verificar** de la sección 7 resuelto o justificado |
| F0.2 | Confirmar la variante del dock (Orin Nano/NX), la cámara de profundidad y el LiDAR de navegación | F0.1 | CH | Tabla con número de serie de módulo, modelo de cámara y LiDAR |
| F0.3 | Respaldar la imagen del dock (o registrar el enlace a la imagen de fábrica [U3]) antes de cualquier cambio | F0.1 | CS | Respaldo verificado (suma de comprobación) o decisión documentada de usar la imagen oficial |
| F0.4 | Crear el repositorio GitHub con la estructura de la sección 4.7 | — | CS (agente: OC) | Repositorio público o privado con README, licencia y estructura; enlace en el informe de la Parte 2 |

### Fase F1. Red y acceso seguro

| ID | Tarea | Depende de | Responsable | Criterio de aceptación |
| --- | --- | --- | --- | --- |
| F1.0 | Preparar la VM Ubuntu 22.04 en VirtualBox: adaptador 1 en NAT, adaptador 2 en puente sobre la NIC Ethernet del robot, política promiscua "Permitir todo", Guest Additions (sección 2.3) | — | CS | `ip -br link` muestra dos interfaces; `enp0s3` obtiene DHCP y sale a internet (`getent hosts github.com`) |
| F1.1 | Fijar la IP de la interfaz puente de la VM en 192.168.123.222/24 con `scripts/red/pc_configurar_interfaz_robot.sh` (perfil `go2-lan`, sin puerta de enlace, `never-default`) | F1.0, F0.1 | CS | `ping -c 20 192.168.123.18` y `.161` con 0 % de pérdida y RTT medio < 2 ms |
| F1.2 | Llaves SSH: `ssh-keygen -t ed25519`, `ssh-copy-id`, cambiar la contraseña por defecto, y luego `PasswordAuthentication no` | F1.1 | CS | Login sin contraseña; intento con contraseña rechazado; contraseña nueva guardada fuera del repositorio |
| F1.3 | Script `scripts/red/pc_compartir_internet.sh` (NAT idempotente con interfaces como parámetros, modo `--quitar`) | F1.1 | CX → revisa CS | `shellcheck` sin errores; ejecutar dos veces no duplica reglas; `--quitar` restaura el estado |
| F1.4 | Script `scripts/red/dock_salida_internet.sh` (ruta por defecto vía PC y DNS con `nmcli`, sin tocar la IP .18 ni `cyclonedds.xml`) | F1.3 | CX → revisa CS | Desde el dock: `ping 1.1.1.1`, `getent hosts github.com` y `apt update` correctos |
| F1.5 | Persistencia: `iptables-persistent` en la PC; en el dock, perfil NetworkManager con ruta de métrica alta | F1.4 | CS | Tras reiniciar PC y dock, F1.4 sigue pasando sin intervención |
| F1.6 | Script `scripts/red/verificar_red.sh` (ping, DNS, rutas, `ros2 topic list` opcional; salida PASA/FALLA) | F1.4 | OC → revisa CX | Detecta una ruta faltante o un DNS vacío provocados a propósito |
| F1.7 | Sincronizar la hora del dock (`chrony` contra la PC o NTP) | F1.4 | CS | Desfase < 100 ms respecto de la PC |
| F1.8 | Piloto B3: adaptador USB Wi-Fi en el dock, conexión a hotspot, ruta con métrica que no interfiera con eth0 | F1.5, D3 | CH (agente: CX) | El dock sale a internet sin la PC; DDS sigue en eth0 (`ros2 topic list` o SDK responden) |
| F1.9 | Prueba de cobertura en el invernadero (RSSI, `mtr`, `iperf3`) en las hileras del piloto | F1.8 | CH | Mapa simple con RSSI y latencia por hilera; insumo para D3 |

### Fase F2. SDK y entorno de desarrollo

| ID | Tarea | Depende de | Responsable | Criterio de aceptación |
| --- | --- | --- | --- | --- |
| F2.1 | PC: Ubuntu 22.04, ROS 2 Humble, `rmw_cyclonedds_cpp`, `venv` con `unitree_sdk2_python` y CycloneDDS 0.10.2 | F1.1 | CS (agente: CX) | `python -c "import unitree_sdk2py"` correcto; `ros2 doctor` sin errores críticos |
| F2.2 | Dock: CycloneDDS 0.10.2 y `unitree_sdk2_python` en un `venv` propio | F1.4 | CS (agente: CX) | Importación correcta en el dock |
| F2.3 | Prueba de solo lectura: suscribirse al estado del robot (`rt/sportmodestate`, `rt/lowstate`) desde la PC y desde el dock con `ChannelFactoryInitialize(0, "<interfaz>")` | F2.1, F2.2 | CS | 60 s de mensajes recibidos; frecuencia medida y registrada; batería legible |
| F2.4 | Documentar la separación de entornos SDK2 / ROS 2 (no cargar ROS en la terminal del SDK [U2]) | F2.3 | SO | Sección en `docs/entorno.md` revisada por OR |
| F2.5 | Captura de prueba con `VideoClient.GetImageSample()` y guardado con metadatos | F2.3 | CS | 10 imágenes JPEG válidas con marca de tiempo; tiempo medio por captura registrado |
| F2.6 | Manual de instalación reproducible (base para RFN7) | F2.1–F2.5 | SO → revisa OC (rutas y comandos) | Un integrante instala desde cero siguiendo solo el manual; tiempo registrado |

### Fase F3. Estructura de código y módulos base

| ID | Tarea | Depende de | Responsable | Criterio de aceptación |
| --- | --- | --- | --- | --- |
| F3.1 | Módulo `seguridad` (limitador de velocidad configurable, watchdog, estado de paro) con pruebas unitarias | F2.3 | CX → diseño y aprobación OR + CH | `pytest`: ningún comando sale con \|vx\| > límite; el watchdog emite `StopMove` si no hay comando en 300 ms |
| F3.2 | Módulo `telemetria` (estado, batería, temperatura; registro a SQLite) | F2.3 | CX | 10 min de registro sin pérdida > 1 %; consulta por intervalo |
| F3.3 | Módulo `captura` (cámara, metadatos hilera/zona/recorrido, cola local) | F2.5 | CX | Cada captura tiene ID único, hilera, zona y recorrido, o queda marcada "sin zona" (CU1) |
| F3.4 | Módulo `sincronizacion` (envío diferido de capturas y telemetría al servidor, reintentos) | F3.3, D1, D5 | CX | Cortar la red a mitad de un envío no pierde capturas; reanuda al reconectar |
| F3.5 | Módulo `movimiento` (comandos de alto nivel solo a través de `seguridad`) | F3.1 | CX → aprobación OR + CH | No existe en el código ninguna llamada a `SportClient.Move` fuera de `seguridad` (verificación con `grep` en CI) |
| F3.6 | Plantillas de configuración (`red.yaml`, `limites_seguridad.yaml`, `cyclonedds.xml`) | F3.1 | OC | Validan contra un esquema; sin secretos |

### Fase F4. Pruebas supervisadas en el robot

| ID | Tarea | Depende de | Responsable | Criterio de aceptación |
| --- | --- | --- | --- | --- |
| F4.1 | Prueba con el robot suspendido o echado: comandos de pie y echado, sin desplazamiento | F3.5 | CH + CS (presentes ambos) | Secuencia completa con el control remoto en mano; sin respuestas anómalas |
| F4.2 | Desplazamiento a 0,3 m/s en zona despejada de 5 m, con zona de exclusión marcada | F4.1 | CH + CS | Velocidad medida ≤ 0,3 m/s ± 10 %; `StopMove` por watchdog en < 0,5 s tras cortar comandos |
| F4.3 | Detención ante obstáculo (RFN5) con evasión activada y un obstáculo blando | F4.2 | CH + CS | Se detiene antes de 0,5 m en 10 de 10 intentos |
| F4.4 | Recorrido de una hilera de prueba con captura por zona y cola local | F4.3, F3.3 | CH + CS | Capturas de todas las zonas o incidencia explícita; sin zonas inventadas |
| F4.5 | Prueba de corte de enlace (B3 o B4) durante el recorrido | F4.4, F3.4 | CH | El robot sigue el protocolo de pérdida de enlace (D9); la evidencia se sincroniza después |

### Fase F5. Documentación y entrega

| ID | Tarea | Depende de | Responsable | Criterio de aceptación |
| --- | --- | --- | --- | --- |
| F5.1 | Incorporar herramientas, alcance y despliegue al informe de la Parte 2 | F2.6, D1–D5 | SO → revisa OR | Cubre los puntos 1, 2, 3 y 8 de la Parte 2 de la rúbrica |
| F5.2 | Diagrama de despliegue (PC, dock, control, router, servidor) en `fases/diagramas/` (HTML + SVG coherentes) | D1, D3 | SO (contenido) + OC (sintaxis SVG y enlaces) | Sin etiquetas recortadas; mismo contenido en HTML y SVG |
| F5.3 | Verificación de enlaces, rutas e imágenes de todos los documentos | F5.1, F5.2 | OC | Cero enlaces rotos o rutas inexistentes |
| F5.4 | Revisión cruzada final contra la rúbrica | F5.3 | SO + OR | Lista de verificación completa; observaciones cerradas |

### 4.1. Configuración de red de referencia

| Equipo | Interfaz | Dirección | Puerta de enlace | DNS |
| --- | --- | --- | --- | --- |
| PC (escenario A) | NIC al robot (nombre **por verificar**) | 192.168.123.222/24 | Ninguna en esta interfaz | El de su conexión a internet |
| VM Ubuntu (escenario A en VirtualBox) | `enp0s8`, adaptador puente (**por verificar**) | 192.168.123.222/24, `never-default` | Ninguna | — |
| VM Ubuntu (escenario A en VirtualBox) | `enp0s3`, adaptador NAT (**por verificar**) | DHCP (10.0.2.15) | 10.0.2.2 (VirtualBox) | El entregado por VirtualBox |
| Dock | eth0 (**por verificar**) | 192.168.123.18/24 (no cambiar) | 192.168.123.222, con métrica alta, solo en A | 1.1.1.1 y 8.8.8.8, explícitos |
| Dock (B3) | wlan0 o `wlx…` (**por verificar**) | DHCP del AP o teléfono | La del AP, con métrica menor que la ruta de A | La del AP o explícita |
| Dock (B4) | 2.º RJ45 (**por verificar**) | DHCP del router, subred ≠ 192.168.123.0/24 | Router 4G | El del router |
| Control de movimiento | Interna | 192.168.123.161 | No se modifica | — |

La regla de oro es no tocar la configuración de red ni el `cyclonedds.xml` del control de movimiento, y no levantar servidores DHCP en 192.168.123.0/24.

### 4.2. Procedimiento de arranque seguro

1. Revisar el entorno: zona despejada de al menos 2 m alrededor [U4], suelo firme y seco, temperatura entre 5 y 35 °C [U4], sin personas dentro de la zona de exclusión.
2. Revisar el robot: batería cargada (> 50 % para pruebas y > 80 % para recorridos), fijación del dock y de los accesorios, y patas libres.
3. Encender el control remoto, y después el robot con su secuencia de botones del manual [U4].
4. Esperar a que el robot se ponga de pie y estabilice. Comprobar con el control remoto que responde.
5. En la PC, ejecutar `scripts/red/verificar_red.sh`, que debe dar PASA.
6. Iniciar la telemetría (solo lectura) y confirmar batería y estado.
7. Iniciar la misión: el limitador queda configurado antes de habilitar `movimiento`.

### 4.3. Procedimiento de apagado seguro

1. Detener la misión (`StopMove`) y esperar a que se detenga por completo.
2. Echar el robot (`StandDown`) en suelo plano.
3. Detener los servicios de Sabueso en el dock y esperar a que termine la sincronización o quede encolada.
4. Apagar el dock de forma ordenada (`sudo shutdown -h now`) si se va a cortar la energía del robot. Si el dock se apaga junto con el robot, confirmar que no queden escrituras pendientes (**por verificar** el comportamiento de apagado del dock).
5. Apagar el robot con la secuencia del manual y luego el control remoto.
6. Retirar la batería para transporte o almacenamiento; cargar según el manual.

### 4.4. Consideraciones de seguridad

| Tema | Medida | Origen |
| --- | --- | --- |
| Velocidad límite | Pruebas: 0,3–0,5 m/s. Operación: tope absoluto de 1,0 m/s en `seguridad` (configurable solo hacia abajo). El Go2 EDU alcanza 3,7 m/s [U3], así que el límite por software es obligatorio | RFN5 |
| Detención ante obstáculos | Evasión del robot activada (`ObstaclesAvoidClient.SwitchSet(True)` [P1]) y además una regla propia: detenerse a < 0,5 m. La evasión oficial solo cubre el frente [U4]: no se permiten desplazamientos laterales o hacia atrás sin supervisión | RFN5; CU1 |
| Paro de emergencia | Primario: el control remoto físico en manos del operador, con su combinación de amortiguación o parada (**por verificar** en el manual). Secundario: watchdog que ordena `StopMove` sin comandos en 300 ms. Terciario: comando manual `StopMove` en la consola | — |
| Zonas de exclusión | Delimitar con cinta un área de prueba; nadie dentro de 2 m del robot en movimiento [U4]; en el invernadero, pasillos de prueba cerrados al personal durante el recorrido | Manual |
| Personas cercanas | El operador mantiene visión directa del robot [U4]; se detiene la misión si alguien entra en la zona; no se opera con niños ni visitantes cerca | Manual |
| Batería | No iniciar misiones con < 30 %; regreso o detención automática al 25 % (umbral **por verificar** en pruebas); cargar con el cargador oficial; no cargar sin supervisión; transportar sin la batería puesta | — |
| Accesorios | Con el dock montado, no ejecutar volteretas ni rodar de costado [U4] | Manual |
| Entorno del invernadero | Robot no impermeable ni a prueba de polvo [U4]: no operar sobre suelo recién regado ni con aspersión activa | Manual |
| Red | DDS solo en la red interna; acceso remoto solo por VPN con llaves; sin contraseña por defecto | — |
| Cambios de firmware | Ningún cambio de firmware ni de JetPack sin respaldo (F0.3) y decisión D7 | — |

### 4.5. Pruebas de verificación por fase (resumen)

| Fase | Prueba | Métrica de aceptación |
| --- | --- | --- |
| F1 | `verificar_red.sh`, en frío y tras reinicio | 100 % PASA; pérdida 0 % en 20 pings; DNS resuelve |
| F1 (B) | `iperf3` y `mtr` en hileras | Registro por hilera; umbral definido en D3 (propuesta: ≥ 2 Mbit/s de subida y < 150 ms medio) |
| F2 | Suscripción de estados | ≥ 60 s sin interrupciones; frecuencia registrada |
| F3 | `pytest` | 100 % de las pruebas de `seguridad` y `captura` pasan |
| F4 | Recorridos supervisados | Velocidad ≤ límite ± 10 %; detención antes de 0,5 m en 10/10 |
| F5 | Instalación desde el manual | Tiempo registrado; meta de RFN7: < 4 h |

### 4.6. Arquitectura lógica propuesta

```text
PC del operador / servidor         Dock Jetson (192.168.123.18)              Control de movimiento (.161)
┌──────────────────────┐   HTTP/   ┌─────────────────────────────────┐ DDS  ┌───────────────────────┐
│ S2 análisis visual   │◄─ MQTT ──►│ sincronizacion ◄─ cola local    │◄────►│ sport, videohub,      │
│ S3 registro (BD)     │ (red de   │ captura · telemetria            │(eth0)│ estado, evasión       │
│ S4 consulta web      │  datos)   │ movimiento ─► seguridad ────────┼─────►│                       │
└──────────────────────┘           └─────────────────────────────────┘      └───────────────────────┘
```

### 4.7. Estructura propuesta del código

```text
sabueso/
├── README.md
├── config/
│   ├── red.yaml                  # interfaces y direcciones (sin secretos)
│   ├── limites_seguridad.yaml    # velocidades, distancias, umbrales de batería
│   └── cyclonedds.xml            # plantilla ligada a la interfaz del robot
├── scripts/
│   └── red/
│       ├── pc_compartir_internet.sh
│       ├── dock_salida_internet.sh
│       └── verificar_red.sh
├── robot/                        # se ejecuta en el dock (S1)
│   └── sabueso_robot/
│       ├── conexion.py           # ChannelFactoryInitialize y selección de interfaz
│       ├── seguridad/            # limitador, watchdog y estado de paro (única puerta al movimiento)
│       ├── movimiento/           # primitivas: avanzar por hilera, girar, detener
│       ├── mision/               # recorrido por hileras y zonas; máquina de estados (Figura 4)
│       ├── telemetria/           # estado, batería, temperatura → SQLite
│       ├── captura/              # cámara frontal o D435i, metadatos hilera/zona/recorrido
│       └── sincronizacion/       # cola local y envío diferido con reintentos
├── servidor/                     # S2–S4; tecnologías según la Parte 2
│   ├── analisis/
│   ├── registro/
│   └── web/
├── tests/
│   ├── robot/                    # pruebas sin hardware (simulan clientes del SDK)
│   └── servidor/
└── docs/
    ├── inventario_robot.md
    ├── entorno.md
    └── manual_instalacion.md
```

Responsabilidades:

- `seguridad` es la única capa que llama a `SportClient`/`ObstaclesAvoidClient` para moverse.
- `mision` implementa los estados de la Figura 4 del informe de la Parte 1.
- `captura` nunca asigna una zona inventada; una captura sin zona se marca para revisión.
- `sincronizacion` hace que una misión con la red caída conserve la evidencia (CU1).

Las pruebas de `robot/` se ejecutan sin hardware sustituyendo los clientes del SDK por dobles de prueba.

---

## 5. Puntos por decidir

| ID | Decisión | Opciones | Recomendación | Plazo |
| --- | --- | --- | --- | --- |
| D1 | Arquitectura de comunicación robot–servidor | (a) SDK2 Python en el dock + HTTP/MQTT al servidor; (b) ROS 2 de punta a punta con DDS por la red de datos; (c) ROS 2 local + puente (Zenoh o `rosbridge`) | (a): menos piezas, no lleva multicast DDS por el enlace inalámbrico y evita el conflicto SDK2/ROS [U2]. ROS 2 queda para visualización | Parte 2 (28/10) |
| D2 | Dónde se procesan las imágenes | (a) En el dock (Orin); (b) en el servidor o PC; (c) mixto: filtrado y compresión en el dock, modelos en el servidor | (c): reduce el consumo de datos y no depende de la potencia del dock mientras se entrenan los modelos | Parte 2 |
| D3 | Salida a internet en el invernadero | B3 (USB Wi-Fi + AP/teléfono), B4 (router 4G), sin internet con descarga al volver | B3 en el piloto; B4 si F1.9 confirma cobertura; siempre con cola local | Tras F1.9 |
| D4 | Cámara de captura | (a) Cámara frontal (`VideoClient`); (b) D435i a la altura del fruto; (c) ambas | Empezar con (a) por simplicidad (F2.5); evaluar (b) si la altura o el encuadre no sirven para RF2 | Tras F2.5 |
| D5 | Almacenamiento de datos | (a) SQLite + archivos en el dock y PostgreSQL en el servidor; (b) solo archivos; (c) servicio en la nube | (a): coherente con la cola local y con RFN4 (consulta < 2 s con 200 zonas) | Parte 2 (punto 5 de la rúbrica) |
| D6 | Frecuencia de monitoreo | Diaria, dos por semana, semanal | Acordar con el cliente; proponer dos recorridos por semana en el piloto | Reunión con el cliente |
| D7 | Actualizar el dock a JetPack 6 / Ubuntu 22.04 / Humble | (a) Mantener JetPack 5.1.1; (b) actualizar [C4, C9] | (a) hasta la Parte 3: el reflasheo borra el dock, cambia el UEFI y no permite volver atrás fácilmente [C4]. Reevaluar solo si la D435i falla en Foxy | Después de F4 |
| D8 | Navegación entre hileras (RF1) | (a) SLAM y navegación oficial del dock (requiere MID-360/XT16) [U2]; (b) trayectorias guiadas con evasión de alto nivel; (c) navegación propia con LiDAR | Depende de F0.2: (a) si el LiDAR está presente; si no, (b) para el piloto | Tras F0.2 |
| D9 | Comportamiento ante pérdida de enlace | (a) Detenerse; (b) terminar la hilera en curso y detenerse; (c) continuar la misión | (a) mientras no exista navegación validada; revisar tras F4.5 | Antes de F4.5 |
| D10 | Responsables por subsistema | Asignación por subsistema S1–S4 | CS: S1 (robot, red y seguridad); CH: S2–S4 (análisis, registro y web); seguridad con aprobación de ambos | Esta semana |

---

## 6. Orquestación con Orca ADE

### 6.1. Roles

- **Orquestador (Opus 5.5).** Descompone el trabajo, asigna tareas, integra resultados y aprueba. Es el único que puede autorizar que un humano ejecute comandos de movimiento sobre el robot.
- **Sonnet 5.5.** Documentación, revisión contra la rúbrica, análisis de requisitos y razonamiento general.
- **Codex (GPT 6.1 Sol).** Código, scripts de red, pruebas automatizadas y depuración con acceso al repositorio.
- **OpenCode (DeepSeek v4.1 flash).** Plantillas, verificación de enlaces y rutas, sintaxis y barridos de documentación.

**Regla general:** ningún subagente ejecuta comandos de movimiento sobre el robot sin aprobación explícita del orquestador y sin un integrante presente con el control remoto. Los subagentes tampoco reciben las credenciales de SSH del robot: el acceso al hardware lo ejecutan CH o CS.

### 6.2. Asignación por subagente

| Subagente | Tareas | Entradas | Entregable | Criterio de aceptación | Revisión del orquestador |
| --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | F2.4, F2.6, F5.1, F5.2 (contenido), F5.4; borradores de D1–D10 para discusión | `fases/fase1_informe_etapa_1.md`, `fases/fase_0_problematica_requisitos.md`, `fases/rubrica_de_etapas_informes.md`, este plan; Context7 (`/unitreerobotics/unitree_ros2`, `/unitreerobotics/unitree_sdk2_python`); Exa (support.unitree.com) | Secciones Markdown en español, con fuentes y fechas | Cada afirmación técnica cita una fuente; se respeta la numeración existente; cumple los puntos de la rúbrica | Al terminar cada sección y antes de integrarla al informe |
| Codex (GPT 6.1 Sol) | F0.1 (guion de inventario de solo lectura), F1.3, F1.4, F1.8 (guion), F2.1, F2.2, F3.1–F3.5 | Este plan (secciones 4.1, 4.4 y 4.7); Context7 (`unitree_sdk2_python`, `unitree_ros2`, `unitree_sdk2`); Agent Reach con GitHub (issues de `unitreerobotics/*`) | Scripts y código con pruebas en una rama y PR | `pytest`, `shellcheck` y `ruff` sin errores; scripts idempotentes; ninguna llamada de movimiento fuera de `seguridad` | Revisión de cada PR; F3.1 y F3.5 exigen además aprobación de CH y CS |
| OpenCode (DeepSeek v4.1 flash) | F0.4 (estructura), F1.6, F3.6, F5.2 (sintaxis SVG), F5.3; barridos de Exa y Agent Reach para actualizar fuentes | Estructura de la sección 4.7; archivos de `fases/` y `fases/diagramas/`; lista de URLs de la sección 8 | Plantillas, informe de enlaces y rutas, lista de fuentes actualizadas con fecha | Cero enlaces rotos; plantillas válidas; sin secretos | Revisión por muestreo de cada entrega |

### 6.3. Validación cruzada (dos subagentes sobre el mismo resultado)

| Resultado | Produce | Valida | Motivo |
| --- | --- | --- | --- |
| Scripts de red (F1.3, F1.4) | Codex | Sonnet (lectura contra la sección 4.1) + CS en hardware | Un error de ruta deja al dock sin acceso |
| Módulo `seguridad` (F3.1) | Codex | Sonnet (revisión de requisitos contra RFN5 y 4.4) | Impacto físico |
| Manual de instalación (F2.6) | Sonnet | OpenCode (comandos y rutas) | RFN7 depende de que sea exacto |
| Tabla de herramientas y versiones | Sonnet | OpenCode (barrido de versiones con Context7 y GitHub) | Las versiones cambian |
| Diagrama de despliegue (F5.2) | Sonnet | OpenCode (coherencia HTML/SVG) | Convención del repositorio (AGENTS.md) |

### 6.4. Tareas que no se delegan

- Los límites de velocidad, las distancias de detención, los umbrales de batería y el protocolo de pérdida de enlace (D9).
- La autorización de cualquier prueba con movimiento (F4.1–F4.5).
- Los cambios de firmware o JetPack (D7) y la restauración de imágenes.
- El manejo de credenciales y llaves SSH.
- Los acuerdos con el cliente (D6) y la aprobación final de entregables.

Estas decisiones las toma el orquestador con CH y CS, y quedan registradas en Beads.

---

## 7. Datos marcados como por verificar

| # | Dato | Cómo verificarlo | Tarea |
| --- | --- | --- | --- |
| V1 | Nombre de la interfaz del dock en 192.168.123.0/24 (¿`eth0`?) | `ip -br addr` en el dock | F0.1 |
| V2 | Nombre de la interfaz de la PC conectada al robot | `ip -br addr` en la PC con el cable conectado | F1.1 |
| V3 | Variante del dock (Orin Nano 8 GB u Orin NX 16 GB) | `cat /proc/device-tree/model`, `tegrastats` | F0.2 |
| V4 | Versión de JetPack/L4T y de Ubuntu del dock | `cat /etc/nv_tegra_release`, `lsb_release -a` | F0.1 |
| V5 | ROS 2 instalado en el dock y su distribución | `ls /opt/ros` | F0.1 |
| V6 | Contenido actual de `/home/unitree/cyclonedds_ws/cyclonedds.xml` | Lectura del archivo | F0.1 |
| V7 | Versión de firmware del cuerpo del Go2 | App Unitree Go | F0.1 |
| V8 | Respuesta de 192.168.123.161 a `ping` | `ping` desde la PC | F1.1 |
| V9 | Presencia y modelo del LiDAR de navegación (MID-360/XT16) y su IP .20 | `ping 192.168.123.20`; inspección física | F0.2 |
| V10 | Presencia y modelo de la cámara de profundidad | `lsusb`, `rs-enumerate-devices` | F0.2 |
| V11 | Existencia del módulo 4G en el cuerpo y su uso en Chile | App (Ajustes → Red móvil) [U4] | F0.1 |
| V12 | Si el dock puede salir a internet por el Wi-Fi del cuerpo en modo STA | Prueba controlada de rutas | F1.8 |
| V13 | Wi-Fi disponible en el predio y cobertura LTE dentro del invernadero | Visita y medición (F1.9) | F1.9 |
| V14 | Combinación del control remoto para amortiguación o parada | Manual del usuario y prueba con el robot suspendido | F4.1 |
| V15 | Comportamiento del dock al apagar el robot (¿apagado abrupto?) | Prueba con escritura en curso | F4.1 |
| V16 | Compatibilidad de `librealsense` con JetPack 5.1.1 en este dock | Instalación de prueba | Tras D4 |
| V17 | Umbral de batería para retorno o detención | Medición de consumo en F4.4 | F4.4 |
| V18 | Bandas LTE del router propuesto frente a operadores locales | Ficha técnica del router | Tras D3 |
| V19 | Comportamiento de NetworkManager "Compartida" con IP 192.168.123.x (DHCP en la red del robot) | Prueba en la PC sin el robot conectado | Opcional |
| V20 | Sistema operativo anfitrión del computador del operador y versión de VirtualBox | Ayuda → Acerca de VirtualBox | F1.0 |
| V21 | Nombres de las interfaces NAT y puente dentro de la VM (`enp0s3`/`enp0s8`) | `ip -br link` en la VM | F1.0 |
| V22 | Descubrimiento DDS a través del adaptador puente de VirtualBox | `ros2 topic list` o suscripción del SDK desde la VM (F2.3) | F2.3 |
| V23 | Si Hyper-V, WSL2 o "Integridad de memoria" están activos en el anfitrión (VirtualBox en modo lento) | `systeminfo` en Windows o el icono de estado de la VM | F1.0 |
| V24 | Latencia y variación VM–dock frente a nativo | `ping -c 100 192.168.123.18` desde la VM | F1.1 |

---

## 8. Fuentes

Consultadas el 21 de octubre de 2026 con Exa, Context7 y GitHub (CLI `gh`, servido por Agent Reach). La documentación oficial de Unitree prevalece; las fuentes de terceros se usan para procedimientos que la documentación oficial no describe.

**Unitree (oficial)**

- [U1] Unitree. *Go2 SDK Development Guide: Quick Start*. https://support.unitree.com/home/en/developer/Quick_start (indexada el 20/09/2026).
- [U2] Unitree. *SLAM and Navigation Services Interface*. https://support.unitree.com/home/en/developer/SLAM%20and%20Navigation_service
- [U3] Unitree. *Go2 Product List* y *Module Update*. https://support.unitree.com/home/en/developer/about_Go2 ; https://support.unitree.com/home/en/developer/module_update (20/07/2026).
- [U4] Unitree. *Go2 User Manual V1.0*. https://static.generation-robots.com/media/Go2-User-Manual.pdf
- [U5] Unitree. *Architecture Description*. https://support.unitree.com/home/en/developer/Architecture%20Description

**Repositorios oficiales (Context7 y GitHub)**

- [P1] unitreerobotics/unitree_sdk2_python, README y referencia de API. Context7 `/unitreerobotics/unitree_sdk2_python`; último commit 21/09/2026.
- [R1] unitreerobotics/unitree_ros2, README y `setup.sh`. Context7 `/unitreerobotics/unitree_ros2`.
- unitreerobotics/unitree_sdk2, release v2.0.2 (07/07/2025).

**Microsoft**

- [W1] Microsoft. *Using Hosted Network and Internet Connection Sharing*. https://learn.microsoft.com/en-us/windows/win32/nativewifi/using-hosted-network-and-internet-connection-sharing
- [W2] Microsoft Q&A. *Internet Connection Sharing don't work if change IP*. https://learn.microsoft.com/en-us/answers/questions/2261381/internet-connection-sharing-dont-work-if-change-ip

**Terceros**

- [C1] todateman. *Unitree Go2 に USB Wi-Fi アダプタをセットアップ*. Qiita, 27/07/2025. https://qiita.com/todateman/items/aea5b12f1456308ed981
- [C2] TechShare. *Go2 Docking Station のインターネット接続方法*. https://techshare.co.jp/faq/unitree/go2_internet_access.html
- [C3] machines-in-motion. *Go2Py: System Setup*. https://github.com/machines-in-motion/Go2Py/blob/main/docs/setup.md
- [C4] Robolegion. *Unitree Go2 EDU: JetPack 6.2.1 Update*, 24/11/2025. https://robolegion.com/unitree-go2-edu-jetpack-6-2-1-update/
- [C5] TechShare. *Unitree Go2 外部PCからSDK or ROSを使う方法*. https://techshare.co.jp/faq/unitree/unitree-go2_pc_lan.html
- [C6] PreFure Wiki. *Go2 Jetson WiFi Network Setup*, 09/07/2026. https://www.prefure.com/docs/technology/Robotics/Unitree/go2_wifi_setup
- [C7] legion1581. *go2_webrtc_connect* / *unitree_webrtc_connect*. https://github.com/legion1581/go2_webrtc_connect
- [C8] lsqyrobot. *Unitree 拓展坞的网络共享与配置*, 05/01/2026. https://lsqyrobot.com/2026/01/05/archived_unitree_%E6%8B%93%E5%B1%95%E5%9D%9E%E7%9A%84%E7%BD%91%E7%BB%9C%E5%85%B1%E4%BA%AB%E5%8D%87%E7%BA%A7%E4%B8%8E%E9%85%8D%E7%BD%AE/
- [C9] AutoRoverLLC. *go2-ubuntu22-jetpack6-upgrade*. https://github.com/AutoRoverLLC/go2-ubuntu22-jetpack6-upgrade
- [C10] Darhan. *Unitree Go2 Multi-Floor Guide Navigation: VMware dual NIC* y *Verify and recover*. https://darhan7.github.io/go2-multifloor-guide-nav/network/vmware-dual-nic/

**VirtualBox**

- [VB1] Oracle. *VirtualBox 7.2 User Manual*, capítulo de redes virtuales (modo puente, NAT y políticas de modo promiscuo). https://www.virtualbox.org/manual/ ; resumen consultado en https://www.ucartz.com/clients/knowledgebase/1190/What-Is-Promiscuous-Mode-Enable-It-in-Linux-and-VirtualBox.html
- [VB2] Oracle. *VirtualBox Extension Pack Personal Use and Evaluation License (PUEL)*. https://www.virtualbox.org/wiki/VirtualBox_PUEL

**Proyecto**

- [R0] Rúbrica de etapas e informes de Proyecto IV (31/08/2026), `fases/rubrica_de_etapas_informes.md`.

**Contradicciones y matices entre fuentes**

1. Unitree dice que no se soporta el desarrollo "en el computador interno del Go2" [U1], pero despliega servicios en el dock [U2]. Se interpreta que la restricción se refiere al control de movimiento (.161).
2. Una fuente de terceros indica que el dock no necesita configurar la puerta de enlace al usar Wi-Fi USB [C2], mientras que con NAT por cable sí hace falta fijar la ruta por defecto y el DNS [C3, C6, C8]. Ambas son coherentes: depende de si la interfaz con internet usa DHCP.
3. La duración de la batería larga figura como 2–4 h en la tabla de producto y como 3–5 h en la tabla de baterías de la misma página [U3]. Para planificar se usa el valor conservador (2 h) hasta medirla (V17).
