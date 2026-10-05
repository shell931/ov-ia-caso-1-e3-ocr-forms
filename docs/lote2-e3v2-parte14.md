# Lote E3V2 . Parte 14 (analisis 256 formularios)

Corrida del 5 oct 2026 sobre los 267 frentes de `s3://forme3/E3V2/front_300/`
con el pipeline del lote E3V2 (ver `docs/lote2-e3v2-parte10.md`) y dos
campos nuevos del pie **INFORMACIÓN DEL FUNCIONARIO ELECTORAL RESPONSABLE DE
LA INSCRIPCIÓN**:

- `funcionario_cedula`: fila de cuadritos CÉDULA, solo dígitos.
- `funcionario_nombre`: caja NOMBRE, manuscrito literal.

Los lee `workers/funcionario_vision.py`, con un recorte ampliado de cada
caja en el VL 7B (`LEER_FUNCIONARIO=1`).

| Métrica | Anterior (dirección) | Parte 14 |
| --- | ---: | ---: |
| KPI oficial vs gold_e3 (19 campos) | 93,2 % | **93,3 %** |
| funcionario_cedula / funcionario_nombre | — | 267/267 leídos, sin gold |
| docs/h | 871 | 845 |
| Errores | 0 | 0 |

El gold del servidor no trae las columnas del funcionario (el CSV se borró
por PII después de convertirlo). `compare_gold_real.py` salta los campos que
el gold no tiene; al volver a cargar `gold_e3.csv` con esas columnas,
`gold_csv_to_json.py` + `compare_gold_real.py` los miden sin volver a
correr el lote (`/data/e3/preds_lote2p14.json` ya tiene las lecturas).

Revisión visual (23 formularios, imagen vs lectura): cédula exacta en 17;
los errores son un dígito cambiado o perdido en cédulas largas.

Visor: menú **Lote E3V2 . Parte 14 (analisis 256 formularios)** (clave
`lote2p14`). KPIs sin PII: `docs/lote2-parte14-gold-kpis.json`. Backup
completo: `backup/parte-14-servidor-fisico/`.
