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
| KPI conf_real | **No disponible**: el lote no tiene gold todavía |

Visor: https://shell931.github.io/e3-pages/ — menú **Lote E3V2 . Parte 10**.
La confianza que muestra es la **declarada** por el extractor, no la
oficial; no se puede comparar con el 89,6 % de Parte 10.

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

## Para tener KPI oficial

Hace falta `gold.json` de estos 267 (mismo formato que el gold de Parte 10).
Con el gold en `/data/e3/gold/`, se corre:

```bash
python3 scripts/compare_gold_real.py /data/e3/gold/gold_lote2.json \
  /data/e3/preds_lote2.json "" lote2
```

Scripts de la corrida: `scripts/lote2/`.
