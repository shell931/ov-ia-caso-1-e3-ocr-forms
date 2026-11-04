#!/usr/bin/env python3
"""Lectura de los grupos de casillas del E3 sobre recortes ampliados.

Por que una pasada aparte
-------------------------
Los campos de casilla (tipo_documento, nivel_estudio, lee_braille,
tipo_discapacidad, etnia) fallaban por dos motivos distintos:

1. Invencion: el NLP solo ve texto y, al pedirsele "que opcion del grupo",
   devolvia la primera con confianza 100 aunque ningun cuadrito estuviera
   marcado (etnia inventada en 14 de 100; tipo_documento=CC en 6000000002
   con ambos cuadritos en blanco — y el gold tambien inventaba CC, asi que
   la eval oficial daba exacto/100).
2. Desalineacion: sobre la pagina completa el VLM corre la marca a la casilla
   vecina (TECNICO leido como PROFESIONAL en 12 de 100).

Este modulo ataca los dos: recorta las bandas donde viven las casillas, las
amplia, y pregunta por CADA cuadrito por separado. El valor del grupo se deriva
despues de forma determinista, y "ningun cuadrito marcado" es un resultado
valido y frecuente en vez de una invitacion a adivinar.

Por que LEE BRAILLE va aparte
-----------------------------
Leer braille+discapacidad+etnia en un solo recorte hacia que el VLM inventara
marcas (p.ej. 6000000020: cuadritos vacios pero respondia lee_braille.SI=✓).
Braille tiene su recorte; discapacidad+etnia siguen juntos (separarlos
derrumbo tipo_discapacidad). Ademas "SI" ya no es marca generica: el eco
lee_braille.SI=[SI] si cuenta como marcado.
"""
import base64
import io
import os
import re
import unicodedata

from PIL import Image

# Regiones en fracciones de (ancho, alto). LEE BRAILLE va aparte: en el pie
# completo el VLM inventaba SI/VISUAL sobre cuadritos vacios (caso 6000000020).
# Discapacidad+etnia siguen juntos (separarlos derrumbo tipo_discapacidad).
REGIONES = {
    # TIPO DE DOCUMENTO (CC / CE) arriba a la derecha de FECHA INSCRIPCION.
    "tipo_documento": (0.42, 0.18, 0.72, 0.33),
    "nivel_estudio": (0.02, 0.55, 0.82, 0.62),
    "lee_braille": (0.015, 0.735, 0.22, 0.815),
    "pie_resto": (0.195, 0.70, 0.90, 0.87),
}

# Escala 3 en el pie: las marcas reales de SI (minoritarias) se ven mejor; en
# nivel_estudio se mantiene 2 (ya medido). Override con CASILLAS_ESCALA.
ESCALA = int(os.getenv("CASILLAS_ESCALA", "2"))
ESCALA_PIE = int(os.getenv("CASILLAS_ESCALA_PIE", "3"))

OPCIONES = {
    # Valores en formato gold (postprocess mapeaba CC->CEDULA_CIUDADANIA).
    "tipo_documento": ("CEDULA_CIUDADANIA", "CEDULA_EXTRANJERIA"),
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

CAMPOS_REGION = {
    "tipo_documento": ("tipo_documento",),
    "nivel_estudio": ("nivel_estudio",),
    "lee_braille": ("lee_braille",),
    "pie_resto": ("tipo_discapacidad", "etnia"),
}

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

_REGLAS_VACIO_FRECUENTE = """
REGLAS (obligatorias):
- [X] SOLO si ves tinta oscura (X, tilde o relleno) DENTRO del cuadrito.
- La etiqueta impresa al lado (SI, NO, VISUAL, etc.) NO es una marca.
- Un cuadrito en blanco es [ ]. Es normal que TODO el grupo quede en [ ].
- NO adivines ni marques la primera opción por descarte.
- Como máximo un [X] por grupo.
Responde SOLO el bloque CASILLAS, sin explicaciones."""

_CUERPOS = {
    "tipo_documento": """Esta imagen es SOLO el grupo TIPO DE DOCUMENTO de un formulario E3
(dos cuadritos verticales: CÉDULA DE CIUDADANÍA arriba, CÉDULA DE EXTRANJERÍA abajo).

CASILLAS:
tipo_documento.CEDULA_CIUDADANIA=[ ]
tipo_documento.CEDULA_EXTRANJERIA=[ ]
""",

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

    "lee_braille": """Esta imagen es SOLO el grupo LEE BRAILLE de un formulario E3
(dos cuadritos: SI a la izquierda, NO a la derecha).

CASILLAS:
lee_braille.SI=[ ]
lee_braille.NO=[ ]
""",

    "pie_resto": """Esta imagen es la banda inferior de un formulario E3 (sin LEE BRAILLE),
con dos grupos de casillas de izquierda a derecha:

1. TIPO DE DISCAPACIDAD: NINGUNA, VISUAL (columna izquierda); FÍSICA, AUDITIVA,
   MÚLTIPLE (columna del medio); INTELECTUAL, PSICOSOCIAL, SORDOCEGUERA (columna derecha).
2. ETNIA: INDÍGENA, AFROCOLOMBIANA, ROM (GITANA) (columna izquierda);
   COM.NEGRAS, RAIZALES, PALENQUEROS (columna derecha).

Reporta el estado del cuadrito de cada opción:

CASILLAS:
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

# pie_resto usa las reglas largas originales (ya medidas); lee_braille y
# tipo_documento las de vacio frecuente: ahi el VLM inventaba la primera opcion
# (SI / CEDULA_CIUDADANIA) sobre cuadritos en blanco.
_REGLAS_POR_REGION = {
    "tipo_documento": _REGLAS_VACIO_FRECUENTE,
    "nivel_estudio": _REGLAS_CORTAS,
    "lee_braille": _REGLAS_VACIO_FRECUENTE,
    "pie_resto": _REGLAS_LARGAS,
}

PROMPTS = {r: _CUERPOS[r] + _REGLAS_POR_REGION[r] for r in _CUERPOS}

SINONIMOS = {
    "COM.NEGRAS": "COM_NEGRAS", "COMNEGRAS": "COM_NEGRAS",
    "COMUNIDADES NEGRAS": "COM_NEGRAS", "NEGRITUDES": "COM_NEGRAS",
    "ROM (GITANA)": "ROM", "GITANA": "ROM", "ROM GITANA": "ROM",
    "AFRO": "AFROCOLOMBIANA", "AFRODESCENDIENTE": "AFROCOLOMBIANA",
    "RAIZAL": "RAIZALES", "PALENQUERO": "PALENQUEROS",
    "SORDO CEGUERA": "SORDOCEGUERA", "MULTIPLES": "MULTIPLE",
    "TECNICA": "TECNICO", "BACHILLER": "BACHILLERATO",
    "CC": "CEDULA_CIUDADANIA", "CEDULA DE CIUDADANIA": "CEDULA_CIUDADANIA",
    "CEDULA CIUDADANIA": "CEDULA_CIUDADANIA",
    "CE": "CEDULA_EXTRANJERIA", "CEDULA DE EXTRANJERIA": "CEDULA_EXTRANJERIA",
    "CEDULA EXTRANJERIA": "CEDULA_EXTRANJERIA",
}

# OJO: no poner "SI" ni "V" aqui. "SI" como valor de lee_braille.SI=SI lo
# manejamos abajo como eco del nombre de la opcion; "V" chocaba con VISUAL.
_MARCADO = {"X", "✓", "✔", "☑", "☒", "*", "●", "■", "1"}
_EN_BLANCO = {"", "[]", "()", "_", "-", "O", "NO", "VACIO", "BLANCO", "0", ".", "SI"}

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


def _marca(valor: str, opcion: str = "") -> bool | None:
    """Interpreta el estado del cuadrito.

    - [X] / ✓ / etc. → marcado
    - vacio / [ ] → en blanco
    - eco del nombre de la opcion (lee_braille.SI=[SI]) → marcado
    - "SI"/"NO" sueltos sin coincidir con la opcion no marcan
    """
    v = _norm(valor).replace(" ", "").strip("[]()")
    op = _norm(opcion)
    if op and v == op:
        # Eco tipico del VLM: lee_braille.SI=[SI] o .NO=[NO]
        return True
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
            # Escala 3 en lee_braille y tipo_documento (detectar vacio vs marca fina).
            escala = ESCALA_PIE if region in ("lee_braille", "tipo_documento") else ESCALA
            if escala != 1:
                rec = rec.resize((rec.width * escala, rec.height * escala),
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
        s = linea.strip().strip("*`|-").strip()
        if not s:
            continue
        # Aceptar "- lee_braille.SI=[X]" 
        if s.startswith("-"):
            s = s.lstrip("-").strip()
        lm = _LINEA_RE.match(s)
        if not lm:
            continue
        campo = lm.group(1).lower()
        if campo not in vistos:
            continue
        opcion = _canonico(campo, lm.group(2))
        estado = _marca(lm.group(3), opcion=opcion)
        if opcion and estado is not None:
            vistos[campo].append((opcion, estado))

    for campo, pares in vistos.items():
        if not pares:
            continue
        estado_por_opcion = {}
        for opcion, est in pares:
            estado_por_opcion[opcion] = estado_por_opcion.get(opcion, False) or est
        marcadas = [o for o, est in estado_por_opcion.items() if est]
        valor = ""
        if len(marcadas) == 1:
            valor = marcadas[0]
        elif (
            campo == "tipo_discapacidad"
            and len(marcadas) == 2
            and "NINGUNA" in marcadas
        ):
            # En el pie del E3 a menudo queda una segunda marca fantasma junto a
            # NINGUNA. Si se blanquea el campo, se pierden ~14 exactos. Se conserva
            # NINGUNA. Caso conocido que sigue mal: 6000000058 (NINGUNA+VISUAL,
            # gold VISUAL).
            valor = "NINGUNA"
        salida[campo] = {
            "valor": valor,
            "evidencia": True,
            "marcadas": len(marcadas),
            "marcadas_ops": marcadas,
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
    """Lee los campos de casilla con una pasada de vision por region."""
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
        parsed = parse_bloque(texto, campos)
        for campo in campos:
            info = parsed[campo]
            # Vision respondio pero no parseamos lineas: tratar como vacio con
            # evidencia (no dejar que el NLP invente SI / primera opcion).
            if not info.get("evidencia") and texto.strip():
                info = {"valor": "", "evidencia": True, "marcadas": 0}
            resultado[campo] = info
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
