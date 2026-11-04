"""Compara campo a campo gold vs resultados y estima una confianza real.

A diferencia de eval_gold.py (exact match, score CORE), acá cada par
gold/predicho recibe una similitud 0-100 y un veredicto, para poder
contrastar la confianza que declara el extractor contra la que merece.

Genera tres salidas junto a resultados.json:
  comparacion-<lote>.csv   detalle fila por fila (tiene PII, no va a git)
  <lote>-gold.json         agregado por campo, sin PII: KPIs del visor
  <lote>-gold-docs.json    valor gold por job y campo (tiene PII): detalle
                           del documento en el visor, viaja dentro del vault
                           cifrado, nunca en claro

Uso:
    python scripts/compare_gold.py [gold.json] [resultados.json] [prefijo] [lote]
"""

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

CAMPOS = (
    "formulario_no",
    "fecha_inscripcion",
    "tipo_documento",
    "numero_documento",
    "fecha_expedicion",
    "primer_apellido",
    "segundo_apellido",
    "primer_nombre",
    "segundo_nombre",
    "nivel_estudio",
    "email",
    "telefono_movil",
    "telefono_fijo",
    "ciudad",
    "direccion",
    "lee_braille",
    "tipo_discapacidad",
    "etnia",
)

# Un solo carácter de diferencia en estos campos ya invalida el dato.
ESTRICTOS = {
    "numero_documento",
    "telefono_movil",
    "telefono_fijo",
    "fecha_inscripcion",
    "fecha_expedicion",
    "formulario_no",
    "tipo_documento",
    "nivel_estudio",
    "lee_braille",
    "tipo_discapacidad",
    "etnia",
}

CASI = 85  # similitud mínima para considerar el valor recuperable


def norm(v) -> str:
    s = unicodedata.normalize("NFD", str(v or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


def similitud(a: str, b: str) -> int:
    if a == b:
        return 100
    if not a or not b:
        return 0
    return round(100 * SequenceMatcher(None, a, b).ratio())


def veredicto(campo: str, sim: int, a: str, b: str) -> str:
    if a == b:
        return "exacto"
    if not a:
        return "vacio_modelo"
    if not b:
        return "sobra_modelo"
    if campo in ESTRICTOS:
        return "distinto"
    return "casi" if sim >= CASI else "distinto"


def comparar(gold: dict, preds: list) -> list:
    filas = []
    for row in preds:
        if row.get("estado") != "listo":
            continue
        g = gold.get(str(row.get("id", "")).rsplit("-", 1)[-1])
        if not g:
            continue
        got = {c["etiqueta"]: c for c in row.get("campos") or []}
        for campo in CAMPOS:
            c = got.get(campo)
            if c is None:
                continue
            pred_raw = str(c.get("valor") or "").strip()
            gold_raw = str(g.get(campo) or "").strip()
            a, b = norm(pred_raw), norm(gold_raw)
            sim = similitud(a, b)
            # JUSTO: si el gold marca telefono_movil como INCOMPLETO, el gold es
            # solo un prefijo truncado del numero real; el modelo que lee el numero
            # completo (que empieza con esos digitos) se considera correcto.
            if campo == "telefono_movil":
                gd = re.sub(r"\D", "", gold_raw)
                pd = re.sub(r"\D", "", pred_raw)
                if str(g.get("telefono_ok", "")).upper() == "INCOMPLETO" and gd and pd.startswith(gd):
                    a = b
                    sim = 100
            filas.append(
                {
                    "documento": str(g["id"]),
                    "job": row["id"],
                    "campo": campo,
                    "gold": gold_raw,
                    "modelo": pred_raw,
                    "similitud": sim,
                    "veredicto": veredicto(campo, sim, a, b),
                    "conf_declarada": int(c.get("confianza") or 0),
                    "conf_real": 100 if a == b else (0 if campo in ESTRICTOS else sim),
                }
            )
    return filas


def resumir(filas: list, lote: str, prefijo: str, n_gold: int) -> dict:
    por_campo = defaultdict(lambda: defaultdict(int))
    suma_dec = defaultdict(int)
    for f in filas:
        c = f["campo"]
        por_campo[c][f["veredicto"]] += 1
        por_campo[c]["n"] += 1
        suma_dec[c] += f["conf_declarada"]

    campos = []
    for campo in CAMPOS:
        d = por_campo.get(campo)
        if not d:
            continue
        n = d["n"]
        exacto = d["exacto"]
        casi = d["casi"]
        dec = round(suma_dec[campo] / n, 1)
        real = round(100 * exacto / n, 1)
        campos.append(
            {
                "etiqueta": campo,
                "n": n,
                "exacto": real,
                "casi": round(100 * casi / n, 1),
                "malo": round(100 * (n - exacto - casi) / n, 1),
                "conf_declarada": dec,
                "conf_real": real,
                "brecha": round(dec - real, 1),
                "estricto": campo in ESTRICTOS,
            }
        )

    n = len(filas)
    exactos = sum(1 for f in filas if f["veredicto"] == "exacto")
    dec = round(sum(f["conf_declarada"] for f in filas) / n, 1) if n else None
    real = round(100 * exactos / n, 1) if n else None
    veredictos = defaultdict(int)
    for f in filas:
        veredictos[f["veredicto"]] += 1
    return {
        "lote": lote,
        "prefijo": prefijo,
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gold_docs": n_gold,
        "jobs": len({f["job"] for f in filas}),
        "comparaciones": n,
        "conf_declarada": dec,
        "conf_real": real,
        "brecha": round(dec - real, 1) if n else None,
        "veredictos": dict(veredictos),
        "falsos_100": sum(
            1 for f in filas if f["conf_declarada"] == 100 and f["veredicto"] == "distinto"
        ),
        "umbral_casi": CASI,
        "campos": campos,
    }


def detalle(filas: list, lote: str, prefijo: str) -> dict:
    """Valor gold por job y campo, para el panel de captura del visor."""
    docs: dict[str, dict] = {}
    for f in filas:
        docs.setdefault(f["job"], {})[f["campo"]] = {
            "gold": f["gold"],
            "sim": f["similitud"],
            "veredicto": f["veredicto"],
            "conf_real": f["conf_real"],
        }
    return {"lote": lote, "prefijo": prefijo, "docs": docs}


def main() -> None:
    gold_path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/e3/gold/gold.json")
    pred_path = Path(sys.argv[2] if len(sys.argv) > 2 else "data/resultados.json")
    prefijo = sys.argv[3] if len(sys.argv) > 3 else ""
    lote = sys.argv[4] if len(sys.argv) > 4 else ""
    if not lote:
        m = re.match(r"^p(\d+)", prefijo)
        lote = f"parte{m.group(1)}" if m else "lote"

    gold = {str(r["id"]): r for r in json.loads(gold_path.read_text(encoding="utf-8"))}
    preds = json.loads(pred_path.read_text(encoding="utf-8"))
    if prefijo:
        preds = [p for p in preds if str(p.get("id", "")).startswith(prefijo)]

    filas = comparar(gold, preds)
    if not filas:
        raise SystemExit(f"Sin coincidencias gold para prefijo {prefijo!r}")
    resumen = resumir(filas, lote, prefijo, len(gold))

    cab = (
        f"{'campo':20s} {'n':>5} {'exacto':>7} {'casi':>6} {'malo':>6} "
        f"{'conf.dec':>9} {'conf.real':>10} {'brecha':>7}"
    )
    print(f"{lote}: {resumen['jobs']} jobs · {resumen['comparaciones']} comparaciones\n")
    print(cab)
    print("-" * len(cab))
    for c in resumen["campos"]:
        print(
            f"{c['etiqueta']:20s} {c['n']:>5} {c['exacto']:>6.1f}% {c['casi']:>5.1f}% "
            f"{c['malo']:>5.1f}% {c['conf_declarada']:>8.1f}% {c['conf_real']:>9.1f}% "
            f"{c['brecha']:>+6.1f}"
        )
    print("-" * len(cab))
    print(
        f"{'TOTAL':20s} {resumen['comparaciones']:>5} {resumen['conf_real']:>6.1f}% "
        f"{'':>6} {'':>6} {resumen['conf_declarada']:>8.1f}% {resumen['conf_real']:>9.1f}% "
        f"{resumen['brecha']:>+6.1f}"
    )
    print(f"\nDeclarados 100% y distintos: {resumen['falsos_100']}")

    csv_out = pred_path.parent / f"comparacion-{lote}.csv"
    with csv_out.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(filas)
    json_out = pred_path.parent / f"{lote}-gold.json"
    json_out.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    docs_out = pred_path.parent / f"{lote}-gold-docs.json"
    docs_out.write_text(
        json.dumps(detalle(filas, lote, prefijo), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        f"\nDetalle (con PII): {csv_out}"
        f"\nAgregado para el visor: {json_out}"
        f"\nGold por documento (con PII, va cifrado): {docs_out}"
    )


if __name__ == "__main__":
    main()
