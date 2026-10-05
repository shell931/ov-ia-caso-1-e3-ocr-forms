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
| KPI oficial (21 campos) | — | **92,4 %** |
| Los 19 campos de antes | 93,2 % | 93,3 % |
| funcionario_cedula (exacta) | — | 73,8 % |
| funcionario_nombre | — | 92,5 % (52,1 % exacto, 30,0 % casi) |
| Nombres marcados `revisar` | — | 37 (31 de ellos mal) |
| docs/h | 871 | 852 |
| Errores | 0 | 0 |

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

## Nombre del funcionario: nombres "por coincidencia"

Caso `6000000306`: escrito "Luz stella Rojas Arce", leído "José Stella Rojas
Ance" (igual en tres llamadas). La "L" y la "z" de "Luz" casi no se
distinguen y el VL completa con un nombre frecuente. En el lote, de 671
palabras de nombre del gold: 117 con letras mal leídas, 41 reemplazadas por
otra palabra, 8 faltantes, 4 agregadas.

Ninguna lectura alternativa acertó más (temperatura 0,3: 91,8–92,1 %;
prompt "letra por letra aunque no parezca un nombre real": 91,5 %), así que
el valor sigue siendo la primera lectura. La segunda lectura (prompt letra
por letra, temperatura 0) se usa para marcar: si la similitud entre ambas es
< 90 (`FUNC_NOM_UMBRAL`), el nombre queda con confianza 60, `revisar: true`
y `segunda_lectura`.

| Marca con segunda lectura (267) | Marcados | De ellos mal | Real marcados / resto |
| --- | ---: | ---: | ---: |
| Temperatura 0,3, cualquier diferencia | 54 | 41 | 87,1 / 94,1 % |
| **Letra por letra, sim < 90** (elegida) | 36 | 31 | 83,3 / 94,2 % |
| Corrida completa | 37 | 31 | 83,0 / 94,0 % |

La temperatura 0,3 no marca `6000000306` (vuelve a leer "José"); letra por
letra sí ("Jue s-teva Rojo Ance"). El visor muestra en el detalle
"revisar · 2ª lectura: …" (también en direcciones marcadas). Cuesta una
llamada VL más por formulario: 860 → 852 docs/h.

Visor: menú **Lote E3V2 . Parte 14 (analisis 256 formularios)** (clave
`lote2p14`). KPIs sin PII: `docs/lote2-parte14-gold-kpis.json`. Backup
completo: `backup/parte-14-servidor-fisico/`.
