#!/usr/bin/env python3
"""Fragmento del visor (Parte 16, Turing) a partir de una corrida de probar_modelo.sh.

Usa scripts/lote2/build_lote2_gold_fragment.py tal cual y después reemplaza lo que
ese script deja fijo de la Parte 10 (modelos, workers, VRAM) por lo de esta corrida.

Uso (desde la raíz del repo, en el servidor):
  python3 planteamiento_rtx_8000/visor_parte16.py <res_dir> <tag_jsonl> <tag_kpi> \
      <docs_h> "<elapsed>" <vl> <salida.json> "<titulo>" "<nota>"

  tag_jsonl  prefijo del .jsonl y del .gpu (p. ej. g4dn-metal-qwen36-27b-fp8_front)
  tag_kpi    lote usado en compare_gold_real.py (sus -gold.json y -gold-docs.json)
  vl         27b | 7b

El fragmento lleva PII (gold por celda): solo va al vault cifrado, nunca a git.
"""
import json
import subprocess
import sys
from pathlib import Path

RES, TAG_JSONL, TAG_KPI, DOCS_H, ELAPSED, VL, OUT, TITULO, NOTA = sys.argv[1:10]
res = Path(RES)

subprocess.run([
    sys.executable, "scripts/lote2/build_lote2_gold_fragment.py",
    str(res / f"{TAG_JSONL}.jsonl"), str(res / f"{TAG_KPI}-gold.json"),
    str(res / f"{TAG_KPI}-gold-docs.json"), OUT, DOCS_H, ELAPSED, NOTA, TITULO,
], check=True)

# VRAM por GPU medida por probar_modelo.sh al levantar (nvidia-smi: "idx, N MiB")
gpus = []
for line in (res / f"{TAG_JSONL.removesuffix('_fix')}.gpu").read_text().splitlines():
    idx, mib = (s.strip() for s in line.split(","))
    gpus.append({"idx": int(idx), "mib": int(mib.split()[0])})
T4_MIB = 15360
usadas = [g for g in gpus if g["mib"] > 0]
mib = lambda ids: sum(g["mib"] for g in gpus if g["idx"] in ids)
gb = lambda m: f"{m / 1024:.1f} GB"

if VL == "27b":
    vl_ids, vl = [0, 1, 2, 3], {"nombre": "Qwen/Qwen3.6-27B-FP8 (rev e89b16eb)",
                                "rol": "Visión / OCR + recortes · FP8 solo pesos (Marlin W8A16), activaciones FP16"}
    vl_donde = "GPU 0-3 · TP=4 · :8001"
    workers, conc = "8 OCR + 12 NLP", 8
else:
    vl_ids, vl = [0, 1], {"nombre": "Qwen/Qwen2.5-VL-7B-Instruct (rev cc594898)",
                          "rol": "Visión / OCR + recortes · FP16 (control)"}
    vl_donde = "GPU 0-1 · TP=2 · :8001"
    workers, conc = "8 OCR + 12 NLP", 8

frag = json.loads(Path(OUT).read_text())
frag["modelos"] = [
    dict(vl, donde=vl_donde,
         vram=f"{gb(mib(vl_ids))} ({' + '.join(gb(g['mib']) for g in gpus if g['idx'] in vl_ids)})"),
    {"nombre": "Qwen/Qwen2.5-7B-Instruct-AWQ (rev b2503754)", "rol": "NLP / JSON",
     "donde": "GPU 4 · :8000", "vram": gb(mib([4]))},
]
frag["workers"], frag["concurrency"] = workers, conc
frag["vram"] = {
    "gpu": "8× Tesla T4 16 GB (Turing sm_75) · g4dn.metal",
    "used_mib": sum(g["mib"] for g in usadas), "total_mib": T4_MIB * len(gpus),
    "used_gb": round(sum(g["mib"] for g in usadas) / 1024, 1),
    "total_gb": round(T4_MIB * len(gpus) / 1024, 1),
    "por_gpu": gpus,
}
Path(OUT).write_text(json.dumps(frag, ensure_ascii=False))
print("modelos/vram actualizados:", frag["modelos"][0]["vram"], "|", frag["modelos"][1]["vram"])
