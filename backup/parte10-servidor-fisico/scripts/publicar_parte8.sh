#!/usr/bin/env bash
# Publica "Parte 8" en el visor e3-pages. Correr DENTRO del clone de e3-pages, en tu Mac.
#
#   bash publicar_parte8.sh <USUARIO_VISOR> <CLAVE_VISOR>
#
# Requisitos: estar en la carpeta del repo e3-pages (que tenga data/vault.json e index.html),
# tener la llave SSH del server, y python3.
set -euo pipefail

VUSER="${1:?Falta usuario del visor: bash publicar_parte8.sh <USUARIO> <CLAVE>}"
VPASS="${2:?Falta clave del visor: bash publicar_parte8.sh <USUARIO> <CLAVE>}"
KEY="${SSH_KEY:-$HOME/Documents/KEYS/llave/OT-IA-SERVER.pem}"
SRV="ubuntu@3.17.139.133"

[ -f data/vault.json ] || { echo "ERROR: no veo data/vault.json. Corre esto dentro del clone de e3-pages."; exit 1; }
[ -f index.html ]      || { echo "ERROR: no veo index.html. Corre esto dentro del clone de e3-pages."; exit 1; }

echo "[1/4] Trayendo el fragmento de la Parte 8 del server..."
scp -i "$KEY" -o StrictHostKeyChecking=accept-new \
  "$SRV:/data/e3/parte8_vault_fragment.json" .

echo "[2/4] Inyectando la Parte 8 al vault (re-cifra AES-GCM)..."
python3 -m pip install --quiet cryptography
VUSER="$VUSER" VPASS="$VPASS" python3 - <<'PY'
import base64, json, os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

user = os.environ["VUSER"]; pw = os.environ["VPASS"]
wrap = json.load(open("data/vault.json"))
salt = base64.b64decode(wrap["s"]); iters = int(wrap["iter"])
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iters).derive(
    (user + "\0" + pw).encode("utf-8"))
try:
    pt = AESGCM(key).decrypt(base64.b64decode(wrap["iv"]), base64.b64decode(wrap["ct"]), None)
except Exception:
    raise SystemExit("ERROR: usuario/clave del visor incorrectos (no se pudo descifrar el vault).")
data = json.loads(pt.decode("utf-8"))
data.setdefault("partes", {})["parte8"] = json.load(open("parte8_vault_fragment.json"))
new_pt = json.dumps(data, ensure_ascii=False).encode("utf-8")
iv = os.urandom(12)
ct = AESGCM(key).encrypt(iv, new_pt, None)
json.dump({"v": wrap.get("v", 1), "iter": iters, "s": wrap["s"],
           "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()},
          open("data/vault.json", "w"))
print("   vault OK: ahora tiene", len(data["partes"]), "partes.")
PY

echo "[3/4] Parcheando el menu en index.html..."
python3 - <<'PY'
s = open("index.html", encoding="utf-8").read()
if '"parte8"' in s:
    print("   index.html ya tenia parte8, no toco nada.")
else:
    anchor = '    };\n    const PARTE_KEYS = ["lote", "finger", "parte3", "parte4", "parte5", "parte6", "parte7"];'
    block = '''      parte8: {
        nav: "Parte 8 . 2 GPU Frente mejoras",
        blurb: "Frente 2x GPU (VL-7B + NLP-7B) con mejoras: fix del prompt NLP, fechas y tipo_documento al formato del gold, 4 campos nuevos (nivel_estudio, lee_braille, tipo_discapacidad, etnia), prompt OCR hibrido y voto numerico. IDs p8*. No pisa Partes 1-7 ni gold.",
        done: "Termino. Este es el resultado del load test.",
        note: "Vista Parte 8 . 2 GPU Frente mejoras. IDs p8*. Confianza real 74.4% (vs 72.6% Parte 4).",
        table: "Documentos parte 8 (frente, 2 GPU, mejoras)",
        ids: "p8",
        layout: "front",
        gpu: "dual",
        disclaimer: "Confianza declarada vs real (gold). Esta corrida incluye las mejoras; misma metrica que Partes 4-7.",
        vramNote: "dual5",
        perfil: "Perfil front (300 dpi).",
      },
    };
    const PARTE_KEYS = ["lote", "finger", "parte3", "parte4", "parte5", "parte6", "parte7", "parte8"];'''
    if anchor not in s:
        raise SystemExit("ERROR: no encontre el ancla en index.html (quizas cambio). Avisale al asistente.")
    open("index.html", "w", encoding="utf-8").write(s.replace(anchor, block, 1))
    print("   index.html parcheado (menu + SPECS.parte8).")
PY

echo "[4/4] Publicando en GitHub..."
rm -f parte8_vault_fragment.json
git add data/vault.json index.html
git commit -m "Parte 8: frente 2 GPU con mejoras (74.4% real vs 72.6% Parte 4)"
git push
echo
echo "LISTO. Abre https://shell931.github.io/e3-pages/ , entra con tu usuario/clave y deberia aparecer 'Parte 8' en el menu."
