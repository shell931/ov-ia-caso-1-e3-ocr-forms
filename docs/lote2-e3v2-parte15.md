# Lote E3V2 · Parte 15 (Qwen3.6-27B-FP8 dual)

Corrida del 6 oct 2026 sobre los **267** frentes de `/data/e3/front`
(`s3://forme3/E3V2/front_300/`) con las tres mejoras pedidas sobre la
Parte 14:

1. **Modelo VL más grande** — ganador `Qwen/Qwen3.6-27B-FP8` en perfil
   **doble** (réplicas en `:8001` y `:8002`).
2. **Confianza real vía logprobs** (`LEER_LOGPROBS=1`, `LP_MARCAR=1`,
   `LP_UMBRAL=80`) → marca `revisar` cuando `conf_lp` cae bajo el umbral.
3. **Normalización de formato de dirección** (`DIR_NORMALIZAR=1`): espacios
   alrededor de `-`, `N°`/`Nº`→`N`, quitar punto final. **No** expandir
   `CL`→`CALLE` (el gold es literal).

| Métrica | Parte 14 (7B) | Parte 15 (27B-FP8 dual) |
| --- | ---: | ---: |
| KPI oficial `conf_real` (21 campos) | **92,4 %** | **95,7 %** |
| Exacto celda a celda | 81,6 % | 87,0 % |
| docs/h | ~852 | **934** |
| Errores de corrida | 0 | 0 |
| Campos marcados `revisar` | ~85 | 1233 |
| Exactitud tras revisar (`LP_UMBRAL=80`) | — | **97,2 %** |
| AUC `conf_lp` vs declarada | — | **92,0** / 47,8 |

Baseline 7B con el **código P15** en los 267: **92,3 %** @ 853 docs/h
(ruido vs Parte 14). La ganancia viene del modelo VL, no del cableado.

## Screening muestra 80 (`random.seed(15)`)

| Config | KPI | docs/h | AUC `conf_lp` |
| --- | ---: | ---: | ---: |
| qwen25vl-7b (baseline muestra) | 91,2 % | — | 87,7 |
| qwen25vl-32b | 86,5 % | 202 | 90,2 |
| qwen25vl-72b-awq | 92,3 % | 167 | 92,9 |
| qwen3vl-32b | 92,8 % | 226 | 83,0 |
| qwen38-27b | 94,5 % | 281 | 93,1 |
| qwen36-27b | 95,5 % | 281 | 91,7 |
| qwen36-27b-rapido | 95,5 % | 416 | 91,5 |
| qwen36-27b-fp8-rapido | 95,2 % | 585 | 91,2 |
| **qwen36-27b-fp8-doble** | **95,3 %** | **966** | 91,3 |
| fp8-doble + `LEER_CONTACTO`/`LEER_APELLIDO` | 95,1 % | 825 | 91,5 |

**No activar** `LEER_CONTACTO=1` / `LEER_APELLIDO=1` con este modelo: email
empeora (49 → 36 % en la muestra).

## Deltas por campo (exacto %, P14 → P15)

| Campo | P14 | P15 | Δ |
| --- | ---: | ---: | ---: |
| direccion | 15,7 | 32,6 | +16,9 |
| funcionario_cedula | 73,8 | 88,8 | +15,0 |
| funcionario_nombre | 52,1 | 64,4 | +12,3 |
| email | 41,6 | 51,7 | +10,1 |
| etnia | 90,3 | 99,6 | +9,3 |
| lee_braille | 91,4 | 99,6 | +8,2 |
| ciudad | 90,3 | 96,6 | +6,3 |
| telefono_movil | 75,7 | 80,1 | +4,4 |

Dirección sigue siendo el cuello de botella de lectura (no de formato):
`DIR_NORMALIZAR` suma poco; el salto grande lo da el 27B.

## Política `revisar` (full 267)

Con `LP_UMBRAL=80` (único): ~22 % celdas marcadas, atrapa ~79 % de errores,
exactitud tras revisión humana de las marcadas ≈ **97,2 %**. AUC de
`conf_lp` **92,0** vs confianza declarada **47,8**.

## Visor

Menú **Lote E3V2 · Parte 15 (Qwen3.6-27B-FP8 dual, 95.7%)** (clave
`lote2p15`). https://shell931.github.io/e3-pages/

KPIs sin PII: `docs/lote2-parte15-gold-kpis.json`.
Backup completo: `backup/parte-15-servidor-fisico/`.
