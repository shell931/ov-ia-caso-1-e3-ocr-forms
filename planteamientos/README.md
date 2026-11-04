# Planteamientos

Cambios de infraestructura: correr el pipeline oficial en hardware nuevo. Cada
carpeta es **ejecutable** (compose, envs, scripts de instalación) y se corre
desde la raíz del repo.

Los resultados de cada planteamiento se registran como una Parte más en
[`../pruebas/`](../pruebas/README.md).

| Carpeta | Hardware destino | Parte que valida | Estado |
| --- | --- | --- | --- |
| [`rtx-8000/`](rtx-8000/README.md) | Dell R740xd · 2× Quadro RTX 8000 (Turing) | [Parte 16](../pruebas/lote2-e3v2/parte-16/resultados.md) en g4dn.metal | Validado en AWS; pendiente en el Dell |
