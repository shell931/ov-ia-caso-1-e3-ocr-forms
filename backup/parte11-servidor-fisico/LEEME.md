# Backup Parte 11 — casillas NINGUNA≥2 + throughput

Carpeta **independiente** del pipeline medido como **Parte 11**
(27 sep 2026). No pisa Parte 8/9/10 del visor.

| Métrica | Parte 10 | Parte 11 |
| --- | ---: | ---: |
| vs `gold.json` | 88,4 % | 88,4 % |
| vs `gold_v2` (**KPI**) | **89,6 %** | 89,5 % |
| `tipo_discapacidad` | 91 % | **92 %** |
| docs/h (meta 1250) | 872 | ~**880** |

Visor: https://shell931.github.io/e3-pages/ — menú **Parte 11**.
Detalle: `docs/parte11-resultados.md` en la raíz del repo.

## En una frase

Tres tweaks post–Parte 10: ampliar la regla NINGUNA de discapacidad,
omitir la pasada VL de teléfono fijo, y reforzar el prompt de
nombres/email. KPI global **plano** (jitter); no reemplaza Parte 10
como mejor resultado. Sí conviene quedarse con NINGUNA≥2.

## Qué cambió vs Parte 10

| Archivo | Cambio |
| --- | --- |
| `workers/casillas_vision.py` | `marcadas == 2` → `marcadas >= 2` si hay `NINGUNA` |
| `workers/casillas_vision.py` | Prompt: X fina cuenta en nivel/braille |
| `workers/digitos_vision.py` | No llama VL a `telefono_fijo` (`DIGITOS_LEER_FIJO=0`) |
| `workers/ocr_worker.py` | Orden apellidos/nombres + letras parecidas en email |

Stack Docker / colas / modelos: **igual** que Parte 10.

## Flujo (diagrama)

```mermaid
flowchart TB
  subgraph ingress["1. Entrada — igual P10"]
    TIF["TIFF /data/e3/front/"]
    ENQ["enqueue 100 docs"]
    TIF --> ENQ --> Q1["RabbitMQ ocr_input"]
  end

  subgraph ocr["2. OCR · 8 workers"]
    OW["ocr_worker.py"]
    Q1 --> OW
    OW --> VL["vLLM GPU0 :8001\nQwen2.5-VL-7B\npágina + voto + dirección"]
    OW --> CAS["casillas_vision.py\nNINGUNA si marcadas ≥ 2"]
    OW --> DIG["digitos_vision.py\ncédula + móvil\nDIGITOS_LEER_FIJO=0"]
    VL --> PACK["JSON doc_id"]
    CAS --> PACK
    DIG --> PACK
    PACK --> Q2["ocr_output"]
  end

  subgraph nlp["3. NLP · 12 workers"]
    Q2 --> NW["nlp_worker.py"]
    NW --> LLM["vLLM GPU1 :8000\nQwen2.5-7B-AWQ"]
    LLM --> APL["aplicar_digitos / casillas / dirección"]
    APL --> Q3["nlp_output"]
  end

  subgraph eval["4. Medición"]
    Q3 --> CON["resultados_parte11.jsonl"]
    CON --> CMP["compare vs gold + gold_v2"]
    CMP --> VIS["visor e3-pages · Parte 11"]
  end
```

## Qué hay aquí

| Ruta | Qué es |
| --- | --- |
| `LEEME.md` | Este archivo |
| `IMPLEMENTACION.md` | Detalle técnico de los 3 cambios |
| `workers/` | Python del día de la medición |
| `docker-compose.yml` | Stack sin VL-small (igual P10) |
| `scripts/` | Fragmento + inyección al vault |
| `kpis/` | Agregados vs gold / gold_v2 (**sin PII**) |

## Redeploy rápido

Mismos pasos que `backup/parte10-servidor-fisico/LEEME.md`
(TIFF + gold aparte, `docker compose up`, enqueue 100, comparar).
Flags: `LEER_DIGITOS=1`, `LEER_CASILLAS=1`, `DIGITOS_LEER_FIJO=0`.
