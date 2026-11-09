# ml: datos, entrenamiento y exportación del detector

Pipeline en PyTorch para el detector de frutos de tomate de Sabueso. Corre en una PC o una GPU externa, **no en el dock**: el dock solo carga el modelo ONNX exportado (`src/deteccion/detector.py`).

## Estado

| Parte | Estado |
| --- | --- |
| Datos, entrenamiento, evaluación, exportación e inferencia | Implementados y probados de punta a punta con una **prueba de humo** (12 imágenes, 2 épocas, CPU) |
| Entrenamiento real | **Pendiente**: hace falta una GPU; no hay números de calidad válidos todavía |
| Clases | Solo `tomate_verde` y `tomate_maduro` |
| Maleza, hojas, flor, plaga | **Sin datos con licencia verificada**; ver [Brechas](#brechas-de-datos) |
| Latencia en el dock | **No medida** (solo en una CPU de portátil) |

## Formulación y modelo

- **Detección de objetos con cajas**, porque el contrato `Deteccion(clase, confianza, caja)` necesita localización y una escena tiene muchos frutos. Clasificar la imagen completa (PlantVillage) no sirve.
- **Faster R-CNN con MobileNetV3-Large FPN** de torchvision (licencia BSD), preentrenado en COCO y con la cabeza reemplazada. Es pequeño, no depende de Ultralytics (AGPL-3.0) y su exportación a ONNX funciona. No se probaron alternativas: no hay números para compararlas.
- Entrada al modelo: lado largo 960 px, lado corto mínimo 640. Aumentos: volteo horizontal y brillo/contraste leves.

## Datos

| Fuente | Enlace | Licencia | Clases | Tamaño | Dominio | Decisión |
| --- | --- | --- | --- | --- | --- | --- |
| AerialYield-T2M (consultada el 2026-11-08) | <https://zenodo.org/records/22071809> | CC BY 4.0 (verificada en la API de Zenodo y en el `LICENSE`) | 6 etapas de madurez, cajas COCO | 677 imágenes, 14.303 instancias, 3,2 GB de imágenes | Invernadero comercial (Emiratos Árabes), 535 cuadros cercanos de teléfono y 142 de dron | **Usada** |

Cita: el registro pide citar el *Data Descriptor* de AerialYield-T2M (Azam, A., Khalifa University); revisa la referencia exacta en el registro de Zenodo.

Las demás candidatas (Laboro Tomato, tomatOD, PlantDoc, PlantVillage, DeepWeeds, CWFID, GROUNDBASED_WEED, TomatoweedDet, TomatoMAP y otras) están en [`fuentes_datasets.md`](fuentes_datasets.md). Esa tabla la generó un worker de Codex y **solo AerialYield está verificado de nuevo por mí**. Todas quedaron descartadas por ahora por licencia no clara, falta de cajas o campos sin verificar.

### Taxonomía

AerialYield tiene 6 etapas (Silal): Green, Breakers, Turning, Pink, Light Red y Red. Se agrupan así (`MAPA_AERIALYIELD` en `comun.py`):

| Clase de Sabueso | Etapas | Color desarrollado |
| --- | --- | --- |
| `tomate_verde` | Green, Breakers, Turning | menos de 40 % |
| `tomate_maduro` | Pink, Light Red, Red | 40 % o más |

Es una decisión de producto: si "maduro" debe significar listo para cosecha, el corte puede moverse. Cambiar la agrupación obliga a reentrenar. La API y la web guardan `clase` como texto libre, así que no hay que tocarlas.

### Splits

Se usan los splits oficiales del dataset: 477 / 105 / 95 imágenes (train / val / test), con semilla 42 y bloques de 300 fotogramas dentro de cada sesión. No comparten bloques entre particiones, pero **las sesiones no se reservan por separado**: es independencia por bloque, no por sesión ni por invernadero. Por eso las métricas serán optimistas respecto a un invernadero nuevo.

**No se usa la exportación YOLO del mismo registro.** Sus carpetas `train`, `val` y `test` suman 989 imágenes (no 677) y repiten archivos entre particiones: 158 nombres coinciden entre `train` y `val` y 134 entre `train` y `test`, y las 40 comparadas entre `train` y `val` eran píxel a píxel idénticas. Usarla filtraría datos de entrenamiento a la evaluación. Además deforma las imágenes a 1024×1024. `preparar_datos.py` lee en cambio las anotaciones COCO, cuyos splits coinciden exactamente con los oficiales y no se solapan.

### Brechas de datos

| Necesidad | Situación | Qué haría falta |
| --- | --- | --- |
| Maleza | Sin dataset con licencia verificada y cajas. GROUNDBASED_WEED (tomate, España) es el candidato más relevante, pero Digital.CSIC devuelve 502 y su licencia no se pudo leer | Reintentar o escribir a los autores; o capturar con el robot |
| Hojas sanas/enfermas | PlantDoc tiene cajas pero derechos de imagen sin auditar | Dataset con licencia de imágenes clara |
| Flor y plaga | Sin conjunto con cajas y licencia clara | Captura propia |
| Dominio | Todo el entrenamiento es de un invernadero y de teléfono/dron, no del Go2 | Capturar y etiquetar un recorrido real: otra altura, luz y fondo |

Plan de captura propia: grabar recorridos con la cámara del Go2 en Pampa Concordia, extraer cuadros espaciados (para no tener cuadros casi idénticos), etiquetar en un formato COCO y reservar recorridos completos (no cuadros sueltos) para val y test.

## Reproducir

Requiere Python 3.10 o más reciente. Desde la raíz del repositorio:

```bash
python -m venv .venv && source .venv/bin/activate     # en Windows: .venv\Scripts\activate
pip install -r ml/requirements.txt                    # con GPU NVIDIA, instala antes torch con el índice de tu CUDA

# 1. Datos (3,2 GB en total; la carpeta datos/ está ignorada por Git)
mkdir -p datos/aerialyield && cd datos/aerialyield
B=https://zenodo.org/api/records/22071809/files
for f in dataset_images.zip dataset_detection_coco.zip splits.zip LICENSE; do curl -L -C - -o $f $B/$f/content; done
md5sum dataset_images.zip   # ae1681d872276fa178c54f4d5740d9d9
python -c "import zipfile; zipfile.ZipFile('dataset_detection_coco.zip').extractall('coco'); zipfile.ZipFile('splits.zip').extractall('splits')"
cd ../..

# 2. Preparar (reescala conservando la proporción y agrupa clases)
python ml/preparar_datos.py --origen datos/aerialyield

# 3. Entrenar (en CPU, unas 20 min por época, estimado a partir de la prueba de humo; en GPU no se midió)
python ml/entrenar.py --datos datos/aerialyield/prep --salida datos/ml --epocas 20

# 4. Evaluar en test (mAP, precisión/recall/F1, matriz de confusión, latencia)
python ml/evaluar.py --pesos datos/ml/mejor.pt --split test --salida datos/ml/test.json

# 5. Exportar y comprobar que ONNX coincide con PyTorch
python ml/exportar.py --pesos datos/ml/mejor.pt --salida datos/ml/sabueso.onnx --imagen datos/aerialyield/prep/test/20260416_123459_000309.jpg
```

Después copia `sabueso.onnx` y `sabueso.onnx.json` al dock en `~/Workspace/farmbot/datos/modelo/`.

Prueba de humo (CPU, ~1 minuto): añade `--maximo 12 --epocas 2 --batch 2 --salida datos/ml_humo` al paso 3.

Pruebas sin hardware (no necesitan datos ni modelo): `python -m pytest tests`.

## Resultados de la prueba de humo

12 imágenes de entrenamiento, 2 épocas, CPU, evaluada en las 20 primeras imágenes de test. **Solo demuestra que el pipeline funciona.** No es una métrica del modelo.

| Medida | Valor |
| --- | --- |
| Pérdida de entrenamiento (época 1 → 2) | 1,49 → 1,17 |
| mAP@.5 en val (época 1 → 2) | 0,20 → 0,23 |
| `tomate_verde` en test (umbral 0,5) | precisión 0,66, recall 0,28, F1 0,39 |
| `tomate_maduro` en test | 0 (no aprendió la clase con tan pocos datos) |
| Matriz de confusión, filas real, columnas predicho [verde, maduro, fondo] | verde [78, 0, 201]; maduro [23, 0, 67]; fondo [17, 0, –] |
| ONNX frente a PyTorch | 6 y 6 detecciones sobre 0,5, diferencia máxima de cajas 0,000 px |

Latencia, medida en un AMD Ryzen 7 7730U (CPU, sin GPU), por imagen de 540×960:

| Ruta | Latencia |
| --- | --- |
| PyTorch, media (p95) | 660 ms (741 ms) |
| ONNX Runtime | 447 ms |

**Esto no es la latencia del dock.** La Jetson puede ir más rápido con GPU o más lento en CPU; hay que medirla allí.

## Límites conocidos

- No hay modelo entrenado en serio ni métricas reales; falta el entrenamiento en GPU.
- Los datos vienen de un solo invernadero, con teléfono y dron. Con el Go2 la altura, el ángulo y la luz serán distintos y la precisión puede bajar mucho.
- Hay desbalance: tras agrupar, train tiene 8.475 cajas `tomate_verde` y 1.543 `tomate_maduro` (val 1.671 y 262; test 1.996 y 204). Con solo 204 maduros en test, el AP de esa clase será ruidoso. La proporción de dron en test (35 de 95 imágenes) es mayor que en train (92 de 477): conviene reportar también las métricas por fuente.
- Las clases se evalúan por la agrupación de etapas; las etapas intermedias (Turning, Pink) son ambiguas incluso para una persona.
- La compatibilidad de `onnxruntime` con Python 3.8 en la Jetson y el rendimiento allí no están verificados. Si no hay wheel disponible, alternativas: ejecutar el modelo en un equipo conectado, o exportar con un opset menor.
- El registro puede repetir el mismo fruto en cuadros seguidos (pendiente ya anotado en `src/recorrido`).

## Siguientes pasos

1. Entrenar en la GPU (pasos 3 a 5), anotar las métricas reales de val y test y actualizar este README.
2. Medir la latencia en el dock y decidir entre ONNX en el dock y un equipo externo.
3. Resolver la licencia de un dataset de maleza en tomate, o capturar y etiquetar un recorrido con el Go2 (esto también cubre el desajuste de dominio).
4. Con datos propios, reentrenar con las clases ampliadas y reservar recorridos completos para val y test.
