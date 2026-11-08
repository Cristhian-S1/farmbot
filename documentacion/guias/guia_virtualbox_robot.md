# Guía: VM Ubuntu en VirtualBox para la red del Go2

Esta guía prepara el computador del operador (una VM Ubuntu 22.04 en VirtualBox) para conectarse al Go2 EDU por cable y compartirle internet. Corresponde a las tareas F1.0–F1.6 y a la sección 2.3 de [`../fases/plan_conectividad_y_entorno.md`](../fases/plan_conectividad_y_entorno.md).

El software del robot está en [`../../src/README.md`](../../src/README.md); esta guía solo cubre la red y la VM.

**Convención:** los comandos se ejecutan desde la raíz del repositorio. Los nombres `enp0s3` (NAT) y `enp0s8` (puente) son los habituales de VirtualBox; confírmelos con `ip -br link` antes de usarlos.

## 1. Preparar la VM (VirtualBox apagada)

1. Instale Ubuntu 22.04 LTS en la VM y luego las Guest Additions.
2. En **Configuración → Red**:
   - **Adaptador 1:** conectado a **NAT**. Será la salida a internet.
   - **Adaptador 2:** conectado a **Adaptador puente**, con nombre igual a la tarjeta **Ethernet** del anfitrión donde está el cable del robot (no la Wi-Fi). En *Avanzado*, elija modo promiscuo **Permitir todo** y deje marcado *Cable conectado*.
3. Equivalente por línea de comandos en el anfitrión (con la VM apagada):

   ```bash
   VBoxManage modifyvm "Ubuntu-Sabueso" --nic1 nat --nic2 bridged \
     --bridgeadapter2 "<nombre de la NIC Ethernet>" --nic-promisc2 allow-all
   ```

4. En Windows: no active "Conexión compartida a Internet" (ICS) en ningún adaptador y desactive la suspensión mientras trabaja con el robot. Si VirtualBox muestra el icono de tortuga verde, Hyper-V, WSL2 o la Integridad de memoria están activos y la VM funcionará más lenta.
5. Instale `chrony` en la VM para mantener la hora sincronizada con el dock (F1.7).

## 2. Red dentro de la VM

```bash
git clone <URL del repositorio> sabueso && cd sabueso
ip -br link                                   # identifique NAT (enp0s3) y puente (enp0s8)
sudo scripts/red/pc_configurar_interfaz_robot.sh --lan enp0s8
ping -c 5 192.168.123.18                      # dock
ping -c 5 192.168.123.161                     # control de movimiento
```

El script crea el perfil de NetworkManager `go2-lan` con la IP `192.168.123.222/24`, sin puerta de enlace y con `ipv4.never-default`, para que la ruta por defecto siga siendo la NAT.

## 3. Acceso por llave SSH (F1.2)

```bash
ssh-keygen -t ed25519 -C "sabueso-operador"
ssh-copy-id unitree@192.168.123.18            # pedirá las credenciales de SSH del robot
ssh -t unitree@192.168.123.18 passwd            # cambie la contraseña por defecto
```

Guarde la contraseña nueva en un gestor de contraseñas, nunca en el repositorio. Desactive el acceso por contraseña (`PasswordAuthentication no` en `/etc/ssh/sshd_config` del dock) solo después de comprobar que la llave funciona.

## 4. Internet para el dock (F1.3–F1.5)

```bash
# En la VM: NAT desde la red del robot hacia el adaptador NAT de VirtualBox
sudo apt install -y iptables-persistent
sudo scripts/red/pc_compartir_internet.sh --lan enp0s8 --wan enp0s3 --persistir

# En el dock: ruta por defecto hacia la VM y DNS explícito
scp scripts/red/dock_salida_internet.sh unitree@192.168.123.18:~/
ssh -t unitree@192.168.123.18 'sudo ~/dock_salida_internet.sh --gw 192.168.123.222'
```

El dock puede traer una puerta de enlace de fábrica (por ejemplo, `192.168.123.1`). Si se queda, compite con la ruta hacia la VM y puede ganar por métrica. El script la guarda en `/var/lib/sabueso/dock_salida_internet.gateway`, la retira y deja la ruta de la VM con métrica 700. Compruebe que la única ruta por defecto sea la de la VM:

```bash
ssh unitree@192.168.123.18 'ip route show default'
# default via 192.168.123.222 dev eth0 proto static metric 700
```

Si aparecen dos rutas por defecto, gana la de menor métrica y el dock puede quedarse sin internet aunque `ping 192.168.123.222` funcione.

Este mecanismo supone que `eth0` está gestionada por NetworkManager y que la puerta de fábrica está en `ipv4.gateway`. Si el dock la recibe por DHCP o la tiene en `ipv4.routes`, el script no puede retirarla: avisa, la verificación final falla y hay que corregir el perfil a mano (`nmcli -t -f DEVICE,STATE device`). Sin NetworkManager solo se aplica una ruta temporal, que no sobrevive al reinicio.

En el NAT de VirtualBox, `ping 8.8.8.8` puede fallar aunque `apt` y `git` funcionen. Compruebe con `getent hosts github.com` y `curl -I https://github.com`.

## 5. Verificación (F1.6)

```bash
scripts/red/verificar_red.sh --lan enp0s8 --ssh unitree@192.168.123.18
ping -c 100 192.168.123.18 | tail -1          # registre latencia y variación (V24)
```

Todas las pruebas deben decir `PASA`. Ejecútelo sin `sudo`: la comprobación de la regla MASQUERADE aparece como `OMITE` porque requiere root; puede verificarla aparte con `sudo iptables -t nat -S POSTROUTING`. El script comprueba la IP de la interfaz, las rutas, el ping al dock y al control, el DNS, el NAT y, con `--ssh`, que el dock tenga una única ruta por defecto vía `192.168.123.222` y DNS.

El script no prueba DDS porque el software actual (`src/`) usa HTTP. Si trabaja con `unitree_ros2`, compruebe aparte `ros2 topic list` con `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` y la interfaz `enp0s8`; si la IP funciona pero DDS no, revise primero el nombre de la interfaz y que no haya un entorno ROS cargado en la terminal del SDK.

## 6. Deshacer

```bash
sudo scripts/red/pc_compartir_internet.sh --lan enp0s8 --wan enp0s3 --quitar
ssh -t unitree@192.168.123.18 'sudo ~/dock_salida_internet.sh --gw 192.168.123.222 --quitar'
```

El script del dock restaura la puerta de enlace de fábrica que guardó al aplicarlo. Como el script no guarda la métrica, si lo aplicó con una `--metrica` distinta de 700, use la misma al quitar para que retire la ruta correcta.

## 7. Compartir la VM con otro operador (OVA)

La ISO de Ubuntu no es la máquina virtual: el sistema, el usuario y las configuraciones viven en el disco virtual. Para entregar la VM completa, expórtela como servicio virtualizado (OVA).

1. Apague la VM por completo (nada de estado guardado ni snapshots pendientes) y vacíe la unidad óptica en **Configuración → Almacenamiento**.
2. En VirtualBox: **Archivo → Exportar servicio virtualizado…**. Seleccione la VM en **Virtual machines** y pulse **Siguiente**.
3. En **Format settings** configure:
   - **Format:** `Open Virtualization Format 1.0`.
   - **File:** `sabueso_operador.ova` (un solo archivo; `.ovf` genera varios).
   - **MAC Address Policy:** `Strip all network adapter MAC addresses`, para que la copia no choque con la original en la misma red.
   - **Write Manifest file:** marcado (verifica la integridad al importar).
   - **Include ISO image files:** desmarcado. La ISO solo sirve para reinstalar; el sistema ya está en el disco virtual.
4. En el equipo del otro operador: **Archivo → Importar servicio virtualizado…** y seleccione el `.ova`.
5. Tras importar, vuelva a elegir su tarjeta Ethernet en el **adaptador 2 (puente)**; el nombre del adaptador del anfitrión no viaja en el OVA. Compruebe que el perfil `go2-lan` siga activo:

   ```bash
   nmcli -t -f NAME,DEVICE connection show
   # si falta: sudo scripts/red/pc_configurar_interfaz_robot.sh --lan enp0s8
   ```

6. Verifique antes de arrancar:

   ```bash
   # En Windows, VBoxManage suele estar fuera del PATH:
   "/c/Program Files/Oracle/VirtualBox/VBoxManage.exe" import sabueso_operador.ova --dry-run
   ```

   `--dry-run` muestra lo que se creará, pero no valida los hashes del manifiesto; esa comprobación ocurre al importar.

No viajan en el OVA: carpetas compartidas, adaptadores solo-anfitrión, redirecciones de puertos del NAT, snapshots ni el Extension Pack del anfitrión. La IP `192.168.123.222/24` del invitado sí se conserva. Si la VM usa carpetas compartidas, quite sus líneas de `/etc/fstab` antes de exportar.

Antes de exportar, quite credenciales del invitado: llaves en `~/.ssh`, historial, tokens y contraseñas. Cambie la contraseña del usuario o cree uno nuevo para el colega.
