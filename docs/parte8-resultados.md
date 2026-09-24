# Parte 8 — resultados, modelos y handoff

Documento de traspaso del lote publicado en el visor como **Parte 8**.
Describe qué número es el oficial, con qué modelos se obtuvo, qué ajustes
están prendidos, qué se midió y se dejó apagado, y cómo debe continuar
otro agente sin deshacer campos ya revisados.

El código de los workers de este estado está en `main`, carpeta `workers/`.
La copia para reinstalar el mismo stack en otro servidor, con los scripts
de medición que solo vivían en la máquina de AWS, está en
`backup/parte8-servidor-fisico/`. El visor es otro repositorio.

`README.md` y `docs/deploy-completo-aws.md` describen la Parte 4
(72,6 %, ~1.700 docs/h). Esta página es la fuente de la Parte 8.

## Resultado publicado

| Qué | Valor |
| --- | --- |
| Lote | 100 frentes, ids `6000000001`–`6000000101` excepto `6000000033` |
| Campos comparados | 18 por formulario, 1.800 celdas |
| Confianza oficial | **87,8 %** = promedio de las 1.800 notas |
| Coincidencia literal | 1.370 / 1.800 = 76,1 %. Existe en el JSON (`exacto`) y no se muestra en el visor |
| Visor | https://shell931.github.io/e3-pages/ — menú Parte 8 |

Promedio por campo (la columna Promedio del visor). En los campos estrictos
el promedio coincide con el porcentaje de coincidencias literales, porque un
error vale 0.

| Campo | Promedio | Literal |
| --- | ---: | ---: |
| formulario_no | 100 | 100 |
| fecha_inscripcion | 89 | 89 |
| tipo_documento | 95 | 95 |
| numero_documento | 86 | 86 |
| fecha_expedicion | 90 | 90 |
| primer_apellido | 92,9 | 73 |
| segundo_apellido | 91,4 | 74 |
| primer_nombre | 93 | 77 |
| segundo_nombre | 95,1 | 78 |
| nivel_estudio | 94 | 94 |
| email | 93,1 | 33 |
| telefono_movil | 41 | 41 |
| telefono_fijo | 74 | 74 |
| ciudad | 93,4 | 79 |
| direccion | 90,3 | 25 |
| lee_braille | 92 | 92 |
| tipo_discapacidad | 82 | 82 |
| etnia | 88 | 88 |

El porcentaje de cada formulario en la lista de la izquierda es el promedio
de las notas de sus celdas. Ejemplo publicado: `6000000097` = 88,6 %.

## Todo lo que produjo este resultado

Misma corrida, dos números. Las lecturas dan 1.370 celdas idénticas al gold
de 1.800 (76,1 %). El 87,8 % publicado es el promedio de la nota de cada
celda, no un modelo distinto. Las técnicas de abajo son las que generaron
esas lecturas. Después está la fórmula que las convierte en 87,8 %.

Runtime de esa corrida, en `ubuntu@3.17.139.133`:

- Imágenes: `/data/e3/front/60000000xx.tif`, frente a ~300 dpi, cerca de 2505×2194.
- Cola RabbitMQ. 8 workers OCR y 12 NLP. El throughput no se usó como meta.
- GPU 0: `Qwen/Qwen2.5-VL-7B-Instruct` en vLLM, puerto 8001,
  `--gpu-memory-utilization 0.90 --max-model-len 16384 --enforce-eager --max-num-seqs 8`.
  Checkpoint 15,45 GiB. La reserva de arranque es la que el visor escribe como ~88 GB.
- GPU 1: `Qwen/Qwen2.5-7B-Instruct-AWQ` en vLLM, puerto 8000,
  `--gpu-memory-utilization 0.40 --max-model-len 8192 --max-num-seqs 32 --enforce-eager`.
  Checkpoint 5,19 GiB. La reserva es la que el visor escribe como ~40 GB.
- No entra en este número: Docling, YOLO, RapidOCR, DeepSeek, ni el VL de 32B
  de la Parte 7.

El código que corre es el de la rama que ya está en `main` a partir de
`756b6c1` (quitar género y estado civil) más los commits anteriores de esa
pila. En el servidor los `.py` viven en `~/test-ia-local/caso-1-v2-e3/workers`,
montados dentro de `caso1v2e3e3-ocr` y `caso1v2e3e3-nlp`.

### 1. Primera pasada: página completa

`workers/ocr_worker.py`, temperatura 0,1, `max_tokens` 2048. El VL transcribe
el formulario entero. El prompt le pide copiar la ortografía, no completar
nombres, copiar el correo carácter a carácter, leer números dígito a dígito
y escribir `VACÍO` si la caja está vacía.

`workers/nlp_worker.py`, el mismo 7B cuantizado, temperatura 0,1. Convierte
ese texto en JSON de campos. El prompt pide los 18 campos del gold más
`votara`. No pide `lugar_expedicion`, `genero` ni `estado_civil`.

### 2. Postproceso de reglas, antes de los recortes

`workers/postprocess_express.py`, función `postprocesar_campos_express`.
Corre sobre el JSON del NLP, antes de que un recorte lo pueda reemplazar.
Si el recorte después pisa el campo, esta corrección no llega al valor
publicado.

| Campo | Regla |
| --- | --- |
| direccion | `C11`/`C1l` → `Cll`, `Cr1` → `Cra`, `+` seguido de dígito → `#`, `+` entre dígitos → `-`, separa letra y número pegados |
| ciudad | quita dígitos y puntos raros, Title Case, y mapea bogota/cali/medellin/barranquilla/cartagena |
| telefono_movil, telefono_fijo | solo dígitos; si pasa de 10 y empieza por 3, se queda con 10 |
| email | intenta recuperar `@`, corrige hotmail/gmail/outlook y `.can`/`.cam`/`.con` → `.com`, quita espacios, pasa a minúsculas |
| apellidos y nombres | quita dígitos y el punto final, Title Case |
| fecha_inscripcion, fecha_expedicion | pasa `YYYY-MM-DD` a `DD/MM/YYYY`, que es el formato del gold. Sin esto las fechas estrictas quedan en 0 |
| tipo_documento | `CC` → `CEDULA_CIUDADANIA`, `CE` → `CEDULA_EXTRANJERIA`. Después la casilla visual pisa este valor |

La confianza declarada de un campo tocado por esta regla baja 5 puntos, con
piso 70. Esa confianza no es el KPI.

### 3. Doble pasada: recorte ampliado, el mismo VL 7B

Segunda llamada al VL. Se recorta la caja en fracciones del ancho y del alto,
se amplía con LANCZOS y se pregunta solo por ese campo, temperatura 0.
No es otro modelo.

Prendidas en la corrida (`LEER_CASILLAS=1`, `LEER_DIRECCION=1`):

| Campo | Archivo | Recorte (x0 y0 x1 y1) | Escala | Efecto en el valor |
| --- | --- | --- | --- | --- |
| tipo_documento | `casillas_vision.py` | 0,42 0,18 0,72 0,33 | 3 | pisa al NLP siempre. Cero marcas = vacío, no `CEDULA_CIUDADANIA` |
| nivel_estudio | el mismo | 0,02 0,55 0,82 0,62 | 2 | pisa al NLP. Una marca manda; dos o más dejan vacío |
| lee_braille | el mismo, recorte propio | 0,015 0,735 0,22 0,815 | 3 | pisa al NLP. Va aparte porque en el pie completo inventaba `SI` |
| tipo_discapacidad | el mismo, banda `pie_resto` | 0,195 0,70 0,90 0,87 | 2 | pisa al NLP. Comparte recorte con etnia |
| etnia | la misma banda | 0,195 0,70 0,90 0,87 | 2 | pisa al NLP |
| direccion | `direccion_vision.py` | 0,04 0,655 0,78 0,722 | 3 | transcribe la caja tal cual (`+` pasa a `#`). Se queda esta lectura si el NLP venía vacío o si el recorte no puntúa peor. 57 de 100 salieron de aquí. Literal del campo: 17 % → 25 %. Promedio de celda: 90,3 |

Regla de la casilla: una sola marca define el valor (confianza declarada 95).
Cero marcas es vacío válido (90). Más de una marca deja el campo vacío (40).
`tipo_documento` y `lee_braille` usan la regla de vacío frecuente.
`nivel_estudio` usa la regla corta. Discapacidad y etnia usan la regla larga.
Separar discapacidad de etnia en dos recortes ya se midió y empeoró
discapacidad; siguen juntas.

Medidas y dejadas apagadas. El código está, el flag por defecto es 0, y en
esta corrida no corrieron:

| Campo | Flag | Recorte | Por qué no está en el resultado |
| --- | --- | --- | --- |
| primer_apellido | `LEER_APELLIDO=0` | 0,02 0,438 0,49 0,505, escala 4 | 1 acierto y 16 empeoramientos. Literal del campo 73 % → 58 % |
| email | `LEER_CONTACTO=0` | 0,01 0,595 0,72 0,675, escala 3 | el recorte con este 7B no subió el exacto |
| telefono_movil | el mismo flag | 0,70 0,605 0,995 0,665, escala 3 | apagado. El móvil publicado sale del voto de la página completa, no de este recorte |
| telefono_fijo | el mismo flag | 0,70 0,665 0,995 0,735, escala 3 | apagado |

Sin segunda pasada, solo la página completa más NLP y postproceso:
`segundo_apellido`, `primer_nombre`, `segundo_nombre`, `ciudad`,
`fecha_inscripcion`, `fecha_expedicion`.

### 4. Voto de números, sin recorte

`VOTE_NUMERIC=1`. Además de la página completa, el VL lee otra vez solo
`numero_documento` y `telefono_movil`, temperaturas 0,3 y 0,7. Son tres
valores (NLP + dos lecturas). Si uno aparece al menos dos veces, ese queda.
Por eso el celular no depende del recorte de contacto.

### 5. Relleno y campos que el formulario no tiene

- `formulario_no` vacío se rellena con el número del archivo
  (`6000000001.tif` → `6000000001`). Por eso ese campo quedó en 100.
- Si el modelo emite `lugar_expedicion`, `genero` o `estado_civil`, se tiran.
  El E3 no tiene esas cajas. `votara` sí puede salir; el gold no lo compara.

Historia medida del literal del lote, antes de cambiar el agregado a
promedio: dirección con recorte dejó el campo en 25 % literal; decir vacío
en `tipo_documento` cuando no hay marca movió el lote de 76,8 % a 76,2 %;
quitar `lugar_expedicion` y volver a medir lo dejó en 76,1 % (1.370 / 1.800).
Género y estado civil se sacaron del JSON ya medido, sin otra corrida.

### 6. La cuenta que publica 87,8 %

Eso no relee la imagen. `compare_gold_real.py` en el servidor puntúa cada
celda como está más abajo. En cédula, teléfonos, fechas, formulario, tipo de
documento, nivel de estudio, braille, discapacidad y etnia, un carácter
distinto vale 0. En apellidos, nombres, correo, ciudad y dirección vale la
similitud. El promedio de las 1.800 notas es 87,8 %. Dirección queda en 90,3
y correo en 93,1 aunque su literal sea 25 % y 33 %.

## Fórmula de la comparación

Script en el servidor, no en este repo:

`~/test-ia-local/caso-1-v2-e3/scripts/compare_gold_real.py`

Salidas: `/data/e3/parte8-gold.json`, `/data/e3/parte8-gold-docs.json`,
`/data/e3/comparacion-parte8.csv` (el CSV tiene datos personales).

Normalización (`norm`): NFD, se quitan las tildes, se colapsan los espacios,
minúsculas.

Por celda, con `a` = lectura normalizada y `b` = gold normalizado:

```text
conf_real = 100                  si a == b
            0                    si a != b y el campo es estricto
            similitud(a, b)      si a != b y el campo es de texto
```

`similitud` es `difflib.SequenceMatcher.ratio`:

```text
similitud = redondeo( 100 × 2 × caracteres que coinciden
                      / (largo del gold + largo de la lectura) )
```

Si uno de los dos textos queda vacío y no son iguales, la similitud es 0.

Campos estrictos (`ESTRICTOS`): `formulario_no`, `fecha_inscripcion`,
`fecha_expedicion`, `tipo_documento`, `numero_documento`, `nivel_estudio`,
`telefono_movil`, `telefono_fijo`, `lee_braille`, `tipo_discapacidad`,
`etnia`.

Campos de texto: `primer_apellido`, `segundo_apellido`, `primer_nombre`,
`segundo_nombre`, `email`, `ciudad`, `direccion`.

El 87,8 % del lote es la suma de las 1.800 notas dividida entre 1.800.
El promedio de un campo es la suma de sus 100 notas dividida entre 100.

Ejemplo real, dirección de un formulario del lote: gold `Cra 93 B # 72-32`
y lectura `cra 93 a # 72-32`. No es 0. SequenceMatcher da 94.

En el visor, encima de esa fórmula, el recuadro dice **expresion regular**.
Esa etiqueta la pidió quien presenta el resultado. El cálculo no es una
expresión regular: es `SequenceMatcher`. No cambies esa etiqueta salvo que
lo pidan.

Veredictos, solo para el detalle del documento: `exacto` si los textos
normalizados coinciden; `casi` si la similitud es ≥ 85 y el campo no es
estricto; si no, `distinto`. Un no-exacto se pinta en ámbar, no en verde.

La confianza que declara el modelo (`confianza` del JSON, a veces 95 o 100)
no es el KPI. El KPI es `conf_real`.

## Modelos y hardware

Inferencia solo en el servidor `ubuntu@3.17.139.133`. Este agente no corre
el modelo en local. La llave SSH es la PEM de OT-IA del operador; no se
copia al repositorio.

Dos NVIDIA RTX PRO 6000 Blackwell Server Edition, 97.887 MiB cada una
(~94,97 GiB utilizables según vLLM).

| GPU | Proceso | Modelo | Puerto |
| --- | --- | --- | --- |
| 0 | `caso1v2e3e3-vllm-vl` | `Qwen/Qwen2.5-VL-7B-Instruct` | 8001 |
| 1 | `caso1v2e3e3-vllm-nlp` | `Qwen/Qwen2.5-7B-Instruct-AWQ` | 8000 |

Arranque que produjo la Parte 8:

```text
vllm serve --model Qwen/Qwen2.5-VL-7B-Instruct \
  --gpu-memory-utilization 0.90 --max-model-len 16384 \
  --enforce-eager --max-num-seqs 8

vllm serve --model Qwen/Qwen2.5-7B-Instruct-AWQ \
  --gpu-memory-utilization 0.40 --max-model-len 8192 \
  --max-num-seqs 32 --enforce-eager
```

Peso del checkpoint, leído una vez en el log de arranque de vLLM (sigue
visible con el proceso en idle):

| Modelo | Checkpoint | Carga del modelo | KV cache disponible |
| --- | ---: | ---: | ---: |
| VL 7B | 15,45 GiB | 15,67 GiB | 67,23 GiB (1.258.816 tokens) |
| NLP 7B AWQ | 5,19 GiB | 5,29 GiB | el resto de la reserva de 0,40 |

Los ~88 GB y ~40 GB de la tabla de modelos del visor son la reserva que
vLLM aparta al arrancar (`gpu-memory-utilization` 0,90 y 0,40) y la
mantiene aunque no haya requests. `nvidia-smi` no sube más cuando el lote
está ocupado: con 1 request el KV del VL andaba cerca del 0,6 %, y con 8
concurrentes cerca del 4,8 %.

Esas dos reservas no caben juntas en una tarjeta de 96 GB. Esta
configuración usa las dos tarjetas a la vez: visión en la 0, NLP en la 1.
La exactitud no exige llenar 87 GB; la segunda tarjeta deja al NLP
trabajando mientras la visión lee la página siguiente.

Comandos para mostrarlo en el servidor:

```bash
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

docker logs caso1v2e3e3-vllm-vl 2>&1 \
  | grep -E "model_tag|Checkpoint size|Model loading took|Available KV cache" | head -4

docker logs caso1v2e3e3-vllm-nlp 2>&1 \
  | grep -E "model_tag|Checkpoint size|Model loading took|Available KV cache" | head -4
```

Los strings `~88 GB` y `~40 GB` del fragmento del visor están escritos a
mano en `build_parte8_fragment.py` del servidor. No salen de un scrape
en vivo de `nvidia-smi`.

Contenedores del compose `caso1v2e3`: `caso1v2e3e3-ocr`, `caso1v2e3e3-nlp`,
`caso1v2e3e3-vllm-vl`, `caso1v2e3e3-vllm-nlp`, `caso1v2e3e3-rabbitmq`.
Los workers del contenedor OCR/NLP están montados desde
`~/test-ia-local/caso-1-v2-e3/workers` en el servidor. Cambiar un `.py` en
git no cambia la corrida hasta copiarlo ahí y reiniciar el worker. No hace
falta reiniciar vLLM para un cambio de worker.

Cola: RabbitMQ. Concurrencia de la corrida publicada: 8 workers OCR y 12
NLP. El throughput no es el objetivo de la Parte 8. El fragmento todavía
trae `docs_per_hour: 968` y `elapsed ~6 min 12 s` como texto fijo; el visor
ya no muestra la meta de 1.250 docs/h.

## Orden del pipeline

Por documento, en `workers/ocr_worker.py` y `workers/nlp_worker.py`:

1. Página completa al VL (`temperature` 0,1, `max_tokens` 2048). El prompt
   pide el texto del formulario.
2. Si `VOTE_NUMERIC=1` (prendido): dos lecturas más de la página completa,
   solo cédula y celular, temperaturas 0,3 y 0,7.
3. Si `LEER_CASILLAS=1` (prendido): cuatro recortes de casillas, temperatura 0.
4. Si `LEER_DIRECCION=1` (prendido): recorte de dirección, escala 3, temperatura 0.
5. `LEER_APELLIDO` y `LEER_CONTACTO` están en 0. El código existe y no corre.
6. El NLP (`temperature` 0,1) arma el JSON de campos y pasa por
   `postprocess_express.py`.
7. `aplicar_casillas` pisa tipo de documento, nivel de estudio, braille,
   discapacidad y etnia.
8. `aplicar_direccion` se queda con la visión si el NLP venía vacío o si la
   visión no sale claramente peor (puntaje por dígitos y tokens).
9. Voto numérico: de las tres lecturas (NLP + dos del VL) se conserva el
   valor que aparece al menos dos veces.
10. `aplicar_primer_apellido` y `aplicar_contacto` no hacen nada mientras
    sus flags estén en 0.
11. Si `formulario_no` viene vacío, se rellena con el número del nombre del
    archivo (`BACKFILL_FORMULARIO=1`).
12. Se descartan `lugar_expedicion`, `genero` y `estado_civil` si el modelo
    igual los emite. Esos tres tampoco están en el prompt.

`votara` sigue en el prompt y puede salir en el JSON. El gold no lo compara.
No se pidió quitarlo.

## Doble pasada y recorte

La doble pasada es una segunda llamada al mismo VL 7B. La primera pasada
lee la página completa y el NLP arma el JSON. La segunda pasada, en los
campos de abajo, recorta la caja, la amplía y vuelve a preguntar solo por
ese campo. Sigue siendo Qwen2.5-VL-7B-Instruct. No hay un modelo distinto
por campo.

| Campo | Doble pasada | Recorte | Qué hace con la primera lectura |
| --- | --- | --- | --- |
| tipo_documento | sí, prendida | banda superior derecha, escala 3 | la pisa siempre |
| nivel_estudio | sí, prendida | fila del medio, escala 2 | la pisa siempre |
| lee_braille | sí, prendida | recorte propio, escala 3 | la pisa siempre |
| tipo_discapacidad | sí, prendida | comparte `pie_resto` con etnia, escala 2 | la pisa siempre |
| etnia | sí, prendida | el mismo `pie_resto`, escala 2 | la pisa siempre |
| direccion | sí, prendida | caja de residencia, escala 3 | la usa si el NLP venía vacío o si el recorte no sale peor |
| numero_documento | lecturas extra, sin recorte | página completa, temperaturas 0,3 y 0,7 | voto: se queda el valor que salga al menos 2 veces de 3 |
| telefono_movil | lecturas extra, sin recorte | página completa, las mismas dos temperaturas | el mismo voto. El recorte de contacto está apagado |
| primer_apellido | código listo, apagada | caja izquierda, escala 4 | no corre. Medido: 1 acierto y 16 empeoramientos |
| email | código listo, apagada | caja de correo, escala 3 | no corre. No subió el exacto |
| telefono_fijo | código listo, apagada | caja al lado de la dirección, escala 3 | no corre, va en el mismo módulo de contacto |
| segundo_apellido, primer_nombre, segundo_nombre, ciudad, fechas, formulario_no | no | página completa | se quedan con la primera pasada. `formulario_no` vacío se rellena con el nombre del archivo |

Las fracciones de cada recorte están en la sección siguiente. Un recorte
apagado no se ejecuta: el flag por defecto es 0.

### Dirección

`workers/direccion_vision.py`. Fracciones `(0,04, 0,655, 0,78, 0,722)`,
escala 3 (`DIR_ESCALA`). Transcribe la caja tal cual; no rearma `Calle` ni
`#`. En la corrida publicada, 57 documentos quedaron con
`fuente=direccion_visual` y 43 con el NLP. El exacto literal de dirección
pasó de 17 % a 25 %. El promedio de la celda quedó en 90,3.

### Casillas

`workers/casillas_vision.py`.

| Región | Fracciones | Escala | Regla | Campos |
| --- | --- | --- | --- | --- |
| tipo_documento | 0,42 0,18 0,72 0,33 | 3 | vacío frecuente | tipo_documento |
| nivel_estudio | 0,02 0,55 0,82 0,62 | 2 | cortas | nivel_estudio |
| lee_braille | 0,015 0,735 0,22 0,815 | 3 | vacío frecuente | lee_braille |
| pie_resto | 0,195 0,70 0,90 0,87 | 2 | largas | tipo_discapacidad, etnia |

Una sola marca define el valor. Cero marcas es un valor vacío válido
(confianza 90). Dos o más marcas dejan el campo vacío (confianza 40). Una
marca con valor queda en confianza 95. `aplicar` pisa lo que haya dicho el
NLP y marca `fuente=casilla_visual`.

Braille va en su propio recorte. Meter braille, discapacidad y etnia en el
mismo recorte hacía que el modelo inventara `lee_braille=SI` sobre cuadritos
vacíos (`6000000020`). Separar discapacidad de etnia derrumbó
`tipo_discapacidad`; por eso siguen juntos en `pie_resto`.

`tipo_documento` vacío dejó de publicarse como `CEDULA_CIUDADANIA`. En
`6000000002` los dos cuadritos están en blanco. El gold también decía CC, así
que antes la celda salía en 100. Al decir vacío, la celda bajó y el literal
del lote pasó de 76,8 % a 76,2 %. Esa bajada es la evaluación correcta.

### Voto de cédula y celular

Tres lecturas, se queda el valor con al menos dos votos. Corre antes del
gancho de contacto. El gancho de contacto está apagado, así que el voto es
la última palabra sobre `telefono_movil`.

### Campos que el formulario no tiene

Se quitaron del prompt y, si el modelo los emite, se filtran:
`lugar_expedicion`, `genero`, `estado_civil`. Quitar `lugar_expedicion` y
volver a medir movió el literal de 76,2 % a 76,1 %. Género y estado civil
se sacaron del JSON ya medido, sin una corrida nueva de los 100.

## Lo que se midió y quedó apagado

No lo prendas con este VL 7B. El código y el comentario del flag explican
el porqué.

| Flag | Default | Medición |
| --- | --- | --- |
| `LEER_APELLIDO` | 0 | Recorte x4 de primer apellido. 1 acierto y 16 empeoramientos. Exacto del campo 73 % → 58 %. |
| `LEER_CONTACTO` | 0 | Recorte x3 de correo y teléfonos. No sube el exacto. Varios `telefono_movil` del gold están truncados a propósito (`telefono_ok=INCOMPLETO`). |

## Hallazgos revisados que no se cambiaron

No corrijas el gold ni la fórmula por tu cuenta. Quedaron así porque quien
revisa el visor no pidió el cambio.

**Teléfono `6000000087`.** El modelo leyó `3125115026`, que es lo que está
en la foto. El gold dice `312511507`, con `telefono_ok=INCOMPLETO` y una
nota de que el móvil está truncado. El campo es estricto, así que la celda
vale 0. El gold no es un prefijo del número de 10 dígitos. En los 100
móviles: 31 de 50 marcados `SI` coinciden; 26 de los `INCOMPLETO` son un
prefijo del valor leído; `6000000087` está entre los 11 `INCOMPLETO` que
ni siquiera son prefijo. Sacar del denominador los que no son `SI` habría
dejado el literal viejo en 1.360 / 1.750 = 77,7 %. No se hizo.

**Nivel de estudio `6000000084`.** Gold `TECNICO`, predicción `PROFESIONAL`,
`fuente=casilla_visual`, `marcadas=1`, confianza declarada 95. Los interiores
de los cinco cuadritos de esa fila midieron blanco (mínimo de pixel 255) en
los cuadrados detectados. El modelo igual reportó una marca en PROFESIONAL.
`nivel_estudio` usa las reglas cortas, que en una fila en blanco pueden
devolver una marca. No se cambió la regla. En el lote hay otros cinco
desacuerdos de este campo (tres `TECNICO` leídos vacíos, uno `PROFESIONAL`
vacío, uno `BACHILLERATO` leído `TECNICO`).

**Discapacidad.** No recibió el mismo tratamiento que braille. Comparte
`pie_resto` con etnia, escala 2, reglas largas. 82 exactos y 18 fallos.
14 fallos son gold `NINGUNA` con `marcadas=2`: el código deja el campo
vacío. Documentos: 0014, 0026, 0039, 0042, 0046, 0053, 0063, 0069, 0083,
0085, 0086, 0087, 0093, 0097. El JSON guardado solo tiene el conteo de
marcas, no cuáles cuadritos eran. La regla propuesta y no implementada: si
hay exactamente dos marcas y una es `NINGUNA`, conservar `NINGUNA`. Hace
falta releer esos recortes antes de subirla. `6000000058` tiene gold
`VISUAL` con nota de que estaban marcadas `NINGUNA` y `VISUAL`; esa regla
lo dejaría mal. No partas el recorte `pie_resto`.

**Dirección y correo, formato.** Canon de vía, espacios, `#` y guiones
subiría el exacto literal de dirección de 25 a 45, y una clave alfanumérica
a 48. En correo, quitar espacios, puntuación final y `.con` suma 3 exactos.
Juntos, +26 exactos literales → 1.396 / 1.800 = 77,6 % en la métrica vieja
de coincidencia literal. Después de normalizar el formato, 19 direcciones
quedan a distancia 1 (12 de dígito, 7 de letra) y 15 a distancia 2. Tratar
distancia ≤ 1 como exacto llega a 79,7 % literal y mete en la misma bolsa
`#22` y `#27`. Distancia ≤ 2 solo en letras llega a 80 % literal y trata
Calle y Carrera como la misma vía. No se implementó. La métrica publicada
es el promedio de celda, donde una letra distinta ya aporta su similitud
(dirección 90,3, correo 93,1) sin declararlas exactas.

## Visor

Repositorio aparte: `shell931/e3-pages`, rama `main`. GitHub Pages sirve
https://shell931.github.io/e3-pages/. El HTML está en `index.html`. Los
resultados van cifrados en `data/vault.json` (AES-GCM; la clave sale de
usuario, contraseña, salt e iteraciones del propio vault).

En el servidor, el fragmento se arma con
`~/test-ia-local/caso-1-v2-e3/scripts/build_parte8_fragment.py` y se mete
al vault con `add_parte8.py`. Las variables `E3_VAULT_USER`, `E3_VAULT_PASS`
y `E3_PAGES_TOKEN` existen en el entorno de quien publica. No las escribas
en el repo, en el chat ni en este documento.

Parte 8 en `index.html` (`SPECS.parte8`): sin frase bajo el título, sin
línea de “terminó el load test”, sin KPI de docs/h, sin párrafo de
confianza bajo los KPI, sin columna Exacto, sin la nota bajo la tabla de
campos, sin la línea de IDs y sin el pie de VRAM (`hideMeta`, `hideFoot`).
Sigue el recuadro **Cómo se calcula Oficial (vs gold)**, debajo de la lista
de documentos, con la fórmula, la etiqueta `expresion regular` y el ejemplo
de `Cra 93 B` / `cra 93 a`.

`tieneExacto` es verdadero si algún campo trae la clave `exacto`. Parte 8
la trae, y por eso la interfaz usa Promedio. Si quitas `exacto` del
fragmento, Parte 8 vuelve a la copia vieja de “Oficial = coincidencia
exacta”. El JSON puede guardar `exacto`; la columna no se renderiza.

Pages cachea `index.html` unos 10 minutos. Un query string en `index.html`
no invalida la CDN. Quien mira el visor tiene que recargar con
Ctrl+Shift+R o Cmd+Shift+R. La descarga de `data/vault.json` va con
`cache: "no-store"`.

Abrir un pull request de `e3-pages` desde el agente falla por permisos de
colaborador. Los cambios del visor se publican con push a `main` de
`shell931/e3-pages`.

## Cómo volver a medir

Solo si lo piden. Una corrida nueva mueve campos que ya se dieron por
buenos (casillas, tipo de documento, la lógica de dirección, braille).

1. Copiar los workers al mount del servidor y reiniciar los contenedores
   OCR y NLP, no vLLM, salvo que el cambio sea del modelo.
2. Correr el lote en el servidor (Rabbit, `load_test_simple.py`, consumir
   el jsonl dentro del contenedor OCR). Imágenes en
   `/data/e3/front/60000000xx.tif`, unos 2505×2194.
3. Armar predicciones con `id` = `doc_id` y `estado` = `listo`.
   Gold: `/data/e3/gold/gold.json` (transcripción del 15 ago 2026,
   regenerado el 17 ago; 97 de 100 tienen `necesita_revision=SI`).
   El gold no incluye `lugar_expedicion`, `genero`, `estado_civil` ni
   `votara`.
4. `compare_gold_real.py` del servidor. Confirmar que el agregado sigue
   siendo el promedio de `conf_real` por celda y que la clave `exacto` del
   JSON por campo sigue siendo el porcentaje literal. Un parche anterior
   guardó el promedio dentro de `exacto`; eso ya se corrigió y no hay que
   revertirlo.
5. `build_parte8_fragment.py` y `add_parte8.py`, push del HTML si cambió,
   y avisar el hard refresh.

En el host del servidor no está PIL. Los recortes de diagnóstico se hacen
con `docker exec -i caso1v2e3e3-ocr python3`. Escribe el script en un
archivo local y súbelo con `scp`; un Python embebido en comillas de SSH
pierde las f-strings.

## Reglas para el siguiente agente

- El KPI que se presenta es el 87,8 %, promedio de celda. No vuelvas a
  poner la columna Exacto ni el 76,1 % en el visor.
- No trates distancia de edición 1 como coincidencia exacta. `#22` y `#27`
  no son la misma dirección.
- No cambies el gold ni `ESTRICTOS` para subir el número. El teléfono
  `6000000087` y varios `INCOMPLETO` son fallos del gold; la celda en 0 es
  la fórmula, no una lectura mala.
- No reejecutes los 100 salvo pedido explícito. Si reejecutas, no toques
  la lógica ya revisada de casillas, `tipo_documento`, dirección y
  `lee_braille`.
- No actives `LEER_APELLIDO` ni `LEER_CONTACTO` con Qwen2.5-VL-7B.
- No separes discapacidad y etnia en dos recortes.
- No copies el prompt de “vacío frecuente” de braille a discapacidad sin
  una medición nueva.
- No digas en una reunión que el modelo pesa 88 GB. Pesa ~16 GiB el VL y
  ~5 GiB el NLP. 88 GB y 40 GB son la reserva de vLLM.
- La inferencia corre en el servidor. Medir en la máquina del agente no
  es el resultado oficial.
- Si piden “solo teoría”, no edites código, no publiques el visor y no
  lances el lote.
- Secretos de vault y tokens de GitHub no van al repositorio ni a la
  respuesta.

## Dónde está cada cosa

| Qué | Dónde |
| --- | --- |
| Este documento | `docs/parte8-resultados.md` en `shell931/ov-ia-caso-1-e3-ocr-forms` |
| Workers | `workers/ocr_worker.py`, `nlp_worker.py`, `casillas_vision.py`, `direccion_vision.py`, `primer_apellido_vision.py`, `contacto_vision.py`, `postprocess_express.py` |
| Copia que ejecuta el servidor | `~/test-ia-local/caso-1-v2-e3/workers` |
| Comparador y fragmento | `~/test-ia-local/caso-1-v2-e3/scripts/` en el servidor. No están en este git |
| Gold e imágenes | `/data/e3/gold/gold.json`, `/data/e3/front/` |
| Visor | `shell931/e3-pages` `index.html` y `data/vault.json`, rama `main` |
