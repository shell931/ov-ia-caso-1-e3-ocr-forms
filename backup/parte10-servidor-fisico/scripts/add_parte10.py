#!/usr/bin/env python3
"""Inyecta partes.parte10 en el vault cifrado del visor e3-pages.

Misma derivación que add_parte8.py / el navegador:
PBKDF2-SHA256 sobre user + "\\0" + pass.

Uso:
  python add_parte10.py <usuario> <password> data/vault.json parte10_vault_fragment.json

El fragmento debe ser el objeto plano (con clave 'rows', no envuelto en
{'parte10': ...}). Ver build_parte10_fragment.py.
"""
import base64, json, os, sys
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

user, pw, vault_path, frag_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
wrap = json.load(open(vault_path))
salt = base64.b64decode(wrap["s"])
iters = int(wrap["iter"])
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iters).derive(
    (user + "\0" + pw).encode("utf-8")
)
pt = AESGCM(key).decrypt(base64.b64decode(wrap["iv"]), base64.b64decode(wrap["ct"]), None)
data = json.loads(pt.decode("utf-8"))
frag = json.load(open(frag_path))
if "parte10" in frag and "rows" not in frag:
    frag = frag["parte10"]
if "resultados" in frag and "rows" not in frag:
    frag["rows"] = frag.pop("resultados")
data.setdefault("partes", {})["parte10"] = frag
iv = os.urandom(12)
ct = AESGCM(key).encrypt(iv, json.dumps(data, ensure_ascii=False).encode("utf-8"), None)
out = {"v": wrap.get("v", 1), "iter": iters, "s": wrap["s"],
       "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()}
json.dump(out, open(vault_path, "w"))
print(f"OK: vault con parte10 ({len(data['partes'])} partes). rows={len(frag.get('rows') or [])}")
