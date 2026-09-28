# Mejoras futuras — pipeline E3 OCR (post Parte 8–11)

Plan de optimización sobre el proceso ya medido en AWS (Docker + RabbitMQ,
8 OCR + 12 NLP, vLLM VL Qwen2.5-VL-7B-Instruct GPU0 + NLP Qwen2.5-7B-Instruct-AWQ
GPU1). KPI oficial: **conf_real** externo vs gold / gold_v2 (no score NLP).

Baseline de referencia (100 docs):

| Hito | vs gold | vs gold_v2 | docs/h (meta 1250) |
| --- | ---: | ---: | ---: |
| Parte 8 | 87,8 % | — | ~968 |
| Parte 9 | — | regla NINGUNA | — |
| Parte 10 | 88,4 % | **89,6 %** | ~872 |
| Parte 11 (PR) | 88,4 % | 89,5 % | ~880 |

Parte 11 demostró que tweaks baratos (prompt, omitir VL de fijo, ampliar
NINGUNA≥2) ya no mueven el KPI global. Lo que sigue exige más datos,
menos llamadas al VL, o adaptación del modelo.

---

## 1. Prioridades (orden sugerido)

### A. Throughput → meta ~1250 docs/h

**Problema:** cada doc hace varias pasadas al VL (página, voto numérico,
casillas, dirección, dígitos). Parte 10 bajó docs/h al sumar crops.

**Opciones (de menor a mayor invasión):**

1. Perfil vLLM: batch, `max_num_seqs`, longitud de imagen, precisión
   (solo cuantizar VL si VRAM lo exige; en GPU grande no fue necesario).
2. Menos llamadas por doc: fusionar voto numérico con página; casillas
   en un solo crop de pie; omitir dirección si el NLP ya es bueno en ese
   campo en el lote.
3. Escalar workers OCR/NLP solo si la GPU no está al 100 % (si GPU satura,
   más workers empeoran cola).
4. Dos GPUs VL o modelo más chico solo para dígitos/casillas.
   **Probado (Parte 12):** Qwen2.5-VL-3B en GPU1 para dígitos/casillas →
   conf_real **69,8 %** (casillas ~1–28 %) y docs/h **igual** (~872).
   Descartado con 3B; cableado queda opcional (`VLLM_VL_SMALL_URL`).
   Ver `docs/parte12-resultados.md`.

**Qué se necesita:**

- Métricas por etapa (latencia p50/p95 de cada llamada VL + NLP).
- Corrida A/B de 100 docs midiendo docs/h **y** conf_real (no optimizar
  solo velocidad).
- Acceso al servidor con GPU (mismo stack o físico).

### B. Campos débiles de texto (email, dirección, nombres)

**Problema:** prompt y crops con el 7B apenas mueven email/dirección.
Parte 11: email ~35 %, dirección ~23 %.

**Opciones:**

1. Dataset de **crops por campo** (no página completa) con gold corregido.
2. Reglas post-proceso (normalizar `Cll`/`#`, dominios frecuentes) solo
   si no bajan conf_real en holdout.
3. Fine-tuning / LoRA del VL en esos crops (ver §3).
4. Modelo distinto solo para email/dirección (ensayo controlado).

**Qué se necesita:**

- Miles de ejemplos etiquetados (ver §2); 100 docs no bastan.
- Holdout fijo (p.ej. últimos 20 ids) para no sobreajustar.
- No reactivar `LEER_CONTACTO` / `LEER_APELLIDO` sin medir: en 7B ya
  empeoraron o no ayudaron.

### C. Casillas (nivel, braille, discapacidad)

**Hecho:** NINGUNA con `marcadas≥2` (Parte 11); escala×3 en braille/tipo_documento.

**Pendiente:** falsos negativos con X fina visible (p.ej. nivel TECNICO /
braille NO en `6000000042`). Escala×3 + autocontraste en nivel se
revirtió (bajaba docs/h sin ganar exactitud).

**Opciones:**

1. Detector clásico de marca (umbral / morfología) como voto junto al VL.
2. Fine-tune VL solo en crops de casillas.
3. Umbrales por región si el layout E3 es estable.

**Qué se necesita:** inventario de FN/FP por campo en gold; crops
etiquetados marca/no-marca.

### D. Dígitos (cédula / celular)

Parte 10 ya aporta el grueso del salto (cédula ~88 %). Mejoras menores:
afinar cajas si hay lotes con layout distinto; no reabrir `telefono_fijo`
salvo depuración (`DIGITOS_LEER_FIJO=1`).

---

## 2. Datos — requisito transversal

Sin más datos etiquetados, fine-tuning y muchas reglas son ruido.

| Recurso | Uso | Nota |
| --- | --- | --- |
| TIFF frente (`/data/e3/front/`) | Entrada OCR | Rsync antes de apagar AWS |
| `gold.json` / `gold_v2.json` | KPI conf_real | gold_v2 corrige teléfonos |
| Correcciones humanas | Train / val | Sobre preds del pipeline actual |
| Crops por campo | Fine-tune VL | Generar con las mismas `REGIONES` del código |
| Lotes nuevos E3 | Generalización | Mismas técnicas; re-medir siempre |

**Volumen orientativo:**

- Reglas / post-proceso: cientos de errores etiquetados bastan para
  validar.
- LoRA / fine-tune VL serio: **miles** de pares crop→valor (mejor
  desbalanceado hacia errores actuales: email, dirección, casillas FN).
- Split: train / val / test por `doc_id` (nunca mezclar páginas del
  mismo form entre splits si hubiera multi-página).

**Privacidad:** no versionar TIFF ni gold con datos personales en el
repo; guardar en disco/Vault aparte (como en los LEEME de
`backup/parte8-servidor-fisico` y `backup/parte10-servidor-fisico`).

---

## 3. Fine-tuning (cuando haya datos)

### Enfoque recomendado

1. Congelar el pipeline Parte 10/11 como **baseline** (conf_real + docs/h).
2. Exportar crops + etiquetas de campos débiles.
3. **LoRA / QLoRA** sobre Qwen2.5-VL-7B (o adapter por tarea:
   dígitos vs texto vs casillas).
4. Servir el adaptador en el mismo vLLM (o swap de pesos) y medir
   otra vez vs gold / gold_v2 en el holdout.
5. Solo entonces tocar NLP AWQ (suele ser secundario si el fallo es lectura).

### Qué se necesita

- GPU(s) de entrenamiento (horas/días según tamaño; aparte del
  servidor de inferencia si se quiere no cortar producción).
- Framework: habitualmente Hugging Face + PEFT / ms-swift / LLaMA-Factory
  (elegir uno y documentarlo en el backup de redeploy).
- Presupuesto y ventana: no mezclar experimentos de throughput con
  cambio de pesos en la misma corrida.
- Criterio de éxito: subir conf_real en campos objetivo **sin** bajar
  docs/h por debajo del umbral de negocio, o aceptar el trade-off
  explícito.

### Qué no hacer al inicio

- Full fine-tune de 7B sin LoRA (caro, fácil de olvidar el layout E3).
- Entrenar solo con los 100 docs del piloto.
- Publicar un “Parte N” en el visor sin ganancia clara vs Parte 10
  (lección Parte 11).

---

## 4. Infra y redeploy

- Empaquetar cada hito medido en `backup/parteN-servidor-fisico/`
  (workers, scripts, LEEME con Mermaid, MANIFEST) como Parte 8/10.
- Flags ya útiles: `LEER_DIGITOS`, `LEER_CASILLAS`, `LEER_DIRECCION`,
  `DIGITOS_LEER_FIJO`, contacto/apellido OFF por defecto.
- Apagar AWS entre campañas; rsync de front + gold antes.
- En servidor físico: mismo contrato de colas
  (`ocr_input` → `ocr_output` → `nlp_output`) y mismo `doc_id` en el
  mensaje (dígitos/casillas van en el JSON, no en cola aparte).

---

## 5. Cómo medir cada experimento

1. Misma lista de 100 (o N) `doc_id`.
2. Wall-clock → docs/h (no inventar throughput).
3. `compare_gold_real.py` vs **gold** y **gold_v2**.
4. Tabla por campo (exact match) + casos problemáticos (tipo 0042).
5. Documento `docs/parteN-resultados.md` + decisión explícita:
   ¿reemplaza KPI del visor o solo queda en rama?

No publicar en el visor un Parte con KPI global peor o igual “por
jitter” presentándolo como mejora.

---

## 6. Roadmap práctico

| Fase | Acción | Bloqueante |
| --- | --- | --- |
| 0 | Rsync datos + apagar cloud si no hay corrida | Disco local / Vault |
| 1 | Instrumentar latencias VL por tipo de llamada | Código + 1 corrida |
| 2 | Un experimento de throughput (menos VL o perfil vLLM) | Fase 1 |
| 3 | Ampliar gold corregido (email, dirección, casillas) | Etiquetado humano |
| 4 | Prototipo LoRA en crops débiles | Fase 3 (volumen) |
| 5 | A/B LoRA vs Parte 10 en holdout | GPU train + inferencia |
| 6 | Si gana: backup físico + Parte N en visor | KPI y docs/h OK |

---

## 7. Referencias en el repo

- `docs/parte8-resultados.md` … `docs/parte11-resultados.md` (si está
  mergeado; si no, rama `cursor/parte11-casillas-throughput-b8cd`)
- `backup/parte8-servidor-fisico/LEEME.md` — flujo + Mermaid Parte 8
- `backup/parte10-servidor-fisico/LEEME.md` — dígitos, doc_id, vs P8
- Workers clave: `ocr_worker.py`, `nlp_worker.py`, `digitos_vision.py`,
  `casillas_vision.py`, `direccion_vision.py`

---

*Documento vivo: actualizar cuando se cierre un experimento con números
vs gold / gold_v2.*
