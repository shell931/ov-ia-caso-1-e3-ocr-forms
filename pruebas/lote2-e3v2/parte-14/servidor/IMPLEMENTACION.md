# Parte 14 — implementación

## Objetivo

Agregar al Lote E3V2 los dos campos del pie **INFORMACIÓN DEL FUNCIONARIO
ELECTORAL RESPONSABLE DE LA INSCRIPCIÓN** (CÉDULA y NOMBRE), compararlos con
el gold y publicar la corrida completa en el visor.

## Cableado

### `workers/funcionario_vision.py` (nuevo)

- Dos recortes sobre la página ya normalizada por `pagina_e3` (si la página
  traía E-3 + E-4, el pie es el del E-3):
  - `funcionario_cedula`: x 0,04–0,52 · y 0,925–0,995, escala 1. Prompt
    que recorre cuadrito por cuadrito (sin saltar 1 delgados ni dígitos
    repetidos), respuesta solo dígitos.
  - `funcionario_nombre`: x 0,50–0,99 · y 0,925–0,995, escala 1. Prompt de
    transcripción literal, sin corregir ni completar.
- `temperature=0`, VL 7B de la página (GPU0).
- Nombre con segunda lectura (`FUNC_NOM_DOBLE=1`): prompt letra por letra,
  temperatura 0. Si la similitud con la primera es < `FUNC_NOM_UMBRAL` (90),
  `estable: false` → confianza 60, `revisar: true`, `segunda_lectura`.
- `aplicar_funcionario()` agrega los dos campos con `fuente:
  funcionario_visual`, confianza 90 con valor / 85 vacío con lectura / 0 sin
  lectura (misma convención que `comunidad_vision`).

### `workers/ocr_worker.py`

- `LEER_FUNCIONARIO` (default `1`) → `salida['funcionario_vision']`.
- Tres llamadas VL más por formulario (cédula, nombre, segunda lectura del nombre): 871 → 852 docs/h.

### `workers/nlp_worker.py`

- `aplicar_funcionario(campos, data['funcionario_vision'])` después de
  comunidad. El NLP no ve esos campos en su prompt.

### Scripts

- `gold_csv_to_json.py`: columnas `FUNCIONARIO - CEDULA` / `FUNCIONARIO -
  NOMBRE` (o cualquier cabecera con FUNCIONARIO + CEDULA/NOMBRE); cédula solo
  dígitos. Si el CSV no las trae, avisa y no las incluye.
- `compare_gold_real.py`: `funcionario_cedula` (estricto) y
  `funcionario_nombre` en `CAMPOS`; un campo que el gold no trae se salta
  (antes contaba como `sobra_modelo`).
- `build_lote2_gold_fragment.py`: octavo argumento opcional con el título
  del menú.

## Calibración

- `scripts/calibracion/tfunc.py`: 7 formularios, sin gold (primer ajuste
  de recortes).
- `scripts/calibracion/tspot.py`: muestra de 16, imagen al lado de la
  lectura.
- Con `gold_e3_obtenido-con-fable.csv`, sobre los 267 (solo el recorte):
  `tfunc2.py` / `tfunc3.py` (cédula) y `tfunc4.py` (nombre).

| Cédula | Exacta |
| --- | ---: |
| Escala 2 (primera corrida) | 66,3 % |
| Escala 3 | 50,6 % |
| Recorte más bajo | 58,4 % |
| Escala 1 | 71,9 % |
| **Escala 1 + prompt por cuadrito** | **74,2 %** |
| Dos lecturas, la más larga | 76,4 % (no activado: otra llamada VL) |

Nombre: escala 2 92,0 % · escala 1 92,7 %.

Segunda lectura del nombre (`tnom2.py` / `tnom3.py`): ninguna variante
acierta más que la primera; letra por letra con umbral 90 marca 36, 31 mal.

## Cómo repetir

```bash
# servidor, con el stack arriba
scp workers/*.py ubuntu@18.188.49.114:test-ia-local/caso-1-v2-e3/workers/
docker restart caso1v2e3e3-ocr caso1v2e3e3-nlp
docker cp scripts/corrida/l2_enqueue.py caso1v2e3e3-ocr:/tmp/
docker cp scripts/corrida/l2_consume.py caso1v2e3e3-ocr:/tmp/
bash scripts/corrida/run_lote2.sh /data/e3/resultados_lote2_parte14c.jsonl /tmp/lote2_p14c.log

cd /data/e3
python3 preds_lote2.py resultados_lote2_parte14c.jsonl preds_lote2p14c.json
python3 compare_gold_real.py gold/gold_lote2.json preds_lote2p14c.json "" lote2p14c
python3 build_lote2_gold_fragment.py resultados_lote2_parte14c.jsonl lote2p14c-gold.json \
    lote2p14c-gold-docs.json lote2_p14c_vault_fragment.json 852.1 "18 min 48 s" \
    "<nota>" "Lote E3V2 . Parte 14 (analisis 256 formularios)"

# repo e3-pages: SPECS.lote2p14 + PARTE_KEYS + vault.json?v=lote2p14c
python3 add_fragment.py "$E3_VAULT_USER" "$E3_VAULT_PASS" data/vault.json \
    lote2_p14c_vault_fragment.json lote2p14
```

## Resultado

| Campo / KPI | Valor |
| --- | --- |
| KPI oficial (21 campos, 5569 celdas) | 92,4 % |
| Los 19 campos de antes | 93,3 % |
| funcionario_cedula | 73,8 % exacta |
| funcionario_nombre | 92,5 % (52,1 % exacto + 30,0 % casi) |
| Nombres revisar | 37 (31 mal; marcados 83,0 % vs resto 94,0 %) |
| docs/h · tiempo | 852 · 18 min 48 s |
| Errores OCR/NLP | 0 |
