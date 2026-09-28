# Parte 11 — implementación

## Objetivo

Medir tres mejoras baratas post–Parte 10 sin cambiar modelos ni colas.

## Cambios

### 1. Casillas — `NINGUNA` con 2+ marcas

En `parse_bloque` de `casillas_vision.py`, para `tipo_discapacidad`:

- Antes (Parte 9/10): `len(marcadas) == 2` y `"NINGUNA" in marcadas` → `NINGUNA`
- Ahora: `len(marcadas) >= 2` y `"NINGUNA" in marcadas` → `NINGUNA`

Motivo: marcas fantasma en el pie (p.ej. `6000000042` con 3 marcas)
dejaban el campo vacío. Caso conocido que sigue mal: `6000000058`
(NINGUNA+VISUAL, gold VISUAL).

Prompts de nivel/braille mencionan que una X fina cuenta. Se probó
escala×3 + autocontraste en `nivel_estudio` y se **revirtió** (bajaba
docs/h sin ganar braille).

### 2. Throughput — sin VL de fijo

`digitos_vision.py`:

- `CAMPOS` por defecto = `(numero_documento, telefono_movil)`
- `DIGITOS_LEER_FIJO=1` restaura la lectura de fijo (solo depuración)
- `aplicar_digitos` sigue iterando `CAMPOS_TODOS` (fijo no se aplica igual)

Ahorra ~1 pasada VL / doc. No alcanzó meta 1250 docs/h.

### 3. Prompt página — nombres / email

En `ocr_worker.py` (`VLM_PROMPT`): orden de cajas apellido→nombre;
cuidado n/h, m/n, a/o en email. Sin reactivar `LEER_CONTACTO` /
`LEER_APELLIDO`.

## Resultado

KPI plano vs Parte 10. Visor: menú Parte 11 (no como “mejor que P10”).
