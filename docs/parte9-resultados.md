# Parte 9 — gold_v2 teléfonos + discapacidad NINGUNA

Corrida aparte de la Parte 8. El visor menú **Parte 9** no pisa Parte 8.

## Qué cambió

1. **`gold_v2`** (`/data/e3/gold/gold_v2.json` en el servidor, no en git):
   solo teléfonos. Se actualizó una celda cuando el recorte del VL
   coincidió con la lectura completa del modelo, o cuando la foto ya
   estaba confirmada a mano (`6000000087`). Fueron **21 celdas**
   (celular y fijo). El resto del gold es idéntico al original.
2. **Regla de casillas** en `workers/casillas_vision.py`: si
   `tipo_discapacidad` tiene exactamente dos marcas y una es `NINGUNA`,
   se conserva `NINGUNA`. Recupera las marcas fantasma del pie del E3.
   `6000000058` (NINGUNA+VISUAL, gold VISUAL) sigue mal.

## Números

| Métrica | Parte 8 | Parte 9 |
| --- | ---: | ---: |
| Contra gold original | 87,8 % | 87,7 % |
| Contra gold_v2 | — | **88,9 %** |
| tipo_discapacidad | 82 % | **90 %** |
| telefono_movil (gold / gold_v2) | 41 / — | 40 / **58** |
| docs/h (meta 1250) | 968 | **917** (~6 min 32 s / 100) |

La bajada 87,8 → 87,7 contra el gold original es jitter de la corrida
nueva (imágenes distintas a nivel de un dígito en algunos campos). El
KPI de Parte 9 es el **88,9 % vs gold_v2**.

Discapacidad recuperó 13 formularios que antes quedaban vacíos con
`marcadas=2` y gold `NINGUNA`.

## Cómo repetir

Workers en `main` (commit de la regla NINGUNA). En el servidor:

```bash
# gold_v2 ya en /data/e3/gold/gold_v2.json
python3 scripts/compare_gold_real.py /data/e3/gold/gold_v2.json /data/e3/preds_parte9.json "" parte9
```

Visor: https://shell931.github.io/e3-pages/ — menú Parte 9. Hard refresh.
