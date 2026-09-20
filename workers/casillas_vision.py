#!/usr/bin/env python3
"""Lectura de los grupos de casillas del E3 sobre recortes ampliados.

Por que una pasada aparte
-------------------------
Los 4 campos de casilla (nivel_estudio, lee_braille, tipo_discapacidad, etnia)
fallaban por dos motivos distintos:

1. Invencion: el NLP solo ve texto y, al pedirsele "que opcion del grupo",
   devolvia la primera con confianza 100 aunque ningun cuadrito estuviera
   marcado (etnia inventada en 14 de 100 documentos).
2. Desalineacion: sobre la pagina completa el VLM corre la marca a la casilla
   vecina (TECNICO leido como PROFESIONAL en 12 de 100).

Este modulo ataca los dos: recorta las dos bandas donde viven las casillas, las
amplia, y pregunta por CADA cuadrito por separado. El valor del grupo se deriva
despues de forma determinista, y "ningun cuadrito marcado" es un resultado
valido y frecuente en vez de una invitacion a adivinar.
"""
import base64
import io
import os
import re
import unicodedata

from PIL import Image

# Regiones en fracciones de (ancho, alto). El formato del formulario es fijo;
# los margenes son holgados para tolerar el par de milimetros de diferencia
# entre escaneos (los altos van de 2018 a 2300 px).
REGIONES = {
    "nivel_estudio": (0.02, 0.55, 0.82, 0.62),
    "pie": (0.02, 0.70, 0.90, 0.87),
}

# Ampliar el recorte cuesta tokens de imagen, pero se paga: medido en los 100
# del gold, la escala 2 rinde 92.5% promedio contra 88.0% de la escala nativa
# (nivel_estudio 94% vs 83%), porque los cuadritos de una fila apretada se
# distinguen mejor. No subir mas sin volver a medir throughput.
ESCALA = int(os.getenv("CASILLAS_ESCALA", "2"))

OPCIONES = {
    "nivel_estudio": ("NINGUNO", "PRIMARIA", "BACHILLERATO", "TECNICO", "PROFESIONAL"),
    "lee_braille": ("SI", "NO"),
    "tipo_discapacidad": (
        "NINGUNA", "FISICA", "INTELECTUAL", "VISUAL", "AUDITIVA",
        "PSICOSOCIAL", "MULTIPLE", "SORDOCEGUERA",
    ),
    "etnia": (
        "INDIGENA", "AFROCOLOMBIANA", "ROM", "COM_NEGRAS", "RAIZALES", "PALENQUEROS",
    ),
}
CAMPOS = tuple(OPCIONES)

# Que campos se leen en cada region.
CAMPOS_REGION = {
    "nivel_estudio": ("nivel_estudio",),
    "pie": ("lee_braille", "tipo_discapacidad", "etnia"),
}

# Las dos regiones necesitan reglas distintas, y la diferencia se midio: con un
# split de 50 documentos para elegir y 50 para validar, las reglas cortas dan
# +10 puntos en nivel_estudio y las largas +4.7 en la banda del pie.
#
# El motivo es la base de cada grupo. En nivel_estudio casi siempre hay una
# marca (99 de 100 en el gold), asi que advertir "no adivines" solo hace que el
# modelo dude y corra la marca a la casilla vecina. En la banda del pie, en
# cambio, el vacio es frecuente (18 de 100 en lee_braille, 10 en
# tipo_discapacidad, 86 en etnia) y sin esa advertencia el modelo rellena.
_REGLAS_CORTAS = """
- [X] solo si hay una marca real dentro del cuadrito. En blanco es [ ].
- Como máximo un [X] por grupo. Si ninguno tiene marca, deja todos en [ ].
Responde SOLO el bloque pedido."""

_REGLAS_LARGAS = """
REGLAS (obligatorias):
- [X] solo si ves una marca real DENTRO del cuadrito (X, ✓, raya o relleno).
- Un cuadrito en blanco es [ ]. La mayoría están en blanco.
- Asocia cada cuadrito con la etiqueta que lo acompaña, no con la de al lado.
- Es normal que un grupo quede todo en [ ]. NO adivines para completarlo.
- NO marques la primera opción ni la más común por descarte.
- Como máximo un [X] por grupo.
Responde SOLO el bloque, sin explicaciones."""

_CUERPOS = {
    "nivel_estudio": """Esta imagen es la fila NIVEL DE ESTUDIO de un formulario E3 colombiano.

Hay 5 cuadritos en una sola fila. De izquierda a derecha, cada etiqueta va
seguida de su cuadrito: NINGUNO, PRIMARIA, BACHILLERATO, TÉCNICO, PROFESIONAL.

Recorre la fila de izquierda a derecha y reporta el estado de cada cuadrito:

CASILLAS:
nivel_estudio.NINGUNO=
nivel_estudio.PRIMARIA=
nivel_estudio.BACHILLERATO=
nivel_estudio.TECNICO=
nivel_estudio.PROFESIONAL=
""",

    "pie": """Esta imagen es la banda inferior de un formulario E3 colombiano, con
tres grupos de casillas, de izquierda a derecha:

1. LEE BRAILLE: dos cuadritos, "SI" y "NO".
2. TIPO DE DISCAPACIDAD: NINGUNA, VISUAL (columna izquierda); FÍSICA, AUDITIVA,
   MÚLTIPLE (columna del medio); INTELECTUAL, PSICOSOCIAL, SORDOCEGUERA (columna derecha).
3. ETNIA: INDÍGENA, AFROCOLOMBIANA, ROM (GITANA) (columna izquierda);
   COM.NEGRAS, RAIZALES, PALENQUEROS (columna derecha).

Reporta el estado del cuadrito de cada opción:

CASILLAS:
lee_braille.SI=
lee_braille.NO=
tipo_discapacidad.NINGUNA=
tipo_discapacidad.FISICA=
tipo_discapacidad.INTELECTUAL=
tipo_discapacidad.VISUAL=
tipo_discapacidad.AUDITIVA=
tipo_discapacidad.PSICOSOCIAL=
tipo_discapacidad.MULTIPLE=
tipo_discapacidad.SORDOCEGUERA=
etnia.INDIGENA=
etnia.AFROCOLOMBIANA=
etnia.ROM=
etnia.COM_NEGRAS=
etnia.RAIZALES=
etnia.PALENQUEROS=
""",
}

_REGLAS_POR_REGION = {"nivel_estudio": _REGLAS_CORTAS, "pie": _REGLAS_LARGAS}

PROMPTS = {r: _CUERPOS[r] + _REGLAS_POR_REGION[r] for r in _CUERPOS}

SINONIMOS = {
    "COM.NEGRAS": "COM_NEGRAS", "COMNEGRAS": "COM_NEGRAS",
    "COMUNIDADES NEGRAS": "COM_NEGRAS", "NEGRITUDES": "COM_NEGRAS",
    "ROM (GITANA)": "ROM", "GITANA": "ROM", "ROM GITANA": "ROM",
    "AFRO": "AFROCOLOMBIANA", "AFRODESCENDIENTE": "AFROCOLOMBIANA",
    "RAIZAL": "RAIZALES", "PALENQUERO": "PALENQUEROS",
    "SORDO CEGUERA": "SORDOCEGUERA", "MULTIPLES": "MULTIPLE",
    "TECNICA": "TECNICO", "BACHILLER": "BACHILLERATO",
}

_MARCADO = {"X", "✓", "✔", "☑", "☒", "V", "SI", "*", "●", "■", "1"}
_EN_BLANCO = {"", "[]", "()", "_", "-", "O", "NO", "VACIO", "BLANCO", "0", "."}

_CASILLAS_RE = re.compile(r"CASILLAS\s*:?", re.IGNORECASE)
_LINEA_RE = re.compile(r"^([a-z_]+)\s*\.\s*([A-Za-z_.()  ]+?)\s*=\s*(.*)$", re.IGNORECASE)


def _norm(valor) -> str:
    s = unicodedata.normalize("NFD", str(valor or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    for basura in "*`\"'":
        s = s.replace(basura, " ")
    return re.sub(r"\s+", " ", s).strip().upper()


def _canonico(campo: str, valor: str) -> str:
    v = _norm(valor)
    v = SINONIMOS.get(v, v)
    if v in OPCIONES[campo]:
        return v
    v2 = v.replace(".", "_").replace(" ", "_")
    v2 = SINONIMOS.get(v2, v2)
    return v2 if v2 in OPCIONES[campo] else ""


def _marca(valor: str) -> bool | None:
    v = _norm(valor).replace(" ", "").strip("[]()")
    if v in _EN_BLANCO:
        return False
    if v in _MARCADO:
        return True
    return None


def recortar(ruta_imagen: str) -> dict:
    """Devuelve {region: png_base64} con las bandas de casillas ampliadas."""
    recortes = {}
    with Image.open(ruta_imagen) as im:
        im = im.convert("L")
        W, H = im.size
        for region, (x0, y0, x1, y1) in REGIONES.items():
            caja = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
            rec = im.crop(caja)
            if ESCALA != 1:
                rec = rec.resize((rec.width * ESCALA, rec.height * ESCALA),
                                 Image.LANCZOS)
            buf = io.BytesIO()
            rec.save(buf, format="PNG")
            recortes[region] = base64.b64encode(buf.getvalue()).decode()
    return recortes


def parse_bloque(texto: str, campos: tuple) -> dict:
    """Deriva el valor de cada grupo a partir del estado de sus cuadritos.

    ``marcadas`` 0 significa que se miraron los cuadritos y ninguno tiene marca
    (dato valido); >1 es ambiguo y se deja vacio en vez de elegir uno.
    """
    salida = {c: {"valor": "", "evidencia": False, "marcadas": 0} for c in campos}
    if not texto:
        return salida
    m = _CASILLAS_RE.search(texto)
    cuerpo = texto[m.end():] if m else texto

    vistos = {c: [] for c in campos}
    for linea in cuerpo.splitlines():
        s = linea.strip().strip("*`|").strip()
        if not s:
            continue
        lm = _LINEA_RE.match(s)
        if not lm:
            continue
        campo = lm.group(1).lower()
        if campo not in vistos:
            continue
        opcion = _canonico(campo, lm.group(2))
        estado = _marca(lm.group(3))
        if opcion and estado is not None:
            vistos[campo].append((opcion, estado))

    for campo, pares in vistos.items():
        if not pares:
            continue
        # El modelo puede repetir una opcion; gana que este marcada al menos una vez.
        estado_por_opcion = {}
        for opcion, est in pares:
            estado_por_opcion[opcion] = estado_por_opcion.get(opcion, False) or est
        marcadas = [o for o, est in estado_por_opcion.items() if est]
        salida[campo] = {
            "valor": marcadas[0] if len(marcadas) == 1 else "",
            "evidencia": True,
            "marcadas": len(marcadas),
        }
    return salida


def confianza(info: dict) -> int:
    """Confianza honesta: alta solo cuando hubo una lectura visual concluyente."""
    if not info.get("evidencia"):
        return 30
    if info.get("marcadas", 0) > 1:
        return 40
    return 95 if info.get("valor") else 90


def leer_casillas(ruta_imagen: str, client, modelo: str) -> dict:
    """Lee los 4 campos de casilla con una pasada de vision por region."""
    resultado = {}
    recortes = recortar(ruta_imagen)
    for region, campos in CAMPOS_REGION.items():
        img = recortes.get(region)
        texto = ""
        if img:
            try:
                r = client.chat.completions.create(
                    model=modelo,
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": PROMPTS[region]},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/png;base64,{img}"}},
                    ]}],
                    max_tokens=400,
                    temperature=0.0,
                )
                texto = r.choices[0].message.content or ""
            except Exception:
                texto = ""
        resultado.update(parse_bloque(texto, campos))
    return resultado


def aplicar(campos: list, lecturas: dict | None) -> list:
    """Sobrescribe los campos de casilla con la lectura visual.

    Solo se sobrescribe cuando hubo lectura. Sin lectura -- porque el bloque no
    vino o porque la pasada de vision fallo entera -- se conserva lo que trajo
    el NLP pero con la confianza bajada: el valor puede ser una adivinanza y no
    debe viajar al visor como certeza.
    """
    lecturas = lecturas or {}
    por_etiqueta = {c.get("etiqueta"): c for c in campos}
    for campo in CAMPOS:
        info = lecturas.get(campo) or {"valor": "", "evidencia": False, "marcadas": 0}
        destino = por_etiqueta.get(campo)
        if not info["evidencia"]:
            if destino is not None:
                destino["confianza"] = min(int(destino.get("confianza") or 0), 50)
                destino["fuente"] = "nlp_sin_lectura_visual"
            continue
        nuevo = {
            "etiqueta": campo,
            "valor": info["valor"],
            "confianza": confianza(info),
            "fuente": "casilla_visual",
            "marcadas": info["marcadas"],
        }
        if destino is None:
            campos.append(nuevo)
        else:
            destino.update(nuevo)
    return campos
