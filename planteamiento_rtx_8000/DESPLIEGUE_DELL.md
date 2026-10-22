# Despliegue en el Dell R740xd (2× Quadro RTX 8000)

Paso a paso de las tareas B2–B4 del plan, con lo aprendido al validar en AWS
g4dn.metal (Parte 16: 27B-FP8 en Turing = 95,5 % vs 95,7 % de la Parte 15).
Todo se corre desde la raíz del repo; la Parte 15 no se toca.

## B2 · Antes de empezar (infra)

| Qué | Valor | Por qué |
| --- | --- | --- |
| Sistema | Ubuntu Server 22.04 o 24.04 LTS | Validado en 24.04 |
| **Secure Boot** | **Apagado** (o firmar el módulo DKMS con una MOK) | El driver se compila con DKMS; con Secure Boot activo no carga |
| BIOS | Perfil de máximo rendimiento · "Memory Mapped I/O above 4 GB" habilitado | GPUs de 48 GB |
| GPUs | Si las RTX 8000 son la versión con ventilador, perfil térmico de iDRAC para tarjetas PCIe de alto consumo | Refrigeración en chasis 2U |
| Disco | `/data` con ≥ 200 GB libres (SSD) | Imagen vLLM 30 GB + pesos ~50 GB + TIFF/resultados |
| Red | Salida a GitHub, Docker Hub, Hugging Face, PyPI, `nvidia.github.io`, `download.docker.com` y S3 | Sin salida: proxy o copiar `/data/hf-cache` e imágenes desde otro servidor |
| Acceso a S3 | Lectura sobre `s3://forme3/E3V2/*` (rol o llaves de solo lectura en `aws configure`) | Política mínima: `s3:ListBucket` con prefijo `E3V2/` + `s3:GetObject` en `forme3/E3V2/*` |
| Firewall | Solo SSH (22) desde la red de administración | RabbitMQ (5672/15672) y vLLM (8000–8002) por túnel SSH |

## B3 · Base del servidor

```bash
git clone https://github.com/shell931/ov-ia-caso-1-e3-ocr-forms.git && cd ov-ia-caso-1-e3-ocr-forms
bash planteamiento_rtx_8000/instalar_servidor.sh   # instala el driver y pide reiniciar
sudo reboot
bash planteamiento_rtx_8000/instalar_servidor.sh   # termina Docker, toolkit y AWS CLI
exit                                               # volver a entrar por SSH (grupo docker)
```

Listo cuando la verificación final lista las 2 RTX 8000 desde un contenedor.

## B4 · Datos, gold, imagen y pesos

```bash
# desde la máquina que tiene el gold (PII: solo por scp, nunca a git)
scp gold_e3_obtenido-con-fable.csv usuario@dell:/tmp/gold_e3.csv

# en el Dell
GOLD_CSV=/tmp/gold_e3.csv bash planteamiento_rtx_8000/preparar_datos.sh && rm /tmp/gold_e3.csv
```

El script baja los 267 TIFF, les quita el prefijo `000000010010101;`, convierte
el gold a JSON (permisos 600), comprueba que los 267 ids coincidan, baja la imagen
de vLLM por digest y verifica que traiga kernels `sm_75`, y baja los pesos
(27B-FP8 + NLP 7B-AWQ; `CONTROL=1` suma el VL 7B del control).

## B4.5 · Levantar y verificar

En el Dell va **una réplica del 27B por GPU, sin TP** (en AWS hizo falta TP=4
porque cada T4 tiene 16 GB). Primero una réplica y el NLP en la GPU 1:

```bash
bash planteamiento_rtx_8000/probar_modelo.sh planteamiento_rtx_8000/modelos/qwen36-27b-fp8-turing-simple.env front
```

`probar_modelo.sh` levanta el stack, espera `verificar.sh` (hasta 20 min; el
primer arranque del 27B compila kernels Triton, ~7–8 min en T4), procesa los 267,
y deja KPI y confianza en `~/e3/p15/res/` (o en `$RES`). **Esperado: KPI ≈ 95,5 %,
0 errores.** Después, la etapa B5 prueba `qwen36-27b-fp8-turing-doble.env`
(dos réplicas) y la concurrencia.

Los envs del Dell (`turing-simple`, `turing-doble`) no se pudieron probar en AWS
porque allá no hay GPUs de 48 GB: los porcentajes de memoria salen de cuentas
(pesos del 27B = 30,9 GB) y se ajustan en B5.

## Problemas conocidos (vistos en g4dn.metal)

| Síntoma | Causa | Arreglo |
| --- | --- | --- |
| `dpkg` falla al instalar el driver; aparece un kernel nuevo | Metapaquete `linux-modules-nvidia-580-server-<flavor>` | No usarlo: `instalar_servidor.sh` usa DKMS y congela el kernel |
| `nvidia-smi`: "couldn't communicate" / `NVRM: API mismatch` en `dmesg` | Módulo y librerías de distinta versión | Igual que arriba (DKMS compila la versión de las librerías) |
| vLLM queda en "No available shared memory broadcast block" sin terminar de arrancar | All-reduce CUSTOM con TP>1 sin NVLink | `--disable-custom-all-reduce` (ya está en el compose; con TP=1 no hace nada) |
| `compare_gold_real.py`: "Sin coincidencias gold" | TIFF con el prefijo de S3 | `preparar_datos.sh` los copia sin prefijo |
| KPI ~4 puntos abajo y `formulario_no` ~18 % | Mismo prefijo: `nlp_worker` completa `formulario_no` con los dígitos del nombre | Igual que arriba |
| `probar_modelo.sh` falla en el paso de preds | El original busca `scripts/corrida/` | Usar `planteamiento_rtx_8000/probar_modelo.sh` |
| `ERROR ... FA version 2 is not supported` en el log de vLLM | FlashAttention 2 no soporta Turing | Esperado: vLLM usa `TRITON_ATTN` sola |

## Referencias

- Resultados de la validación: visor, menús Parte 16 y Parte 16b.
- `README.md` de esta carpeta: decisiones del planteamiento y cuentas de memoria.
