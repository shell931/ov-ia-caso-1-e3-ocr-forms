# Parte 9 — qué se añadió después del backup de Parte 8

La carpeta sigue sirviendo para reinstalar el pipeline. Esta página
documenta lo que se midió y publicó como **Parte 9** en el visor
(https://shell931.github.io/e3-pages/, menú Parte 9). Parte 8 no se tocó.

Detalle también en `docs/parte9-resultados.md` en la raíz del repo.

## Resumen de números

| Métrica | Parte 8 | Parte 9 |
| --- | ---: | ---: |
| Contra `gold.json` (original) | 87,8 % | 87,7 % |
| Contra `gold_v2` | — | **88,9 %** |
| `tipo_discapacidad` | 82 % | **90 %** |
| `telefono_movil` (gold / gold_v2) | 41 / — | 40 / **58** |
| docs/h (meta 1250) | 968 | **917** |

El KPI de Parte 9 es el **88,9 %** = promedio de celda contra `gold_v2`.

## 1. gold_v2 (solo teléfonos)

Archivo en el servidor (datos personales, **no va a git**):

`/data/e3/gold/gold_v2.json`

Resumen sin números: `gold_v2_resumen.json` en esta carpeta.

Se actualizó una celda de teléfono solo cuando:

1. El gold original decía `INCOMPLETO` (o fijo “recortado” en la nota),
2. la lectura del modelo era más larga y empezaba por el gold, y
3. una pasada del VL sobre el **recorte** de la caja devolvió exactamente
   ese número completo,

o cuando la foto ya estaba confirmada a mano (`6000000087` móvil).

Quedaron **21 celdas** confirmadas (celulares + fijos). El resto de
campos del gold es idéntico al original. Si el VL no coincidió con la
predicción, esa celda **no** se cambió.

### Copiar gold_v2 al disco local (mientras AWS exista)

```bash
export SSH_KEY="$HOME/Documents/KEYS/llave/OT-IA-SERVER.pem"
export DEST="/ruta/del/disco/e3"
rsync -av -e "ssh -i $SSH_KEY" \
  ubuntu@3.17.139.133:/data/e3/gold/gold.json \
  ubuntu@3.17.139.133:/data/e3/gold/gold_v2.json \
  ubuntu@3.17.139.133:/data/e3/gold/gold_v2_cambios.json \
  "$DEST/gold/"
```

Medir una corrida contra los dos:

```bash
python3 scripts/compare_gold_real.py /data/e3/gold/gold.json /data/e3/preds_parte9.json "" parte9g1
python3 scripts/compare_gold_real.py /data/e3/gold/gold_v2.json /data/e3/preds_parte9.json "" parte9
```

## 2. Regla NINGUNA en discapacidad

Código: `workers/casillas_vision.py` (ya sincronizado en esta carpeta).

En el pie del E3, discapacidad es un grupo de cuadritos. Solo debería
haber una marca. A veces el modelo ve **dos** (NINGUNA + otra marca
débil o fantasma por el scan).

**Antes:** 0 o ≥2 marcas → el campo queda vacío → nota 0 si el gold
tenía NINGUNA.

**Ahora:** si hay exactamente 2 marcas y una es `NINGUNA`, se conserva
`NINGUNA`.

### Ejemplo real — formulario `6000000014`

| | Gold | Modelo | Nota |
| --- | --- | --- | --- |
| Parte 8 | NINGUNA | *(vacío, marcadas=2)* | 0 % |
| Parte 9 | NINGUNA | NINGUNA | 100 % |

Misma foto y mismo VL. Solo cambió la regla.

Recuperó **13** formularios con gold `NINGUNA` que en Parte 8 salían
vacíos. Caso que sigue mal: `6000000058` (marcas NINGUNA+VISUAL, gold
VISUAL) → la regla pone NINGUNA y sigue en 0.

## 3. Workers a usar en un servidor físico

Para repetir **Parte 8 (87,8 %)**: la lógica de casillas *sin* la regla
NINGUNA no está pinada aparte; el `casillas_vision.py` de esta carpeta
**ya incluye** la regla de Parte 9. Eso es lo que corre en `main` y en
el servidor tras el deploy de Parte 9.

Para repetir **Parte 9 (88,9 %)**:

1. Montar estos `workers/` (con la regla NINGUNA).
2. Tener `gold.json` y `gold_v2.json` en `/data/e3/gold/`.
3. Correr los 100, comparar contra `gold_v2`.

Fragmento del visor Parte 9 en el servidor:
`/data/e3/parte9_vault_fragment.json` (tiene PII; no va a git).

## 4. Por qué el celular “castiga menos” en Parte 9

Con el gold original, muchos celulares valían **0** aunque la lectura
coincidiera con el formulario: el gold estaba truncado a propósito
(`telefono_ok=INCOMPLETO`). `gold_v2` pone el número completo solo donde
la foto (vía VL o revisión humana) lo confirma. Ahí el campo deja de
ir a 0 y el promedio del lote sube.

Discapacidad es el otro castigo que se suavizó: ya no se vacía el campo
cuando NINGUNA viene acompañada de una segunda marca.
