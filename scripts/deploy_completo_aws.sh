#!/bin/bash
# Deploy completo de caso-1-v2-e3 en servidor AWS limpio
# Incluye mejoras de post-procesamiento (72.6% → 80%+)

set -e

SERVER_IP="3.17.139.133"
KEY="${SSH_KEY:-$HOME/Documents/KEYS/llave/OT-IA-SERVER.pem}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Deploy Completo Caso 1 v2 - Formularios E3 + Mejoras      ║${NC}"
echo -e "${BLUE}║  Servidor: $SERVER_IP                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}[1/8] Verificando conexión...${NC}"
if ! ssh -i "$KEY" -o ConnectTimeout=5 ubuntu@$SERVER_IP "echo OK" &>/dev/null; then
    echo "❌ No se puede conectar a $SERVER_IP"
    exit 1
fi
echo "✅ Conectado"

echo ""
echo -e "${GREEN}[2/8] Creando estructura de directorios...${NC}"
ssh -i "$KEY" ubuntu@$SERVER_IP << 'EOF'
mkdir -p ~/test-ia-local/caso-1-v2-e3/{workers,app,scripts,data}
echo "✅ Directorios creados"
EOF

echo ""
echo -e "${GREEN}[3/8] Copiando archivos del repo local...${NC}"

# Verificar que estamos en el directorio correcto
if [ ! -d "caso-1-v2-e3" ]; then
    echo "❌ No estás en el directorio del repo ia-analisis"
    echo "   cd ~/Documents/APPS/overthere/ia-analisis"
    exit 1
fi

# Copiar archivos
echo "  → Copiando workers..."
scp -i "$KEY" caso-1-v2-e3/workers/*.py ubuntu@$SERVER_IP:~/test-ia-local/caso-1-v2-e3/workers/

echo "  → Copiando scripts..."
scp -i "$KEY" caso-1-v2-e3/scripts/*.{py,sh} ubuntu@$SERVER_IP:~/test-ia-local/caso-1-v2-e3/scripts/ 2>/dev/null || true

echo "✅ Archivos copiados"

echo ""
echo -e "${GREEN}[4/8] Generando docker-compose.yml...${NC}"
ssh -i "$KEY" ubuntu@$SERVER_IP << 'EOFCOMPOSE'
cat > ~/test-ia-local/caso-1-v2-e3/docker-compose.yml << 'EOFDOCKER'
name: caso1v2

x-app-env: &app-env
  RABBIT_URL: amqp://guest:guest@rabbitmq:5672/
  DATA_DIR: /data/e3
  VLLM_URL: http://vllm:8000/v1
  VLLM_VL_URL: http://vllm-vl:8000/v1
  VLLM_VL_MODEL: Qwen/Qwen2.5-VL-7B-Instruct
  OCR_ENGINE: hybrid
  OCR_SCALE: "2.0"
  OCR_SKIP_ROIS: "1"
  NLP_MODEL: Qwen/Qwen2.5-7B-Instruct-AWQ
  NLP_ENGINE: vllm

services:
  rabbitmq:
    image: rabbitmq:3.13-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 10s
      timeout: 5s
      retries: 8
    restart: unless-stopped

  vllm:
    profiles: ["gpu"]
    image: vllm/vllm-openai:latest
    runtime: nvidia
    ipc: host
    ports:
      - "8000:8000"
    environment:
      NVIDIA_VISIBLE_DEVICES: "1"
      HF_HOME: /root/.cache/huggingface
    volumes:
      - /data/hf-cache:/root/.cache/huggingface
    command:
      - --model
      - Qwen/Qwen2.5-7B-Instruct-AWQ
      - --gpu-memory-utilization
      - "0.40"
      - --max-model-len
      - "8192"
      - --max-num-seqs
      - "32"
      - --enforce-eager
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["1"]
              capabilities: [gpu]

  vllm-vl:
    profiles: ["gpu"]
    image: vllm/vllm-openai:latest
    runtime: nvidia
    ipc: host
    ports:
      - "8001:8000"
    environment:
      NVIDIA_VISIBLE_DEVICES: "0"
      HF_HOME: /root/.cache/huggingface
    volumes:
      - /data/hf-cache:/root/.cache/huggingface
    command:
      - --model
      - Qwen/Qwen2.5-VL-7B-Instruct
      - --gpu-memory-utilization
      - "0.90"
      - --max-model-len
      - "4096"
      - --enforce-eager
      - --max-num-seqs
      - "8"
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["0"]
              capabilities: [gpu]

volumes:
  rabbit-data:
EOFDOCKER

echo "✅ docker-compose.yml generado"
EOFCOMPOSE

echo ""
echo -e "${GREEN}[5/8] Montando /data (instance store)...${NC}"
ssh -i "$KEY" ubuntu@$SERVER_IP << 'EOF'
# Montar instance store en /data si no está montado
if ! mountpoint -q /data; then
    sudo mkfs -t ext4 /dev/nvme1n1 2>/dev/null || true
    sudo mkdir -p /data
    sudo mount /dev/nvme1n1 /data
    sudo chown -R ubuntu:ubuntu /data
fi
mkdir -p /data/{e3,hf-cache}
echo "✅ /data montado"
EOF

echo ""
echo -e "${GREEN}[6/8] Descargando gold desde S3...${NC}"
ssh -i "$KEY" ubuntu@$SERVER_IP << 'EOF'
aws s3 sync s3://forme3/E3/gold/ /data/e3/gold/ --region us-east-2 --quiet
aws s3 sync s3://forme3/E3/front/ /data/e3/front/ --region us-east-2 --exclude "*" --include "6*.tif" --quiet
echo "✅ Gold descargado ($(ls /data/e3/gold/*.json 2>/dev/null | wc -l) archivos)"
EOF

echo ""
echo -e "${GREEN}[7/8] Levantando servicios Docker...${NC}"
ssh -i "$KEY" ubuntu@$SERVER_IP << 'EOF'
cd ~/test-ia-local/caso-1-v2-e3
sudo docker compose --profile gpu up -d
echo "✅ Servicios iniciando..."
EOF

echo ""
echo -e "${GREEN}[8/8] Esperando que modelos carguen...${NC}"
echo -e "${YELLOW}Esto puede tardar 3-5 minutos (descarga + carga VRAM)${NC}"

ssh -i "$KEY" ubuntu@$SERVER_IP << 'EOF'
cd ~/test-ia-local/caso-1-v2-e3

# Esperar VLM (puerto 8001)
echo -n "  → VL-7B (GPU 0): "
for i in {1..60}; do
    if curl -s http://localhost:8001/v1/models >/dev/null 2>&1; then
        echo "✅ Listo"
        break
    fi
    sleep 5
    echo -n "."
done

# Esperar NLP (puerto 8000)
echo -n "  → NLP-7B (GPU 1): "
for i in {1..60}; do
    if curl -s http://localhost:8000/v1/models >/dev/null 2>&1; then
        echo "✅ Listo"
        break
    fi
    sleep 5
    echo -n "."
done

# Verificar VRAM
echo ""
echo "VRAM utilizada:"
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv
EOF

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ✅ Deploy completado                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Siguiente paso:${NC}"
echo "  1. Verificar visor: http://$SERVER_IP:8080"
echo "  2. Probar con 1 doc: curl -X POST http://$SERVER_IP:8080/procesar ..."
echo "  3. Load test: ssh y ejecutar test_mejoras.sh"
