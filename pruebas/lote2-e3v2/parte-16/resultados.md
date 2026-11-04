# Lote E3V2 · Parte 16 — Parte 15 en Turing (AWS g4dn.metal)

Validación de compatibilidad para el Dell R740xd con 2× Quadro RTX 8000. No hay
RTX 8000 en AWS, así que se usó **g4dn.metal** (8× Tesla T4 16 GB), que tiene la
misma arquitectura Turing `sm_75`.

Mismo pipeline, modelos, revisiones e imagen vLLM que la
[Parte 15](../parte-15/resultados.md). Los cambios los obliga Turing:

- FP16 en vez de BF16.
- FP8 solo pesos (Marlin W8A16).
- Atención `TRITON_ATTN`, porque FlashAttention 2 no soporta `sm_75`.
- VL repartido con tensor parallel porque cada T4 tiene 16 GB.
- `--disable-custom-all-reduce`.

| Corrida | VL | KPI `conf_real` | Referencia en Parte 15 |
| --- | --- | --- | --- |
| **16** | Qwen3.6-27B-FP8, TP=4 | **95,5 %** | 95,7 % (diferencia dentro del ruido) |
| **16b** (control) | Qwen2.5-VL-7B, TP=2 | 92,6 % | 92,3 % |

El control 16b aísla el efecto del hardware: con el mismo 7B, Turing no pierde
KPI.

El throughput medido en g4dn.metal (63,5 docs/h) **no es representativo**:
las T4 hacen el TP por PCIe y corren con `enforce-eager`. El throughput real
se mide solo en el Dell.

Código, envs y guía de despliegue: [`planteamientos/rtx-8000/`](../../../planteamientos/rtx-8000/)
(sección *Validación elegida: g4dn.metal*). Fragmento del visor:
`planteamientos/rtx-8000/visor_parte16.py`.
