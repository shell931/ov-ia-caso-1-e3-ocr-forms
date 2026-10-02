# Lote E3V2 — pipeline Parte 10 en servidor nuevo

Corrida del pipeline **Parte 10 tal cual** (`backup/parte10-servidor-fisico/`)
sobre un lote nuevo de formularios, en un servidor AWS nuevo (2 oct 2026).

| Dato | Valor |
| --- | --- |
| Servidor | `18.188.49.114`, g7e.12xlarge, 2× RTX PRO 6000 Blackwell |
| Imágenes | `s3://forme3/E3V2/front_300/` (267 frentes, 300 dpi) |
| Ids | `6000000030`–`6000000318` |
| Procesados | 267/267, 0 errores |
| Tiempo | 18 min 21 s |
| Throughput | **873 docs/h** (Parte 10 original: 872) |
| KPI conf_real | **92,2 %** vs `gold_e3` (267 docs, 4775 celdas) |

Visor: https://shell931.github.io/e3-pages/ — menú **Lote E3V2 . Parte 10**.
Es otro lote y otro gold: el 92,2 % no se compara uno a uno con el 89,6 %
de Parte 10 (vs `gold_v2`).

También se bajó `s3://forme3/E3V2/finger_500/` (267, 500 dpi) a
`/data/e3/finger/`; Parte 10 solo usa el frente.

## Preparación del servidor

El servidor nuevo es un clon del anterior y necesitó tres arreglos antes
de poder seguir el LEEME de Parte 10:

1. **Driver NVIDIA**: el kernel `7.0.0-1013-aws` no tenía módulo.
   Se instaló `linux-modules-nvidia-595-open-7.0.0-1013-aws`.
   Ojo: grub ya tiene `7.0.0-1014-aws`; si reinicia con ese kernel hay
   que instalar el módulo correspondiente.
2. **Disco de datos**: `nvme1n1` (3,5 TB) sin formato → ext4 en `/data`
   (en `/etc/fstab`).
3. **Docker**: el disco raíz tiene 6,9 GB. `data-root` de Docker en
   `/data/docker` y `/var/lib/containerd` montado (bind) desde
   `/data/containerd`. Runtime NVIDIA vía `nvidia-ctk`.

Después: stack tal cual (`docker compose up -d`), modelos descargados a
`/data/hf-cache`, mismo reparto de VRAM que Parte 10 (GPU0 ~87 GB VL,
GPU1 ~40 GB NLP).

## Nombres de archivo

En S3 los archivos vienen como `000000010010101;6000000030.tif`. Se
copian a `/data/e3/front/6000000030.tif` (el `doc_id` es lo que va
después del `;`). Copias, no symlinks: los contenedores solo montan
`/data/e3`.

## Campos vacíos (de 267)

| Campo | Vacíos |
| --- | ---: |
| telefono_fijo | 186 |
| etnia | 100 |
| segundo_nombre | 40 |
| lee_braille | 26 |
| tipo_discapacidad | 23 |
| nivel_estudio | 22 |
| telefono_movil | 11 |
| segundo_apellido | 10 |

## KPI oficial vs gold_e3

Gold: `gold_e3.csv` (transcripción del operador, 267 filas, mismos ids).
En el servidor: `/data/e3/gold/gold_lote2.json`. No va a git (PII).
Agregado sin PII: [`lote2-gold-kpis.json`](lote2-gold-kpis.json).

| Campo | conf_real | exacto | conf. declarada |
| --- | ---: | ---: | ---: |
| tipo_documento | 100,0 | 100,0 | 94,9 |
| formulario_no | 99,6 | 99,6 | 91,4 |
| ciudad | 97,0 | 91,0 | 97,3 |
| nivel_estudio | 95,1 | 95,1 | 94,2 |
| primer_nombre | 94,7 | 83,9 | 98,3 |
| email | 94,2 | 41,0 | 96,4 |
| primer_apellido | 94,0 | 80,1 | 98,5 |
| fecha_inscripcion | 93,6 | 93,6 | 95,0 |
| fecha_expedicion | 93,6 | 93,6 | 94,6 |
| segundo_apellido | 93,6 | 80,5 | 94,5 |
| segundo_nombre | 93,6 | 83,9 | 81,9 |
| tipo_discapacidad | 93,3 | 93,3 | 90,7 |
| lee_braille | 90,3 | 90,3 | 94,5 |
| direccion | 89,9 | 16,1 | 93,6 |
| telefono_fijo | 88,2 | 88,2 | 21,5 |
| numero_documento | 86,1 | 86,1 | 99,6 |
| etnia | 85,8 | 85,8 | 91,1 |
| telefono_movil | 75,7 | 75,7 | 80,0 |
| **Total** | **92,2** | 82,1 | 89,8 |

Lo más débil: `telefono_movil` (75,7) y `numero_documento` (86,1, con
99,6 declarado: es la brecha más peligrosa). 228 celdas salen con 100 %
declarado y son distintas al gold.

### Cómo se pasó el CSV a gold.json

`scripts/lote2/gold_csv_to_json.py` aplica las mismas normalizaciones que
el pipeline aplica a su salida:

- Casillas con 2 o más marcas → vacío (el pipeline deja vacío con
  `marcadas≥2`): etnia 13, braille 6, discapacidad 5, nivel 3.
- `CEDULA DE CIUDADANIA` → `CEDULA_CIUDADANIA`, `COM.NEGRAS` →
  `COM_NEGRAS`, `ROM (GITANA)` → `ROM`.
- Teléfonos solo dígitos; `N/A` → vacío; `+57` delante se quita.
- `BOGOTA D.C` / `DC` → `BOGOTA` (`corregir_ciudad` colapsa todo a Bogotá).
- Nombres, correo y dirección quedan tal cual; `compare_gold_real.py`
  ya ignora mayúsculas y tildes.

### Cómo repetir

```bash
python3 scripts/lote2/gold_csv_to_json.py gold_e3.csv /data/e3/gold/gold_lote2.json
python3 scripts/compare_gold_real.py /data/e3/gold/gold_lote2.json \
  /data/e3/preds_lote2.json "" lote2
python3 scripts/lote2/build_lote2_gold_fragment.py \
  /data/e3/resultados_lote2_parte10.jsonl /data/e3/lote2-gold.json \
  /data/e3/lote2-gold-docs.json /data/e3/lote2_parte10_gold_vault_fragment.json \
  873 "18 min 21 s"
python3 scripts/lote2/add_fragment.py <usuario> <clave> data/vault.json \
  lote2_parte10_gold_vault_fragment.json lote2p10   # dentro de e3-pages
```

`preds_lote2.json` sale de `scripts/lote2/preds_lote2.py` (jsonl → `id` = `doc_id` y `estado` = `listo`).
Scripts de la corrida: `scripts/lote2/`.

## Arreglo: "A QUE COMUNIDAD" se leía como discapacidad

Caso `6000000041`: todos los cuadritos de TIPO DE DISCAPACIDAD vacíos (gold
vacío) y el modelo devolvía `NINGUNA` con una sola marca. El recorte
`pie_resto` (x 0,195–0,90) incluía la caja A QUE COMUNIDAD DE LA ETNIA
PERTENECE, con "Ninguna" manuscrito, y el VL lo tomó como la casilla.

Arreglo en `workers/casillas_vision.py`: el recorte mantiene su tamaño, pero
desde x = 0,73 de la página se pinta de blanco (`CASILLAS_PIE_BLANCO_X`).
Copia del worker que corrió en el servidor: `backup/lote2-e3v2-servidor/`.

| Corrida (mismo lote, mismo gold) | KPI | discapacidad | etnia | docs/h |
| --- | ---: | ---: | ---: | ---: |
| Parte 10 tal cual | 92,2 % | 93,3 % | 85,8 % | 873 |
| Recorte angosto (x1 = 0,73), descartado | 92,6 % | 95,1 % | 85,0 % | 897 |
| **Comunidad tapada (oficial)** | **92,1 %** | 93,3 % | 89,1 % | 871 |

- `6000000041` queda vacío (= gold) en las dos variantes.
- En este lote es el único formulario con discapacidad en blanco y
  "Ninguna" escrito en comunidad; los otros 3 vacíos ya salían bien.
- Las diferencias de total son ruido entre corridas: con `temperature=0`
  el batching de vLLM cambia ~30 celdas de etnia entre corridas idénticas
  (±0,3 pts en el total). El recorte angosto se descartó porque cambia la
  escala del recorte; tapar no toca la geometría de lo que ya se validó.

Visor: menú **Lote E3V2 . Parte 10 + comunidad tapada**. La corrida anterior
sigue en su menú. KPIs sin PII: `docs/lote2-comunidad-tapada-gold-kpis.json`.

## Campo nuevo: comunidad_etnia

A QUE COMUNIDAD DE LA ETNIA PERTENECE no lo leía el pipeline. Ahora hay un
lector propio (`workers/comunidad_vision.py`, `LEER_COMUNIDAD=1`): recorte
de la caja (x 0,715–0,975 · y 0,72–0,84), escala 2, VL 7B, transcripción
literal y sin punto final. El gold lo trae literal (Ninguna, No aplica, N/A…).

Variantes medidas sobre los 267 (solo la lectura del campo, vs gold_e3):

| Variante | conf_real | exacto |
| --- | ---: | ---: |
| Primer prompt, y hasta 0,82 | 91,9 % | 81,3 % |
| Sin título impreso, y hasta 0,84, sin punto final | 94,4 % | 89,1 % |
| **Prompt nuevo, y hasta 0,84, sin punto final (elegida)** | **95,3 %** | 90,6 % |

El primer prompt respondía VACIO con texto escrito ("N/A", "Ninguna" bajo el
título) y cortaba textos escritos abajo de la caja.

Corrida completa con el campo (pipeline Parte 10 + comunidad tapada +
comunidad_etnia):

| Métrica | Valor |
| --- | ---: |
| comunidad_etnia | **95,3 %** |
| KPI oficial (19 campos) | **92,1 %** |
| Los 18 campos de antes | 91,9 % (ruido entre corridas: 91,9–92,6) |
| docs/h | 854 (una llamada VL más por documento) |

Pendiente: 10 frentes (`6000000108`, `109`, `141`, `153`, `154`, `194`,
`203`, `237`, `238`, `239`) son una página alta con E-3 + E-4 (2499×3307).
Todos los recortes están en fracciones de página, así que en esas 10 no caen
en su caja (6 de los 16 vacíos de comunidad son de ahí). Arreglo propuesto:
recortar la mitad E-3 antes de procesar.

Visor: menú **Lote E3V2 . Parte 10 + comunidad_etnia**. KPIs sin PII:
`docs/lote2-comunidad-etnia-gold-kpis.json`.
