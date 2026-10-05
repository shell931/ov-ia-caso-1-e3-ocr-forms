# Lote E3V2 . Parte 14 (analisis 256 formularios)

Corrida del 5 oct 2026 sobre los 267 frentes de `s3://forme3/E3V2/front_300/`
con el pipeline del lote E3V2 (ver `docs/lote2-e3v2-parte10.md`) y dos
campos nuevos del pie **INFORMACIÓN DEL FUNCIONARIO ELECTORAL RESPONSABLE DE
LA INSCRIPCIÓN**:

- `funcionario_cedula`: fila de cuadritos CÉDULA, solo dígitos (estricto).
- `funcionario_nombre`: caja NOMBRE, manuscrito literal (similitud).

Los lee `workers/funcionario_vision.py`, con un recorte de cada caja en el
VL 7B (`LEER_FUNCIONARIO=1`). Gold: `gold_e3_obtenido-con-fable.csv`
(columnas `FUNCIONARIO - CEDULA` / `FUNCIONARIO - NOMBRE`; los otros 19
campos son idénticos al gold anterior).

| Métrica | Anterior (dirección) | Parte 14 |
| --- | ---: | ---: |
| KPI oficial (21 campos) | — | **92,5 %** |
| Los 19 campos de antes | 93,2 % | 93,4 % |
| funcionario_cedula (exacta) | — | 74,5 % |
| funcionario_nombre | — | 92,7 % (51,7 % exacto, 30,7 % casi) |
| docs/h | 871 | 860 |
| Errores | 0 | 0 (6000000079 se reprocesó: JSON cortado del NLP) |

## Calibración de la cédula contra el gold

Primera corrida (escala 2, prompt de dígitos): 65,9 % exacta. De los 91
errores, 44 eran **un dígito perdido** y 26 un dígito cambiado. Medido solo el
recorte sobre los 267:

| Variante | Exacta |
| --- | ---: |
| Escala 2 (primera corrida) | 66,3 % |
| Escala 3 | 50,6 % |
| Recorte más bajo (y 0,94–0,985) | 58,4 % |
| Escala 1 | 71,9 % |
| **Escala 1 + prompt por cuadrito** (elegida) | **74,2 %** |
| Dos lecturas, quedarse con la más larga | 76,4 % (una llamada VL más) |
| Techo: alguna variante acierta | 77,9 % |

Ampliar empeora: con la imagen más grande el modelo pierde cuadritos. El
nombre no cambia con la escala (92,0 vs 92,7 %, ruido). La doble lectura
suma 2 puntos a costa de otra llamada por formulario; no se activó.

Visor: menú **Lote E3V2 . Parte 14 (analisis 256 formularios)** (clave
`lote2p14`). KPIs sin PII: `docs/lote2-parte14-gold-kpis.json`. Backup
completo: `backup/parte-14-servidor-fisico/`.
