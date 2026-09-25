# Parte 10 — implementación completa

Documentación de lo que se implementó, midió y publicó como **Parte 10**
(lector dedicado de dígitos: cédula + celular). Fecha de corrida
publicada: **25 sep 2026**, servidor AWS `ubuntu@3.17.139.133`.

Visor: https://shell931.github.io/e3-pages/ — menú Parte 10.
KPI oficial: **89,6 %** = promedio de celda (`conf_real`) vs `gold_v2`.
Misma corrida vs gold original: **88,4 %**.

Parte 8 y Parte 9 del visor **no se modificaron**.

---

## 1. Objetivo

Reducir errores de dígito en `numero_documento` y `telefono_movil`
(campos estrictos: un solo carácter distinto → 0 en la fórmula oficial)
sin tocar casillas, dirección ni el gold, y midiendo siempre contra
`gold.json` **y** `gold_v2.json`.

Decisión de arquitectura: **no** cargar un segundo modelo OCR de
dígitos (RapidOCR/Paddle/otro VL). GPU0 ya reserva ~90 GB para el VL 7B;
no hay VRAM libre. En su lugar: el **mismo** Qwen2.5-VL-7B sobre
**recortes ampliados** de las cajas, a temperatura 0.

---

## 2. Archivos nuevos o tocados

| Archivo | Rol |
| --- | --- |
| `workers/digitos_vision.py` | **Nuevo.** Recorta, escala, pregunta solo dígitos, `aplicar_digitos`. |
| `workers/ocr_worker.py` | Importa `leer_digitos`; flag `LEER_DIGITOS=1`; emite `digitos_vision` en la salida OCR. |
| `workers/nlp_worker.py` | Mete el recorte al voto numérico (si formato plausible) y llama `aplicar_digitos`. |
| `workers/casillas_vision.py` | Sin cambios de Parte 10 (sigue la regla NINGUNA de Parte 9). |
| Resto de vision (`direccion`, `contacto`, `primer_apellido`) | Sin cambios de comportamiento (contacto/apellido OFF). |

En el repo raíz los mismos workers viven bajo `workers/`. Esta carpeta de
backup es la copia **tal cual** del disco del servidor el día de la
medición.

---

## 3. Flujo en runtime

```
TIFF → ocr_worker
         ├─ VLM página completa (texto)
         ├─ VOTE_NUMERIC: 2 lecturas focalizadas (cedula+móvil)
         ├─ casillas / dirección (si flags ON)
         └─ LEER_DIGITOS: 3 recortes → digitos_vision
              ↓
         ocr_output → nlp_worker
         ├─ LLM extrae campos del texto
         ├─ postprocess_express
         ├─ aplicar_casillas / dirección / apellido
         ├─ voto: NLP + numeric_reads + digitos (si formato OK)
         ├─ aplicar_digitos (reglas conservadoras)
         └─ aplicar_contacto (OFF por defecto)
              ↓
         nlp_output → preds → compare_gold_real.py
```

Cola RabbitMQ: `ocr_input` → OCR → `ocr_output` → NLP → `nlp_output`.

---

## 4. `digitos_vision.py` — detalle

### Regiones (fracción de ancho/alto de la página)

| Campo | Caja (x0,y0,x1,y1) |
| --- | --- |
| `numero_documento` | `0.02, 0.330, 0.55, 0.410` |
| `telefono_movil` | `0.70, 0.600, 0.995, 0.662` |
| `telefono_fijo` | `0.70, 0.668, 0.995, 0.728` |

Calibración: en `6000000004`, escala **4** leía mal el 7 como 6; escala
**2** + caja de cédula más baja/ancha → `1016071060` exacto. Env vars
opcionales: `CED_*`, `MOVIL_*`, `FIJO_*`, `DIGITOS_ESCALA`.

### Preproceso

1. Abrir TIFF, convertir a escala de grises (`L`).
2. Recortar la caja.
3. Ampliar × `DIGITOS_ESCALA` (default 2) con LANCZOS.
4. PNG en base64 → chat completions del VL (`max_tokens=48`, `temperature=0`).

### Prompts

Piden **solo dígitos** (o `VACIO`). Prohíben completar a 10 dígitos e
inventar ceros en casillas vacías.

### `aplicar_digitos` (después del voto)

- **móvil**: solo si visión tiene 10 dígitos y empieza por `3`; no pisa
  otro móvil ya bien formado salvo extensión por prefijo.
- **cédula**: solo si visión tiene **8–10** dígitos; nunca acorta un NLP
  más largo; rellena si NLP vacío o NLP fuera de 8–10.
- **fijo**: el recorte se lee y viaja en `digitos_vision`, pero
  **`aplicar_digitos` no lo aplica** (en pruebas mezclaba el móvil de
  arriba y bajaba `conf_real`).

### Voto en `nlp_worker`

El recorte solo aporta un voto extra si:

- móvil: `len==10` y `startswith("3")`
- cédula: `8 <= len <= 10`

Si no, se ignora (evita que basura tipo `1012345` gane el Counter).

---

## 5. Qué NO se hizo en Parte 10

- No se tocó el gold ni `gold_v2` (creados en Parte 9).
- No se tocó la regla NINGUNA de discapacidad (Parte 9).
- No se activó `LEER_CONTACTO` ni `LEER_APELLIDO` (empeoran con este VL).
- No se cuantizó el VL ni se añadió RapidOCR/Paddle.
- No se reescribieron Parte 8 / Parte 9 en el visor.

---

## 6. Números publicados

| Métrica | Parte 8 | Parte 9 | Parte 10 |
| --- | ---: | ---: | ---: |
| vs gold | 87,8 % | 87,7 % | **88,4 %** |
| vs gold_v2 | — | 88,9 % | **89,6 %** |
| `numero_documento` | 86 % | 87 % | **88 %** |
| `telefono_movil` (gold / v2) | 41 / — | 40 / 58 | 40 / 58 |
| `tipo_discapacidad` | 82 % | 90 % | 91 % |
| docs/h (meta 1250) | 968 | 917 | **872** |

Agregados sin PII: `kpis/parte10-gold.json` y `kpis/parte10v2-gold.json`.

La ganancia en cédula (+2 pp vs Parte 8) es el efecto más claro del
recorte. El móvil vs gold_v2 quedó en el mismo orden que Parte 9; muchos
gold originales siguen incompletos a propósito.

---

## 7. Cómo se publicó el visor

1. `scripts/build_parte10_fragment.py` arma el objeto `parte10` con
   `rows` (100 docs) y `gold_eval` tomado de la comparación vs
   **gold_v2** (KPI). El visor lee `d.rows` — no `resultados`.
2. Se inyectó en el vault cifrado de `shell931/e3-pages` (`data/vault.json`).
3. `index.html` del visor: entrada de menú `parte10` + `PARTE_KEYS`.

Para repetir la publicación hace falta el usuario/clave del vault (no
van en este backup).

---

## 8. Commits / rama

Trabajo de código en la rama `cursor/parte10-digitos-b8cd` del repo
`shell931/ov-ia-caso-1-e3-ocr-forms`. Esta carpeta
`backup/parte10-servidor-fisico/` es el paquete de despliegue
autocontenido para el servidor físico.
