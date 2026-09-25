# Parte 10 — lector dedicado de dígitos

Se midió y publicó como **Parte 10** en el visor
(https://shell931.github.io/e3-pages/, menú Parte 10). Parte 8 y Parte 9
no se tocaron.

Detalle en `docs/parte10-resultados.md` en la raíz del repo.

## Resumen de números

| Métrica | Parte 8 | Parte 9 | Parte 10 |
| --- | ---: | ---: | ---: |
| Contra `gold.json` | 87,8 % | 87,7 % | **88,4 %** |
| Contra `gold_v2` | — | 88,9 % | **89,6 %** |
| `numero_documento` | 86 % | 87 % | **88 %** |
| `telefono_movil` (gold / gold_v2) | 41 / — | 40 / 58 | 40 / 58 |

KPI de Parte 10 = **89,6 %** vs `gold_v2`.

## Qué se añadió

- `workers/digitos_vision.py` (nuevo)
- Enganche en `ocr_worker.py` (`LEER_DIGITOS=1`) y `nlp_worker.py`
  (voto + `aplicar_digitos`)
- Sin cuantizar VL: no hacía falta (GPU0 ~90 GB ocupados, sin hueco
  para otro modelo)

### Reglas conservadoras

- Móvil solo vota/aplica si son 10 dígitos empezando por 3
- Cédula solo si 8–10 dígitos; no acorta un NLP más largo
- Teléfono fijo: se lee el recorte pero **no** se aplica (contaminaba)

## Medir

```bash
python3 scripts/compare_gold_real.py /data/e3/gold/gold.json \
  /data/e3/preds_parte10.json "" parte10
python3 scripts/compare_gold_real.py /data/e3/gold/gold_v2.json \
  /data/e3/preds_parte10.json "" parte10v2
```

Los workers de esta carpeta de backup se actualizan a la versión Parte 10
(incluye dígitos). Para reinstalar solo Parte 8/9, usa el commit anterior
a Parte 10.
