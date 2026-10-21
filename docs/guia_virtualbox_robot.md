# Guía: conectar el Go2 EDU desde Ubuntu en VirtualBox

Esta guía es para el computador del operador, el que se conecta al robot por cable. Corresponde a las tareas F1.0–F1.6 y a la sección 2.3 de `fases/plan_conectividad_y_entorno.md`. Los nombres de interfaz `enp0s3` y `enp0s8` son los habituales de VirtualBox; confírmelos con `ip -br link` antes de usarlos.

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

4. En Windows: no active "Conexión compartida a Internet" (ICS) en ningún adaptador y desactive la suspensión mientras trabaja con el robot. Si VirtualBox muestra el icono de tortuga verde, Hyper-V está activo y la VM funcionará más lenta.

## 2. Red dentro de la VM

```bash
git clone <URL del repositorio> sabueso && cd sabueso
ip -br link                                   # identifique NAT (enp0s3) y puente (enp0s8)
sudo scripts/red/pc_configurar_interfaz_robot.sh --lan enp0s8
ping -c 5 192.168.123.18                      # dock
ping -c 5 192.168.123.161                     # control de movimiento
```

## 3. Acceso por llave SSH (F1.2)

```bash
ssh-keygen -t ed25519 -C "sabueso-operador"
ssh-copy-id unitree@192.168.123.18            # pedirá las credenciales de SSH del robot
ssh unitree@192.168.123.18 passwd             # cambie la contraseña por defecto
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

En el NAT de VirtualBox, `ping 8.8.8.8` puede fallar aunque `apt` y `git` funcionen. Compruebe con `getent hosts github.com` y `curl -I https://github.com`.

## 5. Verificación (F1.6)

```bash
sudo scripts/red/verificar_red.sh --lan enp0s8 --ssh unitree@192.168.123.18
ping -c 100 192.168.123.18 | tail -1          # registre latencia y variación (V24)
```

Todas las pruebas deben decir `PASA`.

## 6. Inventario del dock (F0.1, solo lectura)

```bash
ssh unitree@192.168.123.18 'bash -s' < scripts/robot/inventario_robot.sh > docs/inventario_robot.md
```

Revise el archivo antes de subirlo al repositorio: no debe contener contraseñas ni tokens.

## 7. DDS a través del puente (V22)

```bash
export CYCLONEDDS_URI=file://$PWD/config/cyclonedds.xml   # interfaz enp0s8
# Con unitree_ros2 (Humble):  ros2 topic list   → deben aparecer /sportmodestate y /lowstate
```

Si la IP funciona pero DDS no, revise en este orden:

1. `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`.
2. El nombre de la interfaz en `CYCLONEDDS_URI`.
3. Que no haya un entorno ROS cargado en la terminal del SDK2.
4. Que el adaptador 2 siga en modo puente sobre la NIC correcta.

Como último recurso, pase a la VM un adaptador USB-Ethernet dedicado. Requiere el Extension Pack.

## Deshacer

```bash
sudo scripts/red/pc_compartir_internet.sh --lan enp0s8 --wan enp0s3 --quitar
ssh -t unitree@192.168.123.18 'sudo ~/dock_salida_internet.sh --gw 192.168.123.222 --quitar'
```
