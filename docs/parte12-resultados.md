# Parte 12 — VL 3B solo para dígitos/casillas

Experimento de throughput de `MEJORAS-FUTURAS.md` §A.4:
segundo vLLM con **Qwen2.5-VL-3B-Instruct** en GPU1 `:8002`;
crops de dígitos y casillas ahí; página / voto / dirección en el 7B (GPU0).

**No reemplaza el KPI de Parte 10.** Calidad casillas se derrumba;
docs/h no mejora.

## Qué se aplicó

| Pieza | Cambio |
| --- | --- |
| `docker-compose.yml` | servicio `vllm-vl-small` (3B, GPU1, util 0.45) |
| `ocr_worker.py` | `VLLM_VL_SMALL_URL` → `_cliente_crops()` para casillas + dígitos |
| Flags en corrida | `VLLM_VL_SMALL_URL=http://vllm-vl-small:8000/v1` |

Tras medir: contenedor 3B detenido; `VLLM_VL_SMALL_URL=""` (vuelve al 7B).

## Números (100 docs)

| Métrica | Parte 10 | Parte 12 (3B crops) |
| --- | ---: | ---: |
| vs gold | **88,4 %** | 69,8 % |
| vs gold_v2 | **89,6 %** | 71,0 % |
| numero_documento | 88 % | 84 % |
| tipo_documento | ~95 % | **28 %** |
| nivel_estudio | 94 % | **1 %** |
| lee_braille | 91 % | **19 %** |
| tipo_discapacidad | 91–92 % | **11 %** |
| docs/h (meta 1250) | 872 | **872** |

Wall-clock ~413 s → ~872 docs/h. El cuello sigue siendo la página completa
en el 7B; mover crops a 3B no acerca a 1250.

## Conclusión

- **Qwen2.5-VL-3B no sirve** para casillas E3 (ni tipo_documento) en este layout.
- Cédula aguanta mejor (−4 pp) pero no justifica el desplome global.
- Throughput: sin ganancia; hay que atacar pasadas del 7B (voto, página) o
  perfil vLLM, no un segundo modelo más chico para casillas.
- Código queda con el cableado opcional (`VLLM_VL_SMALL_URL`); default vacío.

Backup redeploy: `backup/parte12-servidor-fisico/` (LEEME + Mermaid).
Visor: https://shell931.github.io/e3-pages/ — menú **Parte 12** (hard refresh;
marcado como experimento descartado).
