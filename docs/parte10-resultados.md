# Parte 10 — lector dedicado de dígitos (cédula + celular)

Corrida aparte de Parte 8 y Parte 9. El menú **Parte 10** del visor no
pisa las anteriores.

## Qué cambió

1. **`workers/digitos_vision.py`**: recortes ampliados de
   `numero_documento`, `telefono_movil` y `telefono_fijo`, leídos con el
   mismo Qwen2.5-VL-7B a temperatura 0. Escala 2 (escala 4 confundía 7/6).
   Caja de cédula calibrada a `0.02–0.55 × 0.33–0.41`.
2. **`ocr_worker.py`**: `LEER_DIGITOS=1` por defecto; emite
   `digitos_vision` en la salida OCR.
3. **`nlp_worker.py`**: el recorte entra al voto numérico solo si el
   formato es plausible (móvil 10 dígitos que empiezan por 3; cédula
   8–10). `aplicar_digitos` es conservador; **no** pisa teléfono fijo
   (el recorte mezclaba el móvil).

No se cuantizó el VL: GPU0 sigue ~90 GB reservados; no hay VRAM libre
para un segundo modelo.

## Números

| Métrica | Parte 8 | Parte 9 | Parte 10 |
| --- | ---: | ---: | ---: |
| Contra gold original | 87,8 % | 87,7 % | **88,4 %** |
| Contra gold_v2 | — | 88,9 % | **89,6 %** |
| numero_documento | 86 % | 87 % | **88 %** |
| telefono_movil (gold / gold_v2) | 41 / — | 40 / 58 | 40 / 58 |
| tipo_discapacidad | 82 % | 90 % | 91 % |

El KPI de Parte 10 es el **89,6 % vs gold_v2**. La misma corrida mide
**88,4 %** contra el gold original (sube respecto a Parte 8/9).

## Cómo repetir

Workers en la rama `cursor/parte10-digitos-b8cd` (o `main` tras merge).
En el servidor AWS:

```bash
# LEER_DIGITOS=1 (default). Reiniciar ocr + nlp, purgar colas, 100 docs.
python3 scripts/compare_gold_real.py /data/e3/gold/gold.json \
  /data/e3/preds_parte10.json "" parte10
python3 scripts/compare_gold_real.py /data/e3/gold/gold_v2.json \
  /data/e3/preds_parte10.json "" parte10v2
```

Visor: https://shell931.github.io/e3-pages/ — menú Parte 10. Hard refresh.
