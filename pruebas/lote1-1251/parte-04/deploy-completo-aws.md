# Deploy Completo - Caso 1 v2 - Formularios E3 + Mejoras

## 🎯 Objetivo

Desplegar el pipeline de OCR para formularios E3/E4 en AWS **CON mejoras de post-procesamiento** para subir la confianza real de **72.6% → 80%+**.

## 📊 Configuración Actual (Parte 4)

```
✅ Hardware: g7e.12xlarge (2× RTX PRO 6000 Ada, 96 GB VRAM c/u)
✅ GPU 0: Qwen2.5-VL-7B-Instruct (Visión/OCR) → Puerto 8001
✅ GPU 1: Qwen2.5-7B-Instruct-AWQ (NLP/Extracción) → Puerto 8000
✅ Workers: 8 OCR + 12 NLP
✅ Throughput actual: ~1,700 docs/h
✅ Confianza actual: 72.6% real
```

## 🚀 Deploy desde Mac

### 1. Preparar archivos locales

En tu Mac, ve al directorio del proyecto:

```bash
cd ~/Documents/APPS/overthere/ia-analisis
git pull origin main
```

### 2. Ejecutar deploy automático

```bash
# Asegúrate de tener la llave SSH
export SSH_KEY="$HOME/Documents/KEYS/llave/OT-IA-SERVER.pem"

# Ejecutar deploy
./scripts/deploy_completo_aws.sh
```

**Esto hará automáticamente:**

1. ✅ Verificar conexión a AWS (IP: 3.17.139.133)
2. ✅ Crear estructura de directorios
3. ✅ Copiar workers (incluyendo `postprocess_express.py`)
4. ✅ Generar `docker-compose.yml`
5. ✅ Montar `/data` (instance store)
6. ✅ Descargar gold desde S3
7. ✅ Levantar servicios (RabbitMQ + vLLM GPU0 + vLLM GPU1 + Workers)
8. ✅ Esperar carga de modelos (3-5 min)

### 3. Verificar despliegue

SSH al servidor:

```bash
ssh -i "$SSH_KEY" ubuntu@3.17.139.133
```

Verificar VRAM:

```bash
nvidia-smi
```

**Salida esperada:**

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xx       Driver Version: 535.xx       CUDA Version: 12.x   |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
|   0  NVIDIA RTX PRO 6000 Ada   On   | 00000000:00:1E.0 Off |                 0 |
| Memory-Usage: 42GB / 96GB                                                   |
|   1  NVIDIA RTX PRO 6000 Ada   On   | 00000000:00:1F.0 Off |                 0 |
| Memory-Usage: 33GB / 96GB                                                   |
+-----------------------------------------------------------------------------+
```

Verificar servicios:

```bash
cd ~/test-ia-local/caso-1-v2-e3
sudo docker compose ps
```

**Salida esperada:**

```
NAME                 SERVICE    STATUS    PORTS
caso1v2-rabbitmq     rabbitmq   Up        5672, 15672
caso1v2-vllm-nlp     vllm       Up        8000
caso1v2-vllm-vl      vllm-vl    Up        8001
caso1v2-ocr          ocr        Up        (8 workers)
caso1v2-nlp          nlp        Up        (12 workers)
```

Verificar modelos:

```bash
# VLM (GPU 0)
curl http://localhost:8001/v1/models

# NLP (GPU 1)
curl http://localhost:8000/v1/models
```

---

## 🧪 Testing

### Opción 1: Test Rápido (10 documentos)

```bash
cd ~/test-ia-local/caso-1-v2-e3/scripts
./test_mejoras.sh
```

Esto procesa 10 documentos y te da un resultado preliminar en ~2 minutos.

### Opción 2: Test Completo (100 documentos gold)

```bash
cd ~/test-ia-local/caso-1-v2-e3/scripts
python3 load_test_simple.py
```

Espera ~5 minutos para 100 docs @ 20 concurrent.

### Ver progreso en tiempo real

**RabbitMQ UI:**

```
http://3.17.139.133:15672
user: guest / pass: guest
```

**Logs de workers:**

```bash
sudo docker compose logs -f ocr nlp
```

**GPU utilization:**

```bash
watch -n1 nvidia-smi
```

---

## 📊 Comparar Resultados contra Gold

### 1. Extraer resultados de RabbitMQ

Puedes usar la UI de RabbitMQ (http://3.17.139.133:15672) → Queues → `nlp_output` → "Get Messages"

O crear un script consumer:

```bash
cd ~/test-ia-local/caso-1-v2-e3/scripts
python3 consume_results.py > results.jsonl
```

### 2. Comparar contra gold

```bash
python3 compare_gold.py \
  --gold /data/e3/gold/gold.json \
  --preds results.jsonl \
  --output comparacion-parte4-mejorado.csv
```

### 3. Ver métricas

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('comparacion-parte4-mejorado.csv')
print('Confianza Real:', df['conf_real'].mean())
print('Brecha:', df['brecha'].mean())
print('Falsos 100%:', df['falsos_100'].sum())
"
```

**Objetivo:** `conf_real >= 80%`

---

## 🔧 Ajustes y Troubleshooting

### Si los modelos no cargan

```bash
# Ver logs
sudo docker compose logs vllm vllm-vl

# Reintentar
sudo docker compose restart vllm vllm-vl
```

### Si workers no procesan

```bash
# Ver logs
sudo docker compose logs ocr nlp

# Verificar RabbitMQ
curl http://localhost:15672/api/queues

# Reiniciar workers
sudo docker compose restart ocr nlp
```

### Si necesitas actualizar solo el código de workers

```bash
# Desde tu Mac
scp -i "$SSH_KEY" caso-1-v2-e3/workers/*.py ubuntu@3.17.139.133:~/test-ia-local/caso-1-v2-e3/workers/

# En el servidor
ssh -i "$SSH_KEY" ubuntu@3.17.139.133
cd ~/test-ia-local/caso-1-v2-e3
sudo docker compose restart ocr nlp
```

### Ver VRAM en tiempo real

```bash
watch -n1 'nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv'
```

---

## 🎯 Mejoras Implementadas

### 1. Post-procesamiento (`postprocess_express.py`)

**TOP 5 campos corregidos:**

1. **`direccion`** (740 errores)
   - `C11+389-13` → `Cll 73 # 89-13` ✅
   - `cl1 690# 72 038 508` → `Cll 69 D # 72 C 38 Sur` ✅

2. **`telefono_movil`** (673 errores)
   - `3222940576` → `3222940` (recortar dígitos extra) ✅

3. **`email`** (375 errores)
   - `cutlook.can` → `outlook.com` ✅
   - `gimal` → `gmail` ✅

4. **`ciudad`** (311 errores)
   - `Bo50.t3` → `Bogota` ✅
   - Remover números y caracteres especiales ✅

5. **`nombres/apellidos`** (234-174 errores)
   - `Juan1` → `Juan` ✅
   - `Natalia.` → `Natalia` ✅

### 2. Prompts mejorados

Los prompts de `ocr_worker.py` y `nlp_worker.py` incluyen **instrucciones explícitas** sobre formatos:

- **Direcciones:** "Cll" no "C11", "#" no "+"
- **Ciudades:** Sin números ni caracteres especiales
- **Teléfonos:** Solo dígitos, sin espacios
- **Emails:** Formato válido con @ y dominio correcto

---

## 📈 Resultados Esperados

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| **Confianza Real** | 72.6% | **≥80%** | **+7.4%** |
| **Brecha Sobrevaloración** | +20.7 | **≤15** | **-5.7 pts** |
| **Falsos 100%** | 2,747 | **≤1,500** | **-45%** |
| **direccion** errors | 740 | **≤370** | **-50%** |
| **telefono_movil** errors | 673 | **≤340** | **-50%** |
| **email** errors | 375 | **≤190** | **-50%** |

---

## 📝 Notas Importantes

1. **AWS borra todo al apagar:** Guarda los resultados importantes (CSVs, JSONs) en S3 o descárgalos localmente antes de apagar.

2. **Instance store (/data):** Se borra al apagar. Solo úsalo para cache temporal.

3. **Modelos pesados:** El primer arranque descarga ~42 GB de Hugging Face. Los siguientes arranques reusarán `/data/hf-cache` (si no apagas).

4. **Costos AWS:** `g7e.12xlarge` cuesta ~$6.24/hora. Apaga cuando no uses.

5. **Git sync:** Este repo (`ia-analisis`) tiene el código fuente. Cualquier cambio debe commitearse aquí para no perderlo.

---

## 🔗 Links Útiles

- **RabbitMQ UI:** http://3.17.139.133:15672
- **Documentación AWS g7e:** https://aws.amazon.com/ec2/instance-types/g7e/
- **Qwen2.5-VL:** https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
- **vLLM Docs:** https://docs.vllm.ai/

---

**Creado:** Sep 17, 2026  
**Autor:** Cloud Agent  
**Propósito:** Deploy + Mejoras para Parte 4 (72.6% → 80%+)
