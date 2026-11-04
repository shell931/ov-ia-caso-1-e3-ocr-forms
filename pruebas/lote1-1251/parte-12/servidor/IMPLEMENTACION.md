# Parte 12 — implementación (experimento)

## Objetivo

Probar §A.4 de `MEJORAS-FUTURAS.md`: modelo VL más chico solo para
dígitos/casillas, buscando subir docs/h sin tocar la página completa.

## Cableado

### `ocr_worker.py`

- `VLLM_VL_SMALL_URL` / `VLLM_VL_SMALL_MODEL`
- `client_vl_small` si la URL no está vacía
- `_cliente_crops()` → usado solo por `leer_casillas` y `leer_digitos`
- Página, `VOTE_NUMERIC` y `leer_direccion` siguen en el 7B

### `docker-compose.yml`

- Servicio `vllm-vl-small`: GPU1, puerto host `8002`, util `0.45`,
  `max-num-seqs` 16, modelo `Qwen/Qwen2.5-VL-3B-Instruct`
- OCR: `VLLM_VL_SMALL_URL` **vacío por defecto** (post-experimento)
- `ocr` **no** hace `depends_on` de `vllm-vl-small` (opcional)

### NLP en la misma GPU1

NLP ya reservaba ~0.40; el 3B cabía (~7 GB pesos + KV). Tras la corrida
se eliminó el contenedor 3B para liberar VRAM.

## Resultado

| Campo / KPI | Efecto |
| --- | --- |
| Casillas (nivel, braille, discapacidad, tipo_doc) | Colapso |
| Cédula | −4 pp aprox. |
| docs/h | Sin cambio (~872) |

**Decisión:** no usar 3B para casillas E3. Código opcional queda para
re-probar otro modelo chico si se quiere; default = 7B.
