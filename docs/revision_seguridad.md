# Revisión de seguridad del módulo de movimiento

**Sistema de monitoreo terrestre preventivo del cultivo de tomate Sabueso.** Revisión de `robot/sabueso_robot/seguridad/` y de `config/limites_seguridad.yaml` contra RFN5, CU1 y la sección 4.4 del plan. Solo informa: no modifica código. Las decisiones sobre cada hallazgo las toma el coordinador.

**Fecha:** 21 de octubre de 2026. **Revisor:** Sonnet 5.5.

**Convención:** una afirmación sin marca está respaldada por el código o el documento citado (con `archivo:línea`). **Verificado** significa que se ejecutó un fragmento en Python 3.14 con un cliente falso, sin robot ni SDK (`python3 -I`, `sys.path` hacia `robot/`). **Por verificar** significa que depende del robot o del SDK y no se comprobó.

---

## 1. Alcance y versión revisada

El árbol de trabajo cambió mientras se hacía la revisión (el orquestador agregó `supervisor.py`, `cliente_sport.py` y el rechazo de comandos no finitos). Lo revisado es el estado siguiente, partiendo de `HEAD 890400e` más cambios sin confirmar. Si alguna huella cambia, hay que revisar de nuevo el archivo.

| Archivo | SHA-256 (12 primeros) |
| --- | --- |
| `robot/sabueso_robot/seguridad/limites.py` | `0165e7f0a823` |
| `robot/sabueso_robot/seguridad/puerta_movimiento.py` | `14f92d4b8139` |
| `robot/sabueso_robot/seguridad/supervisor.py` | `445c2d3f7468` |
| `robot/sabueso_robot/seguridad/cliente_sport.py` | `a0d97382e6ad` |
| `robot/sabueso_robot/seguridad/__init__.py` | `6017f49fe2f7` |
| `config/limites_seguridad.yaml` | `5e0e3a6803f9` |
| `tests/robot/test_puerta_unica.py` | `ca1946351669` |
| `robot/sabueso_robot/mision/ejecutor.py` (solo el uso de la puerta) | `c2b79bb6f22d` |
| `robot/sabueso_robot/mision/verificacion.py` (solo el uso de los límites) | `ebc656809204` |

`python3 -m pytest -q` en ese estado: 92 pruebas pasan.

**Requisitos contra los que se revisa**

| Fuente | Texto |
| --- | --- |
| RFN5, Tabla 6 de [`fases/fase1_informe_etapa_1.md`](../fases/fase1_informe_etapa_1.md) | «Velocidad inferior a 1 m/s y detención automática ante obstáculos a menos de 0,5 m». Verificación: «desplazamiento y detención en un entorno de prueba supervisado» |
| CU1, sección 2.6.1 del mismo informe | Paso 3: «el software limita la velocidad y verifica obstáculos». Excepciones: sin batería o configuración suficientes no se inicia; ante un obstáculo a menos de 0,5 m el robot se detiene; «el operario solo reanuda tras comprobar condiciones seguras» |
| Sección 4.4 del [plan](../fases/plan_conectividad_y_entorno.md) | Tope absoluto de 1,0 m/s, configurable solo hacia abajo; regla propia de detenerse a < 0,5 m; evasión oficial solo cubre el frente, sin desplazamientos laterales ni hacia atrás sin supervisión [U4]; watchdog de 300 ms; no iniciar con < 30 % de batería y detener al 25 %; sin volteretas con el dock montado |

---

## 2. Resumen

| Severidad | Cantidad | Hallazgos |
| --- | ---: | --- |
| Alta | 4 | S1, S2, S3, S4 |
| Media | 7 | S5–S11 |
| Baja | 4 | S12–S15 |

Lo más urgente antes de F4.1 (primera prueba con el robot): S1 (el paro puede quedar bloqueado hasta 3 s), S2 (sin dato de obstáculo el robot no se detiene), S3 (el watchdog depende de que alguien lo ejecute) y S4 (no se confirma que `StopMove` haya funcionado).

---

## 3. Qué cumple

| Requisito | Evidencia |
| --- | --- |
| RFN5, velocidad < 1 m/s | `Limites` rechaza `vx_max >= 1.0` (`limites.py:26-29`); el valor por defecto y el de `config/limites_seguridad.yaml:3` es 0,5 m/s |
| Todo comando se recorta a los límites | `mover` recorta cada componente (`puerta_movimiento.py:79-83`); la prueba `test_ningun_comando_supera_el_limite` lo cubre |
| Parte bloqueada | `_motivo_paro = "inicio"` (`puerta_movimiento.py:46`) |
| Comandos no finitos | Con `nan` o `inf` en el comando, `mover` detiene y bloquea (`puerta_movimiento.py:75-78`). Cambio reciente, sin confirmar en git |
| El paro queda anotado antes de hablar con el robot | `parar` fija `_motivo_paro` antes de `StopMove` (`puerta_movimiento.py:97-98`); si `StopMove` falla, el robot sigue bloqueado en software (verificado) |
| Reloj monótono | `time.monotonic` por defecto (`puerta_movimiento.py:39`) |
| Claves de límites mal escritas | Se rechazan (`limites.py:37-43`) |
| Pérdida de telemetría | `SupervisorSeguridad.revisar` detiene si no hay telemetría o supera `max_edad_s` (`supervisor.py:48-50`) |
| Obstáculo a < 0,5 m | `informar_obstaculo` usa comparación estricta `<` con `distancia_paro_m` (`puerta_movimiento.py:100-102`), coherente con CU1 |
| Movimiento solo en `seguridad/` | `tests/robot/test_puerta_unica.py` (con las limitaciones del hallazgo S10) |

---

## 4. Hallazgos

### Severidad alta

#### S1. El paro puede quedar retenido hasta el tiempo de espera de una llamada RPC

- **Dónde:** `puerta_movimiento.py:70-86` (`mover`), `:94-98` (`parar`), `:108-116` (`revisar_watchdog`); `cliente_sport.py:9,14` (tiempo de espera de 3,0 s por defecto, igual que `timeout_rpc_s` de `config/robot.yaml`).
- **Problema:** `mover`, `detener` y `parar` usan el mismo `threading.Lock` y lo mantienen mientras esperan la respuesta del robot. Si una hebra está dentro de `Move` (bloqueada por la red), el paro de otra hebra (watchdog, obstáculo, batería) espera a que ese `Move` termine, y ni siquiera se fija `_motivo_paro` hasta entonces.
- **Verificado:** con un `Move` falso que tarda 1,0 s, `parar()` tardó 0,90 s en volver. El tiempo de espera por defecto es 3,0 s.
- **Requisito afectado:** RFN5 (detención automática), sección 4.4 (watchdog de 300 ms) y el criterio de F4.2 (`StopMove` por watchdog en < 0,5 s).
- **Recomendación:**
  1. En `parar`, fijar `_motivo_paro` (o un `threading.Event` de paro) **antes** de pedir el candado, de modo que ningún `mover` posterior envíe comandos.
  2. Enviar `StopMove` sin retener el candado de `mover`, y acotar el tiempo de espera de `Move` a un valor del orden del `timeout_comando_s` (valor **por verificar** en el SDK: `SetTimeout` aplica al cliente completo).
  3. Agregar una prueba con un cliente cuyo `Move` bloquee y comprobar que `parar` vuelve en menos de 0,1 s.

#### S2. Sin dato de obstáculo o de batería, el robot no se detiene

- **Dónde:** `puerta_movimiento.py:100-106` (`informar_obstaculo`, `informar_bateria`); `supervisor.py:37-39` (`al_recibir_estado`); prueba `test_obstaculo_desconocido_no_detiene`.
- **Problema:** `informar_obstaculo(None)` no hace nada por diseño (la prueba lo exige). Un valor `nan` tampoco detiene, porque `nan < x` es falso, y lo mismo pasa con `informar_bateria(nan)`. En `al_recibir_estado`, una batería `None` se ignora.
- **Verificado:** `informar_obstaculo(None)`, `informar_obstaculo(nan)` e `informar_bateria(nan)` dejan la puerta sin bloquear.
- **Agravante:** la única vigencia que revisa el supervisor es la edad global de la telemetría (`supervisor.py:48-50`). El contrato de módulos define `FuenteTelemetria.edad_s` como los «segundos desde el último mensaje», sin distinguir tema. Si `rt/lowstate` sigue llegando y `rt/sportmodestate` (que trae `range_obstacle`) se calla, o al revés, el supervisor no lo nota.
- **Requisito afectado:** RFN5 (detención automática ante obstáculos), CU1 paso 3 («verifica obstáculos»).
- **Recomendación:** decidir y documentar la política «sin dato = sin garantía». Propuesta: mientras la puerta esté habilitada y se haya enviado un comando, un dato ausente o no finito de obstáculo (o de batería) durante más de N ms detiene al robot; medir la edad por tema; rechazar `nan` en `informar_*`. El significado de `range_obstacle` cuando no hay obstáculo (¿0, un valor grande?) está **por verificar** en el robot, y condiciona qué valor se interpreta como «sin dato».

#### S3. El watchdog y el supervisor dependen de que alguien los ejecute

- **Dónde:** `puerta_movimiento.py:108-116` («Debe llamarse periódicamente»); `supervisor.py:52-57` (`iniciar` es opcional); `supervisor.py:65-71` (`_bucle`).
- **Problema:**
  1. `PuertaMovimiento` no tiene hebra propia: sin `revisar_watchdog` periódico no hay watchdog, y `habilitar` y `mover` funcionan igual sin el supervisor. Hoy `__main__.py` no instancia la puerta ni el supervisor (solo `postura`), así que la conexión final aún no existe.
  2. Si `StopMove` falla dentro del `except` de `_bucle` (`supervisor.py:69-70`), la excepción sube y la hebra del supervisor muere. **Verificado:** con `StopMove` que lanza `OSError`, la hebra termina; tras eso la puerta no tiene ninguna supervisión y `motivo_paro` queda en «falla del supervisor: rpc».
- **Requisito afectado:** RFN5 y sección 4.4 («watchdog que ordena `StopMove` sin comandos en 300 ms»).
- **Recomendación:** que `mover` se niegue a enviar si el supervisor no registró un latido reciente (por ejemplo, un `ultimo_latido` que actualice `revisar` y que `mover` compare con `2 × periodo_s`); proteger el `parar` del `except` con su propio `try/except` que reintente y registre; arrancar el supervisor desde el mismo constructor o función que crea la puerta, para que no existan por separado.

#### S4. No se comprueba que `StopMove` ni `Move` hayan sido aceptados

- **Dónde:** `puerta_movimiento.py:77,84,91,98`; `cliente_sport.py:18-22`.
- **Problema:** `ClienteMovimiento` declara `-> int` (código RPC), pero la puerta descarta el valor de retorno. Si `StopMove` devuelve un código de error (por ejemplo, tiempo de espera agotado), el software considera al robot detenido y bloquea nuevos comandos, sin avisar ni reintentar. Según la documentación del SDK, todos los métodos de `SportClient` devuelven el código RPC y 0 indica éxito [P1, Context7]. Además, en la documentación de `SportClient` de B2, `Move` se envía sin esperar respuesta (*no-reply*); si el Go2 hace lo mismo, su código de retorno no confirma la ejecución (**por verificar** en el Go2).
- **Requisito afectado:** RFN5 y CU1 (el robot «se detiene»): el paro es la única medida de mitigación.
- **Recomendación:** en `parar`, comprobar el código; si no es 0, reintentar `StopMove` (p. ej. 3 veces) y, si persiste, registrar una alarma visible al operador para que use el control remoto físico (paro primario de la sección 4.4). Guardar el resultado en `motivo_paro` o en un registro. Probar con un cliente falso que devuelva un código distinto de 0 y con otro que lance una excepción.

### Severidad media

#### S5. «Solo pueden reducirse» no se cumple para los límites que no son `_max`

- **Dónde:** `limites.py:45-52`; `config/limites_seguridad.yaml:2`; `puerta_movimiento.py:66-68` (`reducir_limites`).
- **Problema:** `reducido` solo vigila las claves que terminan en `_max` (`limites.py:48`). Con las demás se puede debilitar la protección en tiempo de ejecución.
- **Verificado:** `Limites().reducido(distancia_paro_m=0.0, timeout_comando_s=60, bateria_min_operacion=0)` se acepta. Por tanto, un fallo o un error de uso desactiva el paro por obstáculo (RFN5: 0,5 m), alarga el watchdog a un minuto y anula la detención por batería.
- **Recomendación:** dar a cada campo su dirección segura (los `_max` y `timeout_comando_s` solo bajan; `distancia_paro_m` y `bateria_min_operacion` solo suben) y rechazar el cambio contrario.

#### S6. La configuración puede incumplir RFN5 sin que `Limites` lo detecte

- **Dónde:** `limites.py:21-35`; `config/limites_seguridad.yaml:3-9`.
- **Problema:**
  1. No hay cota inferior para `distancia_paro_m` (verificado: `Limites(distancia_paro_m=0.0)` es válido). RFN5 exige detenerse a menos de 0,5 m.
  2. No hay cota superior para `timeout_comando_s` (la sección 4.4 fija 300 ms) ni para `vyaw_max` (verificado: `vyaw_max=100.0` es válido).
  3. Los valores no finitos pasan la validación (verificado: `Limites(vx_max=nan)` es válido y `mover(0.3, 0, 0)` envía `Move(nan, 0, 0)` al cliente, porque `max/min` con `nan` devuelve `nan`). Los comparadores `< 0`, `>= 1.0` y `> vx_max` son falsos con `nan`.
- **Recomendación:** en `__post_init__`, exigir `math.isfinite` en todos los campos, `distancia_paro_m >= 0.5` (constante análoga a `VX_MAXIMO_ABSOLUTO`), `timeout_comando_s` con un máximo decidido por el coordinador (propuesta: ≤ 0,3 s) y un tope para `vyaw_max` (valor máximo del SDK **por verificar**).

#### S7. El tope de velocidad no considera la velocidad combinada

- **Dónde:** `limites.py:26-31`.
- **Problema:** se valida `vx_max < 1.0` y `vy_max <= vx_max`, pero no la norma. **Verificado:** `Limites(vx_max=0.99, vy_max=0.99)` es válido y permite una velocidad combinada de 1,40 m/s, por encima del límite de RFN5. Con los valores actuales (0,5 y 0,2) la norma máxima es de 0,54 m/s, así que el riesgo es de futuras ediciones del YAML.
- **Recomendación:** validar `math.hypot(vx_max, vy_max) < VX_MAXIMO_ABSOLUTO` o recortar la norma del comando en `mover`.

#### S8. Se permite avanzar hacia atrás y de lado con la misma magnitud

- **Dónde:** `puerta_movimiento.py:30-31,79-83`; sección 4.4 del plan.
- **Problema:** el recorte es simétrico. **Verificado:** `mover(-0.5, -0.2, 0)` se envía tal cual. La sección 4.4 dice que la evasión oficial solo cubre el frente [U4] y que no se permiten desplazamientos laterales o hacia atrás sin supervisión. La puerta no distingue «con supervisión» de «sin supervisión».
- **Recomendación:** agregar un límite de marcha atrás (por ejemplo `vx_atras_max`, con valor 0 por defecto) y un permiso explícito para movimiento lateral, ambos en `config/limites_seguridad.yaml`. Qué sensores cubre `range_obstacle` está **por verificar** (probablemente solo el frente).

#### S9. `habilitar()` y `reanudar` no vuelven a comprobar las condiciones

- **Dónde:** `puerta_movimiento.py:60-64`; `mision/ejecutor.py:67-70`; `mision/verificacion.py:8-31`.
- **Problema:** `habilitar` limpia el paro sin condiciones. `EjecutorRecorrido.reanudar(seguro=True)` acepta un booleano del operador y llama a `habilitar` sin volver a evaluar `problemas_para_iniciar` (batería, error del robot, obstáculo). **Verificado:** tras `informar_bateria(10)` y `habilitar()`, la puerta queda desbloqueada y solo vuelve a pararse cuando llega otro dato de batería. CU1 dice que el operario reanuda «tras comprobar condiciones seguras»; hoy esa comprobación es un acto de fe.
- **Recomendación:** que `reanudar` (o un `habilitar` con parámetros) llame a `problemas_para_iniciar` con la telemetría vigente y rechace con la lista de motivos. Si lo detenido fue un obstáculo, exigir además una lectura posterior sin obstáculo.

#### S10. La prueba de «puerta única» cubre solo tres nombres de método

- **Dónde:** `tests/robot/test_puerta_unica.py:8,15-18`; `cliente_sport.py:25-37`.
- **Problema:**
  1. El patrón `\.(Move|MoveToAbsolutePosition|MoveToIncrementPosition)\s*\(` se evalúa línea por línea y solo en `robot/**/*.py`. No detecta `getattr(c, "Move")`, `c.Move` con el paréntesis en la línea siguiente, llamadas directas a `_Call` ni a otros scripts del repositorio (`scripts/`).
  2. La API deportiva del Go2 incluye otras acciones que desplazan o ponen en riesgo al robot: según la documentación del SDK figuran `FrontFlip`, `FrontJump`, `FrontPounce`, `FreeWalk`, `StaticWalk`, `TrotRun`, `Dance1` y `Dance2` [P1, Context7]. La sección 4.4 prohíbe las volteretas con el dock montado [U4]. Ninguna está cubierta.
  3. `ClienteSportGo2.amortiguar` (`Damp`, `cliente_sport.py:35-37`), `ponerse_de_pie` y `echarse` no consultan `PuertaMovimiento.bloqueada` y son públicos. `Damp` relaja los motores: con el robot de pie, cae.
- **Recomendación:** pasar a una lista blanca con `ast`: solo `seguridad/cliente_sport.py` puede llamar a atributos de `SportClient`, y solo con nombres de una lista aprobada (`Move`, `StopMove`, `StandUp`, `StandDown`, `BalanceStand`, `Damp`); cualquier otro se rechaza. Exigir confirmación del operador y estado «echado o suspendido» para `Damp`, o no exponerlo hasta F4.1.

#### S11. Datos viejos y distancia de frenado: ambigüedad del criterio de F4.3

- **Dónde:** `supervisor.py:23` (`max_edad_s = 0.5`); `puerta_movimiento.py:101`; plan, F4.3.
- **Problema:**
  1. RFN5 y CU1 piden detenerse **cuando** hay un obstáculo a menos de 0,5 m; el plan, en F4.3, pide que se detenga «**antes de** 0,5 m». Con el disparo en 0,5 m, el robot se detiene más cerca que eso, porque a la latencia de la telemetría y del RPC se suma la distancia de frenado. Con `max_edad_s = 0,5` y 0,5 m/s, el dato puede tener 0,25 m de recorrido desde que se midió.
  2. El criterio de aceptación no dice qué distancia final se acepta.
- **Recomendación:** que el coordinador decida la interpretación y la deje escrita en el plan y en `docs/`. Si se exige «nunca más cerca de 0,5 m», el disparo debe ser `0,5 m + v · (latencia + max_edad_s + frenado)`, con la latencia y el frenado medidos en F4.3 (no se tienen). Reducir `max_edad_s` (propuesta: ≤ 0,2 s) y registrar la distancia final de cada intento.

### Severidad baja

#### S12. La aprobación de dos integrantes no se hace cumplir

- **Dónde:** `config/limites_seguridad.yaml:2`.
- **Problema:** «Cambiar estos valores requiere aprobación de ambos integrantes» es un comentario. Nada en el repositorio lo obliga (no hay `CODEOWNERS` ni prueba que fije la línea base). Tampoco existe el esquema que pide F3.6 para validar las plantillas.
- **Recomendación:** agregar `CODEOWNERS` con ambos integrantes para `config/limites_seguridad.yaml` y `robot/sabueso_robot/seguridad/`, y una prueba que falle si el YAML supera una línea base fijada en el código.

#### S13. `SABUESO_LIMITES` permite cambiar los límites sin dejar rastro

- **Dónde:** `robot/sabueso_robot/config.py:15,45-46,58-59`.
- **Problema:** la variable de entorno sustituye el archivo de límites. Es útil para pruebas, pero en el robot permite cargar límites más débiles (dentro de lo que valida `Limites`, ver S6) sin que quede constancia.
- **Recomendación:** registrar al arrancar la ruta y el hash del archivo de límites usado y los valores efectivos; rechazar un archivo fuera de `config/` si la ejecución es una misión.

#### S14. No hay registro de paros y habilitaciones

- **Dónde:** `puerta_movimiento.py:60-64,94-98`.
- **Problema:** `habilitar` y `parar` no escriben nada. RFN5 se verifica con pruebas supervisadas (F4.2–F4.3) y CU1 exige informar la incidencia; sin registro con hora, motivo y comando enviado, no hay evidencia de la prueba ni de la causa de un paro.
- **Recomendación:** `logging` con nivel `WARNING` para cada `parar`, e `INFO` para `habilitar`, con la marca de tiempo monótona y el motivo; incluir el último comando enviado.

#### S15. Umbrales de batería y pruebas que no coinciden entre secciones del plan

- **Dónde:** `config/limites_seguridad.yaml:8-9`; plan, secciones 4.2 y 4.4; `tests/robot/test_seguridad.py`.
- **Problema:**
  1. La sección 4.2 pide batería > 50 % para pruebas y > 80 % para recorridos; la 4.4 y el YAML usan 30 % para iniciar y 25 % para detener. Son umbrales de naturaleza distinta (procedimiento frente a límite de software), pero el documento no lo aclara. El 25 % sigue **por verificar** (V17).
  2. Las pruebas actuales no cubren: concurrencia entre `mover` y `parar` (S1), valores `nan`, `StopMove` con código distinto de 0 o con excepción (S3, S4), `reducido` sobre claves que no son `_max` (S5) ni el comportamiento del supervisor cuando muere su hebra (S3).
- **Recomendación:** aclarar en la sección 4.2 que 50 % y 80 % son precondiciones del procedimiento, y agregar las pruebas listadas junto con la corrección de cada hallazgo.

---

## 5. Pendientes por verificar

| # | Dato | Cómo verificarlo | Hallazgo |
| --- | --- | --- | --- |
| P1 | Si `Move` del Go2 es *no-reply* y qué devuelve | Leer `unitree_sdk2py/go2/sport/sport_client.py` instalado | S4 |
| P2 | Alcance de `SetTimeout` y valor adecuado para `StopMove` frente a `Move` | Leer `Client.SetTimeout` y `_Call` en el SDK | S1 |
| P3 | Qué valor devuelve `range_obstacle` cuando no hay obstáculo y qué sensores cubre | Suscripción de solo lectura en F2.3 con y sin obstáculo | S2, S8 |
| P4 | Si el robot sigue moviéndose tras la última orden `Move` hasta recibir `StopMove` | Prueba suspendido (F4.1) con el control remoto en mano | S3, S4 |
| P5 | Tope de `vyaw` aceptado por el SDK | Documentación de `SportClient` y prueba suspendida | S6 |
| P6 | Latencia total (telemetría + RPC) y distancia de frenado | Mediciones de F4.2–F4.3 | S11 |

---

## 6. Fuentes

- Requisito RFN5 (Tabla 6) y CU1 (sección 2.6.1): [`fases/fase1_informe_etapa_1.md`](../fases/fase1_informe_etapa_1.md).
- Plan, secciones 4.4, 4.5, 7 y 8: [`fases/plan_conectividad_y_entorno.md`](../fases/plan_conectividad_y_entorno.md); [U4] es el *Go2 User Manual V1.0* citado allí.
- Contrato de módulos: [`docs/contratos_modulos.md`](contratos_modulos.md).
- [P1] unitreerobotics/unitree_sdk2_python, referencia de `SportClient` consultada con Context7 el 21/10/2026 (`/unitreerobotics/unitree_sdk2_python`): lista de acciones del Go2 y devolución de códigos RPC. La referencia de B2 (misma biblioteca) describe `Move` sin respuesta; el Go2 está **por verificar**.
- Ejecuciones de verificación: cliente falso de `Move` y `StopMove`, reloj falso y `python3 -I`, sin robot ni red.
