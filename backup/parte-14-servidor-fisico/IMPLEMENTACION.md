# Parte 14 — implementación

## Objetivo

Agregar al Lote E3V2 los dos campos del pie **INFORMACIÓN DEL FUNCIONARIO
ELECTORAL RESPONSABLE DE LA INSCRIPCIÓN** (CÉDULA y NOMBRE), compararlos con
el gold y publicar la corrida completa en el visor.

## Cableado

### `workers/funcionario_vision.py` (nuevo)

- Dos recortes sobre la página ya normalizada por `pagina_e3` (si la página
  traía E-3 + E-4, el pie es el del E-3):
  - `funcionario_cedula`: x 0,04–0,52 · y 0,925–0,995, escala 2. Prompt de
    dígitos (igual al de `digitos_vision`), respuesta solo dígitos.
  - `funcionario_nombre`: x 0,50–0,99 · y 0,925–0,995, escala 2. Prompt de
    transcripción literal, sin corregir ni completar.
- `temperature=0`, VL 7B de la página (GPU0).
- `aplicar_funcionario()` agrega los dos campos con `fuente:
  funcionario_visual`, confianza 90 con valor / 85 vacío con lectura / 0 sin
  lectura (misma convención que `comunidad_vision`).

### `workers/ocr_worker.py`

- `LEER_FUNCIONARIO` (default `1`) → `salida['funcionario_vision']`.
- Dos llamadas VL más por formulario: 871 → 845 docs/h.

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

- `scripts/calibracion/tfunc.py`: 7 formularios (incluye uno E-3+E-4).
  Variantes: escala 3, recorte más angosto (x1 0,46) y más bajo (y
  0,94–0,985). Ninguna fue mejor que la base (5/7 cédulas exactas); se dejó
  la base.
- `scripts/calibracion/tspot.py`: muestra aleatoria de 16 sobre la corrida
  completa, imagen al lado de la lectura: 12/16 cédulas exactas, nombres
  bien salvo caligrafía difícil.

## Cómo repetir

```bash
# servidor, con el stack arriba
scp workers/*.py ubuntu@18.188.49.114:test-ia-local/caso-1-v2-e3/workers/
docker restart caso1v2e3e3-ocr caso1v2e3e3-nlp
docker cp scripts/corrida/l2_enqueue.py caso1v2e3e3-ocr:/tmp/
docker cp scripts/corrida/l2_consume.py caso1v2e3e3-ocr:/tmp/
bash scripts/corrida/run_lote2.sh /data/e3/resultados_lote2_parte14.jsonl /tmp/lote2_p14.log

cd /data/e3
python3 preds_lote2.py resultados_lote2_parte14.jsonl preds_lote2p14.json
python3 compare_gold_real.py gold/gold_lote2.json preds_lote2p14.json "" lote2p14
python3 build_lote2_gold_fragment.py resultados_lote2_parte14.jsonl lote2p14-gold.json \
    lote2p14-gold-docs.json lote2_p14_vault_fragment.json 845.4 "18 min 57 s" \
    "<nota>" "Lote E3V2 . Parte 14 (analisis 256 formularios)"

# repo e3-pages: SPECS.lote2p14 + PARTE_KEYS + vault.json?v=lote2p14
python3 add_fragment.py "$E3_VAULT_USER" "$E3_VAULT_PASS" data/vault.json \
    lote2_p14_vault_fragment.json lote2p14
```

## Resultado

| Campo / KPI | Valor |
| --- | --- |
| KPI oficial (19 campos con gold, 5029 celdas) | 93,3 % |
| funcionario_cedula / funcionario_nombre | 267/267 con valor; sin gold aún |
| Revisión visual cédula (23 docs) | 17 exactas |
| docs/h · tiempo | 845 · 18 min 57 s |
| Errores OCR/NLP | 0 |
