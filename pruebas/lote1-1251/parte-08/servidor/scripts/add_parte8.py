#!/usr/bin/env python3
"""Inyecta partes.parte8 en el vault cifrado del visor e3-pages.

Descifra data/vault.json (AES-GCM, misma derivacion que el navegador:
PBKDF2-SHA256 sobre  user + "\\0" + pass  con el salt/iter del vault),
inserta el fragmento parte8 y vuelve a cifrar con un IV nuevo.

Requisitos:  pip install cryptography

Uso:
  python add_parte8.py <usuario> <password> data/vault.json parte8_vault_fragment.json

Deja data/vault.json actualizado. Luego: editar index.html (ver snippet),
commit y push a shell931/e3-pages.
"""
import base64
import json
import os
import sys

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

# Descifrar (WebCrypto concatena el tag de 16 bytes al final del ciphertext)
pt = AESGCM(key).decrypt(base64.b64decode(wrap["iv"]), base64.b64decode(wrap["ct"]), None)
data = json.loads(pt.decode("utf-8"))

frag = json.load(open(frag_path))
data.setdefault("partes", {})["parte8"] = frag

# Re-cifrar con IV nuevo (12 bytes, como WebCrypto por defecto)
new_pt = json.dumps(data, ensure_ascii=False).encode("utf-8")
iv = os.urandom(12)
ct = AESGCM(key).encrypt(iv, new_pt, None)

out = {
    "v": wrap.get("v", 1),
    "iter": iters,
    "s": wrap["s"],
    "iv": base64.b64encode(iv).decode(),
    "ct": base64.b64encode(ct).decode(),
}
json.dump(out, open(vault_path, "w"))
print(f"OK: vault actualizado con parte8 ({len(data['partes'])} partes en total).")
print("Verifica abriendo el visor con tu usuario/clave; deberia aparecer 'Parte 8' en el menu.")
