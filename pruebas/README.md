# Pruebas — índice

Cada prueba se identifica por **dos cosas**, siempre juntas:

- **Lote**: el conjunto de formularios y su gold. Cambia los números aunque el
  pipeline sea el mismo.
- **Parte N**: la versión del pipeline (modelos, lectores, reglas). La numeración
  es global y no se reinicia al cambiar de lote.

Por eso **"Lote E3V2 · Parte 10"** no es la Parte 10 original: es el pipeline de
la Parte 10 corrido sobre otro lote y otro gold. Un KPI solo se compara contra
otro **del mismo lote**.

| Lote | Datos | Gold | Carpeta |
| --- | --- | --- | --- |
| **L1** | 1.251 frentes 300 dpi | `gold` / `gold_v2` (teléfonos confirmados por foto) | [`lote1-1251/`](lote1-1251/) |
| **L1-finger** | huellas 500 dpi | — | (sin archivos en el repo) |
| **L2 · E3V2** | 267 frentes 300 dpi (`s3://forme3/E3V2/front_300`) | `gold_e3` (21 campos) | [`lote2-e3v2/`](lote2-e3v2/) |

## Cruce con el visor

Visor: <https://shell931.github.io/e3-pages/>. La columna "Visor" es el texto
del menú.

| Lote | Parte | Qué cambia | KPI `conf_real` | Visor | Carpeta |
| --- | --- | --- | --- | --- | --- |
| L1 | 1 | Frente, primera corrida | — | `L1 · P01 · Frente` | — |
| L1-finger | 2 | Huellas 500 dpi | — | `L1-finger · P02 · Huellas` | — |
| L1 | 3 | Repetición de la 1 con bug NLP de braille corregido | — | `L1 · P03 · Frente (repetición)` | — |
| L1 | 4 | 2× RTX PRO 6000: VL-7B GPU0 + NLP-7B GPU1 | 72,6 % | `L1 · P04 · 2 GPU frente` | [`parte-04`](lote1-1251/parte-04/) |
| L1 | 5 | Repetición limpia de la 4 | — | `L1 · P05 · 2 GPU frente (repetición)` | — |
| L1-finger | 6 | Huellas en 2× GPU | — | `L1-finger · P06 · 2 GPU huellas` | — |
| L1 | 7 | VL-32B-AWQ | — | `L1 · P07 · VL 32B` | — |
| L1 | 8 | Mejoras + casillas | 87,8 % (gold) | `L1 · P08 · mejoras + casillas (87.8%)` | [`parte-08`](lote1-1251/parte-08/) |
| L1 | 9 | gold_v2 teléfonos + discapacidad | 88,9 % (gold_v2) | `L1 · P09 · gold_v2 teléfonos + discapacidad (88.9%)` | [`parte-09`](lote1-1251/parte-09/) |
| L1 | 10 | Lector de dígitos (cédula, celular) | **89,6 %** (gold_v2) | `L1 · P10 · dígitos cédula + celular (89.6%)` | [`parte-10`](lote1-1251/parte-10/) |
| L1 | 11 | Casillas NINGUNA ≥ 2 + throughput | 89,5 % (gold_v2) | `L1 · P11 · casillas NINGUNA≥2 + throughput (89.5%)` | [`parte-11`](lote1-1251/parte-11/) |
| L1 | 12 | VL-3B para dígitos/casillas — **descartado** | 71,0 % (gold_v2) | `L1 · P12 · VL 3B dígitos/casillas, descartado (71.0%)` | [`parte-12`](lote1-1251/parte-12/) |
| L2 | 10a | Pipeline Parte 10 tal cual | 92,2 % | `L2 · P10a · pipeline P10 tal cual (92.2%)` | [`parte-10`](lote2-e3v2/parte-10/) |
| L2 | 10b | + comunidad tapada | 92,1 % | `L2 · P10b · comunidad tapada (92.1%)` | [`parte-10`](lote2-e3v2/parte-10/) |
| L2 | 10c | + campo `comunidad_etnia` | 92,1 % | `L2 · P10c · comunidad_etnia (92.1%)` | [`parte-10`](lote2-e3v2/parte-10/) |
| L2 | 10d | + solo E-3 (recorta el E-4) | 93,4 % | `L2 · P10d · comunidad_etnia + solo E-3 (93.4%)` | [`parte-10`](lote2-e3v2/parte-10/) |
| L2 | 10e | + dirección sin inventos | 93,2 % | `L2 · P10e · dirección sin inventos (93.2%)` | [`parte-10`](lote2-e3v2/parte-10/) |
| L2 | 14 | Cédula + nombre del funcionario (256 con funcionario) | 92,4 % | `L2 · P14 · funcionario, 256 formularios (92.4%)` | [`parte-14`](lote2-e3v2/parte-14/) |
| L2 | 15 | VL Qwen3.6-27B-FP8 dual — **oficial** | **95,7 %** | `L2 · P15 · Qwen3.6-27B-FP8 dual (95.7%)` | [`parte-15`](lote2-e3v2/parte-15/) |
| L2 | 16 | Parte 15 en Turing (g4dn.metal, 4× T4) | 95,5 % | `L2 · P16 · g4dn.metal 4× T4 · 27B-FP8 (95.5%)` | [`parte-16`](lote2-e3v2/parte-16/) |
| L2 | 16b | Control VL 7B en Turing | 92,6 % | `L2 · P16b · g4dn.metal 2× T4 · control VL 7B (92.6%)` | [`parte-16`](lote2-e3v2/parte-16/) |

Las Partes 1 a 7 solo existen en el visor. La Parte 13 no existe.

## Qué hay en cada carpeta `parte-NN/`

| Archivo | Qué es |
| --- | --- |
| `resultados.md` | Informe: qué se cambió, KPI por campo, decisión. |
| `gold-kpis.json` / `kpis/*.json` | KPIs contra el gold, sin PII. En L2 · Parte 10 hay uno por variante (`10a`…`10e`). |
| `servidor/` | Snapshot para redesplegar esa parte tal cual (compose, workers, scripts, `LEEME`, `MANIFEST`). Se copia entero al servidor. |

La Parte 9 no tiene `servidor/` propio: usa el de la Parte 8 (`parte-08/servidor/PARTE9.md`).

## Convención para una prueba nueva

1. Número de Parte siguiente (global, nunca se reutiliza).
2. Carpeta `pruebas/<lote>/parte-NN/` con `resultados.md`, KPIs sin PII y, si
   gana, `servidor/`.
3. En el visor, el nombre empieza por lote y parte: `L2 · P17 · <qué cambia> (KPI)`.
4. Agregar la fila a la tabla de arriba.

Los planteamientos de infraestructura (hardware nuevo, despliegues) van en
[`../planteamientos/`](../planteamientos/), no acá.
